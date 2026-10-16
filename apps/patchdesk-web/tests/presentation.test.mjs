import test from "node:test";
import assert from "node:assert/strict";
import {
  outcomeLabel,
  publicationAction,
  statusTone,
  distinctClients,
} from "../src/presentation.ts";
test("unavailable and denied are never no-match", () => {
  assert.equal(outcomeLabel("unavailable"), "Source unavailable");
  assert.equal(outcomeLabel("denied"), "Permission denied");
});
test("unknown writes cannot be casually retried", () => {
  assert.equal(publicationAction("outcome_unknown"), "reconcile");
  assert.equal(publicationAction("sending"), "reconcile");
  assert.equal(publicationAction("draft"), "approve");
});
test("partial and completed are process states", () => {
  assert.equal(statusTone("partial"), "warning");
  assert.equal(statusTone("completed"), "success");
  assert.notEqual(outcomeLabel("completed"), "Secure");
});
test("client groups preserve scoped project list", () => {
  assert.deepEqual(
    distinctClients([{ client: "B" }, { client: "A" }, { client: "B" }]),
    ["A", "B"],
  );
});
