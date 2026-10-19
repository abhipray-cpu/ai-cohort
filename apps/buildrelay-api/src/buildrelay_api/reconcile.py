"""Bounded missed-event repair. Coverage limits are audit events, not silent success."""

import time

from .github import parse_webhook
from .workflow import Failure


def reconcile(store, github, repo, *, force=False, page_limit=3):
    with store.connect() as db:
        row = db.execute("SELECT last_scan FROM cursors WHERE repo_id=?", (repo["id"],)).fetchone()
    if row and not force and time.time() - row[0] < 300:
        return
    count, complete = 0, False
    # The recent-run API is ordered by run creation, not rerun update time.
    # Explicitly bounded to 300 recent runs by default; no full-history guarantee.
    for page in range(1, page_limit + 1):
        result = github.recent_runs(repo, page)
        runs = result.get("workflow_runs")
        if not isinstance(runs, list):
            raise Failure("github_invalid_run_list")
        for run in runs:
            if run.get("status") != "completed":
                continue
            event = parse_webhook(
                "workflow_run",
                {
                    "action": "completed",
                    "repository": {"id": repo["github_id"], "full_name": repo["name"]},
                    "workflow_run": run,
                },
            )
            if event:
                store.accept(
                    repo["id"],
                    event,
                    "reconciliation",
                    f"{event.run_id}:{event.attempt}:{event.conclusion}",
                )
                count += 1
        if len(runs) < 100:
            complete = True
            break
    with store.write() as db:
        store.record(
            db,
            "reconciliation_completed" if complete else "reconciliation_coverage_gap",
            repo_id=repo["id"],
            detail={
                "completed_runs_seen": count,
                "page_limit": page_limit,
                "scope": "recent run creation order; old reruns outside window may be missed",
            },
        )
        db.execute(
            "INSERT INTO cursors VALUES(?,?) ON CONFLICT(repo_id) DO UPDATE SET last_scan=excluded.last_scan",
            (repo["id"], time.time()),
        )


def reconcile_all(store, github):
    for repo in store.repos():
        try:
            reconcile(store, github, repo)
        except Failure as exc:
            # Back off reconciliation too; do not hit a failing API every polling tick.
            with store.write() as db:
                store.record(
                    db, "reconciliation_failed", repo_id=repo["id"], detail={"code": exc.code}
                )
                db.execute(
                    "INSERT INTO cursors VALUES(?,?) ON CONFLICT(repo_id) DO UPDATE SET last_scan=excluded.last_scan",
                    (repo["id"], time.time() + max(0, exc.retry_after - 300)),
                )
