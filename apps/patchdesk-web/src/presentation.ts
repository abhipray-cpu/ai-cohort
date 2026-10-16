export function outcomeLabel(value: string): string {
  return (
    (
      {
        unavailable: "Source unavailable",
        denied: "Permission denied",
        no_matches: "No matches in query",
        complete_for_query: "Query complete",
        completed: "Checks completed",
        partial: "Partial investigation",
        running: "Investigating",
        queued: "Queued",
        outcome_unknown: "Publication outcome unknown",
        sending: "Awaiting receipt",
        published: "Issue published",
      } as Record<string, string>
    )[value] || value.replaceAll("_", " ")
  );
}
export function publicationAction(status: string): string {
  return ["outcome_unknown", "sending", "quarantined"].includes(status)
    ? "reconcile"
    : status === "draft"
      ? "approve"
      : status === "approved"
        ? "dispatch"
        : "none";
}
export function statusTone(status: string): string {
  return ["completed", "success", "complete_for_query", "published"].includes(
    status,
  )
    ? "success"
    : ["running", "queued"].includes(status)
      ? "active"
      : "warning";
}
export function distinctClients(projects: { client: string }[]): string[] {
  return [...new Set(projects.map((p) => p.client))].sort();
}
