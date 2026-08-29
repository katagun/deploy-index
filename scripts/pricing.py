#!/usr/bin/env python3
"""Pricing dataset: loading, validation, and reference-workload computation.

Observation rows are append-only and dated. Nothing here mutates the catalog,
and no computed figure is published without the rows it was derived from.
"""

from __future__ import annotations

import json
import math
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

        observed = None
        try:
            observed = date.fromisoformat(row["observed_on"])
            if observed > today:
                errors.append(f"{prefix}: observed_on cannot be in the future")
        except (TypeError, ValueError):
            errors.append(f"{prefix}: observed_on must be an ISO date")

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
    try:
        observed = date.fromisoformat(row["observed_on"])
    except (KeyError, TypeError, ValueError):
        return True
    return observed < today - timedelta(days=max_age_days)


def _latest_by_metric(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        current = latest.get(row["metric"])
        if current is None or row["observed_on"] > current["observed_on"]:
            latest[row["metric"]] = row
    return latest


def compute_workload(workload: dict[str, Any], rows: list[dict[str, Any]], today: date) -> dict[str, Any]:
    """Compute a workload's monthly cost from one provider's rows.

    Plans are never mixed: each plan is costed independently and only plans with
    a fresh row for every required line item qualify. A missing required metric
    yields insufficient_data rather than a partial — and therefore misleadingly
    low — total.
    """
    fresh = [row for row in rows if not is_stale(row, today)]
    by_plan: dict[str, list[dict[str, Any]]] = {}
    for row in fresh:
        by_plan.setdefault(row["plan"], []).append(row)

    best: dict[str, Any] | None = None
    missing_overall: set[str] = set()

    for plan, plan_rows in sorted(by_plan.items()):
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
        candidate = {"status": "ok", "plan": plan, "monthly_usd": round(total, 2), "sources": sources}
        if best is None or candidate["monthly_usd"] < best["monthly_usd"]:
            best = candidate

    if best is not None:
        return best
    required = [item["metric"] for item in workload["line_items"] if not item.get("optional")]
    return {
        "status": "insufficient_data",
        "missing_metrics": sorted(missing_overall or set(required)),
    }


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
    errors = validate_observations(rows, load_metrics(), load_catalog())
    if errors:
        print(f"Pricing validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    payload = build_pricing_catalog()
    stale = sum(1 for row in rows if is_stale(row, date.today()))
    print(f"Pricing valid: {len(rows)} rows across {len(payload['providers'])} providers ({stale} stale)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
