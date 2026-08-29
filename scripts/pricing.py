#!/usr/bin/env python3
"""Pricing dataset: loading, validation, and reference-workload computation.

Observation rows are append-only and dated. Nothing here mutates the catalog,
and no computed figure is published without the rows it was derived from.
"""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from catalog import ROOT, load_catalog, normalize_domain

PRICING_DIR = ROOT / "pricing"
METRICS_PATH = PRICING_DIR / "metrics.json"
WORKLOADS_PATH = PRICING_DIR / "workloads.json"
OBSERVATIONS_DIR = PRICING_DIR / "observations"
MAX_AGE_DAYS = 90
CURRENCIES = {"USD"}

# `date.fromisoformat` also accepts the basic form ("20260801"), which sorts
# above every extended-form date as a string and would let a superseded row
# masquerade as the current one. Only the extended form is a valid row date.
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_metrics(path: Path = METRICS_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_workloads(path: Path = WORKLOADS_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_observations(directory: Path = OBSERVATIONS_DIR) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(payload.get("rows", []))
    return sorted(rows, key=lambda row: (row.get("provider_slug", ""), row.get("metric", ""), row.get("observed_on", "")))


REQUIRED_ROW_FIELDS = {
    "provider_slug", "plan", "metric", "value", "currency", "included_allowance",
    "region", "observed_on", "source_url", "confidence", "note",
}
ROW_CONFIDENCE = {"low", "medium", "high"}
REGIONS = {"us-east"}

# A reference workload may only publish an assumption it actually prices.
# Every assumption key maps to the metric that makes it a cost, and the
# workload must carry a line item for that metric. Declaring `vcpu` while
# pricing no compute metric is how a workload silently misdescribes itself.
ASSUMPTION_METRICS = {
    "storage_gib": "storage_gib_month",
    "egress_gib_month": "egress_gib",
    "backup_gib": "backup_gib_month",
    "vcpu": "compute_vcpu_hour",
    "compute_units": "compute_cu_hour",
    "memory_gib": "memory_gib_hour",
    "read_ops_million": "read_ops_million",
    "write_ops_million": "write_ops_million",
}


def parse_observed_on(value: Any) -> date | None:
    """Parse a row date, accepting only the extended ISO form YYYY-MM-DD."""
    if not isinstance(value, str) or not ISO_DATE_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _in_set(value: Any, allowed: set) -> bool:
    """Membership test that tolerates unhashable values from untrusted input."""
    try:
        return value in allowed
    except TypeError:
        return False


def validate_observations(
    rows: list[dict[str, Any]],
    metrics: dict[str, Any],
    catalog: dict[str, Any],
    today: date | None = None,
) -> list[str]:
    """Validate pricing rows against the vocabulary and the canonical catalog."""
    today = today or date.today()
    errors: list[str] = []

    if not isinstance(rows, list):
        return ["rows must be a list"]

    known_metrics = set(metrics["metrics"])
    known_slugs = {item["slug"] for item in catalog["providers"]}
    seen: set[tuple] = set()

    for index, row in enumerate(rows):
        prefix = f"rows[{index}]"

        if not isinstance(row, dict):
            errors.append(f"{prefix}: row must be a dict")
            continue

        missing = REQUIRED_ROW_FIELDS - row.keys()
        if missing:
            errors.append(f"{prefix}: missing fields {sorted(missing)}")
            continue
        if not _in_set(row["metric"], known_metrics):
            errors.append(f"{prefix}: unknown metric {row['metric']!r}")
        if not _in_set(row["provider_slug"], known_slugs):
            errors.append(f"{prefix}: unknown provider_slug {row['provider_slug']!r}")
        if not _in_set(row["currency"], CURRENCIES):
            errors.append(f"{prefix}: unsupported currency {row['currency']!r}")
        if not _in_set(row["region"], REGIONS):
            errors.append(f"{prefix}: unsupported region {row['region']!r}")
        value = row["value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            errors.append(f"{prefix}: value must be a non-negative number")
        allowance = row["included_allowance"]
        if isinstance(allowance, bool) or not isinstance(allowance, (int, float)) or not math.isfinite(allowance) or allowance < 0:
            errors.append(f"{prefix}: included_allowance must be a non-negative number")
        if not isinstance(row["source_url"], str) or not row["source_url"].startswith("https://") or not normalize_domain(row["source_url"]):
            errors.append(f"{prefix}: source_url must be https")
        if not _in_set(row["confidence"], ROW_CONFIDENCE):
            errors.append(f"{prefix}: invalid confidence {row['confidence']!r}")
        for field in ("plan", "note"):
            if not isinstance(row[field], str) or not row[field].strip():
                errors.append(f"{prefix}: {field} must be a non-empty string")

        observed = parse_observed_on(row["observed_on"])
        if observed is None:
            errors.append(f"{prefix}: observed_on must be an ISO date of the form YYYY-MM-DD")
        elif observed > today:
            errors.append(f"{prefix}: observed_on cannot be in the future")

        if observed is not None:
            try:
                identity = (row["provider_slug"], row["plan"], row["metric"], row["region"], observed)
                if identity in seen:
                    errors.append(f"{prefix}: duplicate observation for {identity}")
                seen.add(identity)
            except TypeError:
                errors.append(f"{prefix}: row identity contains unhashable components")

    return errors


def is_stale(row: dict[str, Any], today: date, max_age_days: int = MAX_AGE_DAYS) -> bool:
    """A row is stale once it is older than the freshness threshold."""
    observed = parse_observed_on(row.get("observed_on"))
    if observed is None:
        return True
    return observed < today - timedelta(days=max_age_days)


def _latest_by_metric(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Latest row per metric, compared as dates.

    String comparison would order the basic ISO form above every extended-form
    date and publish a superseded price as current; `parse_observed_on` rejects
    that form outright and this compares the parsed dates.
    """
    latest: dict[str, dict[str, Any]] = {}
    latest_on: dict[str, date] = {}
    for row in rows:
        observed = parse_observed_on(row.get("observed_on"))
        if observed is None:
            continue
        metric = row["metric"]
        if metric not in latest or observed > latest_on[metric]:
            latest[metric] = row
            latest_on[metric] = observed
    return latest


def compute_workload(workload: dict[str, Any], rows: list[dict[str, Any]], today: date) -> dict[str, Any]:
    """Compute a workload's monthly cost from one provider's rows.

    Plans are never mixed, and neither are currencies or regions: each
    (currency, region, plan) group is costed independently and only groups with
    a fresh row for every required line item qualify. A missing required metric
    yields insufficient_data rather than a partial — and therefore misleadingly
    low — total.
    """
    fresh = [row for row in rows if not is_stale(row, today)]
    by_group: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in fresh:
        by_group.setdefault((row["currency"], row["region"], row["plan"]), []).append(row)

    best: dict[str, Any] | None = None
    missing_overall: set[str] = set()

    for (currency, region, plan), plan_rows in sorted(by_group.items()):
        # The published field is `monthly_usd`; a non-USD group is costed in its
        # own currency and must never be compared against a USD total.
        if currency != "USD":
            continue
        latest = _latest_by_metric(plan_rows)
        total = 0.0
        sources: list[dict[str, Any]] = []
        missing: list[str] = []
        for item in workload["line_items"]:
            row = latest.get(item["metric"])
            if row is None:
                if not item.get("optional"):
                    missing.append(item["metric"])
                continue
            billable = max(0.0, float(item["quantity"]) - float(row["included_allowance"]))
            total += billable * float(row["value"])
            sources.append({
                "metric": row["metric"],
                "value": row["value"],
                "observed_on": row["observed_on"],
                "source_url": row["source_url"],
            })
        if missing:
            missing_overall.update(missing)
            continue
        # A total that overflowed to inf (or is otherwise not a real number) is
        # not a price. json.dumps would emit the bare token `Infinity`, which is
        # invalid JSON, and no browser or API consumer could read the payload.
        if not math.isfinite(total):
            missing_overall.update(item["metric"] for item in workload["line_items"] if not item.get("optional"))
            continue
        candidate = {
            "status": "ok",
            "plan": plan,
            "currency": currency,
            "region": region,
            "monthly_usd": round(total, 2),
            "sources": sources,
        }
        if best is None or candidate["monthly_usd"] < best["monthly_usd"]:
            best = candidate

    # How many distinct plans had any fresh row at all. A total drawn from a
    # single plan is a coverage artifact, not the outcome of a comparison, and
    # every surface that shows the number has to be able to say so.
    plans_considered = len({plan for _, _, plan in by_group})

    if best is not None:
        best["plans_considered"] = plans_considered
        return best
    required = [item["metric"] for item in workload["line_items"] if not item.get("optional")]
    return {
        "status": "insufficient_data",
        "plans_considered": plans_considered,
        "missing_metrics": sorted(missing_overall or set(required)),
    }


def validate_workloads(workloads: list[dict[str, Any]], metrics: dict[str, Any]) -> list[str]:
    """Validate reference workload definitions.

    The load-bearing check is that a workload may not publish an assumption it
    does not price. `/pricing/` renders `assumptions` as a description of what
    the figure covers, so an assumption without a matching line item (vCPU and
    memory declared while only storage and egress are priced) silently
    misdescribes every total in the column.
    """
    errors: list[str] = []
    if not isinstance(workloads, list) or not workloads:
        return ["workloads must be a non-empty list"]

    known_metrics = set(metrics["metrics"])
    seen_ids: set[str] = set()

    for index, workload in enumerate(workloads):
        prefix = f"workloads[{index}]"
        if not isinstance(workload, dict):
            errors.append(f"{prefix}: workload must be a dict")
            continue
        for field in ("id", "label"):
            if not isinstance(workload.get(field), str) or not workload[field].strip():
                errors.append(f"{prefix}: {field} must be a non-empty string")
        workload_id = workload.get("id")
        if isinstance(workload_id, str):
            if workload_id in seen_ids:
                errors.append(f"{prefix}: duplicate workload id {workload_id!r}")
            seen_ids.add(workload_id)
        if not workload.get("caveats"):
            errors.append(f"{prefix}: at least one caveat is required")

        line_items = workload.get("line_items")
        if not isinstance(line_items, list) or not line_items:
            errors.append(f"{prefix}: line_items must be a non-empty list")
            continue
        priced: set[str] = set()
        for item_index, item in enumerate(line_items):
            item_prefix = f"{prefix}.line_items[{item_index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_prefix}: line item must be a dict")
                continue
            metric = item.get("metric")
            if not _in_set(metric, known_metrics):
                errors.append(f"{item_prefix}: unknown metric {metric!r}")
                continue
            quantity = item.get("quantity")
            if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not math.isfinite(quantity) or quantity <= 0:
                errors.append(f"{item_prefix}: quantity must be a positive number")
            priced.add(metric)

        assumptions = workload.get("assumptions", {})
        if not isinstance(assumptions, dict):
            errors.append(f"{prefix}: assumptions must be an object")
            continue
        for key in sorted(assumptions):
            metric = ASSUMPTION_METRICS.get(key)
            if metric is None:
                errors.append(
                    f"{prefix}: assumption {key!r} does not name a priced quantity "
                    f"(add it to ASSUMPTION_METRICS or remove it)"
                )
            elif metric not in priced:
                errors.append(
                    f"{prefix}: assumption {key!r} describes metric {metric!r}, "
                    f"which this workload has no line item for"
                )

    return errors


DISCLAIMER = (
    "Prices are dated observations from official pricing pages, not quotes. "
    "Figures are computed from published reference workloads and exclude support plans, "
    "committed-use discounts, and negotiated pricing. Verify current pricing with the provider."
)


def build_pricing_catalog(today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    catalog = load_catalog()
    metrics = load_metrics()
    workloads = load_workloads()["workloads"]
    rows = load_observations()
    by_slug = {item["slug"]: item for item in catalog["providers"]}

    providers = []
    for slug in sorted({row["provider_slug"] for row in rows}):
        entry = by_slug.get(slug)
        if entry is None:
            continue
        provider_rows = [row for row in rows if row["provider_slug"] == slug]
        providers.append({
            "slug": slug,
            "name": entry["name"],
            "detail_path": f"/providers/{slug}/",
            "results": {w["id"]: compute_workload(w, provider_rows, today) for w in workloads},
            "rows": provider_rows,
        })

    return {
        "schema_version": 1,
        "generated_on": today.isoformat(),
        "max_age_days": MAX_AGE_DAYS,
        "disclaimer": DISCLAIMER,
        "metrics": metrics["metrics"],
        "workloads": workloads,
        "providers": providers,
    }


def main() -> int:
    rows = load_observations()
    metrics = load_metrics()
    workloads = load_workloads()["workloads"]
    errors = validate_workloads(workloads, metrics)
    errors += validate_observations(rows, metrics, load_catalog())
    if errors:
        print(f"Pricing validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    payload = build_pricing_catalog()
    stale = sum(1 for row in rows if is_stale(row, date.today()))
    print(
        f"Pricing valid: {len(rows)} rows across {len(payload['providers'])} providers "
        f"({stale} stale), {len(workloads)} reference workloads"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
