# Hosting recommendation engine

## Product goal

The recommender helps a developer reduce a very broad hosting catalog to a small, explainable shortlist. It is not a universal ranking, a price calculator, or an affiliate funnel.

The initial implementation runs entirely in the browser:

```text
catalog/providers.json
        +
catalog/recommendation-overrides.json
        │
        ▼
scripts/recommendations.py
        │
        ▼
dist/catalog/recommendations.json
        │
        ▼
site/recommendation-engine.js
        │
        ▼
/recommend/ — questionnaire, score explanations, trade-offs, shareable URL
```

Every provider and product receives one qualitative profile. Most profile fields are deterministically derived from existing categories and capabilities. A small set of widely used platforms has explicit, reviewable overrides. The generated profile is validated against the canonical catalog so names, URLs, status, availability, and identity cannot drift.

## Current variables

The first release scores variables for which the catalog has broad enough coverage to be useful.

### Workload

- static site;
- frontend or full-stack web application;
- web API or SaaS backend;
- background worker, queue consumer, or cron;
- long-running container service;
- virtual machine;
- Kubernetes workload;
- serverless function;
- edge-native application;
- database or backend platform;
- GPU or AI workload;
- agent/code sandbox;
- game server;
- WordPress or managed CMS;
- decentralized application.

### Deployment artifact

- Git source;
- Docker/OCI image;
- Docker Compose;
- function source;
- VM image or root-access requirement;
- Kubernetes manifests or Helm;
- WebAssembly;
- provider template;
- no preference.

### Economics and billing

- relative starting-cost band, one through five;
- free or nearly-free entry;
- predictable fixed billing;
- usage-based or scale-to-zero billing;
- billing through the customer’s cloud account;
- self-hosted infrastructure economics;
- no billing preference.

The model intentionally does not store dollar prices. Exact prices change frequently and require a separate dated schema with units, currencies, regions, allowances, and official source timestamps.

### Team and operating model

- available expertise, from beginner to platform specialist;
- fully managed cloud;
- bring your own cloud;
- self-hosted on customer servers;
- dedicated infrastructure;
- decentralized network;
- no operating-model preference.

### Traffic and geography

- steady;
- bursty;
- spiky or mostly idle;
- scheduled or batch;
- global traffic;
- one primary region;
- several regions;
- broad global/edge reach;
- regional choice and data-residency need.

### Network and state

- HTTP/HTTPS;
- WebSockets;
- arbitrary TCP;
- UDP;
- stateless operation;
- managed database;
- persistent disk or volume;
- object storage.

### Strong preferences

- scale to zero;
- preview environments;
- private networking;
- open-source platform;
- GPU support.

### Weighted strategic traits

Each can be ignored or weighted from low through critical:

- ease of use;
- low starting cost;
- bill predictability;
- infrastructure control;
- portability;
- maturity;
- global reach;
- enterprise readiness.

## Complete variable backlog

A useful hosting selection system can eventually cover far more than the first questionnaire. These variables should be added only when their definitions, sources, and freshness rules are explicit.

### 1. Economics

- free-tier duration, eligibility, and credit-card requirement;
- minimum monthly spend;
- fixed instance vs per-second, per-request, vCPU-second, memory-second, or token billing;
- idle billing and suspension behavior;
- build-minute and deployment-minute charges;
- bandwidth included and regional egress price;
- inter-region and private-network transfer price;
- IPv4, load balancer, NAT, static IP, and certificate cost;
- persistent disk, snapshot, backup, object storage, database, log, and metric costs;
- support-plan minimums;
- annual commitments, reserved capacity, savings plans, spot/preemptible capacity, and startup credits;
- taxes, currency, billing granularity, invoice support, and cost allocation;
- hard budgets, spend alerts, quotas, and automatic cost controls;
- price predictability and estimated total cost at representative traffic shapes.

### 2. Application and runtime fit

