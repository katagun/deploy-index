# Roadmap

## Phase 1 — trustworthy broad directory

Delivered in the initial repository:

- broad seed covering established and recent providers/products/projects;
- provider/product/project identity model;
- searchable, filterable, responsive static catalog;
- one permanent page per record;
- methodology and public JSON API;
- strict validation and internal-link checks;
- weekly web-research proposal pipeline;
- conservative application policy and GitHub review PRs;
- Codex project instructions and reproducible commands;
- client-side recommendation engine with six presets, shareable state, explainable scoring, and a complete qualitative profile for every catalog entry;
- Cloudflare Workers Static Assets production configuration and deploy workflow.

## Phase 2 — better discovery

Delivered:

- comparison tray for two to four entries, with a capability matrix, qualitative trait bands, and URL-backed state at `/compare/`;
- free-tier tagging across the catalog so free-entry filtering is data-driven.

Next:

- “similar options” ranking;
- geographic region and data-residency facets;
- protocol, storage, compute, scale-to-zero, GPU, and BYOC facets;
- framework/language deployment guides;
- stable catalog changelog and recent-launch feed;
- user-submitted correction form that opens structured GitHub issues.

## Phase 3 — evidence depth

- field-level citations rather than record-level source lists;
- dated ownership and product-status history;
- official status-page and changelog monitoring;
- GitHub release/activity signals for open-source projects;
- automated link-health reports separated from shutdown decisions;
- source snapshots or hashes where licensing and policy allow;
- multi-agent research split by category with a final deduplication pass.

## Phase 4 — practical selection tools

Delivered foundation:

- workload questionnaire producing transparent matches rather than paid rankings;
- scenario presets, relative economics, operating-model constraints, hard requirements, weighted priorities, and trade-off explanations;
- generated recommendation profile API and regression tests.

Delivered — database pricing dataset (foundation):

- a validated, append-only, dated pricing dataset (`pricing/`) — controlled metric vocabulary,
  declarative reference workloads, and `insufficient_data`-over-partial-sum computation — designed in
  [`docs/superpowers/specs/2026-08-29-database-pricing-design.md`](superpowers/specs/2026-08-29-database-pricing-design.md)
  and built per
  [`docs/superpowers/plans/2026-08-29-database-pricing-foundation.md`](superpowers/plans/2026-08-29-database-pricing-foundation.md);
  see [`../pricing/README.md`](../pricing/README.md) for the contributor guide;
- hand-entered seed data for 3 database hosts (Neon, Supabase, PlanetScale), USD / `us-east` only;
- `/pricing/`, a pricing block in `/compare/`, an "Observed pricing" section on provider detail pages,
  and `/catalog/pricing.json`.

The two reference workloads price a plan fee, storage, and egress — **not metered compute**, which
the v1 metric vocabulary cannot express uniformly across Neon's CU-hours, Supabase's plan-bundled
instance credit, and PlanetScale's fixed cluster SKUs. They are named and captioned accordingly
(`storage-egress-100gib`, `storage-egress-10gib`), and `validate_workloads()` rejects any workload
that publishes an assumption it does not price.

Not delivered yet, still planned:

- the model-assisted pricing research scan and its delta-review renderer — the dataset above is
  entirely hand-entered today;
- a compute metric vocabulary that can express Neon-style metered CU-hours, Supabase-style bundled
  instance credits, and PlanetScale-style fixed cluster SKUs in one comparable unit, which is the
  prerequisite for any workload that claims to price a whole deployment;
- expansion from 3 seeded providers to the full v1 target of roughly 12, including a hyperscaler
  baseline;
- multi-region and multi-currency support;
- **block storage pricing** — extends the pricing dataset with volume, IOPS, and
  snapshot metrics. Needs no engine changes, so it ships first and proves the
  model generalizes beyond databases;
- **compute and VM pricing** (EC2, Compute Engine, Azure VMs, Droplets, and the
  VPS field) — needs one new concept, SKU attributes plus shape-based selection,
  because instance types are not comparable across providers by name;
- **catalog prerequisite for both:** the directory currently has no VM or
  block-storage product records at all — no EC2, Compute Engine, Azure VMs, EBS,
  or Persistent Disk. Hyperscaler compute and storage products need their own
  entries; VPS providers can carry pricing on the provider record, since the
  plan is the unit sold. Worth fixing independent of pricing.
- egress, idle billing, minimum spend, cold-start, protocol, volume, and database-operation comparisons;
- migration and portability profiles;
- community-maintained deployment recipes;
- reproducible benchmark harnesses whose methodology is public.

## Phase 5 — sustainable operations

- editorial dashboard for proposal triage;
- maintainer roles and source-review queues;
- signed catalog releases and downloadable snapshots;
- public change API or feed;
- sponsorship that never changes organic ordering;
- formal correction, disclosure, and conflict-of-interest policies.
