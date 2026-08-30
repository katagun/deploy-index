(() => {
  'use strict';

  const root = document.querySelector('#pricing-root');
  const statusNode = document.querySelector('#pricing-status');
  if (!root) return;

  // GitHub Pages serves a project repo under a subpath; the server exposes it once
  // via data-base-path on <html> so the fetch and each provider's detail_path link
  // (root-relative in the JSON payload) stay correct there too.
  const BASE_PATH = document.documentElement.dataset.basePath || '';
  const withBase = (path) => `${BASE_PATH}${path}`;

  const escapeHtml = (value) => String(value)
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');

  const money = (value) => `$${Number(value).toFixed(2)}`;
  // Both endpoints are normalized to UTC calendar dates before subtracting, so
  // the result is a whole number of calendar days independent of the viewer's
  // timezone and time-of-day. `iso` (e.g. "2026-08-29") already parses as UTC
  // midnight per the date-only ECMA-262 form; `today` is normalized the same
  // way using its UTC calendar components rather than local ones.
  const daysBetween = (iso, today) => {
    const todayUtc = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
    return Math.round((todayUtc - new Date(iso).getTime()) / 86400000);
  };

  const ageCell = (result, maxAge, today) => {
    if (result.status !== 'ok' || !result.sources.length) return '';
    const oldest = result.sources.map((source) => source.observed_on).sort()[0];
    const age = daysBetween(oldest, today);
    const stale = age > maxAge;
    return `<span class="price-age${stale ? ' is-stale' : ''}">${stale ? 'stale · ' : ''}${age}d old</span>`;
  };

  // A total is only ever the cheapest of the plans we happen to have recorded.
  // Where that is a single plan there was no comparison to win, and the figure
  // reflects the coverage of the dataset rather than the provider's floor.
  const scopeNote = (result) => {
    const count = Number(result.plans_considered);
    if (!Number.isFinite(count) || count < 1) return '';
    if (count === 1) return '<small class="price-scope">only plan recorded</small>';
    return `<small class="price-scope">cheapest of ${count} recorded plans</small>`;
  };

  const cell = (result, maxAge, today) => {
    if (result.status !== 'ok') {
      return `<td class="price-missing"><span>insufficient data</span><small>${escapeHtml((result.missing_metrics || []).join(', '))}</small></td>`;
    }
    return `<td><strong>${escapeHtml(money(result.monthly_usd))}</strong><small>${escapeHtml(result.plan)} plan</small>${scopeNote(result)}${ageCell(result, maxAge, today)}</td>`;
  };

  fetch(withBase('/catalog/pricing.json'))
    .then((response) => {
      if (!response.ok) throw new Error(`Pricing request failed: ${response.status}`);
      return response.json();
    })
    .then((payload) => {
      const today = new Date();
      const { workloads, providers, max_age_days: maxAge } = payload;
      const head = workloads.map((workload) => `<th scope="col">${escapeHtml(workload.label)}</th>`).join('');
      const body = providers.map((provider) => `<tr>
        <th scope="row"><a href="${escapeHtml(withBase(provider.detail_path))}">${escapeHtml(provider.name)}</a></th>
        ${workloads.map((workload) => cell(provider.results[workload.id] || {status: 'insufficient_data'}, maxAge, today)).join('')}
      </tr>`).join('');

      const assumptions = workloads.map((workload) => `<section class="workload-note">
        <h3>${escapeHtml(workload.label)}</h3>
        <p>Priced quantities — ${escapeHtml(Object.entries(workload.assumptions).map(([key, value]) => `${key.replaceAll('_', ' ')}: ${value}`).join(' · '))}</p>
        <ul>${workload.caveats.map((caveat) => `<li>${escapeHtml(caveat)}</li>`).join('')}</ul>
      </section>`).join('');

      root.innerHTML = `<div class="compare-table-wrap"><table class="compare-table pricing-table">
          <caption class="sr-only">Estimated monthly cost by reference workload</caption>
          <thead><tr><th scope="col">Provider</th>${head}</tr></thead>
          <tbody>${body}</tbody>
        </table></div>
        <p class="pricing-disclaimer">${escapeHtml(payload.disclaimer)} Dataset generated ${escapeHtml(payload.generated_on)}.</p>
        <div class="workload-notes"><h2>What each figure covers</h2>${assumptions}</div>`;
      root.setAttribute('aria-busy', 'false');
    })
    .catch((error) => {
      root.innerHTML = '<div class="compare-empty"><strong>The pricing dataset could not load.</strong></div>';
      root.setAttribute('aria-busy', 'false');
      statusNode.textContent = error.message;
    });
})();
