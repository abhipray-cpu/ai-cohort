"""Explicit fixed-code successors in the original store/grant; no budget reset."""

import argparse
import json
import time
from pathlib import Path

from contracts.shelfproof import Draft, FactPack
from shelfproof_api.core import canonical, code_fingerprint, digest
from shelfproof_api.runtime import runtime_lock
from shelfproof_api.store import Conflict, Store
from shelfproof_api.validation import summarize
from shelfproof_api.workflow import Worker

from scripts.recover_shelfproof_campaign import DiagnosticProvider


def prepare_successors(store, actor, parents, *, expected_head, expected_calls, evidence, key):
    if (
        not 1 <= len(parents) <= 6
        or len(set(parents)) != len(parents)
        or not 1 <= len(evidence) <= 2000
    ):
        raise ValueError("explicit exact bounded parent cohort required")
    with runtime_lock(store.root) as acquired:
        if not acquired:
            raise Conflict("stop and isolate worker")
        store.verify_integrity()
        with store.db() as db:
            rows = [store._scoped_task(db, actor, task, {"owner"}) for task in parents]
            workspace, grant = rows[0]["workspace"], rows[0]["grant_id"]
            payload = {
                "parents": parents,
                "head": expected_head,
                "calls": expected_calls,
                "code": code_fingerprint(),
                "evidence": evidence,
            }
            prior = store._intent(db, actor, workspace, "code_revalidation", key, payload)
            if prior is not None:
                return prior
            authority = db.execute("SELECT * FROM grants WHERE id=?", (grant,)).fetchone()
            epoch = db.execute("SELECT epoch FROM workspaces WHERE id=?", (workspace,)).fetchone()[
                0
            ]
            policy = db.execute(
                "SELECT body FROM policies WHERE workspace=? ORDER BY revision DESC LIMIT 1",
                (workspace,),
            ).fetchone()
            policy = json.loads(policy[0]) if policy else {"brief": "Neutral factual copy."}
            if (
                store.journal_head() != expected_head
                or store._liability(db)
                or db.execute("SELECT 1 FROM tasks WHERE state IN ('queued','running')").fetchone()
                or authority["calls"] != expected_calls
                or authority["max_calls"] > 96
                or authority["calls"] >= authority["max_calls"]
            ):
                raise Conflict("exact spend, head and isolated reconciled campaign required")
            for row in rows:
                if (
                    row["workspace"] != workspace
                    or row["grant_id"] != grant
                    or row["state"] not in {"manual_required", "failed", "review_ready"}
                    or row["epoch"] != epoch
                    or row["calls"] >= 16
                    or row["claims"] >= 4
                    or row["snapshot"]["code_fingerprint"] == code_fingerprint()
                    or row["snapshot"]["policy"] != policy
                    or db.execute("SELECT 1 FROM reviews WHERE task=?", (row["id"],)).fetchone()
                    or db.execute(
                        "SELECT 1 FROM task_links WHERE parent_task=?", (row["id"],)
                    ).fetchone()
                ):
                    raise Conflict("unreviewed unchanged-source changed-code parent required")
            children = []
            for row in rows:
                initial = row["versions"][0] if row["versions"] else None
                original = (
                    Draft.model_validate(initial["draft"])
                    if initial and initial["source"] == "imported"
                    else None
                )
                child = store.create_task(
                    actor,
                    workspace,
                    FactPack.model_validate(row["facts"]),
                    grant,
                    f"revalidate:{key}:{row['id']}",
                    original=original,
                    source_id=row["source_id"],
                    parent_task=row["id"],
                    _db=db,
                )
                db.execute(
                    "UPDATE tasks SET calls=?,claims=? WHERE id=?",
                    (row["calls"], row["claims"], child),
                )
                db.execute("UPDATE tasks SET state='stale',lease=NULL WHERE id=?", (row["id"],))
                store._audit(
                    db,
                    "fixed_code_successor",
                    actor=actor,
                    task=child,
                    body={
                        "parent": row["id"],
                        "old_code": row["snapshot"]["code_fingerprint"],
                        "new_code": code_fingerprint(),
                        "calls_retained": row["calls"],
                        "claims_retained": row["claims"],
                        "evidence": evidence,
                    },
                )
                children.append(child)
            store._remember(db, actor, workspace, "code_revalidation", key, payload, children)
            return children


def execute(run, actor, parent_report, label, evidence, expected_head, expected_calls):
    root = Path(run)
    original = json.loads((root / parent_report).read_text())
    approval = json.loads((root / "approval.json").read_text())
    parents = [p["task"] for p in original["products"]]
    store = Store(root / "service")
    products = [store.task(actor, t)["facts"]["product_id"] for t in parents]
    if (
        len(parents) != 6
        or products != approval["product_ids"]
        or approval["root"] != str(root.resolve())
    ):
        raise Conflict("only the original six products in the original store are authorized")
    output = root / label
    output.mkdir(exist_ok=False)
    store.backup(output / "before-backup")
    binding = {
        "evidence": evidence,
        "expected_head": expected_head,
        "expected_calls": expected_calls,
        "code_fingerprint": code_fingerprint(),
        "parents": parents,
        "source_report_hash": digest((root / parent_report).read_bytes()),
        "original_grant_and_ceiling_retained": True,
    }
    (output / "authority.json").write_text(canonical(binding))
    children = prepare_successors(
        store,
        actor,
        parents,
        expected_head=expected_head,
        expected_calls=expected_calls,
        evidence=evidence,
        key=label,
    )
    (output / "tasks.json").write_text(canonical(children))
    worker = Worker(store, DiagnosticProvider(output / "provider-diagnostics.jsonl"))
    started = time.monotonic()
    try:
        while time.monotonic() - started < 3 * 3600:
            store.heartbeat()
            if store.liability_hold() or not worker.run_once():
                break
            print(
                canonical(
                    {"progress": True, "states": [store.task(actor, t)["state"] for t in children]}
                ),
                flush=True,
            )
    finally:
        report = summarize(store, actor, children, "actual_installed_codex")
        with store.db() as db:
            grant = db.execute(
                "SELECT calls,max_calls FROM grants WHERE id=?",
                (store._task(db, children[0])["grant_id"],),
            ).fetchone()
            unknown = db.execute("SELECT count(*) FROM attempts WHERE status!='known'").fetchone()[
                0
            ]
        report.update(
            {
                "authority": binding,
                "source_manifest_hash": approval["source_manifest_hash"],
                "current_pass_calls": report["actual_calls"],
                "cumulative_calls": grant["calls"],
                "maximum_cumulative_calls": grant["max_calls"],
                "historical_unknown_attempts": unknown,
                "unknown_history_not_erased": True,
                "human_review_performed": False,
                "automatic_approval_performed": False,
                "elapsed_seconds": time.monotonic() - started,
                "post_run_integrity": store.verify_integrity(),
            }
        )
        with (output / "report.json").open("x", encoding="utf-8") as file:
            file.write(canonical(report))
    return {k: v for k, v in report.items() if k not in {"products", "authority"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--parent-report", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-calls", type=int, required=True)
    args = parser.parse_args()
    # Labels/report paths must remain within the already-owned evidence root.
    if (
        not args.label.replace("-", "").isalnum()
        or Path(args.parent_report).is_absolute()
        or ".." in Path(args.parent_report).parts
    ):
        parser.error("local bounded evidence paths required")
    print(
        json.dumps(
            execute(
                args.run,
                args.actor,
                args.parent_report,
                args.label,
                args.evidence,
                args.expected_head,
                args.expected_calls,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
