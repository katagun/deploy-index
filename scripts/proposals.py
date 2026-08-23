#!/usr/bin/env python3
"""Proposal schema and deterministic validation for weekly catalog research."""

from __future__ import annotations

import copy
from datetime import date
from typing import Any
from urllib.parse import urlparse

from catalog import (
    AVAILABILITY,
    CONFIDENCE,
    ENTITY_TYPES,
    ERAS,
    OPERATING_MODELS,
    STATUSES,
    normalize_domain,
    validate_catalog,
)

RESEARCH_CONFIDENCE = {"low", "medium", "high"}
AUTO_APPLY_CONFIDENCE = {"medium", "high"}
SAFE_UPDATE_FIELDS = {
    "name",
    "url",
    "entity_type",
    "primary_category",
    "categories",
    "capabilities",
    "operating_models",
    "era",
    "open_source",
    "summary",
    "best_for",
}


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    """Represent nullable values in a JSON Schema accepted by Structured Outputs."""
    if "type" in schema and isinstance(schema["type"], str):
        result = dict(schema)
        result["type"] = [schema["type"], "null"]
        return result
    return {"anyOf": [schema, {"type": "null"}]}


def research_output_schema(category_names: list[str]) -> dict[str, Any]:
    """Schema supplied to the Responses API for strict structured extraction."""
    https_url = {"type": "string", "pattern": "^https://", "minLength": 9, "maxLength": 500}
    source_urls = {
        "type": "array",
        "minItems": 1,
        "maxItems": 12,
        "items": https_url,
    }
    categories = {
        "type": "array",
        "minItems": 1,
        "maxItems": 8,
        "items": {"type": "string", "enum": category_names},
    }
    capabilities = {
        "type": "array",
        "maxItems": 20,
        "items": {"type": "string", "minLength": 2, "maxLength": 60},
    }
    operating_models = {
        "type": "array",
        "minItems": 1,
        "maxItems": 6,
        "items": {"type": "string", "enum": sorted(OPERATING_MODELS)},
    }
    confidence = {"type": "string", "enum": sorted(RESEARCH_CONFIDENCE)}

    candidate_properties: dict[str, Any] = {
        "slug": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$", "maxLength": 100},
        "name": {"type": "string", "minLength": 1, "maxLength": 100},
        "url": https_url,
        "entity_type": {"type": "string", "enum": sorted(ENTITY_TYPES)},
        "parent_slug": _nullable({"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"}),
        "primary_category": {"type": "string", "enum": category_names},
        "categories": categories,
        "capabilities": capabilities,
        "operating_models": operating_models,
        "era": {"type": "string", "enum": sorted(ERAS)},
        "status": {"type": "string", "enum": ["active", "beta", "transitioning"]},
        "availability": {"type": "string", "enum": ["general", "preview", "limited"]},
        "open_source": {"type": "boolean"},
        "launch_year": _nullable({"type": "integer", "minimum": 1990, "maximum": 2100}),
        "summary": {"type": "string", "minLength": 20, "maxLength": 500},
        "best_for": {"type": "string", "minLength": 20, "maxLength": 500},
        "source_urls": source_urls,
        "confidence": confidence,
        "change_note": {"type": "string", "minLength": 10, "maxLength": 500},
    }

    patch_properties: dict[str, Any] = {
        "name": _nullable({"type": "string", "minLength": 1, "maxLength": 100}),
        "url": _nullable(https_url),
        "entity_type": _nullable({"type": "string", "enum": sorted(ENTITY_TYPES)}),
        "parent_slug_action": {"type": "string", "enum": ["keep", "set", "clear"]},
        "parent_slug": _nullable({"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"}),
        "primary_category": _nullable({"type": "string", "enum": category_names}),
        "categories": _nullable(categories),
        "capabilities": _nullable(capabilities),
        "operating_models": _nullable(operating_models),
        "era": _nullable({"type": "string", "enum": sorted(ERAS)}),
        "open_source": {"type": ["boolean", "null"]},
        "launch_year_action": {"type": "string", "enum": ["keep", "set", "clear"]},
        "launch_year": _nullable({"type": "integer", "minimum": 1990, "maximum": 2100}),
        "summary": _nullable({"type": "string", "minLength": 20, "maxLength": 500}),
        "best_for": _nullable({"type": "string", "minLength": 20, "maxLength": 500}),
    }

    def strict_object(properties: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": list(properties),
            "properties": properties,
        }

    return strict_object(
        {
            "research_date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
            "summary": {"type": "string", "minLength": 20, "maxLength": 1500},
            "new_candidates": {
                "type": "array",
                "maxItems": 30,
                "items": strict_object(candidate_properties),
            },
            "updates": {
                "type": "array",
                "maxItems": 80,
                "items": strict_object(
                    {
                        "slug": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"},
                        "patch": strict_object(patch_properties),
                        "source_urls": source_urls,
                        "rationale": {"type": "string", "minLength": 10, "maxLength": 1000},
                        "confidence": confidence,
                    }
                ),
            },
            "status_alerts": {
                "type": "array",
                "maxItems": 60,
                "items": strict_object(
                    {
                        "slug": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"},
                        "proposed_status": {"type": "string", "enum": sorted(STATUSES)},
                        "proposed_availability": {"type": "string", "enum": sorted(AVAILABILITY)},
                        "effective_date": _nullable({"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}),
                        "rationale": {"type": "string", "minLength": 10, "maxLength": 1200},
                        "source_urls": source_urls,
                        "confidence": confidence,
                    }
                ),
            },
            "checked_active": {
                "type": "array",
                "maxItems": 100,
                "items": strict_object(
                    {
                        "slug": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"},
                        "source_urls": source_urls,
                        "note": {"type": "string", "minLength": 10, "maxLength": 500},
                        "confidence": confidence,
                    }
                ),
            },
        }
    )


def catalog_entry_from_candidate(candidate: dict[str, Any], research_date: str) -> dict[str, Any]:
    """Convert a research candidate into a complete catalog entry."""
    return {
        "slug": candidate["slug"],
        "name": candidate["name"].strip(),
        "url": candidate["url"],
        "entity_type": candidate["entity_type"],
        "parent_slug": candidate["parent_slug"],
        "primary_category": candidate["primary_category"],
        "categories": list(dict.fromkeys(candidate["categories"])),
        "capabilities": list(dict.fromkeys(candidate["capabilities"])),
        "operating_models": list(dict.fromkeys(candidate["operating_models"])),
        "era": candidate["era"],
        "status": candidate["status"],
        "availability": candidate["availability"],
        "open_source": candidate["open_source"],
        "launch_year": candidate["launch_year"],
        "featured": False,
        "summary": candidate["summary"].strip(),
        "best_for": candidate["best_for"].strip(),
        "source_urls": list(dict.fromkeys(candidate["source_urls"])),
        "last_verified": research_date,
        "confidence": candidate["confidence"],
        "change_note": candidate["change_note"].strip(),
    }


def _is_https_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("https://") and bool(normalize_domain(value))


def normalize_url_identity(value: str) -> str:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = "/" + "/".join(part for part in parsed.path.split("/") if part)
    return f"{host}{path.rstrip('/')}"


def _validate_sources(sources: Any, prefix: str, errors: list[str]) -> None:
    if not isinstance(sources, list) or not sources:
        errors.append(f"{prefix}: source_urls must be a non-empty array")
        return
    if len(sources) != len(set(sources)):
        errors.append(f"{prefix}: source_urls contains duplicates")
    for source in sources:
        if not _is_https_url(source):
            errors.append(f"{prefix}: invalid source URL {source!r}")


def _domain_is_related(source_domain: str, canonical_domain: str) -> bool:
    return (
        source_domain == canonical_domain
        or source_domain.endswith("." + canonical_domain)
        or canonical_domain.endswith("." + source_domain)
    )


def has_probable_primary_source(item_url: str, sources: list[str], open_source: bool = False) -> bool:
    """Conservative heuristic; human review remains authoritative."""
    canonical = normalize_domain(item_url)
    for source in sources:
        source_domain = normalize_domain(source)
        if _domain_is_related(source_domain, canonical):
            return True
        if open_source and source_domain == "github.com":
            return True
    return False


def validate_proposal(proposal: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    """Validate research output against the live catalog and publication policy."""
    errors: list[str] = []
    required = {"research_date", "summary", "new_candidates", "updates", "status_alerts", "checked_active"}
    missing = required - proposal.keys()
    if missing:
        return [f"Proposal missing top-level keys: {sorted(missing)}"]

    try:
        date.fromisoformat(proposal["research_date"])
    except (TypeError, ValueError):
        errors.append("research_date must be an ISO date")

    categories = set(catalog["category_labels"])
    providers = catalog["providers"]
    by_slug = {item["slug"]: item for item in providers}
    existing_names = {item["name"].casefold(): item["slug"] for item in providers}
    existing_urls: dict[str, set[str]] = {}
    existing_provider_domains: dict[str, set[str]] = {}
    for item in providers:
        existing_urls.setdefault(normalize_url_identity(item["url"]), set()).add(item["slug"])
        if item["entity_type"] == "provider":
            existing_provider_domains.setdefault(normalize_domain(item["url"]), set()).add(item["slug"])

    candidate_slugs: set[str] = set()
    candidate_names: set[str] = set()
    candidate_urls: set[str] = set()
    candidate_provider_domains: set[str] = set()
    candidates = proposal.get("new_candidates", [])
    if not isinstance(candidates, list):
        errors.append("new_candidates must be an array")
        candidates = []
    for index, candidate in enumerate(candidates):
        prefix = f"new_candidates[{index}]"
        if not isinstance(candidate, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        try:
            entry = catalog_entry_from_candidate(candidate, proposal["research_date"])
        except KeyError as exc:
            errors.append(f"{prefix}: missing field {exc.args[0]!r}")
            continue
        slug = entry["slug"]
        folded_name = entry["name"].casefold()
        domain = normalize_domain(entry["url"])
        url_identity = normalize_url_identity(entry["url"])
        if slug in by_slug:
            errors.append(f"{prefix}: slug {slug!r} already exists; propose an update instead")
        if slug in candidate_slugs:
            errors.append(f"{prefix}: duplicate candidate slug {slug!r}")
        candidate_slugs.add(slug)
        if folded_name in existing_names:
            errors.append(f"{prefix}: name duplicates existing slug {existing_names[folded_name]!r}")
        if folded_name in candidate_names:
            errors.append(f"{prefix}: duplicate candidate name {entry['name']!r}")
        candidate_names.add(folded_name)
        if url_identity in existing_urls:
            errors.append(f"{prefix}: canonical URL already used by {sorted(existing_urls[url_identity])}")
        if url_identity in candidate_urls:
            errors.append(f"{prefix}: duplicate candidate canonical URL {entry['url']!r}")
        candidate_urls.add(url_identity)
        if entry["entity_type"] == "provider" and domain in existing_provider_domains:
            errors.append(f"{prefix}: provider domain already represented by {sorted(existing_provider_domains[domain])}")
        if entry["entity_type"] == "provider" and domain in candidate_provider_domains:
            errors.append(f"{prefix}: duplicate candidate provider domain {domain!r}")
        if entry["entity_type"] == "provider":
            candidate_provider_domains.add(domain)
        if entry["confidence"] not in RESEARCH_CONFIDENCE:
            errors.append(f"{prefix}: confidence must be low, medium, or high")
        if entry["status"] not in {"active", "beta", "transitioning"}:
            errors.append(f"{prefix}: new candidates cannot start archived or sunset")
        if entry["availability"] not in {"general", "preview", "limited"}:
            errors.append(f"{prefix}: invalid new-candidate availability")
        if entry["primary_category"] not in categories:
            errors.append(f"{prefix}: unknown primary category")
        _validate_sources(entry["source_urls"], prefix, errors)
        if not has_probable_primary_source(entry["url"], entry["source_urls"], entry["open_source"]):
            errors.append(f"{prefix}: needs at least one probable first-party source")

    allowed_parent_slugs = set(by_slug) | candidate_slugs
    temp_catalog = copy.deepcopy(catalog)
    temp_catalog["providers"].extend(catalog_entry_from_candidate(c, proposal["research_date"]) for c in candidates if isinstance(c, dict) and all(k in c for k in ["slug", "name", "url", "entity_type", "parent_slug", "primary_category", "categories", "capabilities", "operating_models", "era", "status", "availability", "open_source", "launch_year", "summary", "best_for", "source_urls", "confidence", "change_note"]))
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("parent_slug") not in (None, *allowed_parent_slugs):
            errors.append(f"candidate {candidate.get('slug')!r}: unknown parent_slug {candidate.get('parent_slug')!r}")
    # Reuse the full catalog validator to enforce field shapes and cross references.
    errors.extend(f"candidate catalog: {error}" for error in validate_catalog(temp_catalog))

    seen_updates: set[str] = set()
    updates = proposal.get("updates", [])
    if not isinstance(updates, list):
        errors.append("updates must be an array")
        updates = []
    for index, update in enumerate(updates):
        prefix = f"updates[{index}]"
        if not isinstance(update, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        slug = update.get("slug")
        if slug not in by_slug:
            errors.append(f"{prefix}: unknown slug {slug!r}")
        if slug in seen_updates:
            errors.append(f"{prefix}: duplicate update for {slug!r}")
        seen_updates.add(slug)
        if update.get("confidence") not in RESEARCH_CONFIDENCE:
            errors.append(f"{prefix}: invalid confidence")
        _validate_sources(update.get("source_urls"), prefix, errors)
        patch = update.get("patch")
        if not isinstance(patch, dict):
            errors.append(f"{prefix}: patch must be an object")
            continue
        meaningful = any(patch.get(field) is not None for field in SAFE_UPDATE_FIELDS)
        meaningful = meaningful or patch.get("parent_slug_action") != "keep" or patch.get("launch_year_action") != "keep"
        if not meaningful:
            errors.append(f"{prefix}: patch contains no changes")
        if patch.get("primary_category") is not None and patch["primary_category"] not in categories:
            errors.append(f"{prefix}: unknown primary category")
        if patch.get("categories") is not None:
            unknown = set(patch["categories"]) - categories
            if unknown:
                errors.append(f"{prefix}: unknown categories {sorted(unknown)}")
        if patch.get("operating_models") is not None:
            unknown = set(patch["operating_models"]) - OPERATING_MODELS
            if unknown:
                errors.append(f"{prefix}: unknown operating models {sorted(unknown)}")
        if patch.get("entity_type") is not None and patch["entity_type"] not in ENTITY_TYPES:
            errors.append(f"{prefix}: invalid entity_type")
        if patch.get("era") is not None and patch["era"] not in ERAS:
            errors.append(f"{prefix}: invalid era")
        if patch.get("url") is not None and not _is_https_url(patch["url"]):
            errors.append(f"{prefix}: invalid URL")
        canonical_for_sources = patch.get("url") or (by_slug.get(slug) or {}).get("url", "")
        open_source_for_sources = patch.get("open_source")
        if open_source_for_sources is None and slug in by_slug:
            open_source_for_sources = by_slug[slug]["open_source"]
        if canonical_for_sources and isinstance(update.get("source_urls"), list) and not has_probable_primary_source(canonical_for_sources, update["source_urls"], bool(open_source_for_sources)):
            errors.append(f"{prefix}: needs at least one probable first-party source")
        parent_action = patch.get("parent_slug_action")
        if parent_action not in {"keep", "set", "clear"}:
            errors.append(f"{prefix}: invalid parent_slug_action")
        if parent_action == "set" and patch.get("parent_slug") not in allowed_parent_slugs:
            errors.append(f"{prefix}: unknown proposed parent_slug")
        if parent_action == "set" and patch.get("parent_slug") == slug:
            errors.append(f"{prefix}: parent_slug cannot reference itself")
        launch_action = patch.get("launch_year_action")
        if launch_action not in {"keep", "set", "clear"}:
            errors.append(f"{prefix}: invalid launch_year_action")
        if launch_action == "set" and not isinstance(patch.get("launch_year"), int):
            errors.append(f"{prefix}: launch_year_action=set requires an integer launch_year")

    seen_alerts: set[str] = set()
    alerts = proposal.get("status_alerts", [])
    if not isinstance(alerts, list):
        errors.append("status_alerts must be an array")
        alerts = []
    for index, alert in enumerate(alerts):
        prefix = f"status_alerts[{index}]"
        slug = alert.get("slug") if isinstance(alert, dict) else None
        if slug not in by_slug:
            errors.append(f"{prefix}: unknown slug {slug!r}")
        if slug in seen_alerts:
            errors.append(f"{prefix}: duplicate status alert for {slug!r}")
        seen_alerts.add(slug)
        if isinstance(alert, dict):
            if alert.get("proposed_status") not in STATUSES:
                errors.append(f"{prefix}: invalid status")
            if alert.get("proposed_availability") not in AVAILABILITY:
                errors.append(f"{prefix}: invalid availability")
            if alert.get("confidence") not in RESEARCH_CONFIDENCE:
                errors.append(f"{prefix}: invalid confidence")
            effective = alert.get("effective_date")
            if effective is not None:
                try:
                    date.fromisoformat(effective)
                except (TypeError, ValueError):
                    errors.append(f"{prefix}: effective_date must be ISO date or null")
            _validate_sources(alert.get("source_urls"), prefix, errors)
            if slug in by_slug and isinstance(alert.get("source_urls"), list) and not has_probable_primary_source(by_slug[slug]["url"], alert["source_urls"], by_slug[slug]["open_source"]):
                errors.append(f"{prefix}: needs at least one probable first-party source")

    seen_checked: set[str] = set()
    checked = proposal.get("checked_active", [])
    if not isinstance(checked, list):
        errors.append("checked_active must be an array")
        checked = []
    for index, item in enumerate(checked):
        prefix = f"checked_active[{index}]"
        slug = item.get("slug") if isinstance(item, dict) else None
        if slug not in by_slug:
            errors.append(f"{prefix}: unknown slug {slug!r}")
        elif by_slug[slug]["status"] in {"archived", "sunset"}:
            errors.append(f"{prefix}: archived/sunset entries cannot be checked_active")
        if slug in seen_checked:
            errors.append(f"{prefix}: duplicate checked_active slug {slug!r}")
        seen_checked.add(slug)
        if isinstance(item, dict):
            if item.get("confidence") not in RESEARCH_CONFIDENCE:
                errors.append(f"{prefix}: invalid confidence")
            _validate_sources(item.get("source_urls"), prefix, errors)
            if slug in by_slug and isinstance(item.get("source_urls"), list) and not has_probable_primary_source(by_slug[slug]["url"], item["source_urls"], by_slug[slug]["open_source"]):
                errors.append(f"{prefix}: needs at least one probable first-party source")

    return errors


def proposal_stats(proposal: dict[str, Any]) -> dict[str, int]:
    return {
        "new_candidates": len(proposal.get("new_candidates", [])),
        "updates": len(proposal.get("updates", [])),
        "status_alerts": len(proposal.get("status_alerts", [])),
        "checked_active": len(proposal.get("checked_active", [])),
    }
