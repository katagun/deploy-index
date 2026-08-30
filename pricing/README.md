# Pricing dataset

A separate data plane from `catalog/providers.json`, joined to it only by `provider_slug`. It exists
because exact prices are unstable and require dated, sourced, auditable rows — not a field on a
provider record. See `docs/superpowers/specs/2026-08-29-database-pricing-design.md` for the full design
rationale and `docs/superpowers/plans/2026-08-29-database-pricing-foundation.md` for what shipped.

## The multi-plan rule

**Before recording a provider, look at its whole published lineup and record every plan that could
plausibly win a workload — especially the cheapest one.**

This is the single most important rule here, because breaking it is the only way this dataset has
ever published a wrong number. Three times:

| Provider | Published | Actual | Cause |
|---|---|---|---|
| PlanetScale | $148.00 | $5.00 | only its HA production SKU was recorded |
| Heroku | $350.00 | $200.00 | Standard 2 sat unrecorded between two plans that were |
| Turso | $73.24 | $62.92 | only the Developer plan was recorded; Scaler is cheaper at volume |

None was an arithmetic error. The engine did exactly what it was asked, over an incomplete set. It
picks the cheapest plan *that was recorded*, and has no way to know a cheaper one exists — so a
single-plan provider publishes a number that looks like a floor and is not one. Worse, the result
says "cheapest of N recorded plans", which reads as though a comparison was won.

In practice:

- Enumerate the vendor's tiers before entering anything. Note the ones you reject and why.
- If you record a plan that clears a shape threshold, check explicitly whether a cheaper tier also
  clears it. Watch for traps like Heroku's Premium 0 — same price as Standard 2, half the storage.
- Recording one plan is fine when the vendor genuinely sells one. Say so in the note.

`python3 scripts/pricing.py` prints a caution listing every provider currently recorded at a single
plan. It is not an error — some vendors do sell one tier — but each name on that list is a figure
nobody has yet proven to be a floor.

When you have checked a vendor's lineup and the single recorded plan genuinely is the only one that
can win, set `"sole_plan_verified": true` on one of its rows and put the evidence in that row's
note: which plans exist and why none of them beats the recorded one. The caution then stops naming
that provider. Only set it after actually reading the lineup — it silences the one check that has
caught every pricing error this dataset has published.

## A note on GB and GiB

Metrics and attributes are named `*_gib` and the workloads compare in GiB, but most vendors
publish "GB" without saying whether they mean 10^9 or 2^30 bytes. The two differ by about 7%,
which is usually irrelevant — a plan advertising 256 GB clears a 100 GiB threshold either way.

It matters at the boundary. Prisma's Business plan publishes "100GB" against a 100 GiB
threshold: decimal, that is 93.13 GiB and does not qualify; binary, it qualifies exactly.
Where a reading decides an answer, record the conservative one and say so in the row's note.
Never let an ambiguous unit produce a claim the source cannot support.

**Current scope:** database hosting only, 5 providers (Neon, Supabase, PlanetScale, DigitalOcean Managed Postgres, Heroku Postgres), `USD` /
`us-east` only. The design envisions ~12 providers and a hyperscaler baseline; only the foundation
and a hand-entered seed shipped so far. The model-assisted research scan described in the spec does
not exist — every row below was entered by a human who read the cited source. Do not describe
automated pricing research as a feature until it is actually built.

The spec and plan documents linked above are dated records of intent and were not rewritten. They
name the reference workloads `small-prod-postgres` and `hobby-postgres`; what shipped is
`storage-egress-100gib` and `storage-egress-10gib`, because those workloads price storage and egress
only and must not claim to price a whole Postgres deployment. This file describes what shipped.

## Layout

```
pricing/
  metrics.json                # controlled vocabulary: metric -> unit + description
  workloads.json               # reference workload definitions (line items over the vocabulary)
  observations/YYYY-QN.json    # dated rows, partitioned by quarter
scripts/pricing.py              # loading, validation, staleness, and computation
```

