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


if __name__ == "__main__":
    unittest.main()
