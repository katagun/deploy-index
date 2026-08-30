# Shape-matching extension to the pricing dataset

Branch: `claude/pricing-shape-matching`

## What changed

### `scripts/pricing.py`

- Added `SNAKE_CASE_RE`, shared by row `attributes` keys and workload `shape` attribute names.
- `validate_observations`: an optional `attributes` object on a row is now validated when present —
  must be a dict, keys lowercase snake_case, values finite non-negative numbers. Rows without it are
  unaffected.
- `validate_workloads`: a workload must declare **exactly one** of `line_items` / `shape` (both or
  neither is now a validation error). Extracted the existing `line_items`/`assumptions` check
  unchanged; added `_validate_shape_workload()` for the `shape` path, which checks every shape key is
  `min_<attribute>` in snake_case with a finite non-negative value, and validates `assumptions`
  against the shape's own attributes (not `ASSUMPTION_METRICS`, since a shape workload prices no line
  item).
- `compute_workload` was split into `_compute_line_item_workload` (the original logic, unchanged
  behavior) and `_compute_shape_workload` (new), dispatched on whether the workload carries `shape`.
  `plans_considered` is now computed once in `compute_workload` and applied to either path's result,
  same semantics as before.
- `_compute_shape_workload`: within each `(currency, region)` group, for every plan finds its latest
  `plan_base_month` row; the plan qualifies only if that row has an `attributes` dict satisfying every
  `min_X` requirement (`attributes[X] >= value`). Cheapest qualifying plan wins; ties break on plan
  name (deterministic, alphabetical). Stale rows are excluded before grouping, same as the line-item
  path. No qualifying plan yields `insufficient_data` with `missing_metrics: []` and a `reason` string
  built by `_shape_miss_reason` (e.g. "no recorded plan provides at least 100 GiB of storage").
- The `ok` result shape for both workload kinds is byte-for-byte identical to what shipped before
  (`status`, `plan`, `currency`, `region`, `monthly_usd`, `sources`, `plans_considered`) — no new
  fields were added to `ok` results.

### `pricing/workloads.json`

Added workload `plan-with-100gib-storage` ("Cheapest plan with 100 GiB storage"),
`shape: {"min_storage_gib": 100}`, `assumptions: {"storage_gib": 100}`, with two caveats: it prices
plan fees only (excludes metered compute and egress), and it can only consider plans whose included
storage has been recorded.

### `pricing/observations/2026-Q3.json`

- Added `attributes: {"storage_gib": 10}` to the existing Heroku `essential-1` row (no duplicate row).
- Added `attributes: {"storage_gib": 10, "memory_gib": 1}` to the existing DigitalOcean
  `db-s-1vcpu-1gb` `plan_base_month` row, with a note explaining the value is the floor of DO's
  10–30 GiB included range.
- Added four new Heroku Postgres `plan_base_month` rows (`essential-0` $5.00/1 GiB, `essential-2`
  $20.00/32 GiB, `standard-0` $50.00/64 GiB+4 GiB memory, `premium-2` $350.00/256 GiB+8 GiB memory),
  all `currency: USD`, `region: us-east`, `observed_on: 2026-08-30`, `confidence: high`,
  `source_url: https://elements.heroku.com/addons/heroku-postgresql`, each with a note naming what the
  figure is.

### `site/pricing.js`

`cell()`: when a result is not `ok`, prefer `result.reason` over the joined `missing_metrics` list for
the `<small>` detail text. Nothing else in the file changed.

### `site/compare.js` and `scripts/build.py` — no change needed

- **`scripts/build.py`'s `pricing_section`** renders a provider's raw observation rows
  (`plan`/`metric`/`value`/`included_allowance`/`observed_on`/`source_url`) directly from
  `load_observations()`, independent of workloads or `compute_workload`. It never reads `attributes`
  or `shape`, so the new fields pass through inertly. Verified the built detail pages for
  `heroku-postgres` and `digitalocean-managed-postgresql` render correctly with the new rows.
