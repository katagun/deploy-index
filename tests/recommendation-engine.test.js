'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const engine = require('../site/recommendation-engine.js');

const root = path.resolve(__dirname, '..');

// --- Exact-order scoring regressions against a frozen synthetic fixture. ---
// These fail only when the engine's scoring changes, never when catalog data changes.
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/recommendation-profiles.json'), 'utf8'));
const fixtureResults = engine.scoreProfiles(fixture.profiles, fixture.input, 10);
assert.deepEqual(
  fixtureResults.map((result) => result.profile.slug),
  fixture.expected_order,
  'frozen fixture ordering must only change with an intentional scoring change',
);
assert.ok(
  !fixtureResults.some((result) => result.profile.slug === 'delta-archived'),
  'archived profiles must never appear in results',
);
const [best] = fixtureResults;
assert.ok(best.score > 0 && best.score <= 100, 'scores stay within 0-100');
assert.ok(best.reasons.length >= 1 && best.reasons.length <= 4, 'up to four positive reasons');
assert.ok(best.tradeoffs.length <= 3, 'up to three trade-offs');

// --- Membership sanity checks against the live catalog. ---
// Deliberately order-insensitive: new catalog entries may legitimately outrank
// incumbents, and that must not fail the weekly research pipeline.
const payload = JSON.parse(fs.readFileSync(path.join(root, 'dist/catalog/recommendations.json'), 'utf8'));
const profiles = payload.profiles;

const topSlugs = (preset, limit = 12) => engine
  .scoreProfiles(profiles, engine.presetValues(preset), limit)
  .map((result) => result.profile.slug);

assert.ok(profiles.length >= 250, 'the complete catalog should be scoreable');

const staticTop = topSlugs('static-directory');
assert.ok(staticTop.slice(0, 6).includes('cloudflare-workers'), 'Cloudflare Workers should be a leading static-site result');
assert.ok(staticTop.slice(0, 6).includes('vercel'), 'Vercel should be a leading frontend/static result');

const globalTop = topSlugs('global-container');
assert.ok(globalTop.slice(0, 5).includes('fly-io'), 'Fly.io should be a leading global-container result');

const ownCloudTop = topSlugs('own-cloud');
assert.ok(ownCloudTop.slice(0, 5).includes('northflank-byoc'), 'Northflank BYOC should lead own-cloud matching');
assert.ok(ownCloudTop.slice(0, 5).includes('qovery'), 'Qovery should lead own-cloud matching');

const selfHostedTop = topSlugs('self-hosted');
assert.ok(selfHostedTop.slice(0, 4).includes('coolify'), 'Coolify should be a leading self-hosted result');
assert.ok(selfHostedTop.slice(0, 4).includes('dokploy'), 'Dokploy should be a leading self-hosted result');

const gpuResults = engine.scoreProfiles(profiles, engine.presetValues('gpu-inference'), 20);
assert.ok(gpuResults.length > 5, 'GPU preset should return a useful result set');
assert.ok(gpuResults.every((result) => result.profile.gpu), 'GPU requirement must filter out non-GPU profiles');
assert.ok(gpuResults.slice(0, 5).map((result) => result.profile.slug).includes('modal'), 'Modal should be a leading GPU result');

// The default questionnaire must not encode a billing preference: `free_entry`
// coverage is data-driven (free-tier capability plus overrides), and a default
// of 'free-entry' would systematically penalize platforms lacking that data.
assert.equal(engine.DEFAULT_INPUT.billing, 'any');

// --- Input normalization. ---
const normalized = engine.normalizeInput({ expertise: 99, budget: -4, weights: { ease: 50 } });
assert.equal(normalized.expertise, 5);
assert.equal(normalized.budget, 1);
assert.equal(normalized.weights.ease, 4);

// Unknown enum values (e.g. from a tampered share URL or an external consumer)
// must fall back to defaults instead of crashing the scorer.
const fallback = engine.normalizeInput({
  workload: 'bogus', artifact: 'bogus', billing: 'bogus', operation: 'bogus',
  traffic: 'bogus', protocol: 'bogus', state: 'bogus', reach: 'bogus',
});
assert.equal(fallback.workload, engine.DEFAULT_INPUT.workload);
assert.equal(fallback.artifact, engine.DEFAULT_INPUT.artifact);
assert.equal(fallback.billing, engine.DEFAULT_INPUT.billing);
assert.equal(fallback.operation, engine.DEFAULT_INPUT.operation);
assert.equal(fallback.traffic, engine.DEFAULT_INPUT.traffic);
assert.equal(fallback.protocol, engine.DEFAULT_INPUT.protocol);
assert.equal(fallback.state, engine.DEFAULT_INPUT.state);
assert.equal(fallback.reach, engine.DEFAULT_INPUT.reach);
assert.doesNotThrow(() => engine.scoreProfiles(fixture.profiles, { workload: 'bogus', artifact: 'bogus', billing: 'bogus' }, 5));

console.log('Recommendation engine regression tests passed');
