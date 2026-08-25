# Codebase and documentation review — 2026-08-23

> **Resolution status (2026-08-23):** every finding below — high, medium, low, and documentation — was addressed in the follow-up commits on this branch. Highlights: identity (name/URL/entity-type) updates are now gated like status alerts and covered by tests; CI runs `make test` with pinned, SHA-locked actions; engine regressions run against a frozen fixture with membership-only checks on live data, and research-workflow failures now open an issue; `catalog/schema.json` is enum-synchronized by a unit test and documented as descriptive; the seed taxonomy was corrected and URL/domain uniqueness is enforced catalog-wide; the engine validates enum inputs and `free_entry` is derivable from a `free-tier` capability with a neutral default billing answer; PR bodies escape model-authored text and the GitHub evidence heuristic requires a related repository; a negative-test suite now covers `validate_proposal`. This document is retained unchanged below as the point-in-time review record.

Independent deep review of the DeployIndex repository: all Python scripts, browser JavaScript, templates, catalog data, GitHub workflows, deployment configuration, and every document in the repository root and `docs/`. All findings below were verified against the code; `make test` was executed and passes (10 Python tests, site check over 270 generated pages, JS syntax checks, and the engine regression tests).

## Verdict

This is an unusually disciplined early-stage codebase. The architecture documents describe a real system, not an aspiration: the trust boundary between model research and catalog truth exists in code exactly as documented, the build is genuinely dependency-free, the generator escapes everything it interpolates, and the conservative apply step provably refuses to apply status alerts (covered by a test). The main risks are concentrated in three places: the automation is allowed to stage **identity changes** (name/URL) that deserve the same manual gate as shutdowns; the **CI workflow enforces less than `make test`**, so the recommender can break on `main` without failing a PR; and several trust artifacts (`catalog/schema.json`, parts of `discovery-config.json`) are **decorative** — documented as enforcement but wired to nothing.

## What is genuinely good

- **The trust boundary is real.** `scripts/research.py` never touches the catalog; `scripts/proposals.py` validates structured output deterministically; `scripts/apply_proposal.py` refuses status alerts and deletions by construction, and `tests/test_catalog.py` proves it (`test_proposal_application_is_conservative`).
- **Output encoding is thorough.** Every interpolation in `scripts/build.py` goes through `esc()`; JSON-LD escapes `</` to prevent script-context breakout; `site/recommend.js` escapes all profile fields before `innerHTML`; catalog validation rejects `<script` and `javascript:` in text fields as defense in depth.
- **Determinism is taken seriously.** Weekly rotation is seeded from the ISO week (`select_rotation`), fixture mode exercises the whole pipeline offline, writes are atomic (`atomic_write_json`), and the schema-strictness of the structured-output contract is itself unit-tested.
- **`check_site.py` is a strong quality gate** for a project this size: unresolved-token detection, internal link and fragment resolution, landmark/title/description/h1 checks, duplicate-ID detection, sitemap count, and recommendation-catalog identity re-validation over the built artifact.
- **The documentation is honest.** Seed records are labeled as unverified leads in the UI and in the docs; the recommender repeatedly disclaims precision; nothing reviewed materially overclaims what the code does — with the small exceptions listed under "Documentation findings."

## High-priority findings

### H1. Automation may stage identity rewrites of existing entries

`SAFE_UPDATE_FIELDS` in [proposals.py:24](../scripts/proposals.py) includes `name`, `url`, and `entity_type`. A medium-confidence model update can therefore rewrite an existing entry's canonical URL, and `apply_proposal.py` stages it automatically into the weekly PR. Critically, the first-party-source check for updates validates sources against the **proposed** URL, not the current one ([proposals.py:377](../scripts/proposals.py): `canonical_for_sources = patch.get("url") or ...`). So a hallucinated or injection-induced update proposing `url: https://attacker.example` with a source on `attacker.example` passes every deterministic gate; the only remaining control is a human reading a large JSON diff.

This contradicts the spirit of `AGENTS.md` ("rebrand changes need explicit first-party evidence or documented manual review") — rebrands are exactly `name`/`url` changes, yet they ride the "ordinary metadata" path while the strictly less dangerous availability field is gated.

