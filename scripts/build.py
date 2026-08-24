#!/usr/bin/env python3
"""Build DeployIndex into portable static files with no third-party dependencies."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from catalog import ROOT, load_catalog, validate_catalog
from recommendations import build_recommendation_catalog, validate_recommendation_catalog

SITE = ROOT / "site"
DIST = ROOT / "dist"
SITE_URL = (os.environ.get("SITE_URL") or "http://localhost:8000").rstrip("/")
REPOSITORY_URL = os.environ.get("REPOSITORY_URL") or "https://github.com/"

ENTITY_LABELS = {"provider": "Provider", "product": "Product", "project": "Open project"}
ERA_LABELS = {"established": "Established", "modern": "Modern · 2020–23", "recent": "Recent · 2024+"}
STATUS_LABELS = {
    "active": "Active",
    "beta": "Beta",
    "transitioning": "Transitioning",
    "sunset": "Sunset",
    "archived": "Archived",
}
AVAILABILITY_LABELS = {
    "general": "Generally available",
    "preview": "Preview",
    "limited": "Limited access",
    "existing-customers-only": "Existing customers only",
    "discontinued": "Discontinued",
}
MODEL_LABELS = {
    "managed-cloud": "Managed cloud",
    "bring-your-own-cloud": "Bring your own cloud",
    "self-hosted": "Self-hosted",
    "dedicated-server": "Dedicated server",
    "marketplace": "Marketplace",
    "decentralized-network": "Decentralized network",
}
SPECIAL_LABELS = {
    "tcp-udp": "TCP / UDP",
    "ci-cd": "CI / CD",
    "gpu": "GPU",
    "api": "API",
    "webassembly": "WebAssembly",
    "object-storage": "Object storage",
    "git-deploy": "Git deploy",
    "scale-to-zero": "Scale to zero",
    "private-networking": "Private networking",
    "managed-kubernetes": "Managed Kubernetes",
    "virtual-machines": "Virtual machines",
    "background-workers": "Background workers",
    "preview-environments": "Preview environments",
    "persistent-storage": "Persistent storage",
    "model-inference": "Model inference",
    "code-execution": "Code execution",
    "infrastructure-as-code": "Infrastructure as code",
    "distributed-compute": "Distributed compute",
    "decentralized-storage": "Decentralized storage",
    "managed-cms": "Managed CMS",
    "free-tier": "Free tier",
}


def esc(value: object, *, quote: bool = True) -> str:
    return html.escape(str(value), quote=quote)


def label(value: str) -> str:
    return SPECIAL_LABELS.get(value, value.replace("-", " ").title())


def monogram(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", name).strip()
    parts = [part for part in cleaned.split() if part]
    if not parts:
        return "//"
    if len(parts) == 1:
        token = parts[0]
        if token.isupper() and len(token) <= 5:
            return token[:3]
        return token[:2].upper()
    return "".join(part[0] for part in parts[:2]).upper()


def hue(slug: str) -> int:
    raw = int(hashlib.sha1(slug.encode("utf-8")).hexdigest()[:8], 16)
    return 120 + raw % 210


def normalize_search(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9+.#/ -]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def canonical(path: str) -> str:
    return f"{SITE_URL}{path}"


def render_base(
    *,
    title: str,
    description: str,
    path: str,
    main: str,
    scripts: str = "",
    head_extra: str = "",
    body_class: str = "",
) -> str:
    template = (SITE / "base.html").read_text(encoding="utf-8")
    replacements = {
        "{{TITLE}}": esc(title),
        "{{DESCRIPTION}}": esc(description),
        "{{CANONICAL_URL}}": esc(canonical(path)),
        "{{MAIN}}": main,
        "{{SCRIPTS}}": scripts,
        "{{HEAD_EXTRA}}": head_extra,
        "{{BODY_CLASS}}": esc(body_class),
        "{{REPOSITORY_URL}}": esc(REPOSITORY_URL),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def card_html(item: dict, category_labels: dict[str, str], *, hidden: bool = False) -> str:
    category_names = [category_labels[key] for key in item["categories"]]
    capability_names = [label(value) for value in item["capabilities"]]
    model_names = [MODEL_LABELS[value] for value in item["operating_models"]]
    search_parts = [
        item["name"], item["summary"], item["best_for"], ENTITY_LABELS[item["entity_type"]],
        ERA_LABELS[item["era"]], STATUS_LABELS[item["status"]], *category_names,
        *capability_names, *model_names,
    ]
    if item["open_source"]:
        search_parts.extend(["open source", "opensource", "oss"])
    tags = [category_labels[item["primary_category"]]]
    if item["open_source"]:
        tags.append("Open source")
    for capability in capability_names:
        if capability not in tags and len(tags) < 4:
            tags.append(capability)
    tag_markup = "".join(f'<span class="tag">{esc(value)}</span>' for value in tags)
    foot = f"{ENTITY_LABELS[item['entity_type']]} · {ERA_LABELS[item['era']].replace(' · 2020–23', '').replace(' · 2024+', '')}"
    hidden_attr = " hidden" if hidden else ""
    return f'''<article class="provider-card" style="--card-hue:{hue(item['slug'])}"{hidden_attr}
      data-name="{esc(item['name'].casefold())}"
      data-search="{esc(normalize_search(' '.join(search_parts)))}"
      data-primary="{esc(item['primary_category'])}"
      data-categories="{esc(','.join(item['categories']))}"
      data-entity="{esc(item['entity_type'])}"
      data-era="{esc(item['era'])}"
      data-models="{esc(','.join(item['operating_models']))}"
      data-status="{esc(item['status'])}"
      data-open-source="{str(item['open_source']).lower()}"
      data-launch-year="{item['launch_year'] or ''}"
      data-featured="{1 if item['featured'] else 0}">
      <div class="card-top">
        <div class="provider-monogram" aria-hidden="true">{esc(monogram(item['name']))}</div>
        <div class="card-heading">
          <h3><a href="/providers/{esc(item['slug'])}/">{esc(item['name'])}</a></h3>
          <div class="card-meta"><span>{esc(ENTITY_LABELS[item['entity_type']])}</span><span>·</span><span>{esc(category_labels[item['primary_category']])}</span></div>
        </div>
        <span class="status-pill" data-status="{esc(item['status'])}">{esc(STATUS_LABELS[item['status']])}</span>
      </div>
      <p class="card-summary">{esc(item['summary'])}</p>
      <div class="tag-list">{tag_markup}</div>
      <div class="card-foot"><p>{esc(foot)}</p><span class="card-arrow" aria-hidden="true">↗</span></div>
    </article>'''


def json_ld(item: dict, category_labels: dict[str, str]) -> str:
    if item["entity_type"] == "provider":
        payload = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": item["name"],
            "url": item["url"],
            "description": item["summary"],
        }
    else:
        payload = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": item["name"],
            "url": item["url"],
            "description": item["summary"],
            "applicationCategory": category_labels[item["primary_category"]],
            "operatingSystem": "Cloud / Web",
        }
    return json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")


def related_items(item: dict, providers: list[dict]) -> list[dict]:
    candidates: list[tuple[float, str, dict]] = []
    categories = set(item["categories"])
    capabilities = set(item["capabilities"])
    for other in providers:
        if other["slug"] == item["slug"]:
            continue
        score = 0.0
        if item["parent_slug"] and other["parent_slug"] == item["parent_slug"]:
            score += 15
        if other["parent_slug"] == item["slug"] or item["parent_slug"] == other["slug"]:
            score += 13
        if other["primary_category"] == item["primary_category"]:
            score += 7
        score += len(categories & set(other["categories"])) * 2
        score += len(capabilities & set(other["capabilities"])) * 0.35
        if other["featured"]:
            score += 0.4
        if other["status"] in {"archived", "sunset"}:
            score -= 5
        if score > 0:
            candidates.append((-score, other["name"].casefold(), other))
    candidates.sort(key=lambda entry: (entry[0], entry[1]))
    return [entry[2] for entry in candidates[:6]]


def provider_page(item: dict, providers_by_slug: dict[str, dict], providers: list[dict], category_labels: dict[str, str]) -> str:
    parent = providers_by_slug.get(item["parent_slug"]) if item["parent_slug"] else None
    category_tags = "".join(f'<span class="tag">{esc(category_labels[key])}</span>' for key in item["categories"])
    capability_tags = "".join(f'<span class="tag">{esc(label(value))}</span>' for value in item["capabilities"]) or '<span class="tag">Capabilities pending verification</span>'
    model_tags = "".join(f'<span class="tag">{esc(MODEL_LABELS[value])}</span>' for value in item["operating_models"])
    source_links = "".join(
        f'<a class="source-link" href="{esc(url)}" rel="noreferrer"><span>{esc(urlparse(url).netloc.removeprefix("www."))}</span><span aria-hidden="true">↗</span></a>'
        for url in item["source_urls"]
    )
    verified = item["last_verified"] or "Pending source-by-source verification"
    verification_tone = "Verified" if item["last_verified"] else "Seed record"
    warning = ""
    if item["status"] in {"archived", "sunset"}:
        warning = f'''<div class="verification-note"><div>⚠</div><p><strong>{esc(STATUS_LABELS[item['status']])}:</strong> {esc(item['change_note'])}</p></div>'''
    elif not item["last_verified"]:
        warning = '''<div class="verification-note"><div>⌁</div><p><strong>Verification pending:</strong> this entry came from the initial inventory and should be treated as a lead until its official sources are reviewed by the weekly workflow.</p></div>'''
    related = related_items(item, providers)
    related_markup = "".join(
        f'<a class="related-card" href="/providers/{esc(other["slug"])}/"><strong>{esc(other["name"])}</strong><span>{esc(category_labels[other["primary_category"]])} · {esc(ENTITY_LABELS[other["entity_type"]])}</span></a>'
        for other in related
    )
    parent_row = ""
    if parent:
        parent_row = f'<div><dt>Parent</dt><dd><a href="/providers/{esc(parent["slug"])}/">{esc(parent["name"])}</a></dd></div>'
    year_value = str(item["launch_year"]) if item["launch_year"] else "Not yet sourced"
    oss_value = "Yes" if item["open_source"] else "No / not cataloged as open"
    main = f'''
    <div class="detail-shell shell" style="--card-hue:{hue(item['slug'])}">
      <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Catalog</a><span>/</span><span>{esc(category_labels[item['primary_category']])}</span><span>/</span><span aria-current="page">{esc(item['name'])}</span></nav>
      <section class="detail-hero">
        <div>
          <div class="detail-identity">
            <div class="detail-monogram" aria-hidden="true">{esc(monogram(item['name']))}</div>
            <div>
              <div class="detail-kinds"><span>{esc(ENTITY_LABELS[item['entity_type']])}</span><span>{esc(STATUS_LABELS[item['status']])}</span><span>{esc(category_labels[item['primary_category']])}</span></div>
              <h1>{esc(item['name'])}</h1>
            </div>
          </div>
          <p class="detail-summary">{esc(item['summary'])}</p>
          <p class="detail-best"><strong>Best fit:</strong> {esc(item['best_for'])}</p>
          <div class="detail-actions">
            <a class="button button-primary" href="{esc(item['url'])}" rel="noreferrer">Official website <span aria-hidden="true">↗</span></a>
            <a class="button button-ghost" href="/?category={esc(item['primary_category'])}">Explore similar options</a>
          </div>
        </div>
        <aside class="detail-panel">
          <h2>Catalog record</h2>
          <dl class="fact-list">
            <div><dt>Status</dt><dd>{esc(STATUS_LABELS[item['status']])}</dd></div>
            <div><dt>Availability</dt><dd>{esc(AVAILABILITY_LABELS[item['availability']])}</dd></div>
            <div><dt>Era</dt><dd>{esc(ERA_LABELS[item['era']])}</dd></div>
            <div><dt>Launch year</dt><dd>{esc(year_value)}</dd></div>
            <div><dt>Open source</dt><dd>{esc(oss_value)}</dd></div>
            <div><dt>Evidence level</dt><dd>{esc(item['confidence'].title())}</dd></div>
            {parent_row}
          </dl>
        </aside>
      </section>
      <div class="detail-grid">
        <section class="detail-section"><h2>Capabilities</h2><p>High-level workload and platform primitives associated with this entry.</p><div class="detail-tags">{capability_tags}</div></section>
        <section class="detail-section"><h2>Operating model</h2><p>Where the control plane and workload infrastructure are expected to run.</p><div class="detail-tags">{model_tags}</div></section>
        <section class="detail-section"><h2>Categories</h2><p>Directory facets used for discovery rather than mutually exclusive classifications.</p><div class="detail-tags">{category_tags}</div></section>
        <section class="detail-section"><h2>Verification</h2><p><strong>{esc(verification_tone)}.</strong> Last verified: {esc(verified)}.</p>{warning}</section>
        <section class="detail-section full"><h2>Source trail</h2><p>Official pages and primary evidence used or queued for review. Pricing and feature claims should always include a retrieval date.</p><div class="source-list">{source_links}</div></section>
        <section class="detail-section full"><h2>Related deployment surfaces</h2><p>Entries sharing a parent platform, category, or capability profile.</p><div class="related-grid">{related_markup}</div></section>
      </div>
    </div>'''
    head = f'<script type="application/ld+json">{json_ld(item, category_labels)}</script>'
    return render_base(
        title=f"{item['name']} — DeployIndex",
        description=item["summary"],
        path=f"/providers/{item['slug']}/",
        main=main,
        head_extra=head,
        body_class="provider-detail-page",
    )


def method_page(total: int) -> str:
    main = f'''
    <section class="page-hero shell">
      <p class="kicker">Methodology</p>
      <h1>Automation finds changes.<br />Evidence decides.</h1>
      <p>DeployIndex starts with a broad inventory of {total} entries, then improves it through a weekly research-and-review loop. The system is designed to discover aggressively while publishing conservatively.</p>
    </section>
    <div class="content-grid shell">
      <nav class="toc" aria-label="On this page"><strong>On this page</strong><a href="#scope">Scope</a><a href="#pipeline">Weekly pipeline</a><a href="#changes">Change policy</a><a href="#confidence">Confidence</a><a href="#data">Data model</a><a href="#operations">Operations</a></nav>
      <article class="prose">
        <section id="scope"><h2>What belongs in the directory</h2><p>The unit of discovery is a <em>deployment surface</em>, not merely a company. The catalog therefore distinguishes:</p><ul><li><strong>Providers</strong>, such as AWS, DigitalOcean, or Cloudflare.</li><li><strong>Products</strong>, such as Cloud Run, Workers, App Platform, or Azure Container Apps.</li><li><strong>Open projects</strong>, such as Coolify, Dokku, Knative, or Agones.</li></ul><p>Entries are categorized by primary use while retaining multiple secondary facets. “All” is an evolving target, not a one-time completeness claim.</p></section>
        <section id="pipeline"><h2>The weekly pipeline</h2><div class="pipeline"><div><div><h3>Snapshot</h3><p>Validate the current JSON catalog and choose a rotating batch of existing entries for re-verification.</p></div></div><div><div><h3>Discover</h3><p>Use web search across launch queries, official announcements, documentation, changelogs, and open-source ecosystems.</p></div></div><div><div><h3>Extract</h3><p>Request schema-constrained candidates, updates, status alerts, and source URLs. Unstructured prose never writes directly to the catalog.</p></div></div><div><div><h3>Verify</h3><p>Prefer first-party evidence, normalize domains, check URLs, detect duplicates, and reject incomplete or contradictory records.</p></div></div><div><div><h3>Propose</h3><p>Write a dated proposal and apply only low-risk metadata changes. New entries and material status changes remain explicit diffs.</p></div></div><div><div><h3>Review</h3><p>Open a pull request containing the proposal, catalog diff, source trail, validation results, and regenerated site.</p></div></div><div><div><h3>Publish</h3><p>Merge after review. Any static host can rebuild and deploy the generated files.</p></div></div></div><div class="callout"><strong>Design rule:</strong> the automation may be exhaustive in discovery, but it must be humble in publication.</div></section>
        <section id="changes"><h2>Add, update, archive—never silently erase</h2><h3>Addition</h3><p>A new entry needs a canonical name, official URL, clear deployment relevance, entity type, primary category, and at least one primary source. Similar names and domains are deduplicated before proposal.</p><h3>Updates</h3><p>Low-risk changes include corrected URLs, added official sources, and verification timestamps. Pricing, availability, ownership, product scope, and launch dates require explicit evidence and a dated note.</p><h3>Removal and shutdown</h3><p>A failed request is not evidence that a company is dead. An entry becomes <code>sunset</code> or <code>archived</code> only after official documentation, a first-party announcement, or multiple corroborating signals are reviewed. Archived entries remain addressable so links and historical comparisons do not disappear.</p></section>
        <section id="confidence"><h2>Confidence states</h2><ul><li><code>seed</code>: part of the broad initial inventory and awaiting source-by-source review.</li><li><code>low</code>: plausible, but material fields still need stronger evidence.</li><li><code>medium</code>: supported by reliable sources, with some incomplete fields.</li><li><code>high</code>: recently checked against primary sources and internally consistent.</li></ul><p>Confidence applies to the directory record—not to the reliability or quality of the hosting company.</p></section>
        <section id="data"><h2>Portable data by default</h2><p>The source of truth is <code>catalog/providers.json</code>, validated by the deterministic checks in <code>scripts/validate.py</code>; a descriptive JSON Schema is published at <code>catalog/schema.json</code> and kept enum-synchronized by a unit test. The site generator produces static HTML and a public JSON endpoint. This keeps the catalog inspectable, forkable, and deployable without a proprietary database.</p><div class="code-block">{{\n  "slug": "fly-io",\n  "entity_type": "provider",\n  "primary_category": "managed-containers",\n  "categories": ["managed-containers", "edge-compute", "paas"],\n  "status": "active",\n  "source_urls": ["https://fly.io/"]\n}}</div></section>
        <section id="operations"><h2>Operating safeguards</h2><ul><li>Use read-only web research credentials and a spend cap for the model API.</li><li>Run the workflow with least-privilege GitHub permissions: repository contents and pull requests only.</li><li>Respect robots directives and avoid high-rate crawling; this is research, not indiscriminate scraping.</li><li>Do not publish affiliate rankings as neutral recommendations.</li><li>Run schema validation, duplicate checks, static build, and link checks before every merge.</li><li>Keep generated claims paraphrased and preserve source URLs rather than copying marketing text.</li></ul><p>The weekly researcher uses OpenAI's Responses API with web search and structured output. It can be replaced by another search provider because the proposal schema is independent of the model.</p></section>
      </article>
    </div>'''
    return render_base(
        title="Methodology — DeployIndex",
        description="How DeployIndex discovers, verifies, updates, and archives hosting platforms through a weekly evidence-aware workflow.",
        path="/method/",
        main=main,
        body_class="method-page",
    )


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    # A localhost default is fine for local previews, but a CI build without an
    # explicit SITE_URL would silently publish localhost canonicals, robots.txt,
    # and sitemap entries. Fail loudly instead.
    if os.environ.get("CI") and not os.environ.get("SITE_URL"):
        print("ERROR: SITE_URL must be set for CI builds (e.g. https://deployindex.example); canonical URLs would otherwise point at localhost.")
        return 1
    catalog = load_catalog()
    errors = validate_catalog(catalog)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    recommendation_catalog = build_recommendation_catalog(catalog)
    recommendation_errors = validate_recommendation_catalog(recommendation_catalog, catalog)
    if recommendation_errors:
        for error in recommendation_errors:
            print(f"ERROR: {error}")
        return 1

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets").mkdir(parents=True)
    (DIST / "catalog").mkdir(parents=True)
    (DIST / "providers").mkdir(parents=True)

    for asset in ("styles.css", "app.js", "theme.js", "theme-init.js", "recommendation-engine.js", "recommend.js", "favicon.svg", "og.svg"):
        shutil.copy2(SITE / asset, DIST / "assets" / asset)
    shutil.copy2(ROOT / "catalog" / "providers.json", DIST / "catalog" / "providers.json")
    shutil.copy2(ROOT / "catalog" / "schema.json", DIST / "catalog" / "schema.json")
    if (SITE / "_headers").exists():
        shutil.copy2(SITE / "_headers", DIST / "_headers")
    write(DIST / "catalog" / "recommendations.json", json.dumps(recommendation_catalog, indent=2, ensure_ascii=False) + "\n")

    providers = catalog["providers"]
    category_labels = catalog["category_labels"]
    providers_by_slug = {item["slug"]: item for item in providers}
    available_statuses = {"active", "beta", "transitioning"}
    available = [item for item in providers if item["status"] in available_statuses]
    category_counts = Counter(item["primary_category"] for item in providers)
    open_source_count = sum(item["open_source"] for item in providers)

    initial_order = sorted(providers, key=lambda item: (not item["featured"], item["name"].casefold()))
    cards = "\n".join(
        card_html(item, category_labels, hidden=item["status"] not in available_statuses)
        for item in initial_order
    )
    buttons = "\n".join(
        f'<button class="category-chip" type="button" data-category="{esc(key)}" data-label="{esc(category_labels[key])}">{esc(category_labels[key])} <span>{category_counts[key]}</span></button>'
        for key in sorted(category_labels, key=lambda key: (-category_counts[key], category_labels[key]))
    )
    signals_base = [
        f"{len(providers)} catalog entries",
        *[f"{category_labels[key]} · {category_counts[key]}" for key in sorted(category_counts, key=category_counts.get, reverse=True)[:10]],
        "Weekly evidence review",
        "Portable JSON",
        "No affiliate ranking",
    ]
    signal_items = "".join(f'<span class="signal-item">{esc(value)}</span>' for value in signals_base * 2)
    index_template = (SITE / "index.html").read_text(encoding="utf-8")
    for token, value in {
        "{{TOTAL_COUNT}}": str(len(providers)),
        "{{AVAILABLE_COUNT}}": str(len(available)),
        "{{CATEGORY_COUNT}}": str(len(category_labels)),
        "{{OPEN_SOURCE_COUNT}}": str(open_source_count),
        "{{CATEGORY_BUTTONS}}": buttons,
        "{{PROVIDER_CARDS}}": cards,
        "{{SIGNAL_ITEMS}}": signal_items,
    }.items():
        index_template = index_template.replace(token, value)
    index_page = render_base(
        title="DeployIndex — Every place to run code",
        description="Explore cloud providers, PaaS products, edge runtimes, GPU clouds, backend platforms, and self-hosted deployment projects.",
        path="/",
        main=index_template,
        scripts='<script src="/assets/app.js" defer></script>',
        body_class="catalog-page",
    )
    write(DIST / "index.html", index_page)
    write(DIST / "method" / "index.html", method_page(len(providers)))
    recommend_template = (SITE / "recommend.html").read_text(encoding="utf-8").replace("{{PROFILE_COUNT}}", str(len(recommendation_catalog["profiles"])))
    write(DIST / "recommend" / "index.html", render_base(
        title="Hosting recommendation engine — DeployIndex",
        description="Match workloads, billing preferences, operational expertise, networking, state, and strategic priorities against the complete DeployIndex catalog.",
        path="/recommend/",
        main=recommend_template,
        scripts='<script src="/assets/recommendation-engine.js" defer></script><script src="/assets/recommend.js" defer></script>',
        body_class="recommend-page",
    ))

    for item in providers:
        write(DIST / "providers" / item["slug"] / "index.html", provider_page(item, providers_by_slug, providers, category_labels))

    stats = {
        "generated_on": date.today().isoformat(),
        "total": len(providers),
        "available": len(available),
        "open_source": open_source_count,
        "statuses": dict(sorted(Counter(item["status"] for item in providers).items())),
        "primary_categories": {key: category_counts[key] for key in sorted(category_counts)},
    }
    write(DIST / "catalog" / "stats.json", json.dumps(stats, indent=2) + "\n")
    write(DIST / "catalog" / "index.html", render_base(
        title="Catalog API — DeployIndex",
        description="Machine-readable DeployIndex catalog and JSON Schema.",
        path="/catalog/",
        main='''<section class="page-hero shell"><p class="kicker">Catalog API</p><h1>Portable by design.</h1><p>Use the complete JSON catalog, validation schema, or generated summary statistics.</p><div class="hero-actions"><a class="button button-primary" href="/catalog/providers.json">providers.json</a><a class="button button-ghost" href="/catalog/schema.json">schema.json</a><a class="button button-ghost" href="/catalog/stats.json">stats.json</a><a class="button button-ghost" href="/catalog/recommendations.json">recommendations.json</a></div></section>''',
    ))
    write(DIST / "404.html", render_base(
        title="Not found — DeployIndex",
        description="The requested DeployIndex page was not found.",
        path="/404.html",
        main='''<section class="not-found shell"><div><code>HTTP 404</code><h1>Deployment surface not found.</h1><p>The record may have moved, been archived, or never existed.</p><a class="button button-primary" href="/">Return to catalog</a></div></section>''',
    ))

    manifest = {
        "name": "DeployIndex",
        "short_name": "DeployIndex",
        "description": "Every place to run code.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#080b12",
        "theme_color": "#080b12",
        "icons": [{"src": "/assets/favicon.svg", "sizes": "any", "type": "image/svg+xml"}],
    }
    write(DIST / "manifest.webmanifest", json.dumps(manifest, indent=2) + "\n")
    write(DIST / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    sitemap_urls = ["/", "/recommend/", "/method/", "/catalog/", *[f"/providers/{item['slug']}/" for item in providers]]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(
        f"  <url><loc>{esc(canonical(path))}</loc></url>" for path in sitemap_urls
    ) + "\n</urlset>\n"
    write(DIST / "sitemap.xml", sitemap)

    print(f"Built {len(providers)} provider pages plus recommender, catalog, method, API, and metadata into {DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
