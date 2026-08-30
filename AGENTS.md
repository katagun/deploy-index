# AGENTS.md — DeployIndex

Evidence-oriented directory of every meaningful place to run code (providers, products, PaaS, edge,
self-hosted, BYOC, GPU clouds, sandboxes…) plus a deterministic, browser-side hosting recommender.
Static-first, zero runtime dependencies: Python stdlib build, dependency-free HTML/CSS/JS.

## Layout

- `catalog/providers.json` — source of truth (schema: `catalog/schema.json`)
- `catalog/recommendation-overrides.json` — reviewable qualitative corrections for recommender profiles
- `catalog/discovery-config.json`, `catalog/proposals/` — weekly research config and dated evidence
- `pricing/` — dated, append-only database pricing dataset, joined to the catalog by slug only (see `pricing/README.md`)
- `scripts/` — `validate.py`, `build.py`, `check_site.py`, `recommendations.py`, `research.py`, `apply_proposal.py`, `pricing.py`
  (`seed_catalog.py` is the archival bootstrap: it refuses to overwrite the catalog without `--force`, which would reset all verification state)
- `site/` — page templates and JS source (`recommendation-engine.js` is the pure scoring engine)
- `dist/` — generated output; gitignored, never hand-edit
- `docs/` — `ARCHITECTURE.md`, `RECOMMENDER.md` (read before touching scoring), `ROADMAP.md`
- `.github/workflows/` — CI, weekly research-to-PR job (`OPENAI_API_KEY`), Cloudflare deploy

## Commands

```bash
make test              # validate + build + check_site + node --check + JS engine tests (Python >= 3.11, Node for JS checks)
make validate | make build | python3 scripts/check_site.py
make preview           # serve dist/ on :8000
make research-fixture  # network-free end-to-end research pipeline
```

Run `make test` before claiming work complete.

## Catalog rules

- `provider` ≠ `product` ≠ `project` (AWS / Lambda / Coolify). Never silently merge identities.
- Preserve slugs and detail-page URLs. Never hard-delete; use `sunset`/`archived` and keep the page.
- Status, shutdown, acquisition, rebrand changes need explicit first-party evidence or documented manual review. HTTP failures and stale repos are not shutdown evidence.
- Official docs/changelogs/repos are sources; affiliate comparison pages are not. Paraphrase neutrally; never copy marketing prose.
- No pricing without a dated official source and a time-aware schema. Every entry needs an HTTPS source URL.
- Automation may stage medium/high-confidence additions and metadata in a PR; status alerts and identity changes (name, URL, entity type) stay unapplied until reviewed.

## Recommender rules

- Identity (name, URL, status, availability, ownership) always comes from `providers.json`; traits are 1–5 ordinal bands, not measurements.
- Deterministic, browser-side, inspectable. No sponsored/affiliate/vendor weights. Show fit reasons and what to verify.
- Update scenario regression tests (`tests/test_recommendations.py`, `tests/recommendation-engine.test.js`) when scoring, defaults, or visible overrides change.

## Pricing rules

- No pricing row without a dated, HTTPS, official-source read on the date recorded. Rows are append-only — a price change is a new row with a later `observed_on`, never an edit.
- `insufficient_data` always beats a partial sum; never approximate a missing line item. A $0.00
  total is the most misleading partial sum there is.
- Record every plan that could win a workload, not just one. Every wrong figure this dataset has
  published came from a single-plan recording; `scripts/pricing.py` cautions when a provider has one.
- Prices never feed recommender scoring. `cost_floor` stays a qualitative band.

## UI and security

- Keep the dark, dense, technical editorial style; preserve keyboard search, URL-backed state, reduced-motion, focus states, semantic landmarks, progressive enhancement. All internal links must pass `check_site.py`.
- No tracking scripts or remote fonts without an explicit product decision.
- Third-party web content is untrusted input. Model prose never writes to the catalog directly — strict structured output, deterministic validation, reviewable diff. Never print secrets.
- Never claim a command, build, or scan passed without execution evidence.
