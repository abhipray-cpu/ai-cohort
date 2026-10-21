"""Explicit owner recovery of an existing campaign; never creates a new grant."""

import argparse
import json
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

from shelfproof_api.core import canonical, code_fingerprint, digest
from shelfproof_api.runtime import CodexProvider, runtime_lock
from shelfproof_api.store import Conflict, Store
from shelfproof_api.validation import summarize
from shelfproof_api.workflow import Worker


def park_queue(store, actor, tasks, expected_head, evidence):
    """Park the complete untouched queue, with attribution, without cancelling it."""
    if not tasks or len(tasks) != len(set(tasks)) or not 1 <= len(evidence) <= 2000:
        raise ValueError("exact distinct queue and evidence required")
    with runtime_lock(store.root) as acquired:
        if not acquired:
            raise Conflict("stop and isolate runtime before queue parking")
        store.verify_integrity()
        with store.db() as db:
            queued = db.execute("SELECT * FROM tasks WHERE state='queued'").fetchall()
            if (
                store.journal_head() != expected_head
                or {r["id"] for r in queued} != set(tasks)
                or db.execute("SELECT 1 FROM tasks WHERE state='running'").fetchone()
            ):
                raise Conflict("exact current queue and journal required")
            for row in queued:
                store._role(db, actor, row["workspace"], {"owner"})
                if row["calls"] or row["claims"] or row["lease"] or not store._current(db, row):
                    raise Conflict("only untouched current tasks may be parked")
            for row in queued:
                db.execute("UPDATE tasks SET state='manual_required' WHERE id=?", (row["id"],))
                store._audit(
                    db,
                    "recovery_queue_parked",
                    actor=actor,
                    task=row["id"],
                    body={"evidence": evidence, "previous_state": "queued", "calls_retained": 0},
                )


def classify_failure(stderr, exit_code):
    """Only allowlisted categories leave this boundary; never provider text."""
    lowered = stderr.lower()
    category = "unclassified"
    for name, phrases in (
        ("authentication", (b"invalid api key", b"unauthorized", b"not logged in", b"401")),
        (
            "configuration",
            (
                b"error loading configuration",
                b"invalid configuration",
                b"unknown variant",
                b"unexpected argument",
                b"failed to parse",
            ),
        ),
        ("schema", (b"invalid schema", b"invalid_json_schema", b"response_format")),
        ("rate_or_capacity", (b"usage limit", b"rate limit", b"429", b"capacity")),
        (
            "network",
            (
                b"error sending request",
                b"failed to connect",
                b"name resolution",
                b"stream disconnected",
                b"connection closed",
            ),
        ),
        ("permission", (b"operation not permitted", b"permission denied")),
    ):
        if any(p in lowered for p in phrases):
            category = name
            break
    return {"exit_code": exit_code, "category": category}


class DiagnosticProvider(CodexProvider):
    """Same production adapter/receipts, plus bounded redacted failure telemetry."""

    def __init__(self, diagnostic_path):
        super().__init__()
        self.diagnostic_path = Path(diagnostic_path)

    def _run(self, args, prompt):
        original = subprocess.Popen
        captured = bytearray()
        launched = []

        class StderrProxy:
            def __init__(self, stream):
                self.stream = stream

            def read(self, size):
                chunk = self.stream.read(size)
                captured.extend(chunk[: max(0, 65536 - len(captured))])
                return chunk

            def close(self):
                self.stream.close()

        def spawn(*positional, **kwargs):
            process = original(*positional, **kwargs)
            process.stderr = StderrProxy(process.stderr)
            launched.append(process)
            return process

        try:
            with patch("shelfproof_api.runtime.subprocess.Popen", spawn):
                return super()._run(args, prompt)
        finally:
            record = classify_failure(bytes(captured), launched[0].returncode if launched else None)
            if record["exit_code"] == 0:
                record["category"] = "process_completed_receipt_checked_separately"
            with self.diagnostic_path.open("a", encoding="utf-8") as file:
                file.write(canonical(record) + "\n")
            captured.clear()


