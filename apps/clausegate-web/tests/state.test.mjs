import test from 'node:test';
import assert from 'node:assert/strict';
import { mayDecide, mayExport, statusText, acceptSnapshot } from '../src/state.ts';

test('waiting is a human checkpoint, not an active model spinner',()=>{
  assert.match(statusText('waiting_human'),/human/i);
});
test('stale request revision and expiry disable submission',()=>{
  const r={revision:1,binding:'original',state:'pending',expires_at:'2099-01-01'};
  assert.equal(mayDecide(r,r,'original'),true);
  assert.equal(mayDecide(r,{...r,revision:2},'original'),false);
  assert.equal(mayDecide(r,r,'changed'),false);
  assert.equal(mayDecide({...r,expires_at:'2000-01-01'},r,'original'),false);
});
test('a review-ready draft is not an approved export',()=>{
  assert.equal(mayExport('review_ready',true),false);
  assert.equal(mayExport('finalized',true),true);
  assert.equal(mayExport('stale',true),false);
});

test('out-of-order polling cannot replace newer context; restore epoch can reset it',()=>{
  const current={id:'case',epoch:'original',revision:5};
  assert.equal(acceptSnapshot(current,{...current,revision:4}),false);
  assert.equal(acceptSnapshot(current,{...current,epoch:'restored',revision:1}),true);
});
