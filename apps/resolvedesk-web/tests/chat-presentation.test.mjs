import test from "node:test";
import assert from "node:assert/strict";
import {
  confidenceLabel,
  evidenceTrace,
  ragConcepts,
} from "../src/chatPresentation.ts";

test("all four requested concepts are explicitly named", () => {
  assert.deepEqual(
    ragConcepts.map((c) => c.title),
    [
      "Retrieve context",
      "Answers with sources",
      "Flag low confidence",
      "Fallback to search",
    ],
  );
});
test("uncertain and incomplete answers never render as supported", () => {
  for (const state of ["partial", "conflicting", "insufficient"])
    assert.match(confidenceLabel(state, "draft"), /Low confidence/);
  assert.match(
    confidenceLabel("supported", "failed"),
    /Low confidence.*incomplete/,
  );
  assert.match(confidenceLabel("supported", "draft"), /verify before action/);
});
test("indexed-only answer does not claim search was used", () => {
  assert.deepEqual(
    evidenceTrace({
      events: [{ stage: "retrieval", outcome: "succeeded" }],
      answer: { evidence: [{ origin: "indexed" }] },
    }),
    ["Indexed context: 1 passages retained", "Search fallback: not used"],
  );
});
test("live fetched evidence is labelled separately from indexed evidence", () => {
  assert.deepEqual(
    evidenceTrace({
      events: [
        { stage: "retrieval", outcome: "succeeded" },
        { stage: "search", outcome: "started" },
        { stage: "search", outcome: "succeeded" },
      ],
      answer: { evidence: [{ origin: "search" }, { origin: "indexed" }] },
    }),
    [
      "Indexed context: 1 passages retained",
      "Search fallback: fetched evidence · 1 passages retained",
    ],
  );
});
test("failed, unavailable and empty search never render as recovered", () => {
  for (const outcome of ["failed", "unavailable", "empty"]) {
    const trace = evidenceTrace({
      events: [{ stage: "search", outcome }],
      answer: { evidence: [] },
    }).join(" ");
    assert.doesNotMatch(trace, /Search fallback: fetched evidence/);
    assert.match(trace, /limited|no usable/);
  }
});
