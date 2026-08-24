(function recommendationEngineFactory(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.DeployIndexRecommender = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  'use strict';

  const DEFAULT_INPUT = {
    workload: 'static-site', artifact: 'git-source', expertise: 2, budget: 1,
    billing: 'any', operation: 'managed-cloud', traffic: 'global',
    protocol: 'http', state: 'stateless', reach: 'global',
    requirements: { scaleToZero: true, previewEnvironments: false, privateNetworking: false, openSource: false, gpu: false },
    weights: { ease: 4, cost: 4, predictability: 3, control: 1, portability: 3, maturity: 3, global: 3, enterprise: 1 },
  };

  const LABELS = {
    workloads: {
      'static-site': 'Static site', 'frontend-app': 'Frontend or full-stack web app', 'web-api': 'Web API or SaaS backend',
      'background-worker': 'Worker, queue consumer, or cron', 'container-service': 'Long-running container service',
      'virtual-machine': 'Virtual machine', kubernetes: 'Kubernetes workload', 'serverless-function': 'Serverless function',
      'edge-app': 'Edge-native application', database: 'Database or backend platform', 'gpu-ai': 'GPU or AI workload',
      'agent-sandbox': 'AI agent or code sandbox', 'game-server': 'Game server', wordpress: 'WordPress or managed CMS',
      'decentralized-app': 'Decentralized application',
    },
    artifacts: {
      any: 'Any deployment artifact', 'git-source': 'Git source', 'docker-image': 'Docker / OCI image',
      'docker-compose': 'Docker Compose', 'function-code': 'Function code', 'vm-image': 'VM image or root access',
      'kubernetes-manifest': 'Kubernetes manifests or Helm', wasm: 'WebAssembly', template: 'Provider template',
    },
    operations: {
      any: 'Any operating model', 'managed-cloud': 'Fully managed cloud', 'bring-your-own-cloud': 'Bring my own cloud',
      'self-hosted': 'Self-host on my servers', 'dedicated-server': 'Dedicated infrastructure',
      'decentralized-network': 'Decentralized network',
    },
    billing: {
      any: 'No billing preference', 'free-entry': 'Free or nearly free entry', predictable: 'Predictable fixed billing',
      'usage-based': 'Usage-based or scale-to-zero', 'byoc-infrastructure': 'Bill my cloud account',
      'self-host-infrastructure': 'Pay for my servers',
    },
    traffic: { steady: 'Steady traffic', bursty: 'Bursty traffic', spiky: 'Spiky or mostly idle traffic', scheduled: 'Scheduled or batch traffic', global: 'Global traffic' },
    protocol: { http: 'HTTP', websocket: 'WebSockets', tcp: 'arbitrary TCP', udp: 'UDP' },
    state: { stateless: 'Stateless operation', 'managed-database': 'Managed database', 'persistent-disk': 'Persistent disk or volume', 'object-storage': 'Object storage' },
  };

  const PRESETS = {
    'static-directory': {
      label: 'Static directory', description: 'A content-heavy static site with client-side search and a very low cost floor.',
      values: DEFAULT_INPUT,
    },
    'startup-saas': {
      label: 'Low-ops SaaS', description: 'A small product with an API, background work, managed data, previews, and minimal platform operations.',
      values: {
        workload: 'web-api', artifact: 'git-source', expertise: 2, budget: 3, billing: 'predictable', operation: 'managed-cloud',
        traffic: 'bursty', protocol: 'websocket', state: 'managed-database', reach: 'multi',
        requirements: { scaleToZero: false, previewEnvironments: true, privateNetworking: true, openSource: false, gpu: false },
        weights: { ease: 4, cost: 3, predictability: 4, control: 1, portability: 3, maturity: 4, global: 2, enterprise: 2 },
      },
    },
    'global-container': {
      label: 'Global container', description: 'An OCI workload needing regional placement, private services, persistent volume options, and non-HTTP networking.',
      values: {
        workload: 'container-service', artifact: 'docker-image', expertise: 4, budget: 3, billing: 'usage-based', operation: 'managed-cloud',
        traffic: 'global', protocol: 'tcp', state: 'persistent-disk', reach: 'global',
        requirements: { scaleToZero: false, previewEnvironments: false, privateNetworking: true, openSource: false, gpu: false },
        weights: { ease: 2, cost: 2, predictability: 2, control: 4, portability: 4, maturity: 4, global: 5, enterprise: 2 },
      },
    },
    'own-cloud': {
      label: 'Own-cloud platform', description: 'A developer platform whose workloads and data remain in a customer-controlled cloud account.',
      values: {
        workload: 'container-service', artifact: 'docker-image', expertise: 4, budget: 4, billing: 'byoc-infrastructure', operation: 'bring-your-own-cloud',
        traffic: 'bursty', protocol: 'websocket', state: 'managed-database', reach: 'multi',
        requirements: { scaleToZero: false, previewEnvironments: true, privateNetworking: true, openSource: false, gpu: false },
        weights: { ease: 2, cost: 1, predictability: 3, control: 5, portability: 4, maturity: 4, global: 3, enterprise: 5 },
      },
    },
    'self-hosted': {
      label: 'Self-hosted PaaS', description: 'Docker or Compose on owned servers with predictable infrastructure economics.',
      values: {
        workload: 'container-service', artifact: 'docker-compose', expertise: 5, budget: 2, billing: 'self-host-infrastructure', operation: 'self-hosted',
        traffic: 'steady', protocol: 'websocket', state: 'persistent-disk', reach: 'single',
        requirements: { scaleToZero: false, previewEnvironments: false, privateNetworking: true, openSource: true, gpu: false },
        weights: { ease: 1, cost: 4, predictability: 4, control: 4, portability: 4, maturity: 3, global: 0, enterprise: 1 },
      },
    },
    'gpu-inference': {
      label: 'GPU inference', description: 'A bursty AI endpoint that needs accelerated compute and benefits from scale-to-zero.',
      values: {
        workload: 'gpu-ai', artifact: 'docker-image', expertise: 3, budget: 4, billing: 'usage-based', operation: 'managed-cloud',
        traffic: 'spiky', protocol: 'http', state: 'object-storage', reach: 'multi',
        requirements: { scaleToZero: true, previewEnvironments: false, privateNetworking: false, openSource: false, gpu: true },
        weights: { ease: 3, cost: 3, predictability: 1, control: 2, portability: 3, maturity: 3, global: 3, enterprise: 2 },
      },
    },
  };

  const clone = (value) => JSON.parse(JSON.stringify(value));
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const has = (list, value) => Array.isArray(list) && list.includes(value);
  const hasKey = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

  const ENUM_LABELS = {
    workload: () => LABELS.workloads,
    artifact: () => LABELS.artifacts,
    billing: () => LABELS.billing,
    operation: () => LABELS.operations,
    traffic: () => LABELS.traffic,
    protocol: () => LABELS.protocol,
    state: () => LABELS.state,
  };
  const REACH_VALUES = ['single', 'multi', 'global', 'residency'];

  const normalizeInput = (input = {}) => {
    const merged = clone(DEFAULT_INPUT);
    Object.assign(merged, input);
    Object.entries(ENUM_LABELS).forEach(([key, labels]) => {
      if (!hasKey(labels(), merged[key])) merged[key] = DEFAULT_INPUT[key];
    });
    if (!REACH_VALUES.includes(merged.reach)) merged.reach = DEFAULT_INPUT.reach;
    merged.requirements = Object.assign({}, DEFAULT_INPUT.requirements, input.requirements || {});
    merged.weights = Object.assign({}, DEFAULT_INPUT.weights, input.weights || {});
    merged.expertise = clamp(Number(merged.expertise) || 2, 1, 5);
    merged.budget = clamp(Number(merged.budget) || 2, 1, 5);
    Object.keys(merged.weights).forEach((key) => { merged.weights[key] = clamp(Number(merged.weights[key]) || 0, 0, 4); });
    return merged;
  };

  const traitContribution = (profile, input) => {
    const desirability = {
      ease: 6 - profile.expertise_required,
      cost: 6 - profile.cost_floor,
      predictability: profile.cost_predictability,
      control: profile.control,
      portability: profile.portability,
      maturity: profile.maturity,
      global: profile.global_reach,
      enterprise: profile.enterprise_readiness,
    };
    return Object.entries(input.weights).reduce((total, [key, weight]) => total + desirability[key] * Number(weight), 0);
  };

  const scoreNormalized = (profile, input) => {
    const reasons = [];
    const tradeoffs = [];
    const hardMisses = [];
    let raw = 0;
    let maximum = 0;

    maximum += 36;
    if (has(profile.workloads, input.workload)) { raw += 36; reasons.push(`Built for ${LABELS.workloads[input.workload].toLowerCase()}`); }
    else { raw -= 22; tradeoffs.push(`Adjacent rather than exact ${LABELS.workloads[input.workload].toLowerCase()} fit`); }

    if (input.artifact !== 'any') {
      maximum += 16;
      if (has(profile.artifacts, input.artifact)) { raw += 16; reasons.push(`Accepts ${LABELS.artifacts[input.artifact].toLowerCase()}`); }
      else { raw -= 13; tradeoffs.push(`Does not directly accept ${LABELS.artifacts[input.artifact].toLowerCase()}`); }
    }

    maximum += 10;
    if (profile.expertise_required <= input.expertise) raw += 10;
    else { raw -= (profile.expertise_required - input.expertise) * 8; tradeoffs.push('Requires more infrastructure expertise than selected'); }

    maximum += 10;
    if (profile.cost_floor <= input.budget) raw += 10;
    else { raw -= (profile.cost_floor - input.budget) * 8; tradeoffs.push('Relative starting cost exceeds the selected budget band'); }

    if (input.billing !== 'any') {
      maximum += 12;
      let match = false;
      if (input.billing === 'predictable') match = profile.cost_predictability >= 4 || has(profile.billing_models, 'fixed-instance');
      else if (input.billing === 'free-entry') match = profile.free_entry || has(profile.billing_models, 'free-entry');
      else match = has(profile.billing_models, input.billing);
      if (match) { raw += 12; reasons.push(LABELS.billing[input.billing]); }
      else { raw -= 9; tradeoffs.push(`Billing shape differs from ${LABELS.billing[input.billing].toLowerCase()}`); }
    }

    if (input.operation !== 'any') {
      maximum += 14;
      if (has(profile.operating_models, input.operation)) { raw += 14; reasons.push(LABELS.operations[input.operation]); }
      else { raw -= 20; hardMisses.push('operation'); tradeoffs.push(`Not a ${LABELS.operations[input.operation].toLowerCase()} model`); }
    }

    maximum += 6;
    if (has(profile.traffic, input.traffic)) { raw += 6; if (input.traffic !== 'steady') reasons.push(`Fits ${LABELS.traffic[input.traffic].toLowerCase()}`); }
    else raw -= 4;

    maximum += 10;
    if (has(profile.protocols, input.protocol)) { raw += 10; if (input.protocol !== 'http') reasons.push(`Supports ${LABELS.protocol[input.protocol]}`); }
    else { raw -= 48; hardMisses.push('protocol'); tradeoffs.push(`Missing ${LABELS.protocol[input.protocol]}`); }

    maximum += 10;
    if (has(profile.state_options, input.state)) { raw += 10; if (input.state !== 'stateless') reasons.push(LABELS.state[input.state]); }
    else { raw -= input.state === 'stateless' ? 2 : 20; tradeoffs.push(`Does not directly satisfy ${LABELS.state[input.state].toLowerCase()}`); }

    maximum += 12;
    if (input.reach === 'single') raw += 12;
    else if (input.reach === 'multi' && profile.global_reach >= 4) { raw += 12; reasons.push('Strong multi-region reach'); }
    else if (input.reach === 'global' && profile.global_reach === 5) { raw += 12; reasons.push('Global edge or broad regional reach'); }
    else if (input.reach === 'residency' && profile.global_reach >= 4 && profile.enterprise_readiness >= 4) { raw += 12; reasons.push('Better fit for regional governance'); }
    else { raw -= 12; tradeoffs.push(input.reach === 'global' ? 'Not primarily a global-edge platform' : 'Regional reach requires closer verification'); }

    const checks = [
      ['scaleToZero', 'scale_to_zero', 12, 'Scale-to-zero support', 'No scale-to-zero trait'],
      ['previewEnvironments', 'preview_environments', 10, 'Preview environments', 'No preview-environment trait'],
      ['privateNetworking', 'private_networking', 10, 'Private networking', 'No private-networking trait'],
      ['gpu', 'gpu', 30, 'GPU support', 'No GPU support'],
    ];
    checks.forEach(([inputKey, profileKey, points, yes, no]) => {
      if (!input.requirements[inputKey]) return;
      maximum += points;
      if (profile[profileKey]) { raw += points; reasons.push(yes); }
      else { raw -= inputKey === 'gpu' ? 100 : points * 2; hardMisses.push(inputKey); tradeoffs.push(no); }
    });
    if (input.requirements.openSource) {
      maximum += 10;
      if (profile.open_source) { raw += 10; reasons.push('Open source'); }
      else { raw -= 12; tradeoffs.push('Proprietary platform'); }
    }

    const priorities = traitContribution(profile, input);
    const priorityMaximum = Object.values(input.weights).reduce((total, weight) => total + Number(weight) * 5, 0);
    raw += priorities;
    maximum += priorityMaximum;

    const score = clamp(Math.round((Math.max(0, raw) / Math.max(1, maximum)) * 100), 0, 100);
    return {
      profile, score, raw, maximum,
      reasons: [...new Set(reasons)].slice(0, 4),
      tradeoffs: [...new Set(tradeoffs)].slice(0, 3),
      hardMisses,
    };
  };

  const scoreProfile = (profile, rawInput) => scoreNormalized(profile, normalizeInput(rawInput));

  const scoreProfiles = (profiles, input, limit = 6) => {
    const normalized = normalizeInput(input);
    return profiles
      .filter((profile) => ['active', 'beta', 'transitioning'].includes(profile.status))
      .filter((profile) => !['discontinued', 'existing-customers-only'].includes(profile.availability))
      .filter((profile) => !(normalized.requirements.gpu && !profile.gpu))
      .map((profile) => scoreNormalized(profile, normalized))
      .filter((result) => result.score > 0)
      .sort((a, b) => b.score - a.score || Number(b.profile.featured) - Number(a.profile.featured) || a.profile.name.localeCompare(b.profile.name))
      .slice(0, limit);
  };

  const presetValues = (key) => clone((PRESETS[key] || PRESETS['static-directory']).values);

  return { DEFAULT_INPUT: clone(DEFAULT_INPUT), LABELS, PRESETS, normalizeInput, presetValues, scoreProfile, scoreProfiles };
}));
