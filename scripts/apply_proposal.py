#!/usr/bin/env python3
"""Conservatively apply a validated research proposal to the catalog.

The default path never applies status alerts and never deletes records. It adds
well-supported candidates, applies ordinary metadata corrections, and records
successful re-verifications. The resulting catalog is still intended to be
reviewed in a pull request before publication.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from catalog import CATALOG_PATH, atomic_write_json, load_catalog, validate_catalog
from proposals import AUTO_APPLY_CONFIDENCE, SAFE_UPDATE_FIELDS, catalog_entry_from_candidate, proposal_stats, validate_proposal


def merge_sources(current: list[str], proposed: list[str]) -> list[str]:
    return list(dict.fromkeys([*current, *proposed]))[:20]


def apply_update(item: dict[str, Any], update: dict[str, Any], research_date: str) -> list[str]:
    changed: list[str] = []
    patch = update["patch"]
    for field in sorted(SAFE_UPDATE_FIELDS):
        value = patch.get(field)
        if value is not None and item.get(field) != value:
            item[field] = value
            changed.append(field)

    if patch.get("parent_slug_action") == "set" and item.get("parent_slug") != patch.get("parent_slug"):
        item["parent_slug"] = patch["parent_slug"]
        changed.append("parent_slug")
    elif patch.get("parent_slug_action") == "clear" and item.get("parent_slug") is not None:
        item["parent_slug"] = None
        changed.append("parent_slug")

    if patch.get("launch_year_action") == "set" and item.get("launch_year") != patch.get("launch_year"):
        item["launch_year"] = patch["launch_year"]
        changed.append("launch_year")
    elif patch.get("launch_year_action") == "clear" and item.get("launch_year") is not None:
        item["launch_year"] = None
        changed.append("launch_year")

    merged_sources = merge_sources(item["source_urls"], update["source_urls"])
    if merged_sources != item["source_urls"]:
        item["source_urls"] = merged_sources
        changed.append("source_urls")
    if changed:
        item["last_verified"] = research_date
        item["confidence"] = update["confidence"]
        item["change_note"] = update["rationale"].strip()
    return changed


def apply_proposal(catalog: dict[str, Any], proposal: dict[str, Any], include_low_confidence: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    result = copy.deepcopy(catalog)
    by_slug = {item["slug"]: item for item in result["providers"]}
    allowed_confidence = AUTO_APPLY_CONFIDENCE | ({"low"} if include_low_confidence else set())
    report: dict[str, Any] = {
        "added": [],
        "updated": {},
        "verified": [],
        "skipped_low_confidence": [],
        "status_alerts_not_applied": [alert["slug"] for alert in proposal.get("status_alerts", [])],
    }

    for candidate in proposal.get("new_candidates", []):
        if candidate["confidence"] not in allowed_confidence:
            report["skipped_low_confidence"].append({"kind": "new_candidate", "slug": candidate["slug"]})
            continue
        entry = catalog_entry_from_candidate(candidate, proposal["research_date"])
        result["providers"].append(entry)
        by_slug[entry["slug"]] = entry
        report["added"].append(entry["slug"])

    for update in proposal.get("updates", []):
        if update["confidence"] not in allowed_confidence:
            report["skipped_low_confidence"].append({"kind": "update", "slug": update["slug"]})
            continue
        changed = apply_update(by_slug[update["slug"]], update, proposal["research_date"])
        if changed:
            report["updated"][update["slug"]] = changed

    for checked in proposal.get("checked_active", []):
        if checked["confidence"] not in allowed_confidence:
            report["skipped_low_confidence"].append({"kind": "checked_active", "slug": checked["slug"]})
            continue
        item = by_slug[checked["slug"]]
        item["source_urls"] = merge_sources(item["source_urls"], checked["source_urls"])
        item["last_verified"] = proposal["research_date"]
        item["confidence"] = checked["confidence"]
        item["change_note"] = checked["note"].strip()
        report["verified"].append(checked["slug"])

    result["providers"] = sorted(result["providers"], key=lambda item: (item["name"].casefold(), item["slug"]))
    result["generated_on"] = proposal["research_date"]
    return result, report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal", type=Path)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--output", type=Path, help="Write to another path instead of updating --catalog")
    parser.add_argument("--report", type=Path, help="Write a machine-readable application report")
    parser.add_argument("--include-low-confidence", action="store_true", help="Stage low-confidence findings too; not recommended for scheduled runs")
    parser.add_argument("--check-only", action="store_true", help="Validate and print a plan without writing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog = load_catalog(args.catalog)
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    # Research metadata is allowed around the model-shaped proposal.
    core = {key: proposal[key] for key in ("research_date", "summary", "new_candidates", "updates", "status_alerts", "checked_active") if key in proposal}
    errors = validate_proposal(core, catalog)
    if errors:
        for error in errors:
            print(f"ERROR: proposal: {error}", file=sys.stderr)
        return 1

    result, report = apply_proposal(catalog, core, include_low_confidence=args.include_low_confidence)
    result_errors = validate_catalog(result)
    if result_errors:
        for error in result_errors:
            print(f"ERROR: resulting catalog: {error}", file=sys.stderr)
        return 1

    print("Proposal input: " + ", ".join(f"{key}={value}" for key, value in proposal_stats(core).items()))
    print(f"Will add {len(report['added'])}, update {len(report['updated'])}, and re-verify {len(report['verified'])} entries.")
    if report["status_alerts_not_applied"]:
        print(f"Status alerts intentionally left for review: {', '.join(report['status_alerts_not_applied'])}")
    if report["skipped_low_confidence"]:
        print(f"Skipped low-confidence findings: {len(report['skipped_low_confidence'])}")

    if args.check_only:
        return 0
    destination = args.output or args.catalog
    atomic_write_json(destination, result)
    if args.report:
        atomic_write_json(args.report, report)
    print(f"Wrote catalog: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
