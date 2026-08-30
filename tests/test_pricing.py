from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pricing import load_metrics, load_observations, load_workloads, validate_workloads  # noqa: E402


class PricingDatasetTests(unittest.TestCase):
    def test_metric_vocabulary_defines_unit_and_description(self) -> None:
        metrics = load_metrics()["metrics"]
        self.assertIn("storage_gib_month", metrics)
        self.assertIn("plan_base_month", metrics)
        for name, definition in metrics.items():
            self.assertTrue(definition.get("unit"), f"{name} needs a unit")
            self.assertTrue(definition.get("description"), f"{name} needs a description")

    def test_workloads_declare_explicit_line_items_or_a_shape(self) -> None:
        workloads = load_workloads()["workloads"]
        self.assertTrue(workloads)
        metrics = load_metrics()["metrics"]
        for workload in workloads:
            self.assertTrue(workload["id"])
            self.assertTrue(workload["caveats"])
            if "shape" in workload:
                self.assertTrue(workload["shape"])
                for key in workload["shape"]:
                    self.assertTrue(key.startswith("min_"), f"{workload['id']}: {key!r} is not a min_ key")
                continue
            self.assertTrue(workload["line_items"])
            for item in workload["line_items"]:
                self.assertIn(item["metric"], metrics)
                self.assertGreater(item["quantity"], 0)

    def test_shipped_workloads_pass_the_validator(self) -> None:
        self.assertEqual(validate_workloads(load_workloads()["workloads"], load_metrics()), [])

    def test_shipped_workloads_do_not_name_compute_they_do_not_price(self) -> None:
        """The published assumptions must not imply a compute figure is included."""
        for workload in load_workloads()["workloads"]:
            for key in ("vcpu", "memory_gib", "hours_month", "compute_units"):
                self.assertNotIn(key, workload["assumptions"], f"{workload['id']} declares {key}")

    def test_every_workload_warns_that_compute_is_excluded(self) -> None:
        for workload in load_workloads()["workloads"]:
            caveats = " ".join(workload["caveats"]).lower()
            self.assertIn("compute", caveats, f"{workload['id']} must say compute is excluded")

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

    def test_basic_form_date_is_rejected(self) -> None:
        """`date.fromisoformat` accepts "20260801"; a row date must not.

        The basic form string-sorts above every extended-form date, so a row
        carrying one would win `_latest_by_metric` forever and publish a
        superseded price as current.
        """
        self.assert_error(make_row(observed_on="20260801"), "YYYY-MM-DD")

    def test_other_non_canonical_dates_are_rejected(self) -> None:
        for value in ("2026-8-1", "2026-08-01T00:00:00", " 2026-08-01", "2026-W31-1", 20260801, None):
            with self.subTest(observed_on=value):
                self.assert_error(make_row(observed_on=value), "YYYY-MM-DD")

    def test_non_string_plan_is_rejected(self) -> None:
        self.assert_error(make_row(plan=1), "plan must be a non-empty string")
        self.assert_error(make_row(plan=""), "plan must be a non-empty string")
        self.assert_error(make_row(plan=["launch"]), "plan must be a non-empty string")

    def test_non_string_note_is_rejected(self) -> None:
        self.assert_error(make_row(note=None), "note must be a non-empty string")
        self.assert_error(make_row(note="   "), "note must be a non-empty string")

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

    def test_row_with_valid_attributes_is_accepted(self) -> None:
        errors = validate_observations(
            [make_row(metric="plan_base_month", attributes={"storage_gib": 10, "memory_gib": 1})],
            self.metrics, self.catalog, today=date(2026, 8, 29),
        )
        self.assertEqual(errors, [])

    def test_attributes_value_must_be_non_negative(self) -> None:
        self.assert_error(make_row(attributes={"storage_gib": -1}), "attributes")

    def test_attributes_value_must_be_finite(self) -> None:
        self.assert_error(make_row(attributes={"storage_gib": float("nan")}), "attributes")
        self.assert_error(make_row(attributes={"storage_gib": float("inf")}), "attributes")

    def test_attributes_key_must_be_lowercase_snake_case(self) -> None:
        self.assert_error(make_row(attributes={"StorageGiB": 10}), "snake_case")
        self.assert_error(make_row(attributes={"storage-gib": 10}), "snake_case")

    def test_attributes_must_be_an_object(self) -> None:
        self.assert_error(make_row(attributes=["storage_gib"]), "attributes")


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

    def test_workload_may_not_assume_a_metric_it_does_not_price(self) -> None:
        """A workload's assumptions are rendered as what the figure covers.

        `/pricing/` prints `assumptions` beside the totals, so declaring vCPU,
        memory, or running hours while pricing no compute metric misdescribes
        every number in the column — and biases against providers that fold
        compute into a plan fee, since only theirs gets counted. The validator
        has to reject that rather than the reviewer having to notice it.
        """
        metrics = load_metrics()
        errors = validate_workloads([{
            "id": "compute-that-is-never-priced",
            "label": "Small production Postgres",
            "assumptions": {"vcpu": 2, "memory_gib": 8, "storage_gib": 100, "hours_month": 730},
            "line_items": [
                {"metric": "plan_base_month", "quantity": 1, "optional": True},
                {"metric": "storage_gib_month", "quantity": 100},
            ],
            "caveats": ["test"],
        }], metrics)
        joined = " ".join(errors)
        self.assertIn("'vcpu'", joined)
        self.assertIn("'memory_gib'", joined)
        self.assertIn("'hours_month'", joined)
        self.assertNotIn("'storage_gib'", joined.replace("'storage_gib_month'", ""))

    def test_workload_assumption_matching_a_priced_metric_is_accepted(self) -> None:
        self.assertEqual(validate_workloads([{
            "id": "honest",
            "label": "Storage only",
            "assumptions": {"storage_gib": 100},
            "line_items": [{"metric": "storage_gib_month", "quantity": 100}],
            "caveats": ["test"],
        }], load_metrics()), [])

    def test_workload_declaring_both_line_items_and_shape_is_rejected(self) -> None:
        errors = validate_workloads([{
            "id": "both",
            "label": "Both",
            "shape": {"min_storage_gib": 100},
            "line_items": [{"metric": "storage_gib_month", "quantity": 100}],
            "assumptions": {"storage_gib": 100},
            "caveats": ["test"],
        }], load_metrics())
        self.assertTrue(any("exactly one" in error for error in errors), errors)

    def test_workload_declaring_neither_line_items_nor_shape_is_rejected(self) -> None:
        errors = validate_workloads([{
            "id": "neither",
            "label": "Neither",
            "assumptions": {},
            "caveats": ["test"],
        }], load_metrics())
        self.assertTrue(any("exactly one" in error for error in errors), errors)

    def test_shape_key_must_be_min_prefixed_snake_case(self) -> None:
        errors = validate_workloads([{
            "id": "bad-shape-key",
            "label": "Bad shape key",
            "shape": {"storage_gib": 100},
            "assumptions": {},
            "caveats": ["test"],
        }], load_metrics())
        self.assertTrue(any("min_" in error for error in errors), errors)

    def test_shape_workload_is_accepted_when_valid(self) -> None:
        self.assertEqual(validate_workloads([{
            "id": "shape-ok",
            "label": "Shape ok",
            "shape": {"min_storage_gib": 100},
            "assumptions": {"storage_gib": 100},
            "caveats": ["test"],
        }], load_metrics()), [])

    def test_shape_workload_assumption_must_match_a_shape_attribute(self) -> None:
        errors = validate_workloads([{
            "id": "shape-bad-assumption",
            "label": "Shape bad assumption",
            "shape": {"min_storage_gib": 100},
            "assumptions": {"memory_gib": 4},
            "caveats": ["test"],
        }], load_metrics())
        self.assertTrue(any("memory_gib" in error for error in errors), errors)

    def test_absent_optional_line_item_contributes_zero(self) -> None:
        """Correct only because `plan_base_month` is genuinely optional.

        Neon's Launch plan has no monthly minimum, so no base-fee row exists and
        zero is the true contribution. The dishonesty this used to cover for was
        never here — it was in the workload claiming to price compute it did not.
        """
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

    def test_later_row_supersedes_an_earlier_one(self) -> None:
        """The append-only supersede rule: the latest observation wins.

        A price change is a new row with a later `observed_on`, never an edit,
        so the whole dataset rests on the newest row being the one that is
        costed and cited.
        """
        old = make_row(metric="storage_gib_month", value=0.50, included_allowance=0, observed_on="2026-07-01")
        new = make_row(metric="storage_gib_month", value=0.10, included_allowance=0, observed_on="2026-08-15")
        egress = make_row(metric="egress_gib", value=0.0, included_allowance=0)
        for rows in ([old, new, egress], [new, old, egress], [egress, new, old]):
            with self.subTest(order=[row["observed_on"] for row in rows]):
                result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
                self.assertEqual(result["status"], "ok")
                self.assertAlmostEqual(result["monthly_usd"], 10.00, places=2)
                storage = next(s for s in result["sources"] if s["metric"] == "storage_gib_month")
                self.assertEqual(storage["observed_on"], "2026-08-15")
                self.assertEqual(storage["value"], 0.10)

    def test_superseding_row_is_cited_as_provenance(self) -> None:
        rows = [
            make_row(metric="storage_gib_month", value=0.50, included_allowance=0,
                     observed_on="2026-07-01", source_url="https://neon.com/old"),
            make_row(metric="storage_gib_month", value=0.10, included_allowance=0,
                     observed_on="2026-08-15", source_url="https://neon.com/new"),
            make_row(metric="egress_gib", value=0.0, included_allowance=0),
        ]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        urls = [s["source_url"] for s in result["sources"]]
        self.assertIn("https://neon.com/new", urls)
        self.assertNotIn("https://neon.com/old", urls)

    def test_non_finite_total_never_becomes_a_price(self) -> None:
        """A total that overflows is not a price, and `Infinity` is not JSON."""
        rows = [
            make_row(metric="storage_gib_month", value=1e308, included_allowance=0),
            make_row(metric="egress_gib", value=1e308, included_allowance=0),
        ]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")
        json.dumps(result, allow_nan=False)

    def test_currencies_are_never_mixed(self) -> None:
        rows = [
            make_row(metric="storage_gib_month", value=0.10, included_allowance=0, currency="USD"),
            make_row(metric="egress_gib", value=0.09, included_allowance=0, currency="EUR"),
        ]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIn("egress_gib", result["missing_metrics"])

    def test_regions_are_never_mixed(self) -> None:
        rows = [
            make_row(metric="storage_gib_month", value=0.10, included_allowance=0, region="us-east"),
            make_row(metric="egress_gib", value=0.09, included_allowance=0, region="eu-west"),
        ]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIn("egress_gib", result["missing_metrics"])

    def test_result_carries_its_currency_and_region(self) -> None:
        rows = [
            make_row(metric="storage_gib_month", value=0.10, included_allowance=0),
            make_row(metric="egress_gib", value=0.0, included_allowance=0),
        ]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        self.assertEqual(result["currency"], "USD")
        self.assertEqual(result["region"], "us-east")

    def test_plans_considered_counts_plans_with_fresh_rows(self) -> None:
        """A single-plan total is a coverage artifact, not a comparison."""
        one_plan = [
            make_row(plan="only", metric="storage_gib_month", value=0.10, included_allowance=0),
            make_row(plan="only", metric="egress_gib", value=0.0, included_allowance=0),
        ]
        self.assertEqual(compute_workload(SMALL_WORKLOAD, one_plan, TODAY)["plans_considered"], 1)

        two_plans = one_plan + [
            make_row(plan="other", metric="storage_gib_month", value=0.50, included_allowance=0),
            make_row(plan="other", metric="egress_gib", value=0.0, included_allowance=0),
        ]
        result = compute_workload(SMALL_WORKLOAD, two_plans, TODAY)
        self.assertEqual(result["plans_considered"], 2)
        self.assertEqual(result["plan"], "only")

    def test_plans_considered_counts_plans_that_did_not_qualify(self) -> None:
        rows = [
            make_row(plan="complete", metric="storage_gib_month", value=0.10, included_allowance=0),
            make_row(plan="complete", metric="egress_gib", value=0.0, included_allowance=0),
            make_row(plan="partial", metric="storage_gib_month", value=0.01, included_allowance=0),
        ]
        self.assertEqual(compute_workload(SMALL_WORKLOAD, rows, TODAY)["plans_considered"], 2)

    def test_plans_considered_excludes_stale_plans(self) -> None:
        old = (TODAY - timedelta(days=120)).isoformat()
        rows = [
            make_row(plan="fresh", metric="storage_gib_month", value=0.10, included_allowance=0),
            make_row(plan="fresh", metric="egress_gib", value=0.0, included_allowance=0),
            make_row(plan="ancient", metric="storage_gib_month", value=0.01, included_allowance=0, observed_on=old),
            make_row(plan="ancient", metric="egress_gib", value=0.0, included_allowance=0, observed_on=old),
        ]
        self.assertEqual(compute_workload(SMALL_WORKLOAD, rows, TODAY)["plans_considered"], 1)

    def test_insufficient_data_still_reports_plans_considered(self) -> None:
        rows = [make_row(metric="storage_gib_month", value=0.10, included_allowance=0)]
        result = compute_workload(SMALL_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["plans_considered"], 1)

    def test_is_stale_respects_the_threshold(self) -> None:
        self.assertFalse(is_stale(make_row(observed_on=TODAY.isoformat()), TODAY))
        self.assertFalse(is_stale(make_row(observed_on=(TODAY - timedelta(days=89)).isoformat()), TODAY))
        self.assertTrue(is_stale(make_row(observed_on=(TODAY - timedelta(days=91)).isoformat()), TODAY))


