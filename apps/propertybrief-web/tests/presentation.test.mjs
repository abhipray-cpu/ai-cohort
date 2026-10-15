import assert from 'node:assert/strict';
import test from 'node:test';
import { coverageLabel, date, progress, recordLabel } from '../src/presentation.ts';

test('missing and empty sources cannot appear cleared', () => {
  assert.equal(coverageLabel('not_checked'), 'Not checked');
  assert.equal(coverageLabel('unknown'), 'Incomplete');
  assert.equal(coverageLabel('complete_for_query'), 'Checked');
});
test('budget display stays bounded', () => {
  assert.equal(progress(20, 16), 100);
  assert.equal(progress(-1, 16), 0);
});
test('status preserves historical and complaint uncertainty', () => {
  assert.equal(recordLabel('historical'), 'Historical record');
  assert.equal(recordLabel('reported'), 'Reported condition');
  assert.equal(recordLabel('unknown'), 'Needs clarification');
});

test('unknown acquisition time is explicit rather than an invalid date', () => {
  assert.equal(date('Not recorded; refer to corpus acquisition manifest'), 'Acquisition time not recorded');
});