- supported languages, framework detection, custom buildpacks, Nixpacks, and custom build commands;
- arbitrary Dockerfile and private registry support;
- multi-container and Compose support;
- process types, workers, cron, jobs, queues, and workflow orchestration;
- maximum request duration and background execution limits;
- CPU architecture, vCPU range, memory range, local SSD, and ephemeral disk;
- GPU vendor/model, VRAM, fractional GPU, multi-GPU, and availability guarantees;
- nested virtualization, privileged containers, FUSE, kernel modules, and device access;
- WebAssembly/WASI support;
- browser automation and sandboxed code execution;
- cold-start latency, warm retention, concurrency, and scale-to-zero behavior;
- WebSockets, SSE, gRPC, HTTP/2, HTTP/3, TCP, UDP, and custom ports;
- IPv6 and dual-stack support;
- maximum image, slug, artifact, repository, and deployment size.

### 3. State and data

- managed PostgreSQL, MySQL, Redis-compatible, document, graph, vector, and analytical databases;
- supported database versions and extension availability;
- high availability, read replicas, multi-region replication, and failover;
- backup frequency, retention, point-in-time recovery, restore testing, and export format;
- persistent-volume semantics, attachment limits, snapshots, expansion, IOPS, and regional durability;
- object storage compatibility, lifecycle policies, replication, and CDN integration;
- data locality and cross-region consistency;
- service discovery, connection pooling, database proxies, and private endpoints;
- secrets, encryption at rest, customer-managed keys, and rotation.

### 4. Developer experience

- time to first deploy;
- GitHub, GitLab, Bitbucket, and monorepo integration;
- CLI, API, Terraform/OpenTofu provider, Pulumi, CDK, and GitOps coverage;
- local-development parity and devcontainer support;
- build cache behavior and remote cache support;
- preview environments and preview databases;
- environment cloning, promotion, and ephemeral environments;
- deployment strategies: rolling, blue/green, canary, traffic splitting, and instant rollback;
- release history and reproducibility;
- shell/SSH/exec access;
- log, metric, trace, profile, and event quality;
- OpenTelemetry support and external observability export;
- secret management, configuration inheritance, and environment scoping;
- team workflow, comments, approvals, and auditability;
- documentation, examples, templates, community activity, and support responsiveness.

### 5. Networking and global delivery

- number and location of regions, zones, PoPs, and edge sites;
- actual compute placement versus CDN-only presence;
- regional capacity and product availability differences;
- Anycast, global load balancing, geo-routing, latency routing, and failover;
- private networks, VPC peering, transit, VPN, private link, and on-premises connectivity;
- static ingress and egress IP addresses;
- custom domains, DNS, TLS, mTLS, WAF, DDoS protection, bot management, and rate limiting;
- CDN caching controls and cache purge behavior;
- outbound network controls and egress gateways;
- service mesh, internal DNS, and east-west encryption;
- network observability and access logs.

### 6. Reliability and operations

- published SLO/SLA and credit terms;
- status-page transparency and incident history;
- health checks, startup probes, readiness probes, and deployment gates;
- horizontal, vertical, scheduled, queue-depth, and custom-metric autoscaling;
- minimum and maximum instance controls;
- region and zone failover;
- maintenance policy and upgrade controls;
- quota visibility and increase process;
- disaster-recovery tooling and recovery objectives;
- backup ownership and restore responsibility;
- log and metric retention;
- operational API completeness;
- support channels, hours, response targets, and escalation path;
- provider capacity history and supply constraints.

### 7. Security, privacy, and governance

- SOC 1/2, ISO 27001, PCI DSS, HIPAA, FedRAMP, GDPR, and regional certifications;
- data-processing agreements and subprocessors;
- data residency and sovereign-cloud options;
- SSO, SAML, OIDC, SCIM, RBAC, custom roles, service accounts, and MFA enforcement;
- audit logs and retention;
- customer-managed encryption keys and HSM integration;
- vulnerability scanning, SBOM, image signing, provenance, and policy enforcement;
- network isolation, dedicated tenancy, confidential compute, and sandbox boundary;
- secrets lifecycle and key rotation;
- abuse response and content/workload restrictions;
- organization, project, environment, and billing-account hierarchy;
- policy as code and approval workflows.

