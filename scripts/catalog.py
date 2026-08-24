#!/usr/bin/env python3
"""Shared catalog utilities for validation, builds, and research."""

from __future__ import annotations

import json
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "providers.json"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENTITY_TYPES = {"provider", "product", "project"}
ERAS = {"established", "modern", "recent"}
STATUSES = {"active", "beta", "transitioning", "sunset", "archived"}
AVAILABILITY = {"general", "preview", "limited", "existing-customers-only", "discontinued"}
CONFIDENCE = {"seed", "low", "medium", "high"}
OPERATING_MODELS = {
    "managed-cloud",
    "bring-your-own-cloud",
    "self-hosted",
    "dedicated-server",
    "marketplace",
    "decentralized-network",
}
REQUIRED_PROVIDER_FIELDS = {
    "slug", "name", "url", "entity_type", "parent_slug", "primary_category", "categories",
    "capabilities", "operating_models", "era", "status", "availability", "open_source",
    "launch_year", "featured", "summary", "best_for", "source_urls", "last_verified",
    "confidence", "change_note",
}


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        tmp = Path(handle.name)
    tmp.replace(path)


def normalize_domain(url: str) -> str:
    host = urlparse(url).hostname or ""
    return host.lower().removeprefix("www.")


def normalize_url_identity(value: str) -> str:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = "/" + "/".join(part for part in parsed.path.split("/") if part)
    return f"{host}{path.rstrip('/')}"


