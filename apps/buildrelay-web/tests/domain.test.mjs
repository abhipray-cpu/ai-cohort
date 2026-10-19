import test from 'node:test';
import assert from 'node:assert/strict';
import { canReplay, stateLabel, counters, safeRunUrl } from '../src/domain.ts';

test('only permitted roles can replay dead letters', () => {
  assert.equal(canReplay('dead', 'operator'), true);
  for (const state of ['done', 'processing', 'retry', 'pending']) assert.equal(canReplay(state, 'owner'), false);
  assert.equal(canReplay('dead', 'viewer'), false);
});
test('dashboard counts reflect supplied data, not demo metrics', () => {
  assert.deepEqual(counters([], []), { open: 0, retrying: 0, dead: 0, done: 0 });
  assert.deepEqual(counters([{state:'recovered'}, {state:'needs_triage'}], [{state:'retry'}, {state:'dead'}, {state:'done'}]), {open:1,retrying:1,dead:1,done:1});
});
test('state labels distinguish recovery from verified fixes', () => {
  assert.equal(stateLabel('recovered'), 'Run recovered');
  assert.equal(stateLabel('dead'), 'Needs operator attention');
});
test('run links cannot execute javascript or open non-GitHub hosts', () => {
  assert.equal(safeRunUrl('javascript:alert(1)'), null);
  assert.equal(safeRunUrl('https://github.com.evil.test/a'), null);
  assert.equal(safeRunUrl('https://github.com/acme/shop/actions/runs/77'), 'https://github.com/acme/shop/actions/runs/77');
});