- **`site/compare.js`'s `priceCell`** already guards `missing_metrics` with `|| []` and only renders
  the `<small>` detail when the joined string is non-empty. For a shape workload's `insufficient_data`
  result, `missing_metrics` is `[]` (per the result contract), so `priceCell` degrades gracefully to
  "insufficient data" with no extra detail line — no crash, no wrong information, just less detail
  than `/pricing/` now shows. The task named only `/pricing/`'s display for the `reason` field, so I
  left `compare.js` untouched rather than scope-creeping a second surface; see "Judgment calls" below.

### `pricing/README.md`

Documented the `shape`/`line_items` exactly-one-of rule, added a "Shape workloads" subsection
explaining `attributes`, the qualification rule, tie-breaking, and the `reason` field, and updated the
`/catalog/pricing.json` payload description to mention the optional `reason` field.

### `tests/test_pricing.py`

Added: attribute-row validation tests (valid, non-negative, finite, snake_case, must-be-object);
shape workload computation golden cases (cheapest qualifying plan wins, under-provisioned plan never
selected, exact-boundary qualifies, ties break by plan name, no-qualifying-plan yields
`insufficient_data` with a reason, a plan lacking `attributes` never qualifies, stale rows excluded,
currency/region never mixed, `plans_considered` counts correctly); workload-validation tests (both
`line_items` and `shape` rejected, neither rejected, shape key must be `min_`-prefixed snake_case,
valid shape workload accepted, shape assumption must match a shape attribute); and seed-data
regression tests pinning the exact existing figures (Neon, PlanetScale, Supabase) plus the new
workload's expected Heroku/DigitalOcean outcomes. Fixed one pre-existing test
(`test_workloads_declare_explicit_line_items` → renamed
`test_workloads_declare_explicit_line_items_or_a_shape`) that assumed every workload has `line_items`.

## TDD evidence: red then green

All 20 new/changed tests were written first and run before any implementation change. Failure output
(captured verbatim before implementing `scripts/pricing.py`/data changes):

```
FAIL: test_attributes_key_must_be_lowercase_snake_case ... AssertionError: False is not true : expected 'attributes' in []
FAIL: test_attributes_must_be_an_object ... AssertionError: False is not true : expected 'attributes' in []
FAIL: test_attributes_value_must_be_finite ... AssertionError: False is not true : expected 'attributes' in []
FAIL: test_attributes_value_must_be_non_negative ... AssertionError: False is not true : expected 'attributes' in []
FAIL: test_shape_key_must_be_min_prefixed_snake_case ... ['workloads[0]: line_items must be a non-empty list']
FAIL: test_shape_workload_assumption_must_match_a_shape_attribute ... ['workloads[0]: line_items must be a non-empty list']
FAIL: test_shape_workload_is_accepted_when_valid ... AssertionError: Lists differ
FAIL: test_workload_declaring_both_line_items_and_shape_is_rejected ... AssertionError: False is not true : []
FAIL: test_workload_declaring_neither_line_items_nor_shape_is_rejected ... AssertionError: False is not true
ERROR: test_cheapest_qualifying_plan_wins (KeyError: 'line_items')
ERROR: test_exact_boundary_qualifies (KeyError: 'line_items')
ERROR: test_no_qualifying_plan_yields_insufficient_data_with_reason (KeyError: 'line_items')
ERROR: test_plan_lacking_attributes_never_qualifies (KeyError: 'line_items')
ERROR: test_plans_are_never_mixed_across_currency_or_region (KeyError: 'line_items')
ERROR: test_plans_considered_counts_plans_with_fresh_rows (KeyError: 'line_items')
ERROR: test_stale_rows_are_excluded_from_shape_matching (KeyError: 'line_items')
ERROR: test_ties_break_deterministically_by_plan_name (KeyError: 'line_items')
ERROR: test_under_provisioned_plan_is_never_selected (KeyError: 'line_items')
ERROR: test_new_shape_workload_picks_heroku_premium_2 (StopIteration — workload id not found)
ERROR: test_new_shape_workload_reports_insufficient_data_for_digitalocean (StopIteration)
Ran 71 tests in 0.023s
FAILED (failures=9, errors=11)
```