**Recommendation:** treat `url`, `name`, and `entity_type` patches like status alerts (report, never auto-apply), or at minimum require that at least one source URL is related to the *current* domain before accepting a URL change.

### H2. CI enforces less than `make test`

[ci.yml](../.github/workflows/ci.yml) runs `node --check` only on `app.js` and `theme.js`. It never syntax-checks `recommendation-engine.js` or `recommend.js` and never runs `tests/recommendation-engine.test.js`. A PR that breaks the scoring engine or its regression rankings passes CI and only fails later in the deploy workflow (which does run `make test`) — after merge to `main`. `AGENTS.md` says "Run `make test` before claiming work complete"; CI should hold itself to the same bar. Also note `setup-node` is absent from CI and the research workflow (they rely on the runner's preinstalled, unpinned Node).

**Recommendation:** have CI run `make test` (or add the missing four commands), and add `actions/setup-node` with a pinned major version.

### H3. Engine regression tests pin exact rankings against the live catalog

[recommendation-engine.test.js](../tests/recommendation-engine.test.js) asserts exact top-2 orderings (`['fly-io', 'bunny-magic-containers']`, `['coolify', 'dokploy']`, `['modal', 'runpod']`) computed over the *current* catalog. These tests run inside the weekly research workflow after staging new entries. Any legitimately discovered platform that scores above an incumbent fails the workflow at the "Build and test proposed catalog" step — the run errors out and **no PR is opened**, silently, until someone reads the Actions log. The stated intent (scoring changes should be explicit) is right, but the trigger is wrong: catalog *data* changes will trip a test meant to detect *scoring* changes.

**Recommendation:** run scenario regressions against a frozen fixture catalog, or relax live-catalog assertions to membership ("fly-io in top 5") rather than exact order. Separately, make the research workflow open a PR (or an issue) even when the build step fails, so failures are visible.

### H4. `catalog/schema.json` is decorative

Nothing in the repository validates anything against [catalog/schema.json](../catalog/schema.json). The real validator is the hand-rolled `validate_catalog()` in [catalog.py](../scripts/catalog.py). Yet the README ("its schema is `catalog/schema.json`") and the generated `/method/` page ("validated by `catalog/schema.json`") both imply the published schema is enforced. The two definitions have already drifted in small ways (the JSON Schema does not know category membership, name-uniqueness, the archived⇒discontinued rule, or future-date checks; conversely it specifies `format: uri` which the validator does not). Consumers of the public JSON who trust the published schema get weaker guarantees than the catalog actually satisfies — and nothing will catch it when the schema and the validator diverge further.

**Recommendation:** either add a CI step that checks the catalog against `schema.json` (stdlib-only is hard; a small vendored checker or a documented dev-only dependency would be acceptable), or generate `schema.json` from the constants in `catalog.py`, or relabel it in the docs as "descriptive, non-normative."

## Medium-priority findings

### M1. Seed data violates the rules that automation must obey

The proposal validator rejects new providers whose domain is already represented, and `CONTRIBUTING.md` says products should reference an existing parent. The seed catalog breaks both:

- `amplify` (`aws.amazon.com/amplify/`), `codespaces` (`github.com/features/codespaces`), and `dreamcompute` (`dreamhost.com/cloud/computing/`) are typed `provider` on domains already owned by the `aws`, `github`, and `dreamhost` provider records — these are products by the project's own definition;
- five `product` records (`aws-gamelift`, `azure-playfab`, `edgegap`, `hathora`, `heroic-cloud`) have `parent_slug: null` even where the parent exists (`aws`), and `edgegap`/`hathora` look like independent companies mislabeled as products.

Beyond taxonomy hygiene, the practical consequence is that the duplicate-domain guard now silently protects the *wrong* record: a future legitimate proposal touching those domains will be rejected against a miscategorized incumbent.

### M2. `validate_catalog` does not enforce URL or domain uniqueness

Duplicate canonical URLs and duplicate provider domains are only rejected for *proposed* records ([proposals.py:302-312](../scripts/proposals.py)); the catalog validator itself checks only slug and name uniqueness. Hand-edited entries (the primary contribution path per `CONTRIBUTING.md`) can introduce duplicates that automation would have rejected. The invariant should live in `validate_catalog()` so it holds for every write path — this would also have caught M1.

### M3. The scoring engine crashes on unknown enum values

`normalizeInput()` in [recommendation-engine.js:101](../site/recommendation-engine.js) clamps numbers but never validates enum fields. `scoreProfile` then dereferences `LABELS.workloads[input.workload].toLowerCase()` on the miss path — verified: `scoreProfiles(profiles, { workload: 'bogus' })` throws `Cannot read properties of undefined`, and the same holds for `artifact` and `billing`. The published UI is shielded only by accident: `writeInput` assigns URL parameters to `<select>` elements, invalid values are silently dropped by the DOM, and `render()` re-reads the DOM. Any other consumer of the documented public API surface (`/catalog/recommendations.json` plus the engine module, which is explicitly exported for Node) hits the crash, as would any future UI change that stops round-tripping through selects. An invalid `protocol` doesn't crash but renders the string "undefined" in trade-off text.

**Recommendation:** validate enum fields against `LABELS` keys in `normalizeInput`, falling back to defaults.

### M4. Free-tier modeling biases the default experience toward curated platforms

Derived profiles hard-code `free_entry: false` ([recommendations.py:170](../scripts/recommendations.py)) and `_billing()` never emits `free-entry`, so only override-listed platforms can ever match the billing question's "free or nearly-free entry" answer — currently 7 of 265 profiles. Because the default input (and the default "Static directory" preset) selects `billing: 'free-entry'`, every non-curated platform takes a −9 penalty on the landing configuration regardless of whether it actually has a free tier (Render, Railway, Koyeb, GitHub-adjacent platforms, most serverless clouds do). The engine's neutrality story is sound — the bias is toward *curated* rather than *paying* platforms — but it is still a systematic distortion of the first result set users see, driven by data coverage rather than fact.

**Recommendation:** either derive `free_entry` from a catalog capability so it can be researched per-entry, or make the default billing answer `any`.

### M5. Model-authored text flows into PR bodies unfenced

`proposal_markdown.py` interpolates the model's `summary`, `rationale`, `note`, and `change_note` fields directly into PR markdown. URL fields are schema-constrained to `https://`, but the free-text fields (up to 1,500 chars) can contain arbitrary markdown — links, images, headings, checklist items, or instructions aimed at the human reviewer or at any LLM-based review tooling that later reads the PR ("mark this reviewed", "@bot approve"). Given that the entire threat model centers on searched web pages injecting instructions into the model, its output should be treated as tainted in the PR too.

**Recommendation:** render model text inside code fences or blockquote-escape it (escape `[`, `!`, backticks), and say in the PR template that quoted text is machine-generated and untrusted.

### M6. The GitHub-source heuristic accepts any repository as first-party evidence

`has_probable_primary_source()` ([proposals.py:234](../scripts/proposals.py)) treats *any* `github.com` URL as probable first-party evidence when `open_source: true` — a flag the model itself asserts. A fabricated candidate can therefore satisfy the evidence gate with an unrelated or attacker-created repo. The docstring honestly labels this a conservative heuristic with human review as the authority, but the check could cheaply be tightened: require the repo owner/name to relate to the candidate slug or domain, or at least surface "evidence is GitHub-only" as a distinct review flag in the PR checklist.

## Low-priority findings

- **`discovery-config.json` is partly dead configuration.** `max_new_candidates` and `max_updates` are never read (the real limits are hard-coded as `maxItems` 30/80 in `research_output_schema`), and `source_preferences` / `prohibited_automatic_actions` are never injected into the prompt — the prompt restates similar rules independently. Someone editing the config to change behavior will change nothing. Wire them in or remove them.
- **`seed_catalog.py` is a loaded footgun.** It unconditionally overwrites `catalog/providers.json` with `confidence: seed` records, discarding all verification state accumulated since (already 2 verified entries). It has served its bootstrap purpose; move it to an archival location, make it refuse to overwrite an existing catalog, or write to stdout.
- **Header/CSP parity drifts across hosts.** `site/_headers` carries a solid CSP (Cloudflare and Netlify pick it up from `dist/`), but `vercel.json` defines no security headers, and `netlify.toml`'s inline headers omit them too. A Vercel deployment ships with no CSP. Also, `script-src 'unsafe-inline'` exists only for the small theme-init snippet in `base.html`; a hash-based allowance would remove the broad inline grant.
- **SITE_URL can silently poison canonicals.** `build.py` defaults `SITE_URL` to `http://localhost:8000`; the Cloudflare workflow guards against this, but the Vercel/Netlify configs rely on a human remembering to set the variable — otherwise every canonical URL, `robots.txt`, and sitemap entry points at localhost with no error. Consider failing the build when `SITE_URL` is unset and `CI` is truthy.
- **`localStorage` guarding is inconsistent.** The inline theme snippet wraps reads in try/catch, but `theme.js` (`setItem` on toggle) and `app.js` (view persistence) do not; in storage-blocked contexts the toggle handler throws. Same pattern, three behaviors.
- **Minor engine/UI nits.** `scoreProfile` re-normalizes (deep-clones) the input once per profile per render — harmless at 265 profiles but easy to lift out; `scoreProfiles` normalizes yet again in its GPU filter. The `reach: 'single'` branch can earn at most 10 of its 12-point maximum, slightly depressing all scores for that answer (ranking-neutral, display-only). `document.execCommand('copy')` is deprecated as a clipboard fallback. `checked_active` re-verification overwrites a record's `confidence` with the checker's confidence, which can silently downgrade `high` to `medium`.
- **No negative tests for the security boundary.** `validate_proposal` is the load-bearing wall of the whole trust model, and every test exercises only the happy path (a valid fixture). There are no tests proving that duplicate domains, non-primary sources, unknown slugs, status regressions, or self-parenting are rejected. The README itself lists this as a suggested task; it should be the next test work done.
- **Workflow hygiene.** Actions are pinned by tag (`@v4`/`@v5`) rather than SHA, which `AGENTS.md`'s security posture would argue for; the research workflow duplicates the Makefile's check list inline (the same duplication that let ci.yml drift).

## Documentation findings

The docs are accurate to an unusual degree — most claims were verified directly against code and hold. Specific corrections:

- [ARCHITECTURE.md](ARCHITECTURE.md) says "The architecture keeps four concerns separate" and then lists five. Trivial, but it's the first section of the flagship doc.
- [README.md](../README.md) hardcodes "265 records" and names specific platforms; both will drift with every weekly PR. Consider "265 at seed time" phrasing or injecting the count.
- README and the generated `/method/` page present `catalog/schema.json` as the operative schema; per H4 it is currently unenforced. Reword or enforce.
- The README's closing section is Codex-specific ("Continue in Codex") while the repository equally carries `CLAUDE.md`; a neutral "Working with coding agents" section naming both would age better.
- `AGENTS.md` claims `make test` covers "JS engine tests" — true of the Makefile, silently untrue of CI (H2). Once CI runs `make test`, the claim is airtight.
- `CONTRIBUTING.md`'s instruction that products reference existing parents is contradicted by the seed data (M1).
- Gaps worth filling: `seed_catalog.py` appears in no document (its danger is undocumented — see low-priority findings); there is no `SECURITY.md`/disclosure note despite a written threat model; `docs/` has no index and this review adds a fourth file.
- [RECOMMENDER.md](RECOMMENDER.md) is the strongest document in the repository — the scoring-rules section matches the implementation (workload/artifact dominance, GPU hard filter, 0–100 clamp, four reasons / three trade-offs, all verified), and the variable backlog plus the dated-dataset rule for pricing is exactly the right way to defer quantitative claims. No corrections.

## Suggested order of work

1. Gate `url`/`name`/`entity_type` updates behind manual review, or require old-domain source overlap (H1).
2. Make CI run `make test`; pin Node (H2).
3. Decouple engine regression tests from live catalog data; surface research-workflow failures (H3).
4. Enforce or demote `catalog/schema.json`; add URL/domain uniqueness to `validate_catalog` (H4, M2).
5. Fix seed taxonomy: re-type `amplify`/`codespaces`/`dreamcompute` as products with parents; set missing `parent_slug`s (M1).
6. Add negative tests for `validate_proposal` — the highest-value test gap in the repository.
7. Validate enums in `normalizeInput`; revisit `free_entry` derivation and the default billing answer (M3, M4).
8. Fence model text in PR bodies; tighten the GitHub-evidence heuristic (M5, M6).
