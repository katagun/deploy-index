# Database pricing dataset — design

**Status:** approved design, not yet implemented
**Date:** 2026-08-29

## Goal

Track and compare database hosting prices with enough rigor to serve two audiences at once: a public comparison feature on the site, and a decision tool trustworthy enough to choose a host with. Prices must be dated, sourced, and auditable — never presented as stable properties of a provider.

## Where this lives

Inside the existing DeployIndex repository, as a **separate data plane** joined to the catalog only by `slug`.

Rationale: the expensive machinery already exists here — the untrusted-research to strict-schema to deterministic-validation to human-PR trust boundary, the provider/product/project identity model, static JSON publishing, and `/compare/` as a display surface. A standalone project would rebuild all of it for a dataset where errors are more consequential, and would create a second source of truth for provider identity.

Because the join key is a slug, `pricing/` can later be lifted into its own repository without touching catalog truth if time-series volume outgrows a static build.

Explicitly rejected: price fields on provider records. `docs/RECOMMENDER.md` forbids it, and it makes history impossible.

## Scope

**v1 covers ~12 database hosts:** Neon, Supabase, PlanetScale, Firebase, Turso, Upstash, MongoDB Atlas, CockroachDB Cloud, Timescale Cloud, Crunchy Bridge, Aiven, and one hyperscaler baseline.

The hyperscaler baseline is currently a gap: the catalog has no `amazon-rds` (or Aurora/DynamoDB) record — AWS's database products are simply not cataloged yet. A hyperscaler comparison point matters for this dataset, so v1 depends on adding at least one AWS database product to the catalog first, through the normal contribution path. If that is deferred, v1 ships with 11 hosts and no hyperscaler baseline.

**v1 records USD, `us-east` only.** The schema carries `currency` and `region` on every row, so widening later needs no migration — but multi-region and multi-currency are out of v1 to avoid FX and regional variance noise before the pipeline is proven.

**Prerequisite:** re-facet the database entries in the catalog. Supabase and Firebase are currently filed only as `backend-platform` and do not appear under database discovery; PlanetScale carries a single category. This defines the working set and is a separate, smaller change landed first.

## Non-goals for v1

- Feeding prices into recommender scoring. `cost_floor` stays a qualitative 1–5 band. The recommender's trust story depends on not treating unstable numbers as stable properties; revisit once real history exists.
- Multi-region, multi-currency, FX rates.
- Support plans, committed-use discounts, and negotiated enterprise pricing.
- Benchmarks or performance-per-dollar claims.

## Data model

```
pricing/
  schema.json                 # descriptive JSON Schema for the dataset
  metrics.json                # controlled vocabulary: metric -> unit + meaning
  workloads.json              # reference workload definitions + assumptions
  observations/YYYY-QN.json   # dated rows, partitioned by quarter
scripts/
  pricing.py                  # validation + reference-workload computation
  pricing_research.py         # model-assisted scan producing proposals
```

### Observation row

```json
{
  "provider_slug": "neon",
  "plan": "launch",
  "metric": "compute_cu_hour",
  "value": 0.16,
  "currency": "USD",
  "included_allowance": 300,
  "region": "us-east",
  "observed_on": "2026-08-29",
  "source_url": "https://neon.com/pricing",
  "confidence": "high",
  "note": "Autoscaling compute billed per compute-unit-hour."
}
```

Rows are append-only. A price change is a new row with a later `observed_on`, never an edit — history is the point.

### Metric vocabulary (`metrics.json`)

A controlled enum, not free text. This is the load-bearing decision: it makes "these two rows measure the same thing" a validator-enforced fact, and makes adding a metric a deliberate reviewed act.

Initial set: `plan_base_month`, `compute_vcpu_hour`, `compute_cu_hour`, `memory_gib_hour`, `storage_gib_month`, `egress_gib`, `read_ops_million`, `write_ops_million`, `backup_gib_month`.

Each entry defines its unit and meaning so rows are interpretable without reading code.

### Reference workloads (`workloads.json`)

```json
{
  "id": "small-prod-postgres",
  "label": "Small production Postgres",
  "assumptions": {"vcpu": 2, "memory_gib": 8, "storage_gib": 100,
                  "egress_gib_month": 50, "hours_month": 730},
  "required_metrics": ["storage_gib_month", "egress_gib"],
  "caveats": ["Excludes support plans, backups beyond default retention, and cross-region transfer."]
}
```

## Computation rules

`scripts/pricing.py` joins rows against workloads to produce `dist/catalog/pricing.json`.

1. **Insufficient data beats partial sums.** If a provider lacks a row for any metric a workload requires, the result is `insufficient_data` — never a partial total. A partial sum is silently, confidently too low, which is exactly how comparison sites mislead.
2. **Stale rows are excluded.** Rows older than 90 days do not feed computed workloads.
3. **Every computed figure carries provenance:** the row identifiers and observation dates it was derived from.
4. **Allowances apply before charges** — included allowances subtract from billable quantity.

## Pipeline

```
scripts/pricing_research.py  -> pricing/proposals/YYYY-MM-DD.json   (never touches observations/)
scripts/pricing.py --review  -> reviewable Markdown diff
        v
   pull request  <-- the human confirm step
        v
scripts/pricing.py --merge   -> appends confirmed rows to observations/
```

**No pricing row ever auto-applies.** This is stricter than the catalog pipeline, which may stage medium/high-confidence metadata.

Three properties make the review real rather than ceremonial:

