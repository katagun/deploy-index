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

    def test_profiles_do_not_embed_undated_price_quotes(self) -> None:
        forbidden = {"price", "monthly_price", "hourly_price", "currency", "free_credit"}
        for profile in self.payload["profiles"]:
            self.assertFalse(forbidden & set(profile), profile["slug"])


if __name__ == "__main__":
    unittest.main()
