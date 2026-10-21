import assert from 'node:assert/strict';
import test from 'node:test';
import { canReview, codepointSlice, diffText, selectedVersion, usageLabel } from '../src/domain.ts';

test('review requires independent actor, exact selected version and ready state', () => {
  const task = {maker:'a',state:'review_ready',selected_hash:'v',versions:[{draft_hash:'v'}]};
  assert.equal(canReview(task, 'a'), false);
  assert.equal(canReview(task, 'b'), true);
  assert.equal(canReview({...task,state:'manual_required'}, 'b'), false);
  assert.equal(canReview({...task,selected_hash:null}, 'b'), false);
});
test('selected draft is not necessarily last attempted draft', () => {
  const task = {selected_hash:'old',versions:[{draft_hash:'old'},{draft_hash:'rejected'}]};
  assert.equal(selectedVersion(task).draft_hash, 'old');
});
test('unknown usage is never displayed as zero; Unicode offsets use codepoints', () => {
  assert.equal(usageLabel(null), 'Unknown');
  assert.equal(usageLabel(0), '0');
  assert.equal(codepointSlice('🥣 Oats', 2, 6), 'Oats');
});

test('diff is lossless for Unicode, identical and completely replaced strings',()=>{
  for(const [before,after] of [['🥣 Oats 700 g','🥣 Oats 500 g'],['same','same'],['abc','xyz'],['','new']]){
    const diff=diffText(before,after);
    assert.equal(diff.prefix+diff.removed+diff.suffix,before);
    assert.equal(diff.prefix+diff.added+diff.suffix,after);
  }
});
