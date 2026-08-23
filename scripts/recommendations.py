#!/usr/bin/env python3
"""Generate and validate qualitative recommendation profiles for every catalog entry."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from catalog import ROOT, load_catalog

OVERRIDES_PATH = ROOT / "catalog" / "recommendation-overrides.json"

WORKLOADS = {
    "static-site", "frontend-app", "web-api", "background-worker", "container-service",
    "virtual-machine", "kubernetes", "serverless-function", "edge-app", "database",
    "gpu-ai", "agent-sandbox", "game-server", "wordpress", "decentralized-app",
}
ARTIFACTS = {"git-source", "docker-image", "docker-compose", "function-code", "vm-image", "kubernetes-manifest", "wasm", "template"}
BILLING_MODELS = {"free-entry", "usage-based", "tiered-plan", "fixed-instance", "reserved-commit", "byoc-infrastructure", "self-host-infrastructure", "marketplace"}
TRAFFIC = {"steady", "bursty", "spiky", "scheduled", "global"}
PROTOCOLS = {"http", "websocket", "tcp", "udp"}
STATE = {"stateless", "managed-database", "persistent-disk", "object-storage"}
NUMERIC = {"expertise_required", "cost_floor", "cost_predictability", "control", "portability", "maturity", "global_reach", "enterprise_readiness"}
BOOLEANS = {"free_entry", "scale_to_zero", "preview_environments", "private_networking", "gpu"}
LIST_FIELDS = {"workloads", "artifacts", "billing_models", "traffic", "protocols", "state_options"}

CATEGORY_WORKLOADS = {
    "hyperscale-cloud": {"web-api", "background-worker", "container-service", "virtual-machine", "kubernetes", "serverless-function", "database", "gpu-ai"},
    "cloud-vps": {"web-api", "background-worker", "container-service", "virtual-machine"},
    "paas": {"frontend-app", "web-api", "background-worker", "container-service"},
    "managed-containers": {"web-api", "background-worker", "container-service"},
    "serverless-functions": {"web-api", "background-worker", "serverless-function"},
    "edge-compute": {"web-api", "serverless-function", "edge-app"},
    "frontend-hosting": {"static-site", "frontend-app"},
    "static-hosting": {"static-site", "frontend-app"},
    "byoc-platform": {"web-api", "background-worker", "container-service", "kubernetes"},
    "self-hosted-paas": {"web-api", "background-worker", "container-service"},
    "gpu-ai-cloud": {"web-api", "background-worker", "gpu-ai"},
    "backend-platform": {"frontend-app", "web-api", "background-worker", "database"},
    "database-platform": {"database"},
    "bare-metal": {"container-service", "virtual-machine", "kubernetes", "gpu-ai"},
    "managed-kubernetes": {"container-service", "kubernetes"},
    "managed-wordpress": {"wordpress"},
    "developer-sandbox": {"background-worker", "agent-sandbox"},
    "game-hosting": {"game-server"},
    "decentralized-hosting": {"static-site", "decentralized-app"},
}

DEFAULTS = {
    "hyperscale-cloud": (5, 3, 2, 5, 4, 5, 5),
    "cloud-vps": (4, 2, 5, 5, 5, 3, 3),
    "paas": (2, 2, 3, 2, 3, 3, 3),
    "managed-containers": (3, 2, 3, 3, 4, 3, 3),
    "serverless-functions": (3, 1, 2, 1, 2, 4, 4),
    "edge-compute": (3, 1, 2, 2, 2, 5, 4),
    "frontend-hosting": (1, 1, 4, 1, 3, 4, 3),
    "static-hosting": (1, 1, 5, 1, 5, 4, 2),
    "byoc-platform": (4, 3, 3, 4, 4, 4, 5),
    "self-hosted-paas": (4, 2, 5, 5, 5, 2, 2),
    "gpu-ai-cloud": (3, 4, 2, 3, 3, 3, 3),
    "backend-platform": (2, 2, 3, 2, 2, 3, 3),
    "database-platform": (2, 2, 3, 2, 3, 3, 4),
    "bare-metal": (5, 4, 5, 5, 5, 2, 4),
    "managed-kubernetes": (5, 4, 3, 5, 5, 4, 5),
    "managed-wordpress": (1, 2, 5, 2, 3, 3, 3),
    "developer-sandbox": (2, 2, 2, 2, 3, 3, 3),
    "game-hosting": (2, 2, 4, 3, 3, 3, 2),
    "decentralized-hosting": (4, 2, 3, 4, 4, 4, 2),
}


def _union(*values: list[str] | set[str]) -> list[str]:
    result: set[str] = set()
    for value in values:
        result.update(value)
    return sorted(result)


def _workloads(item: dict[str, Any]) -> list[str]:
    values: set[str] = set()
    for category in item["categories"]:
        values.update(CATEGORY_WORKLOADS.get(category, set()))
    capabilities = set(item["capabilities"])
    if "static-sites" in capabilities:
        values.add("static-site")
    if "gpu" in capabilities:
        values.add("gpu-ai")
    if "code-execution" in capabilities:
        values.add("agent-sandbox")
    return sorted(values or {"web-api"})


def _artifacts(item: dict[str, Any]) -> list[str]:
    caps, cats, models = set(item["capabilities"]), set(item["categories"]), set(item["operating_models"])
    values: set[str] = set()
    if "git-deploy" in caps or cats & {"paas", "frontend-hosting", "static-hosting", "managed-wordpress"}: values.add("git-source")
    if "containers" in caps: values.add("docker-image")
    if "self-hosted" in caps or "self-hosted" in models: values.add("docker-compose")
    if "functions" in caps: values.add("function-code")
    if "virtual-machines" in caps or "bare-metal" in caps: values.add("vm-image")
    if "managed-kubernetes" in caps or "managed-kubernetes" in cats: values.add("kubernetes-manifest")
    if "webassembly" in caps: values.add("wasm")
    if cats & {"managed-wordpress", "backend-platform"}: values.add("template")
    return sorted(values or {"git-source"})


def _billing(item: dict[str, Any]) -> list[str]:
    cats, models = set(item["categories"]), set(item["operating_models"])
    values: set[str] = set()
    if "bring-your-own-cloud" in models: values.add("byoc-infrastructure")
    if "self-hosted" in models or "dedicated-server" in models: values.update({"self-host-infrastructure", "fixed-instance"})
    if "marketplace" in models: values.add("marketplace")
    if cats & {"cloud-vps", "bare-metal", "managed-wordpress", "game-hosting"}: values.add("fixed-instance")
    if cats & {"paas", "managed-containers", "frontend-hosting", "database-platform", "backend-platform", "static-hosting"}: values.add("tiered-plan")
    if cats & {"hyperscale-cloud", "managed-kubernetes"}: values.update({"usage-based", "reserved-commit"})
    if cats & {"serverless-functions", "edge-compute", "gpu-ai-cloud", "developer-sandbox"}: values.add("usage-based")
    return sorted(values or {"tiered-plan"})


def _traffic(item: dict[str, Any]) -> list[str]:
    caps, cats = set(item["capabilities"]), set(item["categories"])
    values = {"steady"}
    if "autoscaling" in caps: values.add("bursty")
    if "scale-to-zero" in caps: values.update({"spiky", "scheduled"})
    if "cron-jobs" in caps or "background-workers" in caps: values.add("scheduled")
    if "multi-region" in caps or cats & {"edge-compute", "frontend-hosting", "static-hosting"}: values.add("global")
    return sorted(values)


def _protocols(item: dict[str, Any]) -> list[str]:
    caps, cats = set(item["capabilities"]), set(item["categories"])
    values = {"http"}
    if cats & {"paas", "managed-containers", "cloud-vps", "hyperscale-cloud", "self-hosted-paas", "game-hosting"}: values.add("websocket")
    if "tcp-udp" in caps or cats & {"cloud-vps", "bare-metal", "game-hosting"}: values.update({"tcp", "udp"})
    return sorted(values)


def _state(item: dict[str, Any]) -> list[str]:
    caps = set(item["capabilities"])
    values = {"stateless"}
    if "databases" in caps: values.add("managed-database")
    if "persistent-storage" in caps or "virtual-machines" in caps or "bare-metal" in caps: values.add("persistent-disk")
    if "object-storage" in caps: values.add("object-storage")
    return sorted(values)


def _maturity(item: dict[str, Any]) -> int:
    if item["status"] == "beta": return 2
    year = item.get("launch_year")
    if not year: return 3
    age = date.today().year - year
    return 5 if age >= 10 else 4 if age >= 5 else 3 if age >= 2 else 2


def _profile(item: dict[str, Any]) -> dict[str, Any]:
    expertise, floor, predictable, control, portability, reach, enterprise = DEFAULTS[item["primary_category"]]
    caps = set(item["capabilities"])
    return {
        "slug": item["slug"], "name": item["name"], "entity_type": item["entity_type"],
        "primary_category": item["primary_category"], "status": item["status"], "availability": item["availability"],
        "open_source": item["open_source"], "featured": item["featured"], "summary": item["summary"],
        "best_for": item["best_for"], "url": item["url"], "detail_path": f"/providers/{item['slug']}/",
        "operating_models": item["operating_models"], "workloads": _workloads(item), "artifacts": _artifacts(item),
        "billing_models": _billing(item), "traffic": _traffic(item), "protocols": _protocols(item),
        "state_options": _state(item), "expertise_required": expertise, "cost_floor": floor,
        "cost_predictability": predictable, "control": control, "portability": portability,
        "maturity": _maturity(item), "global_reach": 5 if "multi-region" in caps else reach,
        "enterprise_readiness": enterprise, "free_entry": False, "scale_to_zero": "scale-to-zero" in caps,
        "preview_environments": "preview-environments" in caps, "private_networking": "private-networking" in caps,
        "gpu": "gpu" in caps, "profile_source": "derived",
    }


def load_overrides(path: Path = OVERRIDES_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_recommendation_catalog(catalog: dict[str, Any], overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = overrides or load_overrides()
    profiles = []
    for item in catalog["providers"]:
        profile = _profile(item)
        override = overrides.get("overrides", {}).get(item["slug"], {})
        for field, value in override.items():
            profile[field] = _union(profile[field], value) if field in LIST_FIELDS else value
        if override: profile["profile_source"] = "curated"
        profiles.append(profile)
    return {
        "schema_version": 1, "generated_on": date.today().isoformat(),
        "methodology": overrides["methodology"], "disclaimer": overrides["disclaimer"],
        "dimensions": overrides["dimensions"], "profiles": profiles,
    }


def validate_recommendation_catalog(payload: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    top = {"schema_version", "generated_on", "methodology", "disclaimer", "dimensions", "profiles"}
    if set(payload) != top: return ["recommendations top-level keys are invalid"]
    if payload["schema_version"] != 1: errors.append("recommendations schema_version must be 1")
    if set(payload["dimensions"]) != NUMERIC: errors.append("recommendation dimensions are incomplete")
    by_slug = {item["slug"]: item for item in catalog["providers"]}
    profiles = payload.get("profiles", [])
    if len(profiles) != len(by_slug): errors.append("recommendations need exactly one profile per catalog entry")
    seen: set[str] = set()
    allowed_lists = {"workloads": WORKLOADS, "artifacts": ARTIFACTS, "billing_models": BILLING_MODELS, "traffic": TRAFFIC, "protocols": PROTOCOLS, "state_options": STATE}
    identity = ("name", "entity_type", "primary_category", "status", "availability", "open_source", "featured", "summary", "best_for", "url", "operating_models")
    for profile in profiles:
        slug = profile.get("slug")
        if slug in seen: errors.append(f"duplicate recommendation profile: {slug}")
        seen.add(slug)
        item = by_slug.get(slug)
        if not item: errors.append(f"unknown recommendation slug: {slug}"); continue
        for field in identity:
            if profile.get(field) != item[field]: errors.append(f"{slug}: {field} diverges from catalog")
        for field, allowed in allowed_lists.items():
            values = profile.get(field)
            if not isinstance(values, list) or not values or len(values) != len(set(values)) or set(values) - allowed:
                errors.append(f"{slug}: invalid {field}")
        for field in NUMERIC:
            value = profile.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5: errors.append(f"{slug}: invalid {field}")
        for field in BOOLEANS:
            if not isinstance(profile.get(field), bool): errors.append(f"{slug}: invalid {field}")
        if profile.get("detail_path") != f"/providers/{slug}/": errors.append(f"{slug}: invalid detail_path")
        if profile.get("profile_source") not in {"derived", "curated"}: errors.append(f"{slug}: invalid profile_source")
    return errors


def main() -> int:
    catalog = load_catalog()
    payload = build_recommendation_catalog(catalog)
    errors = validate_recommendation_catalog(payload, catalog)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print(f"Recommendation profiles valid: {len(payload['profiles'])} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
