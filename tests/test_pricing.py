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

    def test_non_finite_value_is_rejected(self) -> None:
        self.assert_error(make_row(value=float('nan')), "value must be a non-negative number")
        self.assert_error(make_row(value=float('inf')), "value must be a non-negative number")

    def test_unsupported_region_is_rejected(self) -> None:
        self.assert_error(make_row(region="eu-west"), "unsupported region")

    def test_source_url_with_no_host_is_rejected(self) -> None:
        self.assert_error(make_row(source_url="https://"), "source_url must be https")

    def test_duplicate_with_different_date_encoding_is_rejected(self) -> None:
        row = make_row()
        errors = validate_observations([row, make_row(observed_on="20260801")], self.metrics, self.catalog, today=date(2026, 8, 29))
        self.assertTrue(any("duplicate observation" in error for error in errors), errors)

    def test_non_dict_row_returns_error_not_exception(self) -> None:
        errors = validate_observations(["not a dict"], self.metrics, self.catalog, today=date(2026, 8, 29))
        self.assertTrue(any("rows[0]" in error for error in errors), errors)

    def test_unhashable_metric_returns_error_not_exception(self) -> None:
        self.assert_error(make_row(metric={}), "unknown metric")

    def test_unhashable_provider_slug_returns_error_not_exception(self) -> None:
        self.assert_error(make_row(provider_slug=[]), "unknown provider_slug")

    def test_non_list_rows_returns_proper_error(self) -> None:
        errors = validate_observations({"not": "a list"}, self.metrics, self.catalog, today=date(2026, 8, 29))
        self.assertEqual(errors, ["rows must be a list"])


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


if __name__ == "__main__":
    unittest.main()