`python3 scripts/pricing.py` validates the dataset and prints a summary; it is wired into
`make validate` and therefore `make test`. `scripts/build.py`'s own `main()` also validates
workloads and observation rows before writing anything to `dist/`, so a bare `python3 scripts/build.py`
(skipping `make validate`) can never publish a workload or row the validator would reject. There is no
separate `pricing/schema.json` — the enforced shape is `REQUIRED_ROW_FIELDS` and the validators in
`scripts/pricing.py`.

## What a row means

Each row in `observations/YYYY-QN.json` is one dated, sourced observation of a single price
component for one provider plan:

```json
{
  "provider_slug": "neon",
  "plan": "launch",
  "metric": "storage_gib_month",
  "value": 0.35,
  "currency": "USD",
  "included_allowance": 0,
  "region": "us-east",
  "observed_on": "2026-08-29",
  "source_url": "https://neon.com/pricing",
  "confidence": "high",
  "note": "Launch plan storage, billed per GB-month with no included allowance."
}
```

- `provider_slug` must already exist in `catalog/providers.json`.
- `plan` is the provider's own plan/tier/SKU name (`launch`, `pro`, `ps-80-arm64-ha`), a non-empty
  string. Rows for the same metric under different plans are never mixed together. See the
  multi-plan rule below before recording any provider.
- `metric` must be one of the enums in `metrics.json` (see below).
- `value` and `included_allowance` are non-negative numbers; `included_allowance` is the free
  quantity of that metric's unit before `value` applies.
- `currency` must be `USD` and `region` must be `us-east` in v1 — both fields exist on every row so
  widening later needs no migration, but nothing else is accepted yet.
- `observed_on` is an ISO date in the extended form `YYYY-MM-DD` exactly, never in the future, and is
  what staleness and append-only history are computed from. The basic form (`20260801`) is rejected:
  `date.fromisoformat` accepts it, but it string-sorts above every extended-form date, so a row
  carrying one would win the latest-row comparison forever and publish a superseded price as
  current.
- `source_url` must be `https://` and resolve to a real host — it is the official pricing page you
  read on `observed_on`, not a comparison site, blog post, or cached snapshot.
- `confidence` is `low`, `medium`, or `high` — a human judgment of how directly the source states
  the number (e.g. read straight off a pricing table vs. derived from a calculator delta). It is
  informational only: nothing in `scripts/pricing.py` currently branches on it.
- `note` is free text explaining what was read and any interpretation required (e.g. how a rate was
  derived, what a plan bundles). It is required and must be non-empty.

`(provider_slug, plan, metric, region, observed_on)` must be unique — the validator rejects
duplicates.

## Rows are append-only

Never edit or delete an existing row to reflect a new price. A price change is a **new row** with
the same `provider_slug` / `plan` / `metric` / `region` and a later `observed_on`. History is the
point: `scripts/pricing.py` always uses the latest non-stale row per metric per plan, but older rows
stay in the file for anyone who wants to see how a price moved.

Add new rows to the current quarter's file (`observations/YYYY-QN.json`); start a new quarter file
rather than growing one indefinitely.

## Metric vocabulary

`metrics.json` is a controlled enum, not free text, so "these two rows measure the same thing" is a
validator-enforced fact rather than an assumption. Adding a metric is a deliberate, reviewed change:

1. Confirm the existing vocabulary genuinely cannot express the charge (check unit and description
   of every existing entry first).
2. Add an entry to `metrics.json` with a precise `unit` and `description` — someone should be able
   to interpret a row correctly without reading `scripts/pricing.py`.
3. Update or add the reference workload(s) in `workloads.json` that should consume it, if any.
4. Add rows and run `python3 scripts/pricing.py` (or `make validate`).

Do not invent a metric to shoehorn a provider's unusual pricing model into an existing one — an
inexact fit is worse than `insufficient_data`.

## Reference workloads and computation

