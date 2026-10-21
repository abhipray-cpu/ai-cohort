export type Version = {
  draft_hash: string;
  version_index?: number;
  source?: string;
  draft?: { title: string; description: string };
};
type Reviewable = {
  state: string;
  maker: string;
  selected_hash: string | null;
  versions: Version[];
  selected_revision?: number;
};
export function selectedVersion(task: {
  selected_hash: string | null;
  versions: Version[];
  selected_revision?: number;
}) {
  return task.versions.find(
    (v) =>
      v.draft_hash === task.selected_hash &&
      (v.version_index ?? 0) === (task.selected_revision ?? 0),
  );
}
export function canReview(task: Reviewable, actor: string) {
  return (
    task.state === "review_ready" &&
    task.maker !== actor &&
    !!selectedVersion(task)
  );
}
export function usageLabel(value: number | null | undefined) {
  return value == null ? "Unknown" : value.toLocaleString("en-US");
}
export function codepointSlice(text: string, start: number, end: number) {
  return Array.from(text).slice(start, end).join("");
}

export function diffText(before: string, after: string) {
  const old = Array.from(before),
    next = Array.from(after);
  let prefix = 0,
    suffix = 0;
  while (
    prefix < Math.min(old.length, next.length) &&
    old[prefix] === next[prefix]
  )
    prefix++;
  while (
    suffix < Math.min(old.length - prefix, next.length - prefix) &&
    old[old.length - 1 - suffix] === next[next.length - 1 - suffix]
  )
    suffix++;
  return {
    prefix: old.slice(0, prefix).join(""),
    removed: old.slice(prefix, old.length - suffix).join(""),
    added: next.slice(prefix, next.length - suffix).join(""),
    suffix: suffix ? old.slice(-suffix).join("") : "",
  };
}
