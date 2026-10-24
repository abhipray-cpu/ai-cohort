import { test } from "node:test";
import assert from "node:assert/strict";
import { packetAccess, nextAction, factInput, documentReviewNotice } from "../src/domain.ts";

test("parsed documents do not imply invoice understanding or confirmed payment", () => {
  assert.match(documentReviewNotice({ proposals: [], needs_ocr: false }), /no facts/i);
  assert.match(documentReviewNotice({ proposals: [{ field: "diagnostic_code" }] }), /not.*complete/i);
  assert.match(documentReviewNotice({ proposals: [], needs_ocr: true }), /no usable text/i);
});
test("approval never survives revision, source expiry, or TTL", () => {
  const packet = {
    status: "approved",
    fingerprint: "abc",
    approval: { fingerprint: "abc", expires: 200 },
    case_revision: 2,
    registry_epoch: 3,
  };
  assert.equal(packetAccess(packet, 2, 3, "complete", 100).download, true);
  for (const args of [
    [3, 3, "complete", 100],
    [2, 4, "complete", 100],
    [2, 3, "stale", 100],
    [2, 3, "complete", 201],
  ])
    assert.equal(packetAccess(packet, ...args).download, false);
});
test("next action is honest about missing inventory and partial work", () => {
  assert.match(nextAction([], "unavailable"), /source/i);
  assert.match(
    nextAction([{ status: "partial", error: "parser_timeout" }], "complete"),
    /partial/i,
  );
  assert.equal(
    nextAction([{ status: "queued" }], "complete"),
    "Your casework is queued. You can safely leave this page.",
  );
});
test("numeric values preserve money precision and manual attribution", () => {
  assert.deepEqual(factInput("paid_amount", "123.45", "USD"), {
    field: "paid_amount",
    value: "123.45",
    unit: "USD",
    status: "user_reported",
  });
  assert.equal(factInput("model_year", "2018", "").value, 2018);
  assert.throws(() => factInput("repair_mileage", "-3", "mi"));
});