After implementing `scripts/pricing.py`, `pricing/workloads.json`, and the observation rows:

```
Ran 117 tests in 3.83s
OK
```

(117 = the full suite across all test files, not just `test_pricing.py`; `test_pricing.py` alone has
71 tests, all passing.)

## Final computed table (every provider × every workload)

Produced by `build_pricing_catalog()` against the committed dataset:

| Provider | Storage & egress · 100 GiB / 50 GiB egress | Storage & egress · 10 GiB / 5 GiB egress | Cheapest plan with 100 GiB storage |
|---|---|---|---|
| DigitalOcean Managed Databases for PostgreSQL | insufficient_data (missing: egress_gib) | insufficient_data (missing: egress_gib) | insufficient_data — "no recorded plan provides at least 100 GiB of storage" |
| Heroku Postgres | insufficient_data (missing: egress_gib, storage_gib_month) | insufficient_data (missing: egress_gib, storage_gib_month) | **ok** — `premium-2`, **$350.00**, plans_considered=5 |
| Neon | **ok** — `launch`, **$35.00** | **ok** — `launch`, **$3.50** | insufficient_data — "no recorded plan provides at least 100 GiB of storage" |
| PlanetScale | **ok** — `ps-5-non-ha`, **$18.65** | **ok** — `ps-5-non-ha`, **$5.00** | insufficient_data — "no recorded plan provides at least 100 GiB of storage" |
| Supabase | **ok** — `pro`, **$36.50** | **ok** — `pro`, **$25.25** | insufficient_data — "no recorded plan provides at least 100 GiB of storage" |

This matches the expected outcome exactly: Heroku's cheapest plan with ≥100 GiB storage is
`premium-2` at $350.00 (verified — the engine actually walks all 5 Heroku plans and picks it, not a
hardcoded assumption), DigitalOcean is `insufficient_data` with a reason (its one recorded plan
provides 10 GiB), and the two existing workloads are byte-for-byte unaffected: Neon $35.00/$3.50,
PlanetScale $18.65/$5.00, Supabase $36.50/$25.25.

Raw JSON (via `python3 -c "... build_pricing_catalog() ..."`):

```json
digitalocean-managed-postgresql:
  storage-egress-100gib -> {"status": "insufficient_data", "missing_metrics": ["egress_gib"], "plans_considered": 1}
  storage-egress-10gib -> {"status": "insufficient_data", "missing_metrics": ["egress_gib"], "plans_considered": 1}
  plan-with-100gib-storage -> {"status": "insufficient_data", "missing_metrics": [], "reason": "no recorded plan provides at least 100 GiB of storage", "plans_considered": 1}

heroku-postgres:
  storage-egress-100gib -> {"status": "insufficient_data", "missing_metrics": ["egress_gib", "storage_gib_month"], "plans_considered": 5}
  storage-egress-10gib -> {"status": "insufficient_data", "missing_metrics": ["egress_gib", "storage_gib_month"], "plans_considered": 5}
  plan-with-100gib-storage -> {"status": "ok", "plan": "premium-2", "currency": "USD", "region": "us-east", "monthly_usd": 350.0, "sources": [{"metric": "plan_base_month", "value": 350.0, "observed_on": "2026-08-30", "source_url": "https://elements.heroku.com/addons/heroku-postgresql"}], "plans_considered": 5}

neon:
  storage-egress-100gib -> {"status": "ok", "plan": "launch", ..., "monthly_usd": 35.0, ...}
  storage-egress-10gib -> {"status": "ok", "plan": "launch", ..., "monthly_usd": 3.5, ...}
  plan-with-100gib-storage -> {"status": "insufficient_data", "missing_metrics": [], "reason": "no recorded plan provides at least 100 GiB of storage", "plans_considered": 1}

planetscale:
  storage-egress-100gib -> {"status": "ok", "plan": "ps-5-non-ha", ..., "monthly_usd": 18.65, ...}
  storage-egress-10gib -> {"status": "ok", "plan": "ps-5-non-ha", ..., "monthly_usd": 5.0, ...}
  plan-with-100gib-storage -> {"status": "insufficient_data", "missing_metrics": [], "reason": "no recorded plan provides at least 100 GiB of storage", "plans_considered": 2}

supabase:
  storage-egress-100gib -> {"status": "ok", "plan": "pro", ..., "monthly_usd": 36.5, ...}
  storage-egress-10gib -> {"status": "ok", "plan": "pro", ..., "monthly_usd": 25.25, ...}
  plan-with-100gib-storage -> {"status": "insufficient_data", "missing_metrics": [], "reason": "no recorded plan provides at least 100 GiB of storage", "plans_considered": 1}
```

