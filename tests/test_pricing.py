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