SHAPE_WORKLOAD = {
    "id": "shape-test-workload",
    "label": "Shape test workload",
    "shape": {"min_storage_gib": 100},
    "assumptions": {"storage_gib": 100},
    "caveats": ["test"],
}


def make_plan_row(**overrides) -> dict:
    return make_row(metric="plan_base_month", included_allowance=0, **overrides)


class ShapeWorkloadComputationTests(unittest.TestCase):
    """Golden cases for shape matching, per the spec's compute and VMs section."""

    def test_cheapest_qualifying_plan_wins(self) -> None:
        rows = [
            make_plan_row(plan="small", value=50.0, attributes={"storage_gib": 150}),
            make_plan_row(plan="big", value=30.0, attributes={"storage_gib": 200}),
        ]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["plan"], "big")
        self.assertAlmostEqual(result["monthly_usd"], 30.0, places=2)

    def test_under_provisioned_plan_is_never_selected(self) -> None:
        rows = [
            make_plan_row(plan="tiny", value=5.0, attributes={"storage_gib": 10}),
            make_plan_row(plan="ok-plan", value=40.0, attributes={"storage_gib": 100}),
        ]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["plan"], "ok-plan")

    def test_exact_boundary_qualifies(self) -> None:
        rows = [make_plan_row(plan="exact", value=12.0, attributes={"storage_gib": 100})]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["plan"], "exact")

    def test_ties_break_deterministically_by_plan_name(self) -> None:
        rows = [
            make_plan_row(plan="zeta", value=40.0, attributes={"storage_gib": 120}),
            make_plan_row(plan="alpha", value=40.0, attributes={"storage_gib": 150}),
        ]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["plan"], "alpha")

    def test_no_qualifying_plan_yields_insufficient_data_with_reason(self) -> None:
        rows = [make_plan_row(plan="small", value=10.0, attributes={"storage_gib": 10})]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["missing_metrics"], [])
        self.assertIn("100", result["reason"])
        self.assertIn("storage", result["reason"])
        self.assertIn("provides at least", result["reason"])

    def test_reason_says_recorded_plans_fall_short_when_attributes_exist(self) -> None:
        """Attributes were recorded (10 GiB) and simply do not meet the shape.

        This is a fact the dataset can actually assert: the provider's own
        recorded plan is too small. Distinct from the case below, where the
        dataset never recorded any capacity at all and cannot make this claim.
        """
        rows = [
            make_plan_row(plan="small", value=10.0, attributes={"storage_gib": 10}),
            make_plan_row(plan="medium", value=20.0, attributes={"storage_gib": 50}),
        ]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIn("no recorded plan provides at least 100 GiB of storage", result["reason"])
        self.assertNotIn("has been recorded", result["reason"])

    def test_reason_says_nothing_recorded_when_no_plan_has_attributes(self) -> None:
        """No fresh `plan_base_month` row for this provider carries `attributes`
        at all — the dataset has recorded no capacity figure, not that the
        provider's real plans are too small. Saying "no plan provides at least
        100 GiB" here would assert something the dataset cannot know: the
        provider may well sell plans well over 100 GiB that were never
        recorded (this is exactly what happened to Neon before this fix).
        """
        rows = [make_plan_row(plan="mystery", value=10.0)]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIn("has been recorded", result["reason"])
        self.assertIn("storage", result["reason"])
        self.assertNotIn("provides at least", result["reason"])
        self.assertNotIn("100", result["reason"])

    def test_reason_is_nothing_recorded_when_only_row_lacks_a_plan_base_month_metric(self) -> None:
        """A provider that only ever publishes metered rows (no `plan_base_month`
        at all) has recorded nothing about plan capacity, same as one whose
        `plan_base_month` rows omit `attributes`.
        """
        rows = [make_row(plan="metered", metric="storage_gib_month", value=0.10)]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIn("has been recorded", result["reason"])

    def test_plan_lacking_attributes_never_qualifies(self) -> None:
        rows = [make_plan_row(plan="no-attrs", value=1.0)]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")

    def test_stale_rows_are_excluded_from_shape_matching(self) -> None:
        old = (TODAY - timedelta(days=120)).isoformat()
        rows = [make_plan_row(plan="stale", value=1.0, attributes={"storage_gib": 500}, observed_on=old)]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")

    def test_plans_are_never_mixed_across_currency_or_region(self) -> None:
        rows = [
            make_plan_row(plan="eur-plan", value=1.0, attributes={"storage_gib": 500}, currency="EUR"),
        ]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")

    def test_plans_considered_counts_plans_with_fresh_rows(self) -> None:
        rows = [
            make_plan_row(plan="a", value=10.0, attributes={"storage_gib": 10}),
            make_plan_row(plan="b", value=40.0, attributes={"storage_gib": 200}),
        ]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["plans_considered"], 2)

    def test_candidate_sort_breaks_price_ties_on_plan_name_regardless_of_row_order(self) -> None:
        """Pins the explicit `(price, plan)` tiebreak in the candidate sort.

        Two plans tie on price; alphabetically "alpha" must win over "zeta".
        The input rows are given with "zeta" *first* — the adversarial order —
        so a correct result here cannot be explained by plans happening to be
        visited in alphabetical order already; only the sort's own tiebreak
        key can produce it. (Feeding rows in the already-correct order would
        let a masking incidental order stand in for a real tiebreak.)
        """
        rows = [
            make_plan_row(plan="zeta", value=40.0, attributes={"storage_gib": 120}),
            make_plan_row(plan="alpha", value=40.0, attributes={"storage_gib": 150}),
        ]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["plan"], "alpha")

    def test_result_is_independent_of_the_order_plans_are_first_seen(self) -> None:
        """Plans must not be iterated in some incidentally-helpful order.

        Same two tied-price plans as above, fed in both possible orders; both
        must produce the identical winner. If plan iteration order ever
        leaked into the result (e.g. a "first one wins" comparison instead of
        a full sort), these two orderings would disagree.
        """
        first = make_plan_row(plan="zeta", value=40.0, attributes={"storage_gib": 120})
        second = make_plan_row(plan="alpha", value=40.0, attributes={"storage_gib": 150})
        result_a = compute_workload(SHAPE_WORKLOAD, [first, second], TODAY)
        result_b = compute_workload(SHAPE_WORKLOAD, [second, first], TODAY)
        self.assertEqual(result_a["plan"], result_b["plan"])
        self.assertEqual(result_a["plan"], "alpha")

    def test_non_dict_attributes_are_excluded_not_treated_as_empty(self) -> None:
        """A malformed (non-dict) `attributes` value must disqualify the plan
        outright, not be silently coerced to `{}` and fall through to the
        qualification check — which would risk an `AttributeError` on `.get`
        the moment `attributes` is some other truthy, non-dict value.
        """
        rows = [make_plan_row(plan="malformed", value=1.0, attributes="not-a-dict")]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")

    def test_boolean_attribute_value_never_satisfies_a_numeric_minimum(self) -> None:
        """`True` is an instance of `int` in Python (`isinstance(True, int)` is
        `True`, and `float(True) == 1.0`), so without an explicit exclusion a
        `True` attribute value would silently satisfy any `min_` threshold at
        or below 1 — qualifying a plan that never recorded a real quantity.
        """
        low_bar = {
            "id": "shape-test-workload-low-bar",
            "label": "Shape test workload (low bar)",
            "shape": {"min_storage_gib": 1},
            "assumptions": {"storage_gib": 1},
            "caveats": ["test"],
        }
        rows = [make_plan_row(plan="boolean-attr", value=5.0, attributes={"storage_gib": True})]
        result = compute_workload(low_bar, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")

    def test_only_plan_base_month_may_supply_attributes_and_price(self) -> None:
        """A `storage_gib_month` row is a per-GiB metered rate, not a plan fee.

        If the shape matcher let any metric substitute for `plan_base_month`,
        a tiny metered rate (e.g. $0.215/GiB-month) carrying `attributes`
        could be published as if it were a whole plan's monthly price.
        """
        rows = [make_row(
            plan="metered-only", metric="storage_gib_month", value=0.215,
            included_allowance=0, attributes={"storage_gib": 200},
        )]
        result = compute_workload(SHAPE_WORKLOAD, rows, TODAY)
        self.assertEqual(result["status"], "insufficient_data")


class SeedDataTests(unittest.TestCase):
    def test_repository_observations_are_valid(self) -> None:
        rows = load_observations()
        errors = validate_observations(rows, load_metrics(), load_catalog())
        self.assertEqual(errors, [])

    def test_seed_providers_have_computable_workloads(self) -> None:
        rows = load_observations()
        workload = next(w for w in load_workloads()["workloads"] if w["id"] == "storage-egress-100gib")
        for slug in ("neon", "supabase", "planetscale"):
            provider_rows = [row for row in rows if row["provider_slug"] == slug]
            self.assertTrue(provider_rows, f"{slug} needs observation rows")
            result = compute_workload(workload, provider_rows, date.today())
            self.assertEqual(result["status"], "ok", f"{slug}: {result}")


class ShapeWorkloadSeedDataTests(unittest.TestCase):
    """The shape-matching extension must not disturb the existing line-item workloads."""

    def test_existing_workloads_produce_unaffected_figures(self) -> None:
        rows = load_observations()
        workloads = {w["id"]: w for w in load_workloads()["workloads"]}
        expected = {
            "neon": {"storage-egress-100gib": 35.00, "storage-egress-10gib": 3.50},
            "planetscale": {"storage-egress-100gib": 18.65, "storage-egress-10gib": 5.00},
            "supabase": {"storage-egress-100gib": 36.50, "storage-egress-10gib": 25.25},
        }
        for slug, by_workload in expected.items():
            provider_rows = [row for row in rows if row["provider_slug"] == slug]
            for workload_id, expected_total in by_workload.items():
                result = compute_workload(workloads[workload_id], provider_rows, date.today())
                self.assertEqual(result["status"], "ok", f"{slug}/{workload_id}: {result}")
                self.assertAlmostEqual(result["monthly_usd"], expected_total, places=2, msg=f"{slug}/{workload_id}")

    def test_new_shape_workload_picks_heroku_standard_2(self) -> None:
        rows = load_observations()
        workload = next(w for w in load_workloads()["workloads"] if w["id"] == "plan-with-100gib-storage")
        provider_rows = [row for row in rows if row["provider_slug"] == "heroku-postgres"]
        result = compute_workload(workload, provider_rows, date.today())
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["plan"], "standard-2")
        self.assertAlmostEqual(result["monthly_usd"], 200.00, places=2)

    def test_shape_workload_prefers_standard_2_over_premium_2_at_equal_storage(self) -> None:
        """Standard 2 and Premium 2 both provide 256 GiB storage; Standard 2 is
        $150 cheaper. Before Standard 2 was recorded, Premium 2 was the only
        qualifying plan, so a single-candidate default could stand in for a
        real comparison without being caught. This pins the actual comparison:
        with both plans present, the cheaper one must win even though neither
        has more storage than the other.
        """
        rows = load_observations()
        workload = next(w for w in load_workloads()["workloads"] if w["id"] == "plan-with-100gib-storage")
        provider_rows = [row for row in rows if row["provider_slug"] == "heroku-postgres"]
        result = compute_workload(workload, provider_rows, date.today())
        self.assertEqual(result["status"], "ok", result)
        self.assertGreater(result["plans_considered"], 1)
        self.assertEqual(result["plan"], "standard-2")
        self.assertNotEqual(result["plan"], "premium-2")
        self.assertLess(result["monthly_usd"], 350.00)

    def test_new_shape_workload_reports_insufficient_data_for_digitalocean(self) -> None:
        rows = load_observations()
        workload = next(w for w in load_workloads()["workloads"] if w["id"] == "plan-with-100gib-storage")
        provider_rows = [row for row in rows if row["provider_slug"] == "digitalocean-managed-postgresql"]
        result = compute_workload(workload, provider_rows, date.today())
        self.assertEqual(result["status"], "insufficient_data", result)
        self.assertIn("reason", result)
        self.assertTrue(result["reason"])


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


