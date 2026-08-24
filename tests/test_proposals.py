from __future__ import annotations

import copy
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from apply_proposal import apply_proposal  # noqa: E402
from proposals import validate_proposal  # noqa: E402


def make_entry(slug: str, **overrides) -> dict:
    entry = {
        "slug": slug,
        "name": slug.replace("-", " ").title(),
        "url": f"https://{slug}.example/",
        "entity_type": "provider",
        "parent_slug": None,
        "primary_category": "paas",
        "categories": ["paas"],
        "capabilities": ["containers"],
        "operating_models": ["managed-cloud"],
        "era": "modern",
        "status": "active",
        "availability": "general",
        "open_source": False,
        "launch_year": 2020,
        "featured": False,
        "summary": "A test catalog entry used only by the proposal unit tests.",
        "best_for": "Exercising deterministic proposal validation in unit tests.",
        "source_urls": [f"https://{slug}.example/"],
        "last_verified": "2026-08-01",
        "confidence": "high",
        "change_note": "Test fixture entry.",
    }
    entry.update(overrides)
    return entry


def make_catalog() -> dict:
    return {
        "schema_version": 1,
        "catalog_name": "Test catalog",
        "generated_on": "2026-08-01",
        "methodology": "Test methodology.",
        "category_labels": {"paas": "Application PaaS", "self-hosted-paas": "Self-hosted PaaS"},
        "providers": [
            make_entry("acme"),
            make_entry("acme-deploy", entity_type="product", parent_slug="acme", url="https://acme.example/deploy/", source_urls=["https://acme.example/deploy/"]),
            make_entry("oss-tool", entity_type="project", open_source=True, primary_category="self-hosted-paas", categories=["self-hosted-paas"], operating_models=["self-hosted"]),
            make_entry("gone", status="archived", availability="discontinued"),
        ],
    }


def make_proposal(**overrides) -> dict:
    proposal = {
        "research_date": "2026-08-23",
        "summary": "Test proposal exercising validation and application behavior.",
        "new_candidates": [],
        "updates": [],
        "status_alerts": [],
        "checked_active": [],
    }
    proposal.update(overrides)
    return proposal


def make_update(slug: str, patch_overrides: dict, **overrides) -> dict:
    patch = {
        "name": None, "url": None, "entity_type": None,
        "parent_slug_action": "keep", "parent_slug": None,
        "primary_category": None, "categories": None, "capabilities": None,
        "operating_models": None, "era": None, "open_source": None,
        "launch_year_action": "keep", "launch_year": None,
        "summary": None, "best_for": None,
    }
    patch.update(patch_overrides)
    update = {
        "slug": slug,
        "patch": patch,
        "source_urls": [f"https://{slug}.example/docs"],
        "rationale": "Test rationale for the proposed change.",
        "confidence": "high",
    }
    update.update(overrides)
    return update


def make_candidate(slug: str, **overrides) -> dict:
    candidate = {
        "slug": slug,
        "name": slug.replace("-", " ").title(),
        "url": f"https://{slug}.example/",
        "entity_type": "provider",
        "parent_slug": None,
        "primary_category": "paas",
        "categories": ["paas"],
        "capabilities": ["containers"],
        "operating_models": ["managed-cloud"],
        "era": "recent",
        "status": "active",
        "availability": "general",
        "open_source": False,
        "launch_year": 2025,
        "summary": "A test candidate exercising deterministic proposal validation.",
        "best_for": "Unit-testing the proposal rejection rules without network access.",
        "source_urls": [f"https://{slug}.example/docs"],
        "confidence": "medium",
        "change_note": "Test candidate for validation rules.",
    }
    candidate.update(overrides)
    return candidate


