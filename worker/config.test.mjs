import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const config = JSON.parse(readFileSync(new URL('../wrangler.jsonc', import.meta.url)));

test('branch Preview has an explicit configuration and backend variables', () => {
  assert.ok(config.previews, 'wrangler preview requires a previews block');
  assert.equal(config.previews.vars.BACKEND_ORIGIN, 'https://pickleballmvp.run.place');
  assert.equal(config.previews.vars.BACKEND_USERNAME, 'kun');
  assert.equal(config.previews.vars.BACKEND_PASSWORD, undefined, 'passwords must stay in Cloudflare secrets');
});

test('Preview shares the frontend assets while production API routing stays enabled', () => {
  assert.equal(config.assets.binding, 'ASSETS');
  assert.ok(config.assets.run_worker_first.includes('/api/*'));
  assert.equal(config.previews.assets, undefined, 'Preview assets belong at the top level');
  assert.equal(config.vars.BACKEND_ORIGIN, 'https://pickleballmvp.run.place');
  assert.equal(config.vars.BACKEND_PASSWORD, undefined);
});