A workload prices its cost one of two ways — every workload declares **exactly one** of `line_items`
or `shape`; declaring both or neither is a validation error.

`workloads.json` can declare fixed-quantity `line_items`, each an `{metric, quantity}` pair
(optionally `"optional": true` for a component like `plan_base_month` that some plans genuinely do
not have — Neon's Launch plan has no monthly minimum, so no base-fee row exists and zero is the true
contribution).

**A workload may only publish an assumption it actually prices.** `/pricing/` renders `assumptions`
beside the totals as a description of what the figure covers, so an assumption with no matching line
item silently misdescribes every number in that column. `validate_workloads()` enforces this:
every key in `assumptions` must appear in `ASSUMPTION_METRICS` in `scripts/pricing.py`, and the
metric it maps to must have a line item in that workload. Adding `vcpu: 2` to a workload that prices
no compute metric is a validation error, not a documentation choice.

This is not hypothetical. Both shipped workloads used to declare `vcpu`, `memory_gib`, and
`hours_month` while pricing only a plan fee, storage, and egress. The effect was a silent bias:
providers that fold compute into a fixed plan fee had that compute counted, while Neon — which
meters compute per CU-hour — had none of it counted and was published as dramatically the cheapest.
Both workloads are now named and captioned for what they price, and each carries a caveat naming the
omission and its direction. **Do not add compute line items without extending the vocabulary first**;
the three providers meter compute in three incompatible ways (Neon CU-hours, Supabase a plan-bundled
instance credit, PlanetScale a fixed cluster SKU) and the v1 vocabulary cannot express them
uniformly. An inexact fit is worse than an honest omission.

`compute_workload()` costs one workload against one provider's rows:

- Only non-stale rows are considered.
- Rows are grouped by `(currency, region, plan)` and costed independently — **plans, currencies, and
  regions are never mixed**. A total is never assembled from one provider's cheapest storage plan
  plus its cheapest egress plan, nor from a `us-east` storage rate plus a `eu-west` egress rate.
- For a given group, each required line item needs a matching, non-stale row. The latest row per
  metric wins, compared as parsed dates. If any required metric is missing, that group does not
  qualify.
- Across qualifying groups, the cheapest complete one wins. A total that is not a finite number
  (an overflow to `inf`) is not a price and disqualifies its group.
- If no group has a row for every required line item, the result is `insufficient_data` with the
  missing metric names — never a partial sum.
- Every result carries `plans_considered`: how many distinct plans had any fresh row. `1` means
  there was no comparison to win, and the surfaces say so.

### Shape workloads

A workload can instead declare `shape`, an object mapping `min_<attribute>` keys to numbers, e.g.
`{"min_storage_gib": 100}`. This answers a different question than `line_items` does: not "what does
this fixed set of metered quantities cost", but "what is the cheapest plan that provides at least
this much capacity" — the question DigitalOcean Managed Postgres and Heroku Postgres actually need,
since they sell plans with bundled storage rather than metering it per GB. `assumptions` on a shape
workload is validated against the shape itself (every assumption key must have a matching `min_<key>`
entry), not against `ASSUMPTION_METRICS`, since no line item is priced.

An observation row can carry an optional `attributes` object describing what a *plan* provides, e.g.
`{"storage_gib": 10, "memory_gib": 1}` on a `plan_base_month` row. Keys must be lowercase snake_case
and values finite non-negative numbers. Rows without `attributes` are unaffected and can never satisfy
a shape.

`compute_workload()` costs a shape workload by, within each `(currency, region)` group, finding each
plan's latest `plan_base_month` row and checking whether its `attributes` satisfy every `min_X` in the
shape. A plan with no `plan_base_month` row, or none with `attributes`, never qualifies. Among
qualifying plans the cheapest wins; ties break on plan name. As with `line_items`, stale rows are
excluded and plans, currencies, and regions are never mixed.