## Verification run

- `make test` — 117 tests, all pass; `check_site.py` 278 HTML files valid; `node --check` on all site
  JS including `pricing.js` and `compare.js`; JS recommendation-engine regression tests pass.
- `python3 scripts/pricing.py` — "Pricing valid: 18 rows across 5 providers (0 stale), 3 reference
  workloads".
- `python3 scripts/build.py && python3 scripts/check_site.py` — clean build, 278 HTML files, no broken
  internal links or JSON API mismatches.
- `python3.11 -m compileall -q scripts tests` — clean (no backslash-in-f-string or other 3.11
  incompatibilities).
- Manually verified `/pricing/` in a real browser against the built `dist/`: the "Cheapest plan with
  100 GiB storage" column shows `$350.00 premium-2 plan` for Heroku and "insufficient data / no
  recorded plan provides at least 100 GiB of storage" for DigitalOcean, Neon, PlanetScale, and
  Supabase — matching the JSON payload. (Note: an earlier browser reading showed empty `<small>` tags
  for the new column; that was traced to a stale HTTP cache in the already-running preview server's
  browser tab holding the pre-edit `assets/pricing.js` — reproduced correctly loading the file
  fresh with a cache-busting query, confirming this was a test-harness caching artifact and not a bug
  in the shipped code, which has no cache-busting query string on its `<script src>` tag, same as
  before this change.)

## Judgment calls / things worth a second look

1. **`site/compare.js` left untouched.** It already tolerates a shape workload's `insufficient_data`
   result (empty `missing_metrics`) by omitting the detail `<small>` rather than erroring, so it never
   shows a wrong or crashing state — it just doesn't surface `reason` the way `/pricing/` now does.
   The task named only `/pricing/`'s display for this change and explicitly asked me to report rather
   than touch surfaces that don't need it, so I left it as-is. If you want `/compare/` to show the
   reason too, that is a one-line follow-up (`result.reason || missing` instead of just `missing`).
2. **`reason` wording/format.** I generated it programmatically from the shape's `min_<attribute>`
   keys (`_shape_miss_reason` in `scripts/pricing.py`) rather than hand-writing a string per workload,
   so it stays correct if the shape changes and generalizes to multi-attribute shapes (e.g. a future
   `{"min_storage_gib": 100, "min_memory_gib": 4}` shape would read "no recorded plan provides at
   least 100 GiB of storage and at least 4 GiB of memory" — I did not add a test for the
   multi-attribute case since today's only shape workload has one attribute, but the code path is
   exercised by the existing single-attribute tests).
3. **DigitalOcean's `attributes.storage_gib: 10`.** Per instructions, recorded the floor of DO's
   published 10–30 GiB range for the base plan, with a note saying so. This is a conservative choice —
   it means DO's true minimum storage may be understated for shape matching, which only makes it
   *harder* to qualify for a given `min_storage_gib`, never easier, consistent with
   `insufficient_data` beating an optimistic guess.
