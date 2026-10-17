export const terminal = (status: string) =>
  !["queued", "running"].includes(status);
export function canExport(
  output: { reviewer: string | null; state: string; case_revision: number },
  revision: number,
) {
  return (
    Boolean(output.reviewer) &&
    !["stale", "erased"].includes(output.state) &&
    output.case_revision === revision
  );
}
export function syncAction(
  epoch: string,
  revision: number,
  next: { epoch: string; revision: number },
) {
  return next.epoch !== epoch
    ? "reset"
    : next.revision !== revision
      ? "refresh"
      : "unchanged";
}
