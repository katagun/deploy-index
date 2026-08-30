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
