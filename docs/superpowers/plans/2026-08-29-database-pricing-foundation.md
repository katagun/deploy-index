# Database Pricing Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a validated, auditable database pricing dataset with dated observation rows and computed reference workloads, published as JSON and rendered at `/pricing/`.

**Architecture:** A separate `pricing/` data plane inside this repository, joined to the catalog only by `provider_slug`. Observation rows are append-only and dated; a controlled metric vocabulary makes rows comparable; declarative reference workloads with explicit line-item quantities are computed from rows by `scripts/pricing.py`. Missing data yields `insufficient_data`, never a partial sum.

**Tech Stack:** Python 3.11+ standard library only, no third-party dependencies. Plain HTML/CSS/JS for display, matching the existing static build. `unittest` for tests.

**Spec:** `docs/superpowers/specs/2026-08-29-database-pricing-design.md`

**Out of scope for this plan:** the model-assisted research scan and its review renderer (spec rollout steps 5–6). That is an independent subsystem and gets its own plan once this data model is proven with hand-entered rows.

## Global Constraints

- Python 3.11 or newer, standard library only — no third-party packages, ever.
- All prices in v1 are `USD`, region `us-east`. The `currency` and `region` fields exist on every row regardless.
- Observation rows are append-only. A price change is a new row with a later `observed_on` — never an edit to an existing row.
- Rows older than 90 days are stale: excluded from computed workloads, retained in the dataset.
- `insufficient_data` always beats a partial sum.
- Prices never feed recommender scoring in this plan. `cost_floor` stays a qualitative 1–5 band.
- Every source URL must be HTTPS and point at an official provider pricing page.
- Run `make test` before claiming any task complete.
- Never hand-edit `dist/` — it is generated.

---

### Task 1: Catalog prerequisites — database faceting and the AWS database record

The pricing dataset joins on catalog slugs, so the catalog must first represent database hosting correctly. Supabase and Firebase are filed only as `backend-platform` and never appear under database discovery; the catalog has no AWS database product at all.

**Files:**
- Modify: `catalog/providers.json`
- Test: `tests/test_catalog.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: catalog slugs `supabase`, `firebase`, `planetscale`, `amazon-rds` all carrying `database-platform` in their `categories`. Later tasks reference these slugs in pricing rows.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_catalog.py` inside `CatalogTests`:

```python
    def test_database_platforms_are_discoverable_by_category(self) -> None:
        by_slug = {item["slug"]: item for item in self.catalog["providers"]}
        for slug in ("supabase", "firebase", "planetscale", "amazon-rds"):
            self.assertIn(slug, by_slug, f"{slug} must exist in the catalog")
            self.assertIn(
                "database-platform",
                by_slug[slug]["categories"],
                f"{slug} must be discoverable under database-platform",
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_catalog.CatalogTests.test_database_platforms_are_discoverable_by_category -v`
Expected: FAIL — `amazon-rds must exist in the catalog`.

- [ ] **Step 3: Add the AWS database record and re-facet the three existing entries**

Run this script once:

```python
python3 - <<'PY'
import json

path = "catalog/providers.json"
catalog = json.load(open(path, encoding="utf-8"))
by = {x["slug"]: x for x in catalog["providers"]}

# 1. Re-facet existing entries so database discovery finds them.
for slug in ("supabase", "firebase", "planetscale"):
    item = by[slug]
    if "database-platform" not in item["categories"]:
        item["categories"] = [*item["categories"], "database-platform"]
        item["change_note"] = "Added database-platform facet so the entry is discoverable under database hosting."

# 2. Add the missing AWS managed-database product.
catalog["providers"].append({
    "slug": "amazon-rds",
    "name": "Amazon RDS",
    "url": "https://aws.amazon.com/rds/",
    "entity_type": "product",
    "parent_slug": "aws",
    "primary_category": "database-platform",
    "categories": ["database-platform"],
    "capabilities": ["databases", "persistent-storage", "private-networking", "multi-region"],
    "operating_models": ["managed-cloud"],
    "era": "established",
    "status": "active",
    "availability": "general",
    "open_source": False,
    "launch_year": 2009,
    "featured": False,
    "summary": "Amazon's managed relational database service, offering PostgreSQL, MySQL, MariaDB, Oracle, and SQL Server engines with managed backups, replicas, and failover.",
    "best_for": "Teams standardizing on AWS that want managed relational databases with mature operational tooling and regional breadth.",
    "source_urls": ["https://aws.amazon.com/rds/", "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html"],
    "last_verified": None,
    "confidence": "seed",
    "change_note": "Added to provide a hyperscaler baseline for database comparison; awaiting source-by-source verification.",
})

catalog["providers"].sort(key=lambda item: (item["name"].casefold(), item["slug"]))
with open(path, "w", encoding="utf-8") as handle:
    json.dump(catalog, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
print("catalog updated")
PY
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `make test`
Expected: PASS. Entry count rises from 265 to 266; `check_site` reports one more provider page and sitemap entry.

- [ ] **Step 5: Commit**

```bash
git add catalog/providers.json tests/test_catalog.py
git commit -m "catalog: facet database platforms and add Amazon RDS"
```

---

### Task 2: Pricing vocabulary, workload definitions, and dataset loader

**Files:**
- Create: `pricing/metrics.json`
- Create: `pricing/workloads.json`
- Create: `pricing/observations/2026-Q3.json`
- Create: `scripts/pricing.py`
- Test: `tests/test_pricing.py`

**Interfaces:**
- Consumes: catalog slugs from Task 1; `catalog.ROOT` and `catalog.load_catalog` from `scripts/catalog.py`.
- Produces:
  - `PRICING_DIR: Path`, `MAX_AGE_DAYS: int = 90`
  - `load_metrics(path: Path = ...) -> dict[str, Any]`
  - `load_workloads(path: Path = ...) -> dict[str, Any]`
  - `load_observations(directory: Path = ...) -> list[dict[str, Any]]` — concatenated `rows` from every quarter file, sorted by `(provider_slug, metric, observed_on)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pricing.py`:

```python
from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pricing import load_metrics, load_observations, load_workloads  # noqa: E402


