export function canReplay(state: string, role: string) {
  return state === "dead" && ["owner", "operator"].includes(role);
}
export function stateLabel(state: string) {
  return (
    (
      {
        recovered: "Run recovered",
        dead: "Needs operator attention",
        needs_triage: "Needs manual triage",
        investigating: "Investigating",
        retry: "Retry scheduled",
        pending: "Queued",
        processing: "Processing",
        done: "Completed",
      } as Record<string, string>
    )[state] || state
  );
}
export function counters(
  incidents: { state: string }[],
  events: { state: string }[],
) {
  return {
    open: incidents.filter((i) => i.state !== "recovered").length,
    retrying: events.filter((e) => e.state === "retry").length,
    dead: events.filter((e) => e.state === "dead").length,
    done: events.filter((e) => e.state === "done").length,
  };
}
export function safeRunUrl(raw: string) {
  try {
    const u = new URL(raw);
    return u.protocol === "https:" &&
      u.hostname === "github.com" &&
      !u.username &&
      !u.password
      ? u.href
      : null;
  } catch {
    return null;
  }
}
