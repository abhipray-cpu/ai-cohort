export type RequestState = {
  revision: number;
  binding: string;
  state: string;
  expires_at: string;
};
export function acceptSnapshot(
  current: { id: string; epoch: string; revision: number } | null,
  incoming: { id: string; epoch: string; revision: number },
) {
  return (
    !current ||
    current.id !== incoming.id ||
    current.epoch !== incoming.epoch ||
    incoming.revision >= current.revision
  );
}
export function mayDecide(
  opened: RequestState | null,
  current: RequestState | undefined,
  binding: string | null,
) {
  return (
    !!opened &&
    !!current &&
    opened.state === "pending" &&
    current.state === "pending" &&
    opened.revision === current.revision &&
    opened.binding === binding &&
    current.binding === binding &&
    Date.parse(opened.expires_at) > Date.now() &&
    Date.parse(current.expires_at) > Date.now()
  );
}
export function mayExport(state: string, reviewed: boolean) {
  return state === "finalized" && reviewed;
}
export function statusText(state: string) {
  return (
    (
      {
        waiting_human: "Waiting for human input",
        resume_queued: "Revalidating decisions",
        review_ready: "Ready for final human review",
        partial: "Partial analysis · review required",
        stale: "Context changed · review again",
        finalized: "Internally reviewed",
        queued: "Analysis queued",
      } as Record<string, string>
    )[state] ?? state.replaceAll("_", " ")
  );
}
