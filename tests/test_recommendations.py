from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from catalog import load_catalog  # noqa: E402
from recommendations import (  # noqa: E402
    BOOLEANS,
    NUMERIC,
    build_recommendation_catalog,
    validate_recommendation_catalog,
)


class RecommendationProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.payload = build_recommendation_catalog(cls.catalog)
        cls.by_slug = {profile["slug"]: profile for profile in cls.payload["profiles"]}

    def test_recommendation_catalog_is_valid_and_complete(self) -> None:
        self.assertEqual(validate_recommendation_catalog(self.payload, self.catalog), [])
        self.assertEqual(len(self.payload["profiles"]), len(self.catalog["providers"]))

    def test_every_profile_has_bounded_traits(self) -> None:
        for profile in self.payload["profiles"]:
            for field in NUMERIC:
                self.assertIn(profile[field], range(1, 6), f"{profile['slug']}:{field}")
            for field in BOOLEANS:
                self.assertIsInstance(profile[field], bool, f"{profile['slug']}:{field}")

    def test_curated_platforms_encode_known_selection_shapes(self) -> None:
        workers = self.by_slug["cloudflare-workers"]
        self.assertIn("static-site", workers["workloads"])
        self.assertTrue(workers["free_entry"])
        self.assertEqual(workers["global_reach"], 5)

        fly = self.by_slug["fly-io"]
        self.assertIn("docker-image", fly["artifacts"])
        self.assertIn("tcp", fly["protocols"])
        self.assertIn("udp", fly["protocols"])

        coolify = self.by_slug["coolify"]
        self.assertTrue(coolify["open_source"])
        self.assertIn("docker-compose", coolify["artifacts"])
        self.assertEqual(coolify["portability"], 5)

    def test_free_tier_platforms_are_tagged_in_catalog_data(self) -> None:
        representative = {
            "supabase", "neon", "mongodb-atlas", "oracle-cloud", "aws-lambda",
            "google-cloud-run", "render", "koyeb", "github-pages", "wordpress-com",
        }
        for slug in representative:
            self.assertTrue(self.by_slug[slug]["free_entry"], f"{slug} should carry a free-tier tag")
        free_count = sum(1 for profile in self.payload["profiles"] if profile["free_entry"])
        self.assertGreaterEqual(free_count, 50, "free-tier coverage should be data-driven, not override-only")

    def test_free_tier_capability_derives_free_entry(self) -> None:
        entry = dict(next(item for item in self.catalog["providers"] if item["slug"] == "railway"))
        entry = {**entry, "slug": "free-tier-host", "name": "Free Tier Host", "url": "https://free-tier-host.example/",
                 "capabilities": sorted({*entry["capabilities"], "free-tier"})}
        catalog = {**self.catalog, "providers": [entry]}
        overrides = {"methodology": "m", "disclaimer": "d", "dimensions": {}, "overrides": {}}
        payload = build_recommendation_catalog(catalog, overrides)
        profile = payload["profiles"][0]
        self.assertTrue(profile["free_entry"])
        self.assertIn("free-entry", profile["billing_models"])

    def test_profiles_do_not_embed_undated_price_quotes(self) -> None:
        forbidden = {"price", "monthly_price", "hourly_price", "currency", "free_credit"}
        for profile in self.payload["profiles"]:
            self.assertFalse(forbidden & set(profile), profile["slug"])


if __name__ == "__main__":
    unittest.main()
