'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const engine = require('../site/recommendation-engine.js');

const root = path.resolve(__dirname, '..');
const payload = JSON.parse(fs.readFileSync(path.join(root, 'dist/catalog/recommendations.json'), 'utf8'));
const profiles = payload.profiles;

const topSlugs = (preset, limit = 12) => engine
  .scoreProfiles(profiles, engine.presetValues(preset), limit)
  .map((result) => result.profile.slug);

assert.ok(profiles.length >= 250, 'the complete catalog should be scoreable');

const staticTop = topSlugs('static-directory');
assert.ok(staticTop.slice(0, 5).includes('cloudflare-workers'), 'Cloudflare Workers should be a leading static-site result');
assert.ok(staticTop.slice(0, 6).includes('vercel'), 'Vercel should be a leading frontend/static result');

const globalTop = topSlugs('global-container');
assert.deepEqual(globalTop.slice(0, 2), ['fly-io', 'bunny-magic-containers']);

const ownCloudTop = topSlugs('own-cloud');
assert.ok(ownCloudTop.slice(0, 5).includes('northflank-byoc'), 'Northflank BYOC should lead own-cloud matching');
assert.ok(ownCloudTop.slice(0, 5).includes('qovery'), 'Qovery should lead own-cloud matching');

const selfHostedTop = topSlugs('self-hosted');
assert.deepEqual(selfHostedTop.slice(0, 2), ['coolify', 'dokploy']);

const gpuResults = engine.scoreProfiles(profiles, engine.presetValues('gpu-inference'), 20);
assert.ok(gpuResults.length > 5, 'GPU preset should return a useful result set');
assert.ok(gpuResults.every((result) => result.profile.gpu), 'GPU requirement must filter out non-GPU profiles');
assert.deepEqual(gpuResults.slice(0, 2).map((result) => result.profile.slug), ['modal', 'runpod']);

const normalized = engine.normalizeInput({ expertise: 99, budget: -4, weights: { ease: 50 } });
assert.equal(normalized.expertise, 5);
assert.equal(normalized.budget, 1);
assert.equal(normalized.weights.ease, 4);

console.log('Recommendation engine regression tests passed');
