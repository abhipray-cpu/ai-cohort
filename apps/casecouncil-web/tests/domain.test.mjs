import test from "node:test";
import assert from "node:assert/strict";
import {
  highlight,
  voteLabel,
  canReview,
  exportLabel,
  confidenceLabel,
  pendingPacketLabel,
  reviewResponseSeed,
} from "../src/domain.ts";

test("Python Unicode offsets are not JavaScript UTF16 offsets", () => {
  assert.deepEqual(highlight("Policy 😀 café", 7, 8), [
    "Policy ",
    "😀",
    " café",
  ]);
});
test("agreement labels do not invent a probability or shrink the roster", () => {
  assert.equal(voteLabel(2), "2 of 3 roles");
  assert.equal(confidenceLabel("medium"), "Medium · uncalibrated");
});
test("maker cannot approve their own case even with reviewer capability", () => {
  assert.equal(canReview("owner", "alice", "alice", "bob"), false);
  assert.equal(canReview("analyst", "alice", "other", "bob"), false);
  assert.equal(canReview("reviewer", "alice", "other", "bob"), true);
});
test("stale review history is never a reviewed-current export", () => {
  assert.equal(exportLabel("stale", true), "Unapproved historical draft");
  assert.equal(exportLabel("draft_ready", false), "Unapproved draft");
  assert.equal(exportLabel("draft_ready", true), "Human reviewed");
});

test("terminal jobs without a packet never claim to still be running", () => {
  assert.equal(pendingPacketLabel("running"), "Review in progress");
  assert.equal(pendingPacketLabel("queued"), "Review queued");
  for (const state of ["failed", "stale", "cancelled"])
    assert.equal(pendingPacketLabel(state), "Review stopped · " + state);
});

test("review response begins with the handler draft, never AI voting metadata", () => {
  assert.equal(
    reviewResponseSeed("We will request the missing policy."),
    "We will request the missing policy.",
  );
  assert.equal(reviewResponseSeed(undefined), "");
});