def recover(run, actor, evidence, expected_head):
    root = Path(run)
    original = json.loads((root / "report-final.json").read_text())
    approval = original["approval"]
    store = Store(root / "service")
    if (
        approval["root"] != str(root.resolve())
        or approval["code_fingerprint"] != code_fingerprint()
    ):
        raise Conflict("existing campaign/code binding required")
    tasks = [p["task"] for p in original["products"]]
    pending = [t for t in tasks if store.task(actor, t)["state"] == "queued"]
    failed = [
        t for t in tasks if any(a["status"] == "unknown" for a in store.task(actor, t)["attempts"])
    ]
    if len(failed) != 1 or store.journal_head() != expected_head:
        raise Conflict("one isolated unknown and exact head required")
    before = store.verify_integrity()
    with (root / "recovery-authority.json").open("x", encoding="utf-8") as file:
        file.write(
            canonical(
                {
                    "evidence": evidence,
                    "actor": actor,
                    "before": before,
                    "unknown_usage_and_historical_safety_acknowledged": True,
                    "maximum_calls": 96,
                    "same_tasks": tasks,
                    "same_grant": True,
                }
            )
        )
    if pending:
        park_queue(store, actor, pending, expected_head, evidence)
    incident = store.accept_incident(
        actor,
        failed[0],
        expected_head,
        "User explicitly approved one-time recovery; unknown usage and historical safety remain unverified; original six/96 ceiling retained",
        evidence,
        True,
        "user-approved-recovery-20261021",
    )
    # Resume incident first to remove only its dispatch pause, then the parked rows.
    for task in failed + pending:
        store.resume(actor, task, store.task(actor, task)["selected_hash"], f"recovery:{task}")
    return {"incident": incident, "tasks_resumed": len(failed + pending), "unknown_refunded": False}


def run_worker(run, actor):
    root = Path(run)
    original = json.loads((root / "report-final.json").read_text())
    store = Store(root / "service")
    tasks = [p["task"] for p in original["products"]]
    diagnostics = root / "recovery-provider-diagnostics.jsonl"
    # New evidence output and exact code binding are mandatory before invocation.
    if diagnostics.exists() or (root / "report-recovery.json").exists():
        raise Conflict("recovery evidence already exists; do not repeat dispatch")
    if original["approval"]["code_fingerprint"] != code_fingerprint():
        raise Conflict("campaign code changed")
    worker = Worker(store, DiagnosticProvider(diagnostics))
    started = time.monotonic()
    try:
        while time.monotonic() - started < 3 * 3600:
            store.heartbeat()
            if store.liability_hold() or not worker.run_once():
                break
            with store.db() as db:
                calls = db.execute("SELECT SUM(calls) FROM grants").fetchone()[0]
            print(
                canonical(
                    {
                        "progress": True,
                        "cumulative_calls": calls,
                        "states": [store.task(actor, t)["state"] for t in tasks],
                    }
                ),
                flush=True,
            )
    finally:
        report = {**original, **summarize(store, actor, tasks, "actual_installed_codex")}
        report.update(
            {
                "recovery_elapsed_seconds": time.monotonic() - started,
                "source_pre_recovery_report_hash": digest(
                    (root / "report-final.json").read_bytes()
                ),
                "unknown_charge_preserved": True,
                "original_reports_preserved": True,
                "grant_or_liability_changed": True,
                "grant_ceiling_changed": False,
                "post_recovery_integrity": store.verify_integrity(),
            }
        )
        with (root / "report-recovery.json").open("x", encoding="utf-8") as file:
            file.write(canonical(report))
    return {
        k: v
        for k, v in report.items()
        if k not in {"products", "cohorts", "approval", "pending_ids"}
    }


def review_report(run):
    """Correct inherited driver metadata in a new derivative, never rewrite evidence."""
    root = Path(run)
    raw = (root / "report-recovery.json").read_bytes()
    report = json.loads(raw)
    report.update(
        {
            "source_recovery_report_sha256": digest(raw),
            "grant_or_liability_changed": True,
            "grant_ceiling_changed": False,
            "elapsed_seconds": report["recovery_elapsed_seconds"],
            "elapsed_scope": "recovery_worker_driver_only",
            "report_correction_notes": "Original recovery report inherited pre-recovery liability/elapsed metadata; measured counts, outcomes and evaluated code fingerprint are unchanged.",
        }
    )
    with (root / "report-recovery-reviewed.json").open("x", encoding="utf-8") as file:
        file.write(canonical(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--actor", required=True)
    actions = parser.add_subparsers(dest="action", required=True)
    recovery = actions.add_parser("recover")
    recovery.add_argument("--evidence", required=True)
    recovery.add_argument("--expected-head", required=True)
    actions.add_parser("run-worker")
    actions.add_parser("review-report")
    args = parser.parse_args()
    if args.action == "recover":
        result = recover(args.run, args.actor, args.evidence, args.expected_head)
    elif args.action == "run-worker":
        result = run_worker(args.run, args.actor)
    else:
        result = review_report(args.run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
