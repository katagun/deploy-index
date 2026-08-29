from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import copy  # noqa: E402

from apply_proposal import apply_proposal  # noqa: E402
from catalog import (  # noqa: E402
    AVAILABILITY,
    CONFIDENCE,
    ENTITY_TYPES,
    ERAS,
    OPERATING_MODELS,
    REQUIRED_PROVIDER_FIELDS,
    STATUSES,
    load_catalog,
    validate_catalog,
)
from proposals import research_output_schema, validate_proposal  # noqa: E402
from research import select_rotation  # noqa: E402


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.fixture = json.loads((ROOT / "tests" / "fixtures" / "research-output.json").read_text(encoding="utf-8"))

    def test_catalog_is_valid(self) -> None:
        self.assertEqual(validate_catalog(self.catalog), [])

    def test_catalog_has_unique_provider_pages(self) -> None:
        slugs = [item["slug"] for item in self.catalog["providers"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertGreaterEqual(len(slugs), 250)

    def test_structured_output_schema_is_strict(self) -> None:
        schema = research_output_schema(list(self.catalog["category_labels"]))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(schema["properties"]))
        candidate = schema["properties"]["new_candidates"]["items"]
        self.assertFalse(candidate["additionalProperties"])
        self.assertEqual(set(candidate["required"]), set(candidate["properties"]))

    def test_structured_output_schema_honors_configured_limits(self) -> None:
        schema = research_output_schema(list(self.catalog["category_labels"]), max_new_candidates=5, max_updates=7)
        self.assertEqual(schema["properties"]["new_candidates"]["maxItems"], 5)
        self.assertEqual(schema["properties"]["updates"]["maxItems"], 7)

    def test_fixture_proposal_is_valid(self) -> None:
        self.assertEqual(validate_proposal(self.fixture, self.catalog), [])

    def test_proposal_application_is_conservative(self) -> None:
        result, report = apply_proposal(self.catalog, self.fixture)
        self.assertEqual(validate_catalog(result), [])
        by_slug = {item["slug"]: item for item in result["providers"]}
        self.assertIn("fixture-hosting-labs", by_slug)
        self.assertEqual(by_slug["fly-io"]["last_verified"], "2026-08-23")
        self.assertIn("railway", report["updated"])
        self.assertIn("aws-app-runner", report["status_alerts_not_applied"])
        # The status alert is deliberately not applied by the scheduled path.
        self.assertNotEqual(by_slug["aws-app-runner"]["status"], "archived")

    def test_published_json_schema_matches_validator_constants(self) -> None:
        schema = json.loads((ROOT / "catalog" / "schema.json").read_text(encoding="utf-8"))
        provider = schema["$defs"]["provider"]
        properties = provider["properties"]
        self.assertEqual(set(provider["required"]), REQUIRED_PROVIDER_FIELDS)
        self.assertEqual(set(properties), REQUIRED_PROVIDER_FIELDS)
        self.assertEqual(set(properties["entity_type"]["enum"]), ENTITY_TYPES)
        self.assertEqual(set(properties["era"]["enum"]), ERAS)
        self.assertEqual(set(properties["status"]["enum"]), STATUSES)
        self.assertEqual(set(properties["availability"]["enum"]), AVAILABILITY)
        self.assertEqual(set(properties["confidence"]["enum"]), CONFIDENCE)
        self.assertEqual(set(properties["operating_models"]["items"]["enum"]), OPERATING_MODELS)

    def test_duplicate_canonical_urls_are_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        first, second = catalog["providers"][0], catalog["providers"][1]
        second["url"] = first["url"] + "#fragment"
        errors = validate_catalog(catalog)
        self.assertTrue(any("duplicate canonical url" in error.lower() for error in errors), errors)

    def test_duplicate_provider_domains_are_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        providers_only = [item for item in catalog["providers"] if item["entity_type"] == "provider"]
        first, second = providers_only[0], providers_only[1]
        second["url"] = first["url"].rstrip("/") + "/other-path/"
        errors = validate_catalog(catalog)
        self.assertTrue(any("provider domain" in error.lower() for error in errors), errors)

    def test_weekly_rotation_is_reproducible(self) -> None:
        first = select_rotation(self.catalog["providers"], 45, date(2026, 8, 23))
        second = select_rotation(self.catalog["providers"], 45, date(2026, 8, 23))
        other_week = select_rotation(self.catalog["providers"], 45, date(2026, 8, 30))
        self.assertEqual([x["slug"] for x in first], [x["slug"] for x in second])
        self.assertNotEqual([x["slug"] for x in first], [x["slug"] for x in other_week])
        self.assertEqual(len(first), 45)

    def test_database_platforms_are_discoverable_by_category(self) -> None:
        by_slug = {item["slug"]: item for item in self.catalog["providers"]}
        for slug in ("supabase", "firebase", "planetscale", "amazon-rds"):
            self.assertIn(slug, by_slug, f"{slug} must exist in the catalog")
            self.assertIn(
                "database-platform",
                by_slug[slug]["categories"],
                f"{slug} must be discoverable under database-platform",
            )


if __name__ == "__main__":
    unittest.main()
