import assert from "node:assert/strict";
import test from "node:test";
import { terminal, canExport, syncAction } from "../src/state.ts";
test("partial is a terminal draft, not a spinner or certified resolution", () => {
  assert.equal(terminal("partial"), true);
  assert.equal(terminal("running"), false);
});
test("exports require exact reviewed current revision", () => {
  assert.equal(
    canExport({ reviewer: "alice", state: "partial", case_revision: 4 }, 4),
    true,
  );
  for (const out of [
    { reviewer: null, state: "partial", case_revision: 4 },
    { reviewer: "alice", state: "stale", case_revision: 4 },
    { reviewer: "alice", state: "partial", case_revision: 3 },
  ])
    assert.equal(canExport(out, 4), false);
});
test("epoch reset invalidates cached views even if revision matches", () => {
  assert.equal(syncAction("old", 4, { epoch: "new", revision: 4 }), "reset");
  assert.equal(syncAction("old", 4, { epoch: "old", revision: 5 }), "refresh");
  assert.equal(
    syncAction("old", 4, { epoch: "old", revision: 4 }),
    "unchanged",
  );
});