class PricingDatasetTests(unittest.TestCase):
    def test_metric_vocabulary_defines_unit_and_description(self) -> None:
        metrics = load_metrics()["metrics"]
        self.assertIn("storage_gib_month", metrics)
        self.assertIn("plan_base_month", metrics)
        for name, definition in metrics.items():
            self.assertTrue(definition.get("unit"), f"{name} needs a unit")
            self.assertTrue(definition.get("description"), f"{name} needs a description")

    def test_workloads_declare_explicit_line_items(self) -> None:
        workloads = load_workloads()["workloads"]
        self.assertTrue(workloads)
        metrics = load_metrics()["metrics"]
        for workload in workloads:
            self.assertTrue(workload["id"])
            self.assertTrue(workload["caveats"])
            self.assertTrue(workload["line_items"])
            for item in workload["line_items"]:
                self.assertIn(item["metric"], metrics)
                self.assertGreater(item["quantity"], 0)

    def test_observations_load_from_quarter_files(self) -> None:
        rows = load_observations()
        self.assertIsInstance(rows, list)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_pricing -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pricing'`.

- [ ] **Step 3: Create the data files**

`pricing/metrics.json`:

```json
{
  "schema_version": 1,
  "metrics": {
    "plan_base_month": {"unit": "USD per month", "description": "Fixed recurring plan or cluster fee, independent of usage."},
    "compute_vcpu_hour": {"unit": "USD per vCPU-hour", "description": "Charge per virtual CPU per hour of running compute."},
    "compute_cu_hour": {"unit": "USD per compute-unit-hour", "description": "Charge per provider-defined compute unit per hour, where vCPU and memory are bundled."},
    "memory_gib_hour": {"unit": "USD per GiB-hour", "description": "Charge per gibibyte of memory per hour, where memory is billed separately from vCPU."},
    "storage_gib_month": {"unit": "USD per GiB-month", "description": "Charge per gibibyte of persistent database storage per month."},
    "egress_gib": {"unit": "USD per GiB", "description": "Charge per gibibyte of outbound data transfer to the public internet."},
    "read_ops_million": {"unit": "USD per million reads", "description": "Charge per million read operations, for providers billing by operation."},
    "write_ops_million": {"unit": "USD per million writes", "description": "Charge per million write operations, for providers billing by operation."},
    "backup_gib_month": {"unit": "USD per GiB-month", "description": "Charge per gibibyte of backup storage per month beyond any included retention."}
  }
}
```

`pricing/workloads.json` — note that `line_items` carries explicit quantities so no hidden derivation happens at compute time, while `assumptions` is human-facing documentation:

```json
{
  "schema_version": 1,
  "workloads": [
    {
      "id": "small-prod-postgres",
      "label": "Small production Postgres",
      "assumptions": {"vcpu": 2, "memory_gib": 8, "storage_gib": 100, "egress_gib_month": 50, "hours_month": 730},
      "line_items": [
        {"metric": "plan_base_month", "quantity": 1, "optional": true},
        {"metric": "storage_gib_month", "quantity": 100},
        {"metric": "egress_gib", "quantity": 50}
      ],
      "caveats": [
        "Excludes support plans, committed-use discounts, and negotiated enterprise pricing.",
        "Excludes backups beyond default retention and cross-region transfer.",
        "Compute is compared through each provider's own plan fee where compute is bundled into the plan."
      ]
    },
    {
      "id": "hobby-postgres",
      "label": "Hobby Postgres",
      "assumptions": {"vcpu": 1, "memory_gib": 1, "storage_gib": 10, "egress_gib_month": 5, "hours_month": 730},
      "line_items": [
        {"metric": "plan_base_month", "quantity": 1, "optional": true},
        {"metric": "storage_gib_month", "quantity": 10},
        {"metric": "egress_gib", "quantity": 5}
      ],
      "caveats": [
        "Free tiers often cover this workload entirely; a zero total means the plan's included allowances absorb it.",
        "Excludes support plans and committed-use discounts."
      ]
    }
  ]
}
```

`pricing/observations/2026-Q3.json` — starts empty; Task 5 fills it:

```json
{
  "schema_version": 1,
  "rows": []
}
```

- [ ] **Step 4: Create the loader module**

Create `scripts/pricing.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_pricing -v`
Expected: PASS, 3 tests.

- [ ] **Step 6: Commit**

```bash
git add pricing/ scripts/pricing.py tests/test_pricing.py
git commit -m "pricing: metric vocabulary, reference workloads, and dataset loader"
```

---

### Task 3: Observation validation

Rows come from untrusted research later, so validation is the security boundary. Negative tests define it.

**Files:**
- Modify: `scripts/pricing.py`
- Test: `tests/test_pricing.py`

**Interfaces:**
- Consumes: `load_metrics`, `load_observations` from Task 2; `load_catalog` from `scripts/catalog.py`.
- Produces: `validate_observations(rows: list[dict], metrics: dict, catalog: dict, today: date | None = None) -> list[str]` — returns human-readable error strings, empty when valid.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pricing.py`:

```python
from datetime import date, timedelta  # noqa: E402

from catalog import load_catalog  # noqa: E402
from pricing import validate_observations  # noqa: E402


def make_row(**overrides) -> dict:
    row = {
        "provider_slug": "neon",
        "plan": "launch",
        "metric": "storage_gib_month",
        "value": 0.35,
        "currency": "USD",
        "included_allowance": 10,
        "region": "us-east",
        "observed_on": "2026-08-01",
        "source_url": "https://neon.com/pricing",
        "confidence": "high",
        "note": "Storage billed per GiB-month.",
    }
    row.update(overrides)
    return row


class ObservationValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.metrics = load_metrics()

    def assert_error(self, row: dict, needle: str) -> None:
        errors = validate_observations([row], self.metrics, self.catalog, today=date(2026, 8, 29))
        self.assertTrue(any(needle in error for error in errors), f"expected {needle!r} in {errors}")

    def test_valid_row_produces_no_errors(self) -> None:
        errors = validate_observations([make_row()], self.metrics, self.catalog, today=date(2026, 8, 29))
        self.assertEqual(errors, [])

    def test_unknown_metric_is_rejected(self) -> None:
        self.assert_error(make_row(metric="cost_per_widget"), "unknown metric")

    def test_slug_absent_from_catalog_is_rejected(self) -> None:
        self.assert_error(make_row(provider_slug="not-a-real-host"), "unknown provider_slug")

    def test_future_observation_date_is_rejected(self) -> None:
        self.assert_error(make_row(observed_on="2027-01-01"), "cannot be in the future")

    def test_non_https_source_is_rejected(self) -> None:
        self.assert_error(make_row(source_url="http://neon.com/pricing"), "source_url must be https")

    def test_unsupported_currency_is_rejected(self) -> None:
        self.assert_error(make_row(currency="EUR"), "unsupported currency")

    def test_negative_value_is_rejected(self) -> None:
        self.assert_error(make_row(value=-1), "value must be a non-negative number")

    def test_duplicate_row_is_rejected(self) -> None:
        row = make_row()
        errors = validate_observations([row, dict(row)], self.metrics, self.catalog, today=date(2026, 8, 29))
        self.assertTrue(any("duplicate observation" in error for error in errors), errors)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_pricing -v`
Expected: FAIL — `ImportError: cannot import name 'validate_observations'`.

- [ ] **Step 3: Implement the validator**

Append to `scripts/pricing.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_pricing -v`
Expected: PASS, 11 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/pricing.py tests/test_pricing.py
git commit -m "pricing: deterministic observation validation"
```

---

### Task 4: Reference-workload computation

**Files:**
- Modify: `scripts/pricing.py`
- Test: `tests/test_pricing.py`

**Interfaces:**
- Consumes: `load_observations`, `load_workloads`, `MAX_AGE_DAYS` from Task 2.
- Produces:
  - `is_stale(row: dict, today: date, max_age_days: int = MAX_AGE_DAYS) -> bool`
  - `compute_workload(workload: dict, rows: list[dict], today: date) -> dict` — returns `{"status": "ok", "monthly_usd": float, "plan": str, "sources": [...]}` or `{"status": "insufficient_data", "missing_metrics": [...]}`. `sources` entries are `{"metric", "value", "observed_on", "source_url"}`.

Computation rules: rows are grouped by `(plan, metric)` so tiers are never mixed; for each candidate plan every non-optional line item must have a fresh row, and billable quantity is `max(0, quantity - included_allowance)`. When several plans qualify, the cheapest complete plan is reported.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pricing.py`:

```python
from pricing import compute_workload, is_stale  # noqa: E402


SMALL_WORKLOAD = {
    "id": "test-workload",
    "label": "Test workload",
    "line_items": [
        {"metric": "plan_base_month", "quantity": 1, "optional": True},
        {"metric": "storage_gib_month", "quantity": 100},
        {"metric": "egress_gib", "quantity": 50},
    ],
    "caveats": ["test"],
}
TODAY = date(2026, 8, 29)


