# Contributing to DeployIndex

DeployIndex welcomes new hosting platforms, corrected records, source upgrades, and improvements to the research pipeline. The goal is breadth without sacrificing evidence.

## Add or update an entry

Edit `catalog/providers.json` and preserve the schema in `catalog/schema.json`. A record represents one of three things:

- `provider`: a company or broad cloud platform, such as AWS, DigitalOcean, or Cloudflare;
- `product`: a separately selectable deployment surface, such as Lambda, Cloud Run, Workers, or App Platform;
- `project`: an open-source deployment platform, such as Coolify, Dokku, or Knative.

Use a stable kebab-case slug, canonical official HTTPS URL, neutral summary, concrete best-fit description, relevant facets, and at least one first-party source. Products should reference a parent provider where the parent already exists.

Do not remove discontinued records. Change their status and availability only when the source trail supports it; historical pages are intentionally preserved.

Do not re-run `scripts/seed_catalog.py`: it is the archival bootstrap and would reset every record's verification state. It refuses to overwrite an existing catalog unless `--force` is passed.

## Evidence standard

Preferred sources, in order:

1. Official product documentation.
2. Official company announcement or changelog.
3. Official GitHub repository and release history.
4. Reputable reporting that points to primary evidence.

A broken site, expired certificate, inactive social account, or stale repository is not enough to declare a platform dead.

## Validate your change

```bash
make test
```

This compiles the scripts, runs unit tests, validates catalog invariants, builds all static pages, checks internal links and fragments, verifies API JSON, and checks browser JavaScript syntax.

## Exercise the research workflow locally

No key or network is needed for the deterministic fixture:

```bash
make research-fixture
```

A real scan requires an OpenAI API key and uses live web search:

```bash
export OPENAI_API_KEY=...
python3 scripts/research.py
```

Review the dated proposal before applying it. The default application command will not apply status alerts or delete anything.

## Pull requests

Explain the identity of the entry, why it belongs in this directory, and what the cited sources establish. Keep unrelated catalog and UI changes in separate commits when practical.