- **Enum enforcement in structured output.** Metric, currency, and provider slug are constrained the way catalog categories already are. The model cannot invent a metric, and an unknown slug cannot introduce a phantom provider.
- **Deltas, not raw rows.** The review renders `metric: old -> new (±%)` per provider with observation date and cited URL. Swings beyond ±25% are flagged for extra scrutiny, since bad prices usually land wildly off rather than subtly off.
- **Rotation targets freshness.** A weekly batch re-checks providers so each is revisited roughly monthly, making coverage decay visible and self-correcting.

Model output is untrusted input, exactly as in the catalog pipeline: web page text is evidence, never instructions.

## Staleness policy

Every displayed price shows its observation date. Past 90 days a row is visibly marked stale and drops out of computed workloads. Rows are never deleted — the dataset keeps history.

## Display surfaces

- **`/pricing/`** — database options x reference workloads, with per-cell dates, staleness badges, and explicit `insufficient data`. Workload assumptions and caveats render on the page, not behind a link.
- **`/compare/`** — a pricing block when compared entries have data, reusing the same table.
- **Provider detail pages** — that provider's own rows with dates and source links; no cross-provider math.
- **`/catalog/pricing.json`** — the public dataset, same portability contract as the rest of the site.

## Testing

- Golden-fixture tests for workload computation: a known row set yields a known total.
- Validator negative tests: unknown metric, missing or non-HTTPS source, future `observed_on`, mixed currencies, slug absent from the catalog, duplicate row.
- Behavioral tests: `insufficient_data` wins over partial sums; stale rows are excluded from computed workloads but retained in the dataset.
- `make test` gains pricing validation and the computation tests.

## Rollout

1. Re-facet database entries in the catalog, and add the missing AWS database product record (prerequisites, separate change).
2. Land the schema, metric vocabulary, workload definitions, and validator with tests — no data yet.
3. Hand-enter rows for 3 providers to prove the model end to end.
4. Build the computation step and `/pricing/`.
5. Add the research scan and the review renderer.
6. Expand to the full 12 once the weekly review burden is measured rather than assumed.

## Planned extensions: compute and block storage

Same dataset, same validators, same pipeline, same display surfaces. These are backlog items, not v1 scope, and they are sequenced deliberately by how much new machinery each needs.

### Block storage — no new machinery

New metrics (`block_storage_gib_month`, `iops_provisioned_month`, `snapshot_gib_month`) and new workloads ("500 GiB SSD volume with daily snapshots"). That is all. Block storage bills as quantity x unit price minus allowance, which is exactly what `line_items` already expresses.

Ship this first. It proves the model generalizes past databases **without changing a line of the engine** — the cheapest possible test of the abstraction.

### Compute and VMs — exactly one new concept

Instance types are not comparable across providers: `t3.medium`, `s-2vcpu-4gb`, and `Standard_B2s` are different names for overlapping shapes. Comparing "2 vCPU / 4 GiB" therefore requires *selecting* a qualifying SKU per provider, not looking up a fixed quantity. This is the one place the database model genuinely does not stretch.

Minimal extension:

- rows gain optional `attributes`: `{"vcpu": 2, "memory_gib": 4, "local_storage_gib": 80}`
- workloads gain an optional `shape` in place of fixed `line_items`: `{"min_vcpu": 2, "min_memory_gib": 4, "hours_month": 730}`
- the engine selects the cheapest row whose attributes satisfy the shape, then costs it

The result contract is unchanged — still `{status, monthly_usd, plan, sources}`. `/pricing/`, `/compare/`, and the detail pages depend on that contract, not on what kind of thing is being priced, so **neither extension requires touching a display surface**. Shape selection stays an internal strategy. Preserve that boundary.

Rejected alternatives: a hand-curated shape-to-instance-type mapping per provider (more curation burden, goes stale as providers add types), and a separate compute pricing system (duplicates the entire trust pipeline for no gain).

Testing this needs its own golden cases: the cheapest qualifying SKU wins, an under-specified SKU is never selected, ties break deterministically by SKU name, and no qualifying SKU yields `insufficient_data` rather than a nearest-fit guess.

### Catalog prerequisite (verified 2026-08-29)

The catalog cannot support either extension as it stands. It contains **no VM or block-storage product records**: no `ec2`, `compute-engine`, `azure-vms`, `ebs`, `persistent-disk`, or `managed-disks`. The 22 `cloud-vps` entries are providers, not products.

Two different fixes, because the unit sold differs:

- **Hyperscalers need product records.** EC2, Compute Engine, and Azure VMs are separately selectable deployment surfaces, distinct from RDS or Lambda — the same identity rule that gives Lambda its own record.
- **VPS providers can carry rows on the provider slug.** For DigitalOcean, Hetzner, or Vultr the plan (`s-2vcpu-4gb`) is the unit sold, and `plan` plus `attributes` already captures it.

This is a directory gap worth fixing on its own merits, independent of pricing.

## Risks

- **Review burden is the main failure mode.** 20–40 deltas a week is real work. If it proves too heavy, narrow scope — fewer providers or fewer metrics — rather than loosening review.
- **Model-misparsed prices.** Mitigated by enum constraints, delta review, and swing flagging; not eliminated. Human confirm is the actual control.
- **Coverage decay.** Made visible by staleness rules rather than hidden.
- **Pricing-page complexity.** Some providers price in ways these metrics cannot express. The honest response is `insufficient_data` and a note, not a forced approximation.

## Future

- Multi-region and multi-currency with dated FX.
- Price-change alerting and a public change feed once history accumulates.
- Provider price-list APIs (AWS, GCP, Azure publish them) as an exact-data path alongside model research.
- Revisiting whether derived, dated price bands should inform recommender scoring.