class WorkloadComputationTests(unittest.TestCase):
    def test_complete_plan_computes_expected_total(self) -> None:
        rows = [
            make_row(metric="plan_base_month", value=19.0, included_allowance=0),
            make_row(metric="storage_gib_month", value=0.35, included_allowance=10),
            make_row(metric="egress_gib", value=0.09, included_allowance=0),
        ]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        # 19.00 + (100 - 10) * 0.35 + 50 * 0.09 = 19.00 + 31.50 + 4.50
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["monthly_usd"], 55.00, places=2)
        self.assertEqual(len(result["sources"]), 3)

    def test_missing_required_metric_yields_insufficient_data(self) -> None:
        rows = [make_row(metric="storage_gib_month", value=0.35, included_allowance=0)]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIn("egress_gib", result["missing_metrics"])

    def test_optional_line_item_absence_contributes_zero(self) -> None:
        rows = [
            make_row(metric="storage_gib_month", value=0.10, included_allowance=0),
            make_row(metric="egress_gib", value=0.0, included_allowance=0),
        ]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["monthly_usd"], 10.00, places=2)

    def test_stale_rows_are_excluded_from_computation(self) -> None:
        old = (TODAY - timedelta(days=120)).isoformat()
        rows = [
            make_row(metric="storage_gib_month", value=0.35, included_allowance=0, observed_on=old),
            make_row(metric="egress_gib", value=0.09, included_allowance=0),
        ]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIn("storage_gib_month", result["missing_metrics"])

    def test_plans_are_never_mixed(self) -> None:
        rows = [
            make_row(plan="free", metric="storage_gib_month", value=0.0, included_allowance=100),
            make_row(plan="pro", metric="egress_gib", value=0.09, included_allowance=0),
        ]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")

    def test_cheapest_complete_plan_wins(self) -> None:
        rows = [
            make_row(plan="cheap", metric="storage_gib_month", value=0.10, included_allowance=0),
            make_row(plan="cheap", metric="egress_gib", value=0.0, included_allowance=0),
            make_row(plan="pricey", metric="storage_gib_month", value=0.50, included_allowance=0),
            make_row(plan="pricey", metric="egress_gib", value=0.0, included_allowance=0),
        ]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["plan"], "cheap")
        self.assertAlmostEqual(result["monthly_usd"], 10.00, places=2)

    def test_is_stale_respects_the_threshold(self) -> None:
        self.assertFalse(is_stale(make_row(observed_on=TODAY.isoformat()), TODAY))
        self.assertFalse(is_stale(make_row(observed_on=(TODAY - timedelta(days=89)).isoformat()), TODAY))
        self.assertTrue(is_stale(make_row(observed_on=(TODAY - timedelta(days=91)).isoformat()), TODAY))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_pricing -v`
Expected: FAIL — `ImportError: cannot import name 'compute_workload'`.

- [ ] **Step 3: Implement computation**

Append to `scripts/pricing.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_pricing -v`
Expected: PASS, 18 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/pricing.py tests/test_pricing.py
git commit -m "pricing: reference-workload computation with insufficient-data semantics"
```

---

### Task 5: Seed real observations for three providers

Proves the model against reality before automation. Enter rows by hand from official pricing pages.

**Files:**
- Modify: `pricing/observations/2026-Q3.json`
- Test: `tests/test_pricing.py`

