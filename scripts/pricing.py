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