4. **`pricing/README.md`.** The "Current scope: database hosting only, 3 providers" line was already
   stale before this change (the dataset already had DigitalOcean and Heroku rows from a prior
   commit, `d61501f`), and it grows more so now (5 providers with pricing rows). That line was not in
   scope for this task, so I left it as I found it — flagging it here rather than fixing it silently
   or drifting scope into an unrelated doc claim.

## Fix report: code review follow-up (2026-08-30)

A code review of the shape-matching extension above found six issues, from a $150 published-price
error down to a build-path validation gap. All six are fixed. Commits (on
`claude/pricing-shape-matching`):

- `4bea83d` — pricing: record Heroku Standard 2/3, fixing a $150 published-price error
- `78c50d8` — pricing: fix misleading shape-miss reason and order-dependent tiebreak
- `e85f905` — site: prefer the shape-miss reason in compare.js price cells
- `962ad04` — build: render plan attributes and validate pricing before publishing
- `44ea526` — docs: document shape-miss reason distinction, capacity column, build gate

### 1. CRITICAL — Heroku's published $350 answer was wrong; the real answer is $200

The shape workload's "cheapest plan with ≥100 GiB storage" reported `premium-2` at $350.00 because
`standard-2` ($200/mo, 256 GB storage, 8 GB RAM) — which sits between the already-recorded
`standard-0` and `premium-2` rows — had simply never been recorded. Re-read
`https://elements.heroku.com/addons/heroku-postgresql` on 2026-08-30 and added two `plan_base_month`
rows: `standard-2` ($200.00, `{"storage_gib": 256, "memory_gib": 8}`) and `standard-3` ($400.00,
`{"storage_gib": 512, "memory_gib": 15}`), each with an honest note, `confidence: high`, and the
source URL. No other Heroku plans were added.

`test_new_shape_workload_picks_heroku_premium_2` is renamed
`test_new_shape_workload_picks_heroku_standard_2` and now asserts `standard-2` / $200.00. A second
test, `test_shape_workload_prefers_standard_2_over_premium_2_at_equal_storage`, asserts the engine
picks the cheaper plan even though `standard-2` and `premium-2` both provide the identical 256 GiB —
the actual regression: before `standard-2` existed, `premium-2` was the *only* qualifying plan
(`plans_considered == 1`), so there was never a real comparison to get wrong. The new test asserts
`plans_considered > 1` specifically so a future "only one plan recorded" state can't silently satisfy
it again.

### 2. IMPORTANT — `insufficient_data` no longer asserts what the dataset can't know

`_shape_miss_reason` built its text purely from the shape's `min_X` keys, so "no recorded plan
provides at least 100 GiB of storage" was shown identically whether a provider's plans were genuinely
too small (DigitalOcean, 10 GiB recorded) or its capacity was simply never recorded at all (Neon,
PlanetScale, Supabase — none of which carry a single `plan_base_month` row with `attributes`). The
Neon case was live and wrong: Neon plainly sells more than 100 GiB.

`_compute_shape_workload` now tracks `has_recorded_attributes` — true only if some fresh
`plan_base_month` row for the provider carried an `attributes` object at all, regardless of whether it
qualified — and `_shape_miss_reason` branches on it: `"no plan's included storage has been recorded
for this provider"` when nothing was recorded, the original `"no recorded plan provides at least ..."`
only when attributes exist and fall short. Confirmed against the real dataset: Neon, PlanetScale, and
Supabase now report the "nothing recorded" text; DigitalOcean still correctly reports "falls short"
(it has a recorded 10 GiB plan). Four new tests cover both branches plus the two ways "nothing
recorded" can arise (no `attributes` key, and no `plan_base_month` row at all).

### 3. IMPORTANT — `/compare/` now shows the same explanation as `/pricing/`

`compare.js`'s `priceCell` guarded `missing_metrics` with `|| []` and rendered a bare "insufficient
data" for a shape workload's result (whose `missing_metrics` is always `[]` by contract — the
explanation lives in `reason`). Changed to prefer `result.reason`, falling back to the joined
missing-metric list, matching `pricing.js`. Output stays escaped through the existing `escapeHtml`.