**Interfaces:**
- Consumes: the validator from Task 3 and computation from Task 4.
- Produces: real rows for `neon`, `supabase`, and `planetscale`, enabling end-to-end output in Tasks 6–7.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pricing.py`:

```python
class SeedDataTests(unittest.TestCase):
    def test_repository_observations_are_valid(self) -> None:
        rows = load_observations()
        errors = validate_observations(rows, load_metrics(), load_catalog())
        self.assertEqual(errors, [])

    def test_seed_providers_have_computable_workloads(self) -> None:
        rows = load_observations()
        workload = next(w for w in load_workloads()["workloads"] if w["id"] == "small-prod-postgres")
        for slug in ("neon", "supabase", "planetscale"):
            provider_rows = [row for row in rows if row["provider_slug"] == slug]
            self.assertTrue(provider_rows, f"{slug} needs observation rows")
            result = compute_workload(workload, provider_rows, date.today())
            self.assertEqual(result["status"], "ok", f"{slug}: {result}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_pricing.SeedDataTests -v`
Expected: FAIL — `neon needs observation rows`.

- [ ] **Step 3: Enter the rows**

Open each provider's official pricing page, read the current values, and write rows into `pricing/observations/2026-Q3.json`. **Do not copy the values below as fact** — they are shape examples. Every `value`, `included_allowance`, and `plan` must be read from the live page today, and `observed_on` must be today's date (`date -u +%F`).

Pages to read:
- Neon — https://neon.com/pricing
- Supabase — https://supabase.com/pricing
- PlanetScale — https://planetscale.com/pricing

Required per provider: one `plan_base_month` row (if the plan has a fixed fee), one `storage_gib_month` row, and one `egress_gib` row, all for the same `plan` value so the workload can compute. Shape:

```json
{
  "provider_slug": "neon",
  "plan": "launch",
  "metric": "storage_gib_month",
  "value": 0.35,
  "currency": "USD",
  "included_allowance": 10,
  "region": "us-east",
  "observed_on": "2026-08-29",
  "source_url": "https://neon.com/pricing",
  "confidence": "high",
  "note": "Storage beyond the plan's included allowance, billed per GiB-month."
}
```

If a provider prices in a way these metrics cannot express, record what is expressible and leave the rest out — `insufficient_data` is the correct outcome, not a forced approximation.

- [ ] **Step 4: Validate and run the tests**

Run: `python3 scripts/pricing.py && python3 -m unittest tests.test_pricing -v`
Expected: validation prints a row count with no errors; tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pricing/observations/2026-Q3.json tests/test_pricing.py
git commit -m "pricing: seed observations for Neon, Supabase, and PlanetScale"
```

---

### Task 6: CLI entry point and published JSON API

**Files:**
- Modify: `scripts/pricing.py`
- Modify: `scripts/build.py`
- Modify: `scripts/check_site.py:136-141`
- Modify: `Makefile`
- Test: `tests/test_pricing.py`

**Interfaces:**
- Consumes: everything from Tasks 2–5.
- Produces:
  - `build_pricing_catalog(today: date | None = None) -> dict[str, Any]` with keys `schema_version`, `generated_on`, `max_age_days`, `disclaimer`, `metrics`, `workloads`, `providers`. Each `providers` entry is `{"slug", "name", "detail_path", "results": {workload_id: <compute_workload output>}, "rows": [...]}`.
  - `main() -> int` — validates the dataset and prints a summary; exit 1 on any error.
  - `dist/catalog/pricing.json` published by the build.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pricing.py`:

```python
from pricing import build_pricing_catalog  # noqa: E402


class PricingCatalogTests(unittest.TestCase):
    def test_published_payload_has_provenance_and_disclaimer(self) -> None:
        payload = build_pricing_catalog()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["max_age_days"], 90)
        self.assertTrue(payload["disclaimer"])
        self.assertTrue(payload["providers"])
        for provider in payload["providers"]:
            self.assertTrue(provider["slug"])
            self.assertEqual(provider["detail_path"], f"/providers/{provider['slug']}/")
            for result in provider["results"].values():
                self.assertIn(result["status"], {"ok", "insufficient_data"})
                if result["status"] == "ok":
                    self.assertTrue(result["sources"], "an ok result must carry its source rows")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_pricing.PricingCatalogTests -v`
Expected: FAIL — `ImportError: cannot import name 'build_pricing_catalog'`.

- [ ] **Step 3: Implement the builder and CLI**

Append to `scripts/pricing.py`:

```python
import sys

from catalog import load_catalog

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
```

- [ ] **Step 4: Publish it from the build**

In `scripts/build.py`, add the import beside the existing `recommendations` import:

```python
from pricing import build_pricing_catalog
```

Then, immediately after the line that writes `recommendations.json`, add:

```python
    write(DIST / "catalog" / "pricing.json", json.dumps(build_pricing_catalog(), indent=2, ensure_ascii=False) + "\n")
```

In `scripts/check_site.py`, extend the API file tuple so the new endpoint is checked:

```python
    for api_file in ("catalog/providers.json", "catalog/schema.json", "catalog/stats.json", "catalog/recommendations.json", "catalog/pricing.json"):
```

In the `Makefile`, add pricing validation to the `validate` target:

```makefile
validate:
	python3 scripts/validate.py
	python3 scripts/pricing.py
```

- [ ] **Step 5: Run the full suite**

Run: `make test`
Expected: PASS. `check_site` reports the JSON APIs checked; `dist/catalog/pricing.json` exists.

- [ ] **Step 6: Commit**

```bash
git add scripts/pricing.py scripts/build.py scripts/check_site.py Makefile tests/test_pricing.py
git commit -m "pricing: publish /catalog/pricing.json and validate it in CI"
```

---

### Task 7: The `/pricing/` page

**Files:**
- Create: `site/pricing.html`
- Create: `site/pricing.js`
- Modify: `site/styles.css`
- Modify: `site/base.html:41-45`
- Modify: `scripts/build.py`
- Modify: `scripts/check_site.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: `/catalog/pricing.json` from Task 6.
- Produces: a rendered page at `/pricing/`, a nav link, and a sitemap entry (count rises to providers + 6).

- [ ] **Step 1: Write the failing check**

In `scripts/check_site.py`, add `"pricing"` to the tool-page tuple and raise the sitemap count:

```python
    for tool_page in ("recommend", "method", "compare", "pricing"):
        if not (dist / tool_page / "index.html").exists():
            errors.append(f"Missing tool page: /{tool_page}/")
    expected_sitemap_entries = len(catalog["providers"]) + 6
```

- [ ] **Step 2: Run the check to verify it fails**

Run: `python3 scripts/build.py && python3 scripts/check_site.py`
Expected: FAIL — `Missing tool page: /pricing/` and a sitemap count mismatch.

- [ ] **Step 3: Create the page template**

Create `site/pricing.html`:

```html
<section class="page-hero shell">
  <p class="kicker">Database pricing</p>
  <h1>Dated prices,<br />not quotes.</h1>
  <p>Every figure is computed from dated observations of official pricing pages, using published reference workloads. Nothing here is a quote — verify current pricing with the provider before committing.</p>
</section>
<section class="pricing-shell shell" aria-labelledby="pricing-title">
  <h2 id="pricing-title" class="sr-only">Reference workload comparison</h2>
  <noscript>
    <div class="compare-empty">
      <strong>This comparison renders in the browser.</strong>
      <p>The underlying dataset is published at <a href="/catalog/pricing.json">/catalog/pricing.json</a>.</p>
    </div>
  </noscript>
  <div id="pricing-status" class="compare-status" role="status" aria-live="polite"></div>
  <div id="pricing-root" class="pricing-root" aria-busy="true"></div>
</section>
```

- [ ] **Step 4: Create the renderer**

Create `site/pricing.js`:

```javascript
(() => {
  'use strict';

  const root = document.querySelector('#pricing-root');
  const statusNode = document.querySelector('#pricing-status');
  if (!root) return;

  const escapeHtml = (value) => String(value)
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');

  const money = (value) => `$${Number(value).toFixed(2)}`;
  const daysBetween = (iso, today) => Math.round((today - new Date(iso)) / 86400000);

  const ageCell = (result, maxAge, today) => {
    if (result.status !== 'ok' || !result.sources.length) return '';
    const oldest = result.sources.map((source) => source.observed_on).sort()[0];
    const age = daysBetween(oldest, today);
    const stale = age > maxAge;
    return `<span class="price-age${stale ? ' is-stale' : ''}">${stale ? 'stale · ' : ''}${age}d old</span>`;
  };

  const cell = (result, maxAge, today) => {
    if (result.status !== 'ok') {
      return `<td class="price-missing"><span>insufficient data</span><small>${escapeHtml((result.missing_metrics || []).join(', '))}</small></td>`;
    }
    return `<td><strong>${escapeHtml(money(result.monthly_usd))}</strong><small>${escapeHtml(result.plan)} plan</small>${ageCell(result, maxAge, today)}</td>`;
  };

  fetch('/catalog/pricing.json')
    .then((response) => {
      if (!response.ok) throw new Error(`Pricing request failed: ${response.status}`);
      return response.json();
    })
    .then((payload) => {
      const today = new Date();
      const { workloads, providers, max_age_days: maxAge } = payload;
      const head = workloads.map((workload) => `<th scope="col">${escapeHtml(workload.label)}</th>`).join('');
      const body = providers.map((provider) => `<tr>
        <th scope="row"><a href="${escapeHtml(provider.detail_path)}">${escapeHtml(provider.name)}</a></th>
        ${workloads.map((workload) => cell(provider.results[workload.id] || {status: 'insufficient_data'}, maxAge, today)).join('')}
      </tr>`).join('');

      const assumptions = workloads.map((workload) => `<section class="workload-note">
        <h3>${escapeHtml(workload.label)}</h3>
        <p>${escapeHtml(Object.entries(workload.assumptions).map(([key, value]) => `${key.replaceAll('_', ' ')}: ${value}`).join(' · '))}</p>
        <ul>${workload.caveats.map((caveat) => `<li>${escapeHtml(caveat)}</li>`).join('')}</ul>
      </section>`).join('');

      root.innerHTML = `<div class="compare-table-wrap"><table class="compare-table pricing-table">
          <caption class="sr-only">Estimated monthly cost by reference workload</caption>
          <thead><tr><th scope="col">Provider</th>${head}</tr></thead>
          <tbody>${body}</tbody>
        </table></div>
        <p class="pricing-disclaimer">${escapeHtml(payload.disclaimer)} Dataset generated ${escapeHtml(payload.generated_on)}.</p>
        <div class="workload-notes"><h2>Workload assumptions</h2>${assumptions}</div>`;
      root.setAttribute('aria-busy', 'false');
    })
    .catch((error) => {
      root.innerHTML = '<div class="compare-empty"><strong>The pricing dataset could not load.</strong></div>';
      root.setAttribute('aria-busy', 'false');
      statusNode.textContent = error.message;
    });
})();
```

- [ ] **Step 5: Add styles**

Append inside the `@layer components` block in `site/styles.css`, immediately before its closing brace:

```css
  .pricing-shell { padding-bottom: 90px; }
  .pricing-table td { vertical-align: top; }
  .pricing-table td strong { display: block; font-size: 1rem; }
  .pricing-table td small { display: block; margin-top: 3px; color: var(--text-faint); font-size: .7rem; }
  .price-age { display: inline-block; margin-top: 6px; padding: 2px 6px; border-radius: 6px; background: var(--surface-soft); color: var(--text-faint); font-family: var(--mono); font-size: .62rem; }
  .price-age.is-stale { color: var(--accent-3); background: color-mix(in srgb, var(--accent-3) 14%, transparent); }
  .price-missing span { color: var(--text-faint); font-style: italic; }
  .price-missing small { display: block; margin-top: 3px; color: var(--text-faint); font-family: var(--mono); font-size: .62rem; }
  .pricing-disclaimer { margin-top: 18px; color: var(--text-soft); font-size: .82rem; line-height: 1.6; }
  .workload-notes { margin-top: 46px; }
  .workload-note { margin-top: 24px; padding: 18px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface-soft); }
  .workload-note p { margin-top: 8px; color: var(--text-soft); font-family: var(--mono); font-size: .74rem; }
  .workload-note ul { margin: 10px 0 0; padding-left: 18px; color: var(--text-faint); font-size: .78rem; line-height: 1.6; }