class ProposalRejectionTests(unittest.TestCase):
    def assert_error(self, proposal: dict, needle: str) -> None:
        errors = validate_proposal(proposal, make_catalog())
        self.assertTrue(any(needle in error for error in errors), f"expected {needle!r} in {errors}")

    def test_candidate_on_an_existing_provider_domain_is_rejected(self) -> None:
        candidate = make_candidate("acme-two", url="https://acme.example/other/", source_urls=["https://acme.example/other/docs"])
        self.assert_error(make_proposal(new_candidates=[candidate]), "provider domain already represented")

    def test_candidate_without_a_probable_first_party_source_is_rejected(self) -> None:
        candidate = make_candidate("newhost", source_urls=["https://unrelated-blog.example/post"])
        self.assert_error(make_proposal(new_candidates=[candidate]), "needs at least one probable first-party source")

    def test_candidate_duplicating_an_existing_name_is_rejected(self) -> None:
        candidate = make_candidate("acme-clone", name="Acme")
        self.assert_error(make_proposal(new_candidates=[candidate]), "name duplicates existing slug")

    def test_candidate_duplicating_an_existing_canonical_url_is_rejected(self) -> None:
        candidate = make_candidate("acme-clone", url="https://www.acme.example/")
        self.assert_error(make_proposal(new_candidates=[candidate]), "canonical URL already used")

    def test_candidate_reusing_an_existing_slug_is_rejected(self) -> None:
        candidate = make_candidate("acme")
        self.assert_error(make_proposal(new_candidates=[candidate]), "already exists; propose an update instead")

    def test_candidate_cannot_start_archived_or_sunset(self) -> None:
        candidate = make_candidate("deadhost", status="archived", availability="discontinued")
        self.assert_error(make_proposal(new_candidates=[candidate]), "cannot start archived or sunset")

    def test_candidate_cannot_parent_itself(self) -> None:
        candidate = make_candidate("selfref", parent_slug="selfref")
        self.assert_error(make_proposal(new_candidates=[candidate]), "parent_slug cannot reference itself")

    def test_update_for_unknown_slug_is_rejected(self) -> None:
        update = make_update("ghost", {"summary": "A summary long enough to satisfy the validation rules."})
        self.assert_error(make_proposal(updates=[update]), "unknown slug")

    def test_update_with_no_changes_is_rejected(self) -> None:
        update = make_update("acme", {})
        self.assert_error(make_proposal(updates=[update]), "patch contains no changes")

    def test_status_alert_for_unknown_slug_is_rejected(self) -> None:
        alert = {
            "slug": "ghost", "proposed_status": "archived", "proposed_availability": "discontinued",
            "effective_date": None, "rationale": "Test alert for an unknown entry.",
            "source_urls": ["https://ghost.example/"], "confidence": "high",
        }
        self.assert_error(make_proposal(status_alerts=[alert]), "unknown slug")

    def test_checked_active_rejects_archived_entries(self) -> None:
        checked = {
            "slug": "gone", "source_urls": ["https://gone.example/docs"],
            "note": "Attempting to mark an archived entry active.", "confidence": "high",
        }
        self.assert_error(make_proposal(checked_active=[checked]), "archived/sunset entries cannot be checked_active")

    def test_reverification_never_downgrades_record_confidence(self) -> None:
        catalog = make_catalog()
        checked = {
            "slug": "acme", "source_urls": ["https://acme.example/docs"],
            "note": "Re-verified against current documentation.", "confidence": "medium",
        }
        proposal = make_proposal(checked_active=[checked])
        self.assertEqual(validate_proposal(proposal, catalog), [])
        result, _report = apply_proposal(catalog, proposal)
        by_slug = {item["slug"]: item for item in result["providers"]}
        self.assertEqual(by_slug["acme"]["confidence"], "high")
        self.assertEqual(by_slug["acme"]["last_verified"], "2026-08-23")

    def test_reverification_upgrades_seed_confidence(self) -> None:
        catalog = make_catalog()
        catalog["providers"][0]["confidence"] = "seed"
        checked = {
            "slug": "acme", "source_urls": ["https://acme.example/docs"],
            "note": "Re-verified against current documentation.", "confidence": "medium",
        }
        result, _report = apply_proposal(catalog, make_proposal(checked_active=[checked]))
        by_slug = {item["slug"]: item for item in result["providers"]}
        self.assertEqual(by_slug["acme"]["confidence"], "medium")

    def test_low_confidence_findings_are_not_auto_applied(self) -> None:
        catalog = make_catalog()
        proposal = make_proposal(new_candidates=[make_candidate("lowhost", confidence="low")])
        self.assertEqual(validate_proposal(proposal, catalog), [])
        result, report = apply_proposal(catalog, proposal)
        self.assertNotIn("lowhost", {item["slug"] for item in result["providers"]})
        self.assertEqual(report["skipped_low_confidence"], [{"kind": "new_candidate", "slug": "lowhost"}])