### 4. IMPORTANT — mutation-pinning tests, including a real order-dependency fix

Investigated all five reported survivors by hand-mutating a copy of `scripts/pricing.py` and running
scenarios against it:

- **Explicit plan-name tiebreak in the candidate sort.** Confirmed by experiment that this mutant
  (dropping `candidate[1]` from the sort key) produced byte-identical output against the *original*
  code, for any input — because `plans_by_cr` used a `set`, always re-sorted alphabetically before
  building `candidates`, which already put ties in the same order the tiebreak would. The tiebreak key
  was true dead code, and no test could distinguish it without a source change. Fixed by switching
  `plans_by_cr` to an insertion-ordered `dict` (order follows the caller's row order, not an incidental
  resort) and iterating it directly — correctness now depends solely on the explicit `(price, plan)`
  sort key. Re-ran the same hand-mutation experiment against the fixed code: the mutant now visibly
  picks the wrong plan when rows are fed in adversarial (non-alphabetical) order. Two new tests pin
  this: one feeds the "wrong" plan first and asserts the alphabetically-correct winner anyway; the
  other feeds both orderings and asserts they agree.
- **Iterating plans unsorted.** Same root cause and same fix as above — removing the redundant
  `sorted(plans)` was the change that made the explicit tiebreak load-bearing instead of dead code.
- **Treating a missing `attributes` as `{}`.** Verified algebraically that this can't actually let a
  plan wrongly *qualify* given the existing `isinstance` checks in `qualifies` (any shape has ≥1
  required attribute, and a missing key always fails `isinstance(None, (int, float))`). The
  observable risk is a non-dict-but-truthy `attributes` value (e.g. a stray string) reaching
  `.get()` and raising, or silently corrupting `has_recorded_attributes`. Added a test with
  `attributes: "not-a-dict"` asserting `insufficient_data` with no exception.
- **Dropping the boolean guard on attribute values.** `isinstance(True, int)` is `True` in Python, so
  without the explicit bool exclusion, `attributes: {"storage_gib": True}` would satisfy any
  `min_storage_gib` ≤ 1. Added a workload with `min_storage_gib: 1` (low enough for `True` to matter)
  and confirmed a `True` attribute value never qualifies.
- **Allowing a metric other than `plan_base_month` to supply attributes and price.** Added a test with
  only a `storage_gib_month` row of $0.215 carrying `attributes: {"storage_gib": 200}` and confirmed
  the shape matcher reports `insufficient_data` rather than publishing $0.22 as a plan price.

### 5. IMPORTANT — provider detail pages now show the capacity that decided the answer