The result contract for `ok` is identical to a `line_items` result. For `insufficient_data`, a shape
result carries an optional `reason` string in place of a useful `missing_metrics` list —
`missing_metrics` stays present as an empty list so consumers that read it unconditionally do not
break. The `reason` text distinguishes two different facts the dataset must not conflate:

- **No plan's capacity has been recorded at all** (e.g. "no plan's included storage has been recorded
  for this provider") — no fresh `plan_base_month` row for that provider carries an `attributes`
  object, so nothing is known about whether any plan qualifies. This is the case for a provider that
  is only ever observed on metered metrics (Neon's `storage_gib_month`/`egress_gib`, say), and it is
  not a claim that the provider's real plans are too small.
- **Recorded plans fall short** (e.g. "no recorded plan provides at least 100 GiB of storage") — at
  least one plan's `attributes` were recorded, and none of them meet the shape. This is the only case
  where the dataset can honestly say a provider's plans do not provide enough.

Saying the second when only the first is true is exactly the kind of wrong-but-confident claim this
dataset exists to avoid — a provider that plainly sells larger plans than were ever recorded must not
be told apart from one that genuinely doesn't.

**`insufficient_data` beats a partial sum, always.** A partial total is silently, confidently too
low, which is exactly how comparison sites mislead. If you cannot find an official, dated source for
a required line item, leave it out and let the computation report `insufficient_data` rather than
guessing, estimating, or copying a number from a third-party aggregator.

## Staleness

A row is stale once it is older than `MAX_AGE_DAYS` (90 days), computed from `observed_on`. Stale
rows are **excluded from computed workload totals** but are never deleted — the dataset keeps full
history. `/pricing/` and provider detail pages mark stale rows explicitly rather than hiding them.

## Sourcing requirement

No row may be added without an HTTPS official source — the provider's own pricing page, docs, or
pricing calculator — read on the date recorded in `observed_on`. Do not add a row from memory, from
a competitor's comparison page, from an affiliate site, or from a date other than when you actually
read it. If a provider's pricing model cannot be expressed by the current metric vocabulary or
workload definitions, that is a reason to extend the vocabulary (see above) or to omit the row, not
to approximate.

## What this dataset is not

- Not fed into recommender scoring. `docs/RECOMMENDER.md` keeps `cost_floor` as a qualitative 1–5
  band; exact prices stay out of that model on purpose.
- Not a quote. Every surface that renders this data carries the disclaimer from
  `scripts/pricing.py` — figures are dated observations run through published assumptions, not
  something a provider will honor.
- Not automated. There is no research scan, no delta-review renderer, and no auto-merge path yet.
  Every row today was hand-entered against a cited source.

## Published surfaces

- `/pricing/` — reference-workload comparison across providers with pricing data. An
  `insufficient_data` cell shows the shape-miss `reason` (or the missing-metric list for a
  `line_items` workload) as its detail text.
- `/compare/` — a pricing block appears when compared entries have data; an `insufficient_data` cell
  prefers the shape-miss `reason` and falls back to the missing-metric list, same as `/pricing/`.
- Provider detail pages (`/providers/<slug>/`) — that provider's own dated rows, newest first within
  each plan and metric, with superseded and stale rows marked, plus a Capacity column rendering that
  row's `attributes` (e.g. "256 GiB storage · 8 GiB memory") — the fact that decided whether a plan
  qualified for a shape workload is not left invisible on the page that exists to show evidence. No
  cross-provider math.
- `/catalog/pricing.json` — the published payload (`build_pricing_catalog()`): metrics, workloads,
  computed results per provider, the raw rows, and the disclaimer. An `ok` result carries `plan`,
  `currency`, `region`, `monthly_usd`, `plans_considered`, and the `sources` it was derived from; an
  `insufficient_data` result carries `missing_metrics` and `plans_considered`, and — for a shape
  workload that found no qualifying plan — an optional `reason` string. It is serialized with
  `allow_nan=False`, so a non-finite figure fails the build rather than emitting the bare token
  `Infinity`, which Python's `json.loads` accepts but no browser does.
