export const ragConcepts = [
  {
    title: "Retrieve context",
    detail:
      "Version-filtered passages from the knowledge library, retrieved afresh each turn.",
  },
  {
    title: "Answers with sources",
    detail: "Material claims link to exact quotes in stored source passages.",
  },
  {
    title: "Flag low confidence",
    detail:
      "Missing, partial or conflicting evidence stays visible; no invented certainty score.",
  },
  {
    title: "Fallback to search",
    detail:
      "When evidence is missing or weak, search approved official sources within budget and fetch pages before answering.",
  },
];

export function confidenceLabel(state: string, status: string): string {
  if (status === "failed") return "Low confidence · incomplete answer";
  return state === "supported"
    ? "Evidence supported · verify before action"
    : `Low confidence · ${state}`;
}

export function evidenceTrace(run: {
  events: { stage: string; outcome: string }[];
  answer: null | { evidence: { origin: string }[] };
}): string[] {
  const events = run.events;
  const result: string[] = [];
  if (
    events.some((e) => e.stage === "retrieval" && e.outcome === "succeeded")
  ) {
    const count =
      run.answer?.evidence.filter((p) => p.origin === "indexed").length || 0;
    result.push(
      `Indexed context: ${count ? `${count} passages retained` : "no passages retained"}`,
    );
  }
  const search = events.filter((e) => e.stage === "search").at(-1);
  if (!search) result.push("Search fallback: not used");
  else if (search.outcome === "succeeded") {
    const count =
      run.answer?.evidence.filter((p) => p.origin === "search").length || 0;
    result.push(
      `Search fallback: fetched evidence${count ? ` · ${count} passages retained` : ""}`,
    );
  } else if (search.outcome === "failed" || search.outcome === "unavailable")
    result.push(
      `Search fallback: ${search.outcome} · evidence remains limited`,
    );
  else if (search.outcome === "empty")
    result.push("Search fallback: no usable fetched evidence");
  else result.push("Search fallback: searching official sources");
  return result;
}
