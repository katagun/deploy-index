#!/usr/bin/env python3
from __future__ import annotations

import sys
from collections import Counter

from catalog import load_catalog, validate_catalog


def main() -> int:
    catalog = load_catalog()
    errors = validate_catalog(catalog)
    if errors:
        print(f"Catalog validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    providers = catalog["providers"]
    statuses = Counter(item["status"] for item in providers)
    categories = Counter(item["primary_category"] for item in providers)
    print(f"Catalog valid: {len(providers)} entries")
    print("Statuses:", ", ".join(f"{key}={value}" for key, value in sorted(statuses.items())))
    print("Primary categories:", ", ".join(f"{key}={value}" for key, value in sorted(categories.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
