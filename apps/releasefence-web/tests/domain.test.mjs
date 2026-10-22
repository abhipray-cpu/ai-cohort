import { test } from "node:test";
import assert from "node:assert/strict";
import {
  canAct,
  canApprove,
  display,
  tone,
  tracePolicy,
  duration,
} from "../src/domain.ts";
test("control is role, phase and approved scope bound", () => {
  const r = { id: "r", creator: "maker", state: "ready", stage: 0 };
  const a = [
    { rollout: "r", actions: ["canary"], expires: 200, revoked: false },
  ];
  assert.equal(canAct("observer", r, a, "canary", 100), false);
  assert.equal(canAct("owner", r, [], "canary", 100), false);
  assert.equal(canAct("owner", r, a, "canary", 100), true);
  assert.equal(canAct("owner", r, a, "promote", 100), false);
  assert.equal(canAct("owner", r, a, "canary", 201), false);
  assert.equal(canApprove("owner", "maker", r), false);
  assert.equal(canApprove("approver", "reviewer", r), true);
});
test("unknown is not a zero and partial is not success", () => {
  assert.equal(display(null), "—");
  assert.equal(display(0), "0");
  assert.equal(tone("rollback_verified"), "good");
  assert.equal(tone("partial"), "warning");
  assert.notEqual(tone("verifying"), "good");
});
test("trace profile is explicit without weakening statistical policy", () => {
  assert.deepEqual(tracePolicy("mlflow-phoenix-v1"), {
    trace_profile: "mlflow-phoenix-v1",
  });
  assert.deepEqual(tracePolicy("langsmith-phoenix-v1"), {
    trace_profile: "langsmith-phoenix-v1",
  });
  assert.throws(() => tracePolicy("skip-checks"));
});
test("latency rendering is rounded without inventing unavailable measurements", () => {
  assert.equal(duration(18.549999999999997), "18.55");
  assert.equal(duration(0), "0");
  assert.equal(duration(null), "—");
  assert.equal(duration(Number.NaN), "—");
});