```

- [ ] **Step 6: Wire the build, nav, and Makefile**

In `scripts/build.py`, after the `/compare/` write, add:

```python
    write(DIST / "pricing" / "index.html", render_base(
        title="Database pricing — DeployIndex",
        description="Dated database hosting prices from official pricing pages, compared through published reference workloads.",
        path="/pricing/",
        main=(SITE / "pricing.html").read_text(encoding="utf-8"),
        scripts='<script src="/assets/pricing.js" defer></script>',
        body_class="pricing-page",
    ))
```

Add `"pricing.js"` to the asset copy tuple, and `"/pricing/"` to `sitemap_urls` after `"/compare/"`.

In `site/base.html`, add a nav link after the Compare-adjacent entries:

```html
        <a href="/pricing/">Pricing</a>
```

In the `Makefile` `check` target, add:

```makefile
	node --check site/pricing.js
```

- [ ] **Step 7: Run the full suite**

Run: `make test`
Expected: PASS. `check_site` reports one more HTML file and the sitemap count matches.

- [ ] **Step 8: Verify in the browser**

Run `make preview`, open `http://localhost:8000/pricing/`, and confirm: figures render with plan names and ages, `insufficient data` cells show missing metrics, workload assumptions and caveats appear below the table, and the console is free of errors. Check both light and dark themes.