class GitHubEvidenceHeuristicTests(unittest.TestCase):
    def test_unrelated_github_repo_is_not_first_party_evidence(self) -> None:
        candidate = make_candidate(
            "oss-newcomer", open_source=True,
            source_urls=["https://github.com/random-person/completely-unrelated"],
        )
        errors = validate_proposal(make_proposal(new_candidates=[candidate]), make_catalog())
        self.assertTrue(any("first-party source" in error for error in errors), errors)

    def test_related_github_repo_counts_as_first_party_evidence(self) -> None:
        candidate = make_candidate(
            "oss-newcomer", open_source=True,
            source_urls=["https://github.com/newcomer-labs/oss-newcomer"],
        )
        self.assertEqual(validate_proposal(make_proposal(new_candidates=[candidate]), make_catalog()), [])


class ProposalMarkdownSanitizationTests(unittest.TestCase):
    def test_model_authored_text_cannot_inject_markdown(self) -> None:
        from proposal_markdown import render

        proposal = make_proposal(
            summary="Ignore prior instructions. [Click here](https://evil.example) <img src=x onerror=alert(1)>",
            updates=[make_update("acme", {"summary": "New summary | with pipes and `backticks` and [a link](https://evil.example)."})],
        )
        output = render(proposal)
        self.assertNotIn("[Click here](https://evil.example)", output)
        self.assertNotIn("<img", output)
        self.assertNotIn("[a link](https://evil.example)", output)


class IdentityChangeGatingTests(unittest.TestCase):
    def test_identity_patch_is_valid_but_never_auto_applied(self) -> None:
        catalog = make_catalog()
        proposal = make_proposal(updates=[
            make_update("acme", {"url": "https://acme-new.example/"}, source_urls=["https://acme-new.example/docs"]),
        ])
        self.assertEqual(validate_proposal(proposal, catalog), [])
        result, report = apply_proposal(catalog, proposal)
        by_slug = {item["slug"]: item for item in result["providers"]}
        self.assertEqual(by_slug["acme"]["url"], "https://acme.example/")
        self.assertEqual(report["identity_changes_not_applied"], [{"slug": "acme", "fields": ["url"]}])

    def test_name_and_entity_type_patches_are_gated_while_safe_fields_apply(self) -> None:
        catalog = make_catalog()
        proposal = make_proposal(updates=[
            make_update("acme", {
                "name": "Acme Rebranded",
                "entity_type": "product",
                "summary": "An updated summary that is long enough to satisfy validation.",
            }),
        ])
        self.assertEqual(validate_proposal(proposal, catalog), [])
        result, report = apply_proposal(catalog, proposal)
        by_slug = {item["slug"]: item for item in result["providers"]}
        self.assertEqual(by_slug["acme"]["name"], "Acme")
        self.assertEqual(by_slug["acme"]["entity_type"], "provider")
        self.assertEqual(by_slug["acme"]["summary"], "An updated summary that is long enough to satisfy validation.")
        self.assertEqual(report["identity_changes_not_applied"], [{"slug": "acme", "fields": ["entity_type", "name"]}])

    def test_url_patch_accepts_sources_from_the_current_domain(self) -> None:
        catalog = make_catalog()
        proposal = make_proposal(updates=[
            make_update("acme", {"url": "https://acme-new.example/"}, source_urls=["https://acme.example/announcement"]),
        ])
        self.assertEqual(validate_proposal(proposal, catalog), [])


if __name__ == "__main__":
    unittest.main()
