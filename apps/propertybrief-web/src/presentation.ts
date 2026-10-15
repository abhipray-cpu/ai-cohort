export function coverageLabel(status: string): string {
  return (
    (
      {
        complete_for_query: "Checked",
        not_checked: "Not checked",
        unknown: "Incomplete",
        truncated: "Results capped",
        drift_detected: "Source changed",
      } as Record<string, string>
    )[status] || "Unavailable"
  );
}
export function recordLabel(status: string): string {
  return (
    (
      {
        historical: "Historical record",
        recorded_open: "Recorded open",
        reported: "Reported condition",
      } as Record<string, string>
    )[status] || "Needs clarification"
  );
}
export function progress(used: number, limit: number): number {
  return Math.max(0, Math.min(100, (used / limit) * 100));
}
export function human(value: string): string {
  return value.replaceAll("_", " ");
}
export function date(value?: string): string {
  if (!value) return "Not acquired";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Acquisition time not recorded" : parsed.toLocaleString();
}
