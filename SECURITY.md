# Security policy

## Reporting a vulnerability

Open a private security advisory on this repository (GitHub → Security → Advisories → "Report a vulnerability"). Please do not open a public issue for anything exploitable. Reports are acknowledged on a best-effort basis; this is an open-source directory project without a paid response team.

In scope, among other things:

- ways to get untrusted content past the research trust boundary and into the published catalog or generated HTML;
- HTML/markdown injection through catalog fields, research output, or generated pull-request bodies;
- weaknesses in the deterministic proposal validation (`scripts/proposals.py`) that would let automation stage changes the documented policy forbids (deletions, status changes, identity changes);
- workflow or supply-chain issues in `.github/workflows/`.

## Design

The threat model and its controls are documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#threat-model). The core invariants:

- third-party web content and model output are untrusted input, always;
- the model never writes to the catalog — strict structured output plus deterministic validation plus human PR review;
- automation never deletes records and never applies status, shutdown, archive, or identity (name/URL/entity-type) changes;
- generated pages escape every interpolated value, and the published site carries a `default-src 'self'` Content-Security-Policy with no inline-script allowance.