def validate_catalog(catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_top = {"schema_version", "catalog_name", "generated_on", "methodology", "category_labels", "providers"}
    missing_top = required_top - catalog.keys()
    if missing_top:
        errors.append(f"Missing top-level keys: {sorted(missing_top)}")
        return errors
    if catalog["schema_version"] != 1:
        errors.append("schema_version must be 1")
    if not isinstance(catalog.get("catalog_name"), str) or not catalog["catalog_name"].strip():
        errors.append("catalog_name must be a non-empty string")
    if not isinstance(catalog.get("methodology"), str) or not catalog["methodology"].strip():
        errors.append("methodology must be a non-empty string")
    try:
        generated_on = date.fromisoformat(catalog.get("generated_on"))
        if generated_on > date.today():
            errors.append("generated_on cannot be in the future")
    except (TypeError, ValueError):
        errors.append("generated_on must be an ISO date")
    categories = catalog.get("category_labels", {})
    if not isinstance(categories, dict) or not categories:
        errors.append("category_labels must be a non-empty object")
        categories = {}
    else:
        for key, value in categories.items():
            if not isinstance(key, str) or not SLUG_RE.fullmatch(key):
                errors.append(f"Invalid category key: {key!r}")
            if not isinstance(value, str) or not value.strip():
                errors.append(f"Category {key!r} must have a non-empty label")
    providers = catalog.get("providers", [])
    if not isinstance(providers, list):
        return errors + ["providers must be an array"]

    slugs: set[str] = set()
    names: dict[str, list[str]] = {}
    url_identities: dict[str, list[str]] = {}
    provider_domains: dict[str, list[str]] = {}
    for index, item in enumerate(providers):
        prefix = f"providers[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = REQUIRED_PROVIDER_FIELDS - item.keys()
        if missing:
            errors.append(f"{prefix} missing keys: {sorted(missing)}")
            continue
        slug = item["slug"]
        if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
            errors.append(f"{prefix}.slug is invalid: {slug!r}")
        elif slug in slugs:
            errors.append(f"Duplicate slug: {slug}")
        else:
            slugs.add(slug)
        name = item["name"]
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            errors.append(f"{slug}: name must be a non-empty string of at most 100 characters")
        names.setdefault(str(name).casefold(), []).append(str(slug))
        if item["entity_type"] not in ENTITY_TYPES:
            errors.append(f"{slug}: invalid entity_type {item['entity_type']!r}")
        if item["era"] not in ERAS:
            errors.append(f"{slug}: invalid era {item['era']!r}")
        if item["status"] not in STATUSES:
            errors.append(f"{slug}: invalid status {item['status']!r}")
        if item["availability"] not in AVAILABILITY:
            errors.append(f"{slug}: invalid availability {item['availability']!r}")
        if item["confidence"] not in CONFIDENCE:
            errors.append(f"{slug}: invalid confidence {item['confidence']!r}")
        if item["primary_category"] not in categories:
            errors.append(f"{slug}: unknown primary category {item['primary_category']!r}")
        item_categories = item["categories"]
        if not isinstance(item_categories, list) or not all(isinstance(value, str) for value in item_categories):
            errors.append(f"{slug}: categories must be an array of strings")
        elif item["primary_category"] not in item_categories:
            errors.append(f"{slug}: categories must include primary_category")
        else:
            unknown = sorted(set(item_categories) - set(categories))
            if unknown:
                errors.append(f"{slug}: unknown categories {unknown}")
            if len(item_categories) != len(set(item_categories)):
                errors.append(f"{slug}: duplicate categories")
        capabilities = item["capabilities"]
        if not isinstance(capabilities, list) or not all(isinstance(value, str) and value.strip() for value in capabilities):
            errors.append(f"{slug}: capabilities must be an array of non-empty strings")
        elif len(capabilities) != len(set(capabilities)):
            errors.append(f"{slug}: duplicate capabilities")
        models = item["operating_models"]
        if not isinstance(models, list) or not models or not all(isinstance(value, str) for value in models):
            errors.append(f"{slug}: operating_models must be a non-empty array of strings")
        else:
            unknown_models = sorted(set(models) - OPERATING_MODELS)
            if unknown_models:
                errors.append(f"{slug}: invalid operating_models {unknown_models}")
            if len(models) != len(set(models)):
                errors.append(f"{slug}: duplicate operating_models")
        if not isinstance(item["open_source"], bool):
            errors.append(f"{slug}: open_source must be boolean")
        if not isinstance(item["featured"], bool):
            errors.append(f"{slug}: featured must be boolean")
        for field in ("url",):
            value = item[field]
            if not isinstance(value, str) or not value.startswith("https://") or not normalize_domain(value):
                errors.append(f"{slug}: {field} must be a valid https URL")
            else:
                url_identities.setdefault(normalize_url_identity(value), []).append(str(slug))
                if item["entity_type"] == "provider":
                    provider_domains.setdefault(normalize_domain(value), []).append(str(slug))
        source_urls = item["source_urls"]
        if not isinstance(source_urls, list) or not source_urls:
            errors.append(f"{slug}: source_urls must be non-empty")
        else:
            for source in source_urls:
                if not isinstance(source, str) or not source.startswith("https://") or not normalize_domain(source):
                    errors.append(f"{slug}: invalid source URL {source!r}")
        launch_year = item["launch_year"]
        if launch_year is not None and (isinstance(launch_year, bool) or not isinstance(launch_year, int) or not (1990 <= launch_year <= date.today().year + 1)):
            errors.append(f"{slug}: launch_year must be an integer in range or null")
        if item["last_verified"] is not None:
            try:
                verified_date = date.fromisoformat(item["last_verified"])
                if verified_date > date.today():
                    errors.append(f"{slug}: last_verified cannot be in the future")
            except (TypeError, ValueError):
                errors.append(f"{slug}: last_verified must be ISO date or null")
        if item["status"] == "archived" and item["availability"] != "discontinued":
            errors.append(f"{slug}: archived entries must be discontinued")
        text_limits = {"summary": (20, 500), "best_for": (20, 500), "change_note": (1, 500)}
        for field, (minimum, maximum) in text_limits.items():
            text = item[field]
            if not isinstance(text, str) or not text.strip() or not (minimum <= len(text) <= maximum):
                errors.append(f"{slug}: {field} must contain {minimum}-{maximum} characters")
            if isinstance(text, str) and ("<script" in text.lower() or "javascript:" in text.lower()):
                errors.append(f"{slug}: unsafe content in {field}")

    for item in providers:
        parent = item.get("parent_slug")
        if parent is not None and (not isinstance(parent, str) or parent not in slugs):
            errors.append(f"{item.get('slug')}: parent_slug {parent!r} does not exist")
        if parent == item.get("slug"):
            errors.append(f"{item.get('slug')}: parent_slug cannot reference itself")

    for folded_name, name_slugs in names.items():
        if len(name_slugs) > 1:
            errors.append(f"Duplicate name {folded_name!r}: {sorted(name_slugs)}")

    for identity, identity_slugs in url_identities.items():
        if len(identity_slugs) > 1:
            errors.append(f"Duplicate canonical URL {identity!r}: {sorted(identity_slugs)}")

    for domain, domain_slugs in provider_domains.items():
        if len(domain_slugs) > 1:
            errors.append(f"Provider domain {domain!r} represented by multiple providers: {sorted(domain_slugs)}")

    return errors
