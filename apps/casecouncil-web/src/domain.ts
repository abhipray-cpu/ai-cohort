export function highlight(
  text: string,
  start: number,
  end: number,
): [string, string, string] {
  const chars = Array.from(text);
  return [
    chars.slice(0, start).join(""),
    chars.slice(start, end).join(""),
    chars.slice(end).join(""),
  ];
}
export const voteLabel = (n: number) => `${n} of 3 roles`;
export const confidenceLabel = (band: string) =>
  `${band === "medium" ? "Medium" : "Low"} · uncalibrated`;
export const canReview = (
  role: string,
  actor: string,
  creator: string,
  author: string,
) =>
  ["owner", "reviewer"].includes(role) && actor !== creator && actor !== author;
export const exportLabel = (state: string, reviewed: boolean) =>
  state === "stale"
    ? "Unapproved historical draft"
    : reviewed && ["draft_ready", "manual_required"].includes(state)
      ? "Human reviewed"
      : "Unapproved draft";
export const roleName = (role: string) =>
  ({
    customer: "Customer advocate",
    insurer: "Insurer evidence",
    fairness: "Fair-resolution reviewer",
  })[role] || role;
export const readable = (value: string) =>
  value.replaceAll("_", " ").replaceAll(":", " · ");
export const pendingPacketLabel = (state: string) =>
  state === "running"
    ? "Review in progress"
    : state === "queued"
      ? "Review queued"
      : `Review stopped · ${readable(state)}`;

// AI synthesis is an internal review brief, not a ready-to-send customer letter.
export const reviewResponseSeed = (handlerDraft: string | undefined) =>
  handlerDraft ?? "";
