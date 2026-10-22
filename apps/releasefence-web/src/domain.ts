export type Row = { id: string; [key: string]: any };
export const traceProfiles = ["mlflow-phoenix-v1", "langsmith-phoenix-v1"];
export function tracePolicy(profile: string) {
  if (!traceProfiles.includes(profile))
    throw new Error("Unsupported trace profile");
  return { trace_profile: profile };
}
export function display(value: unknown): string {
  return value === null || value === undefined ? "—" : String(value);
}
export function duration(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("en-US", { maximumFractionDigits: 2 })
    : "—";
}
export function tone(state: string): string {
  return [
    "rollback_verified",
    "promoted",
    "delivered",
    "pass",
    "verified",
  ].includes(state)
    ? "good"
    : [
          "partial",
          "paused_inconclusive",
          "inconclusive",
          "retry",
          "verifying",
          "unknown",
        ].includes(state)
      ? "warning"
      : ["open", "failed_canary", "dead_letter", "fail", "blocked"].includes(
            state,
          )
        ? "bad"
        : "neutral";
}
export function canApprove(role: string, actor: string, roll: Row): boolean {
  return (
    ["owner", "approver"].includes(role) &&
    actor !== roll.creator &&
    !["rollback_verified", "promoted", "cancelled"].includes(roll.state)
  );
}
export function canAct(
  role: string,
  roll: Row,
  approvals: Row[],
  action: string,
  now = Date.now() / 1000,
): boolean {
  if (
    !["owner", "operator"].includes(role) ||
    !approvals.some(
      (a) =>
        a.rollout === roll.id &&
        !a.revoked &&
        a.expires > now &&
        a.actions.includes(action),
    )
  )
    return false;
  if (action === "canary")
    return (
      roll.state === "ready" ||
      (roll.state === "promotion_pending" && roll.stage === 5)
    );
  if (action === "promote")
    return roll.state === "promotion_pending" && roll.stage === 25;
  return ![
    "ready",
    "rollback_verified",
    "promoted",
    "cancelled",
    "verifying",
  ].includes(roll.state);
}
