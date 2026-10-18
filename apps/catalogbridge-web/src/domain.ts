export function budgetLabel(m: {
  tokens: number;
  reserved_tokens: number;
  unknown_attempts: number;
}) {
  return `${m.tokens.toLocaleString()} measured · ${m.reserved_tokens.toLocaleString()} reserved${m.unknown_attempts ? ` · ${m.unknown_attempts} unknown` : ""}`;
}
export function canReview(t: { state: string }) {
  return !["queued", "running", "cancelled"].includes(t.state);
}
export function formatCost(microunits: number | null, unit: string) {
  return microunits === null
    ? "Unknown"
    : `${(microunits / 1000000).toFixed(6)} ${unit}`;
}
export function canContinue(
  state: string,
  metrics: { unknown_attempts: number; reserved_tokens: number; runtime_circuit?: { open: boolean } },
) {
  return (
    state === "partial" &&
    !metrics.runtime_circuit?.open &&
    metrics.unknown_attempts === 0 &&
    metrics.reserved_tokens === 0
  );
}
export function isReviewStale(opened: number | null, live: number) {
  return opened === null || opened !== live;
}
export function prettyState(s: string) {
  return (
    (
      {
        recommended_match: "Unreviewed recommendation",
        needs_review: "Needs review",
        no_verified_match: "No verified match",
        partial: "Partial · completed rows preserved",
        review_ready: "Ready for review",
      } as Record<string, string>
    )[s] || s.replaceAll("_", " ")
  );
}
export function validateBatch(
  master: string,
  supplier: string,
  economy: string,
  strong: string,
) {
  if (!master || !supplier) return "Choose both immutable feed revisions.";
  if (!economy.trim() || !strong.trim() || economy === strong)
    return "Choose two distinct model identities.";
  return "";
}
