#!/usr/bin/env python3
"""Pricing dataset: loading, validation, and reference-workload computation.

Observation rows are append-only and dated. Nothing here mutates the catalog,
and no computed figure is published without the rows it was derived from.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from catalog import ROOT

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


def validate_observations(
    rows: list[dict[str, Any]],
    metrics: dict[str, Any],
    catalog: dict[str, Any],
    today: date | None = None,
) -> list[str]:
    """Validate pricing rows against the vocabulary and the canonical catalog."""
    today = today or date.today()
    errors: list[str] = []
    known_metrics = set(metrics["metrics"])
    known_slugs = {item["slug"] for item in catalog["providers"]}
    seen: set[tuple] = set()

    for index, row in enumerate(rows):
        prefix = f"rows[{index}]"
        missing = REQUIRED_ROW_FIELDS - row.keys()
        if missing:
            errors.append(f"{prefix}: missing fields {sorted(missing)}")
            continue
        if row["metric"] not in known_metrics:
            errors.append(f"{prefix}: unknown metric {row['metric']!r}")
        if row["provider_slug"] not in known_slugs:
            errors.append(f"{prefix}: unknown provider_slug {row['provider_slug']!r}")
        if row["currency"] not in CURRENCIES:
            errors.append(f"{prefix}: unsupported currency {row['currency']!r}")
        value = row["value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            errors.append(f"{prefix}: value must be a non-negative number")
        allowance = row["included_allowance"]
        if isinstance(allowance, bool) or not isinstance(allowance, (int, float)) or allowance < 0:
            errors.append(f"{prefix}: included_allowance must be a non-negative number")
        if not isinstance(row["source_url"], str) or not row["source_url"].startswith("https://"):
            errors.append(f"{prefix}: source_url must be https")
        if row["confidence"] not in ROW_CONFIDENCE:
            errors.append(f"{prefix}: invalid confidence {row['confidence']!r}")
        try:
            observed = date.fromisoformat(row["observed_on"])
            if observed > today:
                errors.append(f"{prefix}: observed_on cannot be in the future")
        except (TypeError, ValueError):
            errors.append(f"{prefix}: observed_on must be an ISO date")
        identity = (row["provider_slug"], row["plan"], row["metric"], row["region"], row["observed_on"])
        if identity in seen:
            errors.append(f"{prefix}: duplicate observation for {identity}")
        seen.add(identity)

    return errors
