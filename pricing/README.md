# Pricing dataset

A separate data plane from `catalog/providers.json`, joined to it only by `provider_slug`. It exists
because exact prices are unstable and require dated, sourced, auditable rows — not a field on a
provider record. See `docs/superpowers/specs/2026-08-29-database-pricing-design.md` for the full design
rationale and `docs/superpowers/plans/2026-08-29-database-pricing-foundation.md` for what shipped.

**Current scope:** database hosting only, 3 providers (Neon, Supabase, PlanetScale), `USD` /
`us-east` only. The design envisions ~12 providers and a hyperscaler baseline; only the foundation
and a hand-entered seed shipped so far. The model-assisted research scan described in the spec does
not exist — every row below was entered by a human who read the cited source. Do not describe
automated pricing research as a feature until it is actually built.

## Layout

```
pricing/
  metrics.json                # controlled vocabulary: metric -> unit + description
  workloads.json               # reference workload definitions (line items over the vocabulary)
  observations/YYYY-QN.json    # dated rows, partitioned by quarter
scripts/pricing.py              # loading, validation, staleness, and computation
```

`python3 scripts/pricing.py` validates the dataset and prints a summary; it is wired into
`make validate` and therefore `make test`. There is no separate `pricing/schema.json` — the
enforced shape is `REQUIRED_ROW_FIELDS` and the validators in `scripts/pricing.py`.

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
- `plan` is the provider's own plan/tier/SKU name (`launch`, `pro`, `ps-80-arm64-ha`). Rows for the
  same metric under different plans are never mixed together.
- `metric` must be one of the enums in `metrics.json` (see below).
- `value` and `included_allowance` are non-negative numbers; `included_allowance` is the free
  quantity of that metric's unit before `value` applies.
- `currency` must be `USD` and `region` must be `us-east` in v1 — both fields exist on every row so
  widening later needs no migration, but nothing else is accepted yet.
- `observed_on` is an ISO date, never in the future, and is what staleness and append-only history
  are computed from.
- `source_url` must be `https://` and resolve to a real host — it is the official pricing page you
  read on `observed_on`, not a comparison site, blog post, or cached snapshot.
- `confidence` is `low`, `medium`, or `high` — a human judgment of how directly the source states
  the number (e.g. read straight off a pricing table vs. derived from a calculator delta). It is
  informational only: nothing in `scripts/pricing.py` currently branches on it.
- `note` is free text explaining what was read and any interpretation required (e.g. how a rate was
  derived, what a plan bundles).

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

`workloads.json` declares fixed-quantity `line_items`, each an `{metric, quantity}` pair (optionally
`"optional": true` for a component like `plan_base_month` that some plans fold into other metrics).
`compute_workload()` in `scripts/pricing.py` costs one workload against one provider's rows:

- Only non-stale rows are considered.
- Rows are grouped by `plan` and costed independently — **plans are never mixed**. A total is never
  assembled from one provider's cheapest storage plan plus its cheapest egress plan.
- For a given plan, each required line item needs a matching, non-stale row. If any required metric
  is missing, that plan does not qualify.
- Across qualifying plans, the cheapest complete one wins.
- If no plan has a row for every required line item, the result is `insufficient_data` with the
  missing metric names — never a partial sum.

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

- `/pricing/` — reference-workload comparison across providers with pricing data.
- `/compare/` — a pricing block appears when compared entries have data.
- Provider detail pages (`/providers/<slug>/`) — that provider's own dated rows, no cross-provider
  math.
- `/catalog/pricing.json` — the published payload (`build_pricing_catalog()`): metrics, workloads,
  computed results per provider, the raw rows, and the disclaimer.
