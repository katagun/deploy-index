(() => {
  'use strict';

  const engine = window.DeployIndexRecommender;
  const form = document.querySelector('#recommend-form');
  if (!engine || !form) return;

  // GitHub Pages serves a project repo under a subpath; the server exposes it once
  // via data-base-path on <html> so the fetch and each profile's detail_path link
  // (root-relative in the JSON payload) stay correct there too.
  const BASE_PATH = document.documentElement.dataset.basePath || '';
  const withBase = (path) => `${BASE_PATH}${path}`;

  const resultsNode = document.querySelector('#recommend-results');
  const countNode = document.querySelector('#recommend-count');
  const summaryNode = document.querySelector('#recommend-summary');
  const statusNode = document.querySelector('#recommend-status');
  const shareButton = document.querySelector('#recommend-share');
  const resetButton = document.querySelector('#recommend-reset');
  const presetButtons = [...document.querySelectorAll('[data-preset]')];
  const requirementInputs = [...form.querySelectorAll('[data-requirement]')];
  const weightInputs = [...form.querySelectorAll('[data-weight]')];
  let profiles = [];
  let activePreset = null;
  let updateTimer = null;

  const field = (name) => document.querySelector(`#rec-${name}`);
  const escapeHtml = (value) => String(value)
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');

  const traitLabel = (value) => ['—', 'very low', 'low', 'medium', 'high', 'very high'][Number(value)] || 'unknown';
  const scoreBand = (score) => score >= 82 ? 'strong' : score >= 68 ? 'good' : 'possible';

  const readInput = () => ({
    workload: field('workload').value,
    artifact: field('artifact').value,
    expertise: Number(field('expertise').value),
    budget: Number(field('budget').value),
    billing: field('billing').value,
    operation: field('operation').value,
    traffic: field('traffic').value,
    protocol: field('protocol').value,
    state: field('state').value,
    reach: field('reach').value,
    requirements: Object.fromEntries(requirementInputs.map((input) => [input.dataset.requirement, input.checked])),
    weights: Object.fromEntries(weightInputs.map((input) => [input.dataset.weight, Number(input.value)])),
  });

  const writeInput = (input) => {
    const value = engine.normalizeInput(input);
    ['workload', 'artifact', 'expertise', 'budget', 'billing', 'operation', 'traffic', 'protocol', 'state', 'reach']
      .forEach((name) => { field(name).value = String(value[name]); });
    requirementInputs.forEach((inputNode) => { inputNode.checked = Boolean(value.requirements[inputNode.dataset.requirement]); });
    weightInputs.forEach((inputNode) => {
      inputNode.value = String(value.weights[inputNode.dataset.weight]);
      const output = form.querySelector(`[data-weight-output="${inputNode.dataset.weight}"]`);
      if (output) output.value = inputNode.value;
    });
  };

  const paramsFromInput = (input) => {
    const params = new URLSearchParams();
    const keys = { workload: 'w', artifact: 'a', expertise: 'x', budget: 'b', billing: 'bill', operation: 'op', traffic: 't', protocol: 'p', state: 's', reach: 'r' };
    Object.entries(keys).forEach(([key, short]) => params.set(short, String(input[key])));
    const enabled = Object.entries(input.requirements).filter(([, value]) => value).map(([key]) => key);
    if (enabled.length) params.set('req', enabled.join(','));
    params.set('wt', Object.entries(input.weights).map(([key, value]) => `${key}:${value}`).join(','));
    if (activePreset) params.set('preset', activePreset);
    return params;
  };

  const inputFromParams = () => {
    const params = new URLSearchParams(location.search);
    const preset = params.get('preset');
    let value = preset && engine.PRESETS[preset] ? engine.presetValues(preset) : engine.DEFAULT_INPUT;
    const keys = { w: 'workload', a: 'artifact', x: 'expertise', b: 'budget', bill: 'billing', op: 'operation', t: 'traffic', p: 'protocol', s: 'state', r: 'reach' };
    const patch = {};
    Object.entries(keys).forEach(([short, key]) => { if (params.has(short)) patch[key] = params.get(short); });
    if (params.has('req')) {
      const enabled = new Set(params.get('req').split(',').filter(Boolean));
      patch.requirements = Object.fromEntries(Object.keys(engine.DEFAULT_INPUT.requirements).map((key) => [key, enabled.has(key)]));
    }
    if (params.has('wt')) {
      patch.weights = {};
      params.get('wt').split(',').forEach((pair) => {
        const [key, raw] = pair.split(':');
        if (key in engine.DEFAULT_INPUT.weights) patch.weights[key] = Number(raw);
      });
    }
    activePreset = preset && engine.PRESETS[preset] ? preset : null;
    return engine.normalizeInput(Object.assign({}, value, patch, {
      requirements: Object.assign({}, value.requirements, patch.requirements || {}),
      weights: Object.assign({}, value.weights, patch.weights || {}),
    }));
  };

  const setPresetState = () => {
    presetButtons.forEach((button) => {
      const selected = button.dataset.preset === activePreset;
      button.classList.toggle('is-active', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
  };

  const recommendationCard = (result, index) => {
    const { profile, score, reasons, tradeoffs } = result;
    const reasonList = reasons.length ? reasons : ['Broad compatibility with the selected shape'];
    const tradeoffList = tradeoffs.length ? tradeoffs : ['No major modeled mismatch; verify current limits'];
    const badges = [
      profile.free_entry ? 'Free entry' : null,
      profile.scale_to_zero ? 'Scale to zero' : null,
      profile.preview_environments ? 'Previews' : null,
      profile.private_networking ? 'Private network' : null,
      profile.gpu ? 'GPU' : null,
      profile.open_source ? 'Open source' : null,
    ].filter(Boolean).slice(0, 4);
    return `<article class="recommendation-card" data-score-band="${scoreBand(score)}">
      <div class="recommendation-rank"><span>${String(index + 1).padStart(2, '0')}</span><div class="score-ring" style="--score:${score}" aria-label="${score} percent fit"><strong>${score}</strong><small>fit</small></div></div>
      <div class="recommendation-main">
        <div class="recommendation-title"><div><p>${escapeHtml(profile.primary_category.replaceAll('-', ' '))}</p><h3><a href="${escapeHtml(withBase(profile.detail_path))}">${escapeHtml(profile.name)}</a></h3></div><a class="official-link" href="${escapeHtml(profile.url)}" rel="noopener noreferrer" target="_blank">Official ↗</a></div>
        <p class="recommendation-copy">${escapeHtml(profile.summary)}</p>
        <div class="recommendation-badges">${badges.map((badge) => `<span>${escapeHtml(badge)}</span>`).join('')}</div>
        <div class="fit-grid"><div><strong>Why it fits</strong><ul>${reasonList.map((reason) => `<li>${escapeHtml(reason)}</li>`).join('')}</ul></div><div><strong>Verify first</strong><ul>${tradeoffList.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div></div>
        <dl class="trait-strip"><div><dt>Expertise</dt><dd>${escapeHtml(traitLabel(profile.expertise_required))}</dd></div><div><dt>Cost floor</dt><dd>${escapeHtml(traitLabel(profile.cost_floor))}</dd></div><div><dt>Predictability</dt><dd>${escapeHtml(traitLabel(profile.cost_predictability))}</dd></div><div><dt>Control</dt><dd>${escapeHtml(traitLabel(profile.control))}</dd></div><div><dt>Portability</dt><dd>${escapeHtml(traitLabel(profile.portability))}</dd></div></dl>
      </div>
    </article>`;
  };

  const describeInput = (input) => {
    const workload = engine.LABELS.workloads[input.workload] || input.workload;
    const operation = engine.LABELS.operations[input.operation] || 'Any operating model';
    const extras = Object.entries(input.requirements).filter(([, enabled]) => enabled).length;
    return `${workload} · ${operation}${extras ? ` · ${extras} strong preference${extras === 1 ? '' : 's'}` : ''}`;
  };

  const render = ({ updateUrl = true } = {}) => {
    if (!profiles.length) return;
    const input = readInput();
    const recommendations = engine.scoreProfiles(profiles, input, 6);
    countNode.textContent = String(recommendations.length);
    summaryNode.textContent = describeInput(input);
    resultsNode.innerHTML = recommendations.length
      ? recommendations.map(recommendationCard).join('')
      : '<div class="recommend-empty"><strong>No compatible options survived these constraints.</strong><p>Relax a hard requirement, broaden the operating model, or increase the expertise and budget bands.</p></div>';
    resultsNode.setAttribute('aria-busy', 'false');
    if (updateUrl) {
      try { history.replaceState(null, '', `${location.pathname}?${paramsFromInput(input)}${location.hash}`); } catch (_error) { /* file previews may have an opaque origin */ }
    }
    setPresetState();
  };

  const scheduleRender = () => {
    activePreset = null;
    clearTimeout(updateTimer);
    updateTimer = setTimeout(() => render(), 60);
  };

  form.addEventListener('input', (event) => {
    if (event.target.matches('[data-weight]')) {
      const output = form.querySelector(`[data-weight-output="${event.target.dataset.weight}"]`);
      if (output) output.value = event.target.value;
    }
    scheduleRender();
  });
  form.addEventListener('change', scheduleRender);

  presetButtons.forEach((button) => button.addEventListener('click', () => {
    activePreset = button.dataset.preset;
    writeInput(engine.presetValues(activePreset));
    render();
    document.querySelector('#recommend-title').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  }));

  resetButton.addEventListener('click', () => {
    activePreset = 'static-directory';
    writeInput(engine.DEFAULT_INPUT);
    render();
  });

  shareButton.addEventListener('click', async () => {
    const shareUrl = `${location.origin}${location.pathname}?${paramsFromInput(readInput())}`;
    let clearDelay = 2400;
    try {
      await navigator.clipboard.writeText(shareUrl);
      statusNode.textContent = 'Shareable link copied.';
    } catch (_error) {
      // Clipboard access can be denied; surface the URL so it can be copied manually.
      statusNode.textContent = `Clipboard unavailable — copy this link: ${shareUrl}`;
      clearDelay = 20000;
    }
    setTimeout(() => { statusNode.textContent = ''; }, clearDelay);
  });

  fetch(withBase('/catalog/recommendations.json'))
    .then((response) => {
      if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
      return response.json();
    })
    .then((payload) => {
      profiles = payload.profiles || [];
      writeInput(inputFromParams());
      render({ updateUrl: !location.search });
    })
    .catch((error) => {
      resultsNode.setAttribute('aria-busy', 'false');
      resultsNode.innerHTML = `<div class="recommend-empty"><strong>The recommendation catalog could not load.</strong><p>${escapeHtml(error.message)}</p></div>`;
      statusNode.textContent = 'Recommendation data unavailable.';
    });
})();