- [ ] **Step 9: Commit**

```bash
git add site/pricing.html site/pricing.js site/styles.css site/base.html scripts/build.py scripts/check_site.py Makefile
git commit -m "site: /pricing/ reference-workload comparison page"
```

---

### Task 8: Pricing block on `/compare/`

**Files:**
- Modify: `site/compare.js`

**Interfaces:**
- Consumes: `/catalog/pricing.json` from Task 6; the existing `renderTable` in `site/compare.js`.
- Produces: a pricing group inside the comparison table when data exists for the compared entries.

- [ ] **Step 1: Fetch the pricing dataset alongside the others**

In `site/compare.js`, extend the `Promise.all` to a third request that tolerates absence:

```javascript
    fetch('/catalog/pricing.json').then((response) => (response.ok ? response.json() : null)).catch(() => null),
```

and widen the destructuring to `([catalog, recommendations, pricing]) => {`.

- [ ] **Step 2: Build a slug-keyed pricing index**

Immediately after the existing `profilesBySlug` line:

```javascript
    const pricingBySlug = new Map(((pricing || {}).providers || []).map((entry) => [entry.slug, entry]));
    const pricingWorkloads = (pricing || {}).workloads || [];
```

- [ ] **Step 3: Pass it into the renderer and add the rows**

Change the signature from `const renderTable = (entries, profilesBySlug, categoryLabels) => {` to:

```javascript
  const renderTable = (entries, profilesBySlug, categoryLabels, pricingBySlug, pricingWorkloads) => {
```

and its call site from `renderTable(entries, profilesBySlug, catalog.category_labels || {})` to:

```javascript
    root.innerHTML = renderTable(entries, profilesBySlug, catalog.category_labels || {}, pricingBySlug, pricingWorkloads);
```

Then add this group immediately before the `Verification` group:

```javascript
    const priced = entries.filter((entry) => pricingBySlug.has(entry.slug));
    if (priced.length && pricingWorkloads.length) {
      rows.push(groupRow('Estimated monthly cost · dated observations, not quotes'));
      pricingWorkloads.forEach((workload) => {
        rows.push(row(escapeHtml(workload.label), (entry) => {
          const result = (pricingBySlug.get(entry.slug) || {}).results?.[workload.id];
          if (!result || result.status !== 'ok') return td('<span class="compare-miss">insufficient data</span>');
          return td(`<strong>$${Number(result.monthly_usd).toFixed(2)}</strong> <small>${escapeHtml(result.plan)} plan</small>`);
        }));
      });
    }
```

- [ ] **Step 4: Verify in the browser**

Run: `make test && make preview`
Open `http://localhost:8000/compare/?s=neon,supabase,planetscale` and confirm the cost group renders, entries without data show `insufficient data`, and the console is clean. Then open a comparison of two entries with no pricing rows and confirm the group is omitted entirely rather than rendering empty.

- [ ] **Step 5: Commit**

```bash
git add site/compare.js
git commit -m "site: show dated cost estimates in the comparison table"
```

---

### Task 9: Pricing block on provider detail pages

The spec lists provider detail pages as a display surface: that provider's own rows with dates and source links, and deliberately no cross-provider math. Detail pages are generated server-side, so this is a build-time render with no JavaScript.

**Files:**
- Modify: `scripts/build.py`
- Test: `tests/test_pricing.py`

