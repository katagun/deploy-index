(() => {
  'use strict';

  const root = document.querySelector('#compare-root');
  const statusNode = document.querySelector('#compare-status');
  if (!root) return;

  // GitHub Pages serves a project repo under a subpath; the server exposes it once
  // via data-base-path on <html> so fetches and generated links stay correct there too.
  const BASE_PATH = document.documentElement.dataset.basePath || '';
  const withBase = (path) => `${BASE_PATH}${path}`;

  const MAX_ENTRIES = 4;
  const escapeHtml = (value) => String(value)
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');
  const SPECIAL_LABELS = {
    'tcp-udp': 'TCP / UDP', 'ci-cd': 'CI / CD', gpu: 'GPU', api: 'API',
    webassembly: 'WebAssembly', 'gpu-ai': 'GPU / AI', wasm: 'WebAssembly',
    http: 'HTTP', tcp: 'TCP', udp: 'UDP', 'managed-cms': 'Managed CMS',
  };
  const humanize = (value) => {
    if (SPECIAL_LABELS[value]) return SPECIAL_LABELS[value];
    const text = String(value).replaceAll('-', ' ');
    return text.charAt(0).toUpperCase() + text.slice(1);
  };
  const traitLabel = (value) => `${['—', 'very low', 'low', 'medium', 'high', 'very high'][Number(value)] || '—'} (${Number(value) || '—'}/5)`;

  const ENTITY_LABELS = { provider: 'Provider', product: 'Product', project: 'Open project' };
  const STATUS_LABELS = { active: 'Active', beta: 'Beta', transitioning: 'Transitioning', sunset: 'Sunset', archived: 'Archived' };
  const AVAILABILITY_LABELS = {
    general: 'Generally available', preview: 'Preview', limited: 'Limited access',
    'existing-customers-only': 'Existing customers only', discontinued: 'Discontinued',
  };
  const ERA_LABELS = { established: 'Established', modern: 'Modern · 2020–23', recent: 'Recent · 2024+' };
  const MODEL_LABELS = {
    'managed-cloud': 'Managed cloud', 'bring-your-own-cloud': 'Bring your own cloud', 'self-hosted': 'Self-hosted',
    'dedicated-server': 'Dedicated server', marketplace: 'Marketplace', 'decentralized-network': 'Decentralized network',
  };
  const TRAITS = [
    ['expertise_required', 'Expertise required'], ['cost_floor', 'Starting-cost band'],
    ['cost_predictability', 'Bill predictability'], ['control', 'Infrastructure control'],
    ['portability', 'Portability'], ['maturity', 'Maturity'],
    ['global_reach', 'Global reach'], ['enterprise_readiness', 'Enterprise readiness'],
  ];
  const FEATURES = [
    ['free_entry', 'Free or nearly-free entry'], ['scale_to_zero', 'Scale to zero'],
    ['preview_environments', 'Preview environments'], ['private_networking', 'Private networking'], ['gpu', 'GPU support'],
  ];
  const PROFILE_LISTS = [
    ['workloads', 'Workloads'], ['artifacts', 'Deployment artifacts'], ['billing_models', 'Billing models'],
    ['protocols', 'Protocols'], ['traffic', 'Traffic shapes'], ['state_options', 'State options'],
  ];

  const requestedSlugs = () => {
    const raw = new URLSearchParams(location.search).get('s') || '';
    return [...new Set(raw.split(',').map((value) => value.trim()).filter(Boolean))].slice(0, MAX_ENTRIES);
  };

  const compareHref = (slugs) => slugs.length ? `${location.pathname}?s=${slugs.map(encodeURIComponent).join(',')}` : location.pathname;

  const mark = (present) => present
    ? '<span class="compare-check" aria-hidden="true">✓</span><span class="sr-only">yes</span>'
    : '<span class="compare-miss" aria-hidden="true">—</span><span class="sr-only">no</span>';

  const listCell = (values, labels) => {
    if (!Array.isArray(values) || !values.length) return '<span class="compare-miss">—</span>';
    return escapeHtml(values.map((value) => (labels ? labels[value] : null) || humanize(value)).join(', '));
  };

  // Both endpoints are normalized to UTC calendar dates before subtracting, so the
  // result is a whole number of calendar days independent of the viewer's timezone.
  const daysBetween = (iso, today) => {
    const todayUtc = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
    return Math.round((todayUtc - new Date(iso).getTime()) / 86400000);
  };

  // The oldest observation behind a total governs how much of it is still current.
  const observedOn = (result) => (result.sources || []).map((source) => source.observed_on).sort()[0] || '';

  const priceCell = (result, hasRows, maxAge, today) => {
    if (!hasRows) {
      return `<td><span class="compare-miss">not priced here</span>
        <small>Outside the database pricing dataset — not a missing number.</small></td>`;
    }
    if (!result || result.status !== 'ok') {
      const reason = (result || {}).reason;
      const missing = ((result || {}).missing_metrics || []).join(', ');
      const detail = reason || (missing ? `no dated row for ${missing}` : '');
      return `<td><span class="compare-miss">insufficient data</span>
        ${detail ? `<small>${escapeHtml(detail)}</small>` : ''}</td>`;
    }
    const oldest = observedOn(result);
    const age = oldest ? daysBetween(oldest, today) : null;
    const stale = age !== null && age > maxAge;
    const dateNote = oldest
      ? `<span class="price-age${stale ? ' is-stale' : ''}">${stale ? 'stale · ' : ''}observed ${escapeHtml(oldest)} · ${age}d old</span>`
      : '';
    const scope = Number(result.plans_considered) === 1 ? '<small class="price-scope">only plan recorded</small>' : '';
    return `<td><strong>$${Number(result.monthly_usd).toFixed(2)}</strong>
      <small>${escapeHtml(result.plan)} plan</small>${scope}${dateNote}</td>`;
  };

  const renderTable = (entries, profilesBySlug, categoryLabels, pricingBySlug, pricing) => {
    const slugs = entries.map((entry) => entry.slug);
    const headCells = entries.map((entry) => {
      const remaining = slugs.filter((slug) => slug !== entry.slug);
      return `<th scope="col"><div class="compare-head"><a href="${withBase(`/providers/${escapeHtml(entry.slug)}/`)}">${escapeHtml(entry.name)}</a>
        <span class="status-pill" data-status="${escapeHtml(entry.status)}">${escapeHtml(STATUS_LABELS[entry.status] || entry.status)}</span>
        <a class="compare-remove" href="${escapeHtml(compareHref(remaining))}" aria-label="Remove ${escapeHtml(entry.name)} from comparison">Remove ✕</a></div></th>`;
    }).join('');

    const row = (label, cell) => `<tr><th scope="row">${label}</th>${entries.map(cell).join('')}</tr>`;
    const groupRow = (label) => `<tr class="compare-group"><th scope="row" colspan="${entries.length + 1}">${label}</th></tr>`;
    const td = (content) => `<td>${content}</td>`;

    const capabilityUnion = [...new Set(entries.flatMap((entry) => entry.capabilities))].sort();
    const rows = [];

    rows.push(groupRow('Identity'));
    rows.push(row('Entry type', (entry) => td(escapeHtml(ENTITY_LABELS[entry.entity_type] || entry.entity_type))));
    rows.push(row('Availability', (entry) => td(escapeHtml(AVAILABILITY_LABELS[entry.availability] || entry.availability))));
    rows.push(row('Era', (entry) => td(escapeHtml(ERA_LABELS[entry.era] || entry.era))));
    rows.push(row('Launch year', (entry) => td(entry.launch_year ? escapeHtml(String(entry.launch_year)) : '<span class="compare-miss">Not yet sourced</span>')));
    rows.push(row('Open source', (entry) => td(mark(entry.open_source))));
    rows.push(row('Operating models', (entry) => td(listCell(entry.operating_models, MODEL_LABELS))));
    rows.push(row('Categories', (entry) => td(listCell(entry.categories, categoryLabels))));

    if (capabilityUnion.length) {
      rows.push(groupRow('Capabilities'));
      capabilityUnion.forEach((capability) => {
        rows.push(row(escapeHtml(humanize(capability)), (entry) => td(mark(entry.capabilities.includes(capability)))));
      });
    }

    const hasProfiles = entries.every((entry) => profilesBySlug.has(entry.slug));
    if (hasProfiles) {
      rows.push(groupRow('Recommender profile · relative bands, not measurements'));
      TRAITS.forEach(([key, label]) => {
        rows.push(row(escapeHtml(label), (entry) => td(escapeHtml(traitLabel(profilesBySlug.get(entry.slug)[key])))));
      });
      FEATURES.forEach(([key, label]) => {
        rows.push(row(escapeHtml(label), (entry) => td(mark(Boolean(profilesBySlug.get(entry.slug)[key])))));
      });
      PROFILE_LISTS.forEach(([key, label]) => {
        rows.push(row(escapeHtml(label), (entry) => td(listCell(profilesBySlug.get(entry.slug)[key]))));
      });
    }

    const pricingWorkloads = (pricing || {}).workloads || [];
    const priced = entries.filter((entry) => pricingBySlug.has(entry.slug));
    if (priced.length && pricingWorkloads.length) {
      const maxAge = Number(pricing.max_age_days) || 90;
      const today = new Date();
      rows.push(`<tr class="compare-group"><th scope="row" colspan="${entries.length + 1}">
        Estimated monthly cost · dated observations, not quotes
        <small class="compare-group-note">${escapeHtml(pricing.disclaimer || '')}
        These workloads price a plan fee, storage, and egress only — metered compute is not included.
        See <a href="${withBase('/pricing/')}">/pricing/</a> for what each figure covers.</small>
      </th></tr>`);
      pricingWorkloads.forEach((workload) => {
        rows.push(row(escapeHtml(workload.label), (entry) => priceCell(
          (pricingBySlug.get(entry.slug) || {}).results?.[workload.id],
          pricingBySlug.has(entry.slug),
          maxAge,
          today,
        )));
      });
    }

    rows.push(groupRow('Verification'));
    rows.push(row('Last verified', (entry) => td(entry.last_verified ? escapeHtml(entry.last_verified) : '<span class="compare-miss">Seed record</span>')));
    rows.push(row('Evidence level', (entry) => td(escapeHtml(humanize(entry.confidence)))));
    rows.push(row('Official site', (entry) => td(`<a href="${escapeHtml(entry.url)}" rel="noreferrer">${escapeHtml(new URL(entry.url).hostname.replace(/^www\./, ''))} ↗</a>`)));

    return `<div class="compare-table-wrap"><table class="compare-table">
      <caption class="sr-only">Comparison of ${entries.map((entry) => escapeHtml(entry.name)).join(', ')}</caption>
      <thead><tr><th scope="col">Attribute</th>${headCells}</tr></thead>
      <tbody>${rows.join('')}</tbody>
    </table></div>
    <p class="compare-footnote"><a href="${withBase('/')}">← Add or change entries in the catalog explorer</a></p>`;
  };

  const renderEmpty = (message) => {
    root.innerHTML = `<div class="compare-empty"><strong>${escapeHtml(message)}</strong>
      <p>Pick two to four entries with the Compare buttons in the catalog explorer, then return here.</p>
      <a class="button button-primary" href="${withBase('/')}">Browse the catalog</a></div>`;
    root.setAttribute('aria-busy', 'false');
  };

  const slugs = requestedSlugs();
  if (slugs.length < 2) {
    renderEmpty(slugs.length ? 'Pick at least two entries to compare.' : 'Nothing selected yet.');
    return;
  }

  Promise.all([
    fetch(withBase('/catalog/providers.json')).then((response) => {
      if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
      return response.json();
    }),
    fetch(withBase('/catalog/recommendations.json')).then((response) => (response.ok ? response.json() : null)).catch(() => null),
    fetch(withBase('/catalog/pricing.json')).then((response) => (response.ok ? response.json() : null)).catch(() => null),
  ]).then(([catalog, recommendations, pricing]) => {
    const bySlug = new Map(catalog.providers.map((entry) => [entry.slug, entry]));
    const profilesBySlug = new Map(((recommendations || {}).profiles || []).map((profile) => [profile.slug, profile]));
    const pricingBySlug = new Map(((pricing || {}).providers || []).map((entry) => [entry.slug, entry]));
    const entries = slugs.map((slug) => bySlug.get(slug)).filter(Boolean);
    const unknown = slugs.filter((slug) => !bySlug.has(slug));
    if (unknown.length) statusNode.textContent = `Not in the catalog and skipped: ${unknown.join(', ')}.`;
    if (entries.length < 2) {
      renderEmpty('Fewer than two of the requested entries exist in the catalog.');
      return;
    }
    root.innerHTML = renderTable(entries, profilesBySlug, catalog.category_labels || {}, pricingBySlug, pricing);
    root.setAttribute('aria-busy', 'false');
    document.title = `${entries.map((entry) => entry.name).join(' vs ')} — DeployIndex`;
  }).catch((error) => {
    renderEmpty('The catalog data could not load.');
    statusNode.textContent = error.message;
  });
})();