class DetailPageSectionTests(unittest.TestCase):
    def test_section_is_empty_for_providers_without_rows(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        from build import pricing_section

        self.assertEqual(pricing_section("no-rows-here", "No Rows Here", [], load_metrics(), date(2026, 8, 29)), "")

    def test_section_escapes_and_lists_rows_with_dates(self) -> None:
        from build import pricing_section

        rows = [make_row(plan="<script>alert(1)</script>")]
        html = pricing_section("neon", "Neon", rows, load_metrics(), date(2026, 8, 29))
        self.assertIn("2026-08-01", html)
        self.assertIn("https://neon.com/pricing", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_section_renders_the_attributes_that_decided_qualification(self) -> None:
        """The fact that made a plan qualify for a shape workload (its recorded
        capacity) must be visible on the page that exists to show evidence —
        otherwise a reader sees `$200.00` with no way to check what earned it.
        """
        from build import pricing_section

        rows = [make_row(
            metric="plan_base_month", value=200.0, included_allowance=0,
            attributes={"storage_gib": 256, "memory_gib": 8},
        )]
        html = pricing_section("neon", "Neon", rows, load_metrics(), date(2026, 8, 29))
        self.assertIn("256", html)
        self.assertIn("GiB", html)
        self.assertIn("storage", html)
        self.assertIn("8", html)
        self.assertIn("memory", html)
        self.assertIn('<th scope="col">Capacity</th>', html)

    def test_section_escapes_attribute_keys_safely_and_never_crashes_on_bad_attributes(self) -> None:
        """`attributes` is attacker-shaped free-form JSON from the dataset, not
        a value the renderer should ever trust blindly — a non-dict value must
        degrade to the empty marker rather than raising.
        """
        from build import pricing_section

        rows = [make_row(metric="plan_base_month", value=9.0, included_allowance=0, attributes="not-a-dict")]
        html = pricing_section("neon", "Neon", rows, load_metrics(), date(2026, 8, 29))
        self.assertIn("compare-miss", html)

    def test_section_shows_miss_marker_when_row_has_no_attributes(self) -> None:
        from build import pricing_section

        rows = [make_row(metric="storage_gib_month", value=0.35)]
        html = pricing_section("neon", "Neon", rows, load_metrics(), date(2026, 8, 29))
        self.assertIn('<span class="compare-miss">—</span>', html)

    def test_section_preserves_existing_caption_and_column_headers(self) -> None:
        from build import pricing_section

        rows = [make_row()]
        html = pricing_section("neon", "Neon", rows, load_metrics(), date(2026, 8, 29))
        self.assertIn('<caption class="sr-only">Observed pricing for Neon</caption>', html)
        for header in ("Plan", "Metric", "Value", "Included", "Capacity", "Observed", "Evidence"):
            self.assertIn(f'<th scope="col">{header}</th>', html)


if __name__ == "__main__":
    unittest.main()
