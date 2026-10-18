import assert from "node:assert/strict";
import { test } from "node:test";
import {
  budgetLabel,
  canContinue,
  canReview,
  formatCost,
  isReviewStale,
  prettyState,
  validateBatch,
} from "../src/domain.ts";

test("unknown usage is never rendered as free", () => {
  assert.match(
    budgetLabel({ tokens: 40, reserved_tokens: 12000, unknown_attempts: 1 }),
    /unknown/,
  );
});
test("running/cancelled rows cannot be approved", () => {
  assert.equal(canReview({ state: "running" }), false);
  assert.equal(canReview({ state: "needs_review" }), true);
});
test("duplicate model tiers and missing feeds block start", () => {
  assert.ok(validateBatch("", "s", "a", "b"));
  assert.ok(validateBatch("m", "s", "a", "a"));
  assert.equal(validateBatch("m", "s", "a", "b"), "");
});
test("state labels communicate review instead of approval", () => {
  assert.equal(prettyState("recommended_match"), "Unreviewed recommendation");
  assert.equal(prettyState("partial"), "Partial · completed rows preserved");
});

test("unknown or in-flight usage blocks continuation", () => {
  assert.equal(
    canContinue("partial", { unknown_attempts: 1, reserved_tokens: 10 }),
    false,
  );
  assert.equal(
    canContinue("partial", { unknown_attempts: 0, reserved_tokens: 0 }),
    true,
  );
  assert.equal(
    canContinue("running", { unknown_attempts: 0, reserved_tokens: 0 }),
    false,
  );
});

test("polling cannot silently approve a newer context with an old form", () => {
  assert.equal(isReviewStale(1, 2), true);
  assert.equal(isReviewStale(2, 2), false);
  assert.equal(isReviewStale(null, 2), true);
});

test("cost shows units and never treats unknown as zero", () => {
  assert.equal(formatCost(null, "USD"), "Unknown");
  assert.equal(formatCost(1200000, "USD"), "1.200000 USD");
});

test("a circuit opened by another batch blocks continuation", () => {
  assert.equal(canContinue("partial", {
    unknown_attempts: 0, reserved_tokens: 0, runtime_circuit: { open: true },
  }), false);
});