### 8. Strategic and organizational fit

- provider age, funding, profitability, ownership, acquisition history, and roadmap stability;
- product status, deprecation policy, migration support, and historical shutdown behavior;
- open-source license, governance, release cadence, maintainer count, and bus factor;
- standard OCI, Kubernetes, PostgreSQL, S3, OpenTelemetry, and Terraform compatibility;
- export paths for data, images, configuration, logs, and secrets;
- BYOC, hybrid, on-premises, and air-gapped deployment;
- customer ownership of cloud resources and direct cloud billing;
- lock-in at runtime, API, data, networking, identity, and workflow layers;
- ecosystem partners, marketplace, consultants, and hiring availability;
- contract terms, procurement friendliness, insurance, and enterprise references.

### 9. Workload-specific signals

- frontend: framework support, image optimization, ISR, edge middleware, preview UX;
- SaaS/API: connection limits, worker processes, WebSockets, queues, private services;
- AI: GPU cold starts, model caching, weights storage, autoscaling latency, inference observability;
- agents: sandbox startup, isolation, snapshots, persistence, internet controls, maximum session duration;
- databases: extensions, branch/clone speed, PITR, replicas, connection pooling;
- games: UDP, session orchestration, regional fleets, DDoS protection, state handoff;
- media: transcoding acceleration, local scratch space, large uploads, egress economics;
- WordPress/CMS: migrations, staging, backups, CDN/WAF, plugin constraints, support;
- regulated workloads: approved regions, private connectivity, evidence packages, audit support.

## Scoring rules

The engine combines four kinds of evidence:

1. **Compatibility** — workload and artifact matches receive the largest positive weight.
2. **Constraints** — unsupported protocols, GPU requirements, and incompatible operating models receive strong penalties; GPU is a hard filter.
3. **Scenario fit** — traffic, geography, state, budget, expertise, billing shape, and requested features adjust the score.
4. **Priorities** — users control the relative importance of ease, cost, predictability, control, portability, maturity, reach, and enterprise readiness.

The engine returns a zero-to-100 fit score, up to four positive reasons, and up to three trade-offs. It does not claim statistical precision. The number is a deterministic summary of the selected assumptions.

## Data and trust rules

- Recommendation identity fields must exactly match the canonical catalog.
- A profile exists for every catalog entry, including archived entries; unavailable entries are excluded from live results.
- Curated overrides are small, version-controlled diffs.
- No affiliate or sponsored weight exists.
- No exact price is stored without a dated pricing schema.
- A qualitative profile is not evidence that a provider is reliable, secure, or suitable for regulated production.
- The UI must always show fit reasons, verification caveats, and an official-provider link.
- Material scoring changes require regression tests for representative scenarios.

## Separate dated datasets, not profile fields

Exact pricing, benchmarks, regions, compliance, and incidents do not belong as loose fields on the
qualitative profile. Each needs a dated, source-aware dataset with units and provenance of its own.
That separation allows historical comparison and expiry rules without pretending that today's price
is a permanent property of the provider — and it keeps the recommender's `cost_floor` an honest
qualitative band rather than a number pretending to precision.

The first such dataset has shipped: `pricing/` holds append-only, dated database pricing
observations joined to the catalog by slug only, with a controlled metric vocabulary, declarative
reference workloads, and `insufficient_data`-over-partial-sum computation. See
[`../pricing/README.md`](../pricing/README.md) for the row shape, the append-only supersede rule,
the sourcing requirement, and how to add a metric or a row.

Prices still never feed recommender scoring, and nothing in `scripts/recommendations.py` reads the
pricing dataset. Benchmarks, regions, compliance, and incidents remain undesigned.