`pricing_section` in `scripts/build.py` rendered plan/metric/value/allowance/date/source but never
`attributes`, so `/providers/heroku-postgres/` showed `standard-2 · plan_base_month · 200.0 ·
Included: 0` with no mention of the 256 GiB that qualified it. Added a `_format_attributes` helper
(reusing `pricing.py`'s `_humanize_attribute`/`_format_quantity`) and a new "Capacity" column rendering
a compact string like `256 GiB storage · 8 GiB memory`, escaped via the existing `esc()`, with a
"—" marker for rows with no attributes. The existing columns, `<caption>`, and `scope="col"` headers
are unchanged — verified by a test asserting all seven headers are present. Verified the built
`/providers/heroku-postgres/` page renders "256 GiB storage · 8 GiB memory" next to the $200.00
`standard-2` row.

### 6. MINOR — `python3 scripts/build.py` can no longer publish an invalid workload

Only `scripts/pricing.py`'s `main()` (run via `make validate`) validated workloads and observation
rows; `scripts/build.py`'s `main()` never did, so running it directly skipped validation entirely.
Wired `validate_workloads`/`validate_observations` into `build.py`'s `main()`, before `dist/` is
touched. Verified by temporarily corrupting `pricing/workloads.json` (emptying a workload's
`line_items`) and confirming `python3 scripts/build.py` fails with `ERROR: workloads[0]: line_items
must be a non-empty list` and exit code 1, then restoring the file and confirming a clean build.

## Verification run (2026-08-30)

- `make test` — 130 tests, all pass (up from 117; `test_pricing.py` alone is 84, up from 71); build,
  `check_site.py` (278 HTML files), and all `node --check` / JS regression checks pass.
- `python3 scripts/pricing.py` — `Pricing valid: 20 rows across 5 providers (0 stale), 3 reference
  workloads`.
- `python3 scripts/build.py && python3 scripts/check_site.py` — clean build, 278 HTML files, no broken
  links or JSON API mismatches.
- `python3.11 -m compileall -q scripts tests` — clean.
- Full computed table for every provider × workload (`build_pricing_catalog()` against the committed
  dataset):

  | Provider | Storage & egress · 100 GiB | Storage & egress · 10 GiB | Cheapest plan with 100 GiB storage |
  |---|---|---|---|
  | DigitalOcean | insufficient_data (missing: egress_gib) | insufficient_data (missing: egress_gib) | insufficient_data — "no recorded plan provides at least 100 GiB of storage" |
  | Heroku Postgres | insufficient_data (missing: egress_gib, storage_gib_month) | insufficient_data (missing: egress_gib, storage_gib_month) | **ok** — `standard-2`, **$200.00**, plans_considered=7 |
  | Neon | **ok** — `launch`, **$35.00** | **ok** — `launch`, **$3.50** | insufficient_data — "no plan's included storage has been recorded for this provider" |
  | PlanetScale | **ok** — `ps-5-non-ha`, **$18.65** | **ok** — `ps-5-non-ha`, **$5.00** | insufficient_data — "no plan's included storage has been recorded for this provider" |
  | Supabase | **ok** — `pro`, **$36.50** | **ok** — `pro`, **$25.25** | insufficient_data — "no plan's included storage has been recorded for this provider" |

  The three metered providers are confirmed byte-for-byte unchanged: Neon $35.00/$3.50, PlanetScale
  $18.65/$5.00, Supabase $36.50/$25.25. Heroku's answer moved from the wrong $350.00 (`premium-2`) to
  the correct $200.00 (`standard-2`), now backed by a real 7-plan comparison. DigitalOcean's reason is
  unchanged (it has a recorded, if small, plan); Neon/PlanetScale/Supabase's reason changed to
  correctly say nothing was recorded, rather than implying their real plans are too small.

## Judgment calls / things worth a second look (this pass)

1. **Bundled findings 2 and 4 into one commit (`78c50d8`) and findings 5/6 into one commit (`962ad04`).**
   Findings 2 and 4 both live inside `_compute_shape_workload` and are causally linked — the order-
   independence fix for finding 4 is what makes finding 2's `has_recorded_attributes` tracking
   trustworthy under any input order — so splitting them at the line level would have meant
   duplicating the same diff hunks across two commits with no real isolation. Findings 5 and 6 are both
   `scripts/build.py` changes that share a single import statement; same reasoning.
2. **`pricing_metrics`/`pricing_rows` in `build.py`'s `main()`.** Wiring in validation needed
   `load_metrics()`/`load_observations()` before `dist/` is touched; the later `pricing_section` loop
   already loaded them again under the same names, so I removed the second load and reused the first,
   rather than leaving two redundant reads of the same files.
3. **Did not touch the stale "Current scope: 3 providers" line in `pricing/README.md`**, noted as
   already out of scope in the prior pass above — still out of scope here.
4. **The `_format_attributes` helper in `build.py` silently skips a non-numeric or boolean value**
   inside an `attributes` dict rather than rendering it, consistent with `_compute_shape_workload`'s
   own numeric-and-non-boolean guard — a malformed attribute is treated as absent everywhere, not
   rendered as garbage in one place and excluded in another.
