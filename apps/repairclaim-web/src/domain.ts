export type Item = Record<string, any>;
export const currencies = ["USD", "EUR", "GBP"];
export const outcomeKinds = [
  "requested",
  "confirmed_covered",
  "approved",
  "received",
  "avoided_cost",
];
export const label = (value: string) => value.replaceAll("_", " ");
export function documentReviewNotice(parsed: Item) {
  if (parsed.needs_ocr)
    return "Some pages have no usable text. Review every relevant page and enter missing facts manually. Blank extraction is not evidence of absence.";
  if (!parsed.proposals?.length)
    return "The document opened, but no facts were extracted. Review the page preview and enter repair facts manually. Dates, mileage, currency and payment are not confirmed.";
  return "These are unconfirmed proposals, not a complete reading of the document. Review dates, mileage units, currency and payment evidence before confirming. An invoice total or estimate is not proof of payment.";
}
export function packetAccess(
  p: Item,
  revision: number,
  epoch: number,
  source: string,
  now = Date.now() / 1000,
) {
  const fresh =
    !p.stale &&
    p.case_revision === revision &&
    p.registry_epoch === epoch &&
    source === "complete";
  return {
    approve: fresh && p.status === "rendered",
    download:
      fresh &&
      p.status === "approved" &&
      p.approval?.expires > now &&
      p.approval.fingerprint === p.fingerprint,
  };
}
export function nextAction(jobs: Item[], source: string) {
  const job = jobs.at(-1);
  if (job?.stale)
    return "Evidence changed. Review the facts and run a fresh condition check.";
  if (job?.status === "queued")
    return "Your casework is queued. You can safely leave this page.";
  if (job?.status === "running")
    return "Review in progress. Your confirmed facts are saved.";
  if (job?.status === "partial")
    return "Partial review saved. Inspect the issue before retrying.";
  if (source !== "complete")
    return "Official source inventory needs operator review. This is not a negative coverage result.";
  const question = job?.result?.next_question;
  return question
    ? `Please provide ${label(question.field)}. ${label(question.reason)}.`
    : "Confirm your repair facts, then check the documented conditions.";
}
export function factInput(field: string, value: string, unit: string): Item {
  if (!value.trim()) throw Error("Enter a fact value.");
  let parsed: string | number = value.trim();
  if (field === "model_year") {
    parsed = Number(value);
    if (!Number.isInteger(parsed)) throw Error("Use a whole year.");
  }
  if (
    [
      "paid_amount",
      "invoice_total",
      "repair_mileage",
      "current_mileage",
    ].includes(field) &&
    !/^\d+(\.\d{1,2})?$/.test(value)
  )
    throw Error("Use a positive decimal value.");
  return { field, value: parsed, unit: unit || null, status: "user_reported" };
}
export function aware(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) throw Error("Choose a date and time.");
  return date.toISOString();
}