**Interfaces:**
- Consumes: `load_observations` and `is_stale` from Tasks 2 and 4.
- Produces: `pricing_section(slug: str, rows: list[dict], metrics: dict, today: date) -> str` in `scripts/build.py` — returns an HTML section, or `""` when the provider has no rows.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pricing.py`:

```python
class DetailPageSectionTests(unittest.TestCase):
    def test_section_is_empty_for_providers_without_rows(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        from build import pricing_section

        self.assertEqual(pricing_section("no-rows-here", [], load_metrics(), date(2026, 8, 29)), "")

    def test_section_escapes_and_lists_rows_with_dates(self) -> None:
        from build import pricing_section

        rows = [make_row(note="<script>alert(1)</script>")]
        html = pricing_section("neon", rows, load_metrics(), date(2026, 8, 29))
        self.assertIn("2026-08-01", html)
        self.assertIn("https://neon.com/pricing", html)
        self.assertNotIn("<script>alert(1)</script>", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_pricing.DetailPageSectionTests -v`
Expected: FAIL — `ImportError: cannot import name 'pricing_section'`.

- [ ] **Step 3: Implement the section renderer**

In `scripts/build.py`, add to the imports:

```python
from pricing import is_stale, load_metrics, load_observations
```

Then add this function beside the other renderers:

```python
def pricing_section(slug: str, rows: list[dict], metrics: dict, today: date) -> str:
    """Render one provider's own dated price rows. No cross-provider math."""
    provider_rows = sorted(
        (row for row in rows if row["provider_slug"] == slug),
        key=lambda row: (row["plan"], row["metric"]),
    )
    if not provider_rows:
        return ""
    items = []
    for row in provider_rows:
        unit = metrics["metrics"].get(row["metric"], {}).get("unit", "")
        stale = " · stale" if is_stale(row, today) else ""
        items.append(
            f'<tr><td>{esc(row["plan"])}</td><td>{esc(row["metric"])}</td>'
            f'<td>{esc(row["value"])} <small>{esc(unit)}</small></td>'
            f'<td>{esc(row["included_allowance"])}</td>'
            f'<td>{esc(row["observed_on"])}{esc(stale)}</td>'
            f'<td><a href="{esc(row["source_url"])}" rel="noreferrer">source ↗</a></td></tr>'
        )
    return (
        '<section class="detail-section full"><h2>Observed pricing</h2>'
        "<p>Dated observations from this provider's official pricing pages. These are records, not quotes — "
        "verify current pricing with the provider.</p>"
        '<div class="compare-table-wrap"><table class="compare-table">'
        "<thead><tr><th>Plan</th><th>Metric</th><th>Value</th><th>Included</th><th>Observed</th><th>Evidence</th></tr></thead>"
        f"<tbody>{''.join(items)}</tbody></table></div></section>"
    )
```

- [ ] **Step 4: Call it from the detail page**

In `provider_page(...)`, add a parameter `pricing_html: str = ""` and render it inside `detail-grid`, immediately before the `Source trail` section. In `main()`, load the rows once before the provider loop:

```python
    pricing_rows = load_observations()
    pricing_metrics = load_metrics()
    today = date.today()
```

and pass `pricing_section(item["slug"], pricing_rows, pricing_metrics, today)` into each `provider_page(...)` call.

- [ ] **Step 5: Run the suite**

Run: `make test`
Expected: PASS. `check_site` still validates every generated page, including the new section's links.

- [ ] **Step 6: Commit**

```bash
git add scripts/build.py tests/test_pricing.py
git commit -m "site: show observed pricing rows on provider detail pages"
```

---

### Task 10: Documentation

**Files:**
- Create: `pricing/README.md`
- Modify: `docs/README.md`
- Modify: `README.md`
- Modify: `docs/ROADMAP.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: the finished feature.
- Produces: contributor-facing rules for the dataset.

- [ ] **Step 1: Write the dataset guide**

Create `pricing/README.md` covering: what a row means; that rows are append-only and a price change is a new dated row; the metric vocabulary and how to propose an addition; that `insufficient_data` is correct and preferable to an approximation; the 90-day staleness rule; and that no row may be added without an HTTPS official source read on the date recorded.

- [ ] **Step 2: Update the indexes**

- `docs/README.md`: link the spec and this plan.
- `README.md`: add `/pricing/` and `/catalog/pricing.json` to the published-paths list.
- `docs/ROADMAP.md`: move pricing snapshots from Phase 4 "Next" into a delivered subsection.
- `AGENTS.md`: add a pricing rule line — prices need a dated official source; rows are append-only; `insufficient_data` beats a partial sum; prices never feed recommender scoring.

- [ ] **Step 3: Verify and commit**

```bash
make test
git add pricing/README.md docs/README.md README.md docs/ROADMAP.md AGENTS.md
git commit -m "docs: pricing dataset rules and index updates"
```

---

## Follow-up work (not in this plan)

- The model-assisted pricing research scan and its delta-review renderer (spec rollout steps 5–6), which needs its own plan.
- Expanding from 3 seeded providers to the full v1 list of ~12.
- Multi-region and multi-currency support.
