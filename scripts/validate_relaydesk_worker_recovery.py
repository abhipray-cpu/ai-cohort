"""Kill/restart a real isolated worker during indexing; labelled lease-expiry injection."""

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from contracts.relaydesk import ImportBatch
from relaydesk_api.common import file_hash, now
from relaydesk_api.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    corpus = Path("var/validation/relaydesk-aggressive-corpus-v1")
    r = json.loads((corpus / "report.json").read_text())
    messages = []
    for row in r["threads"]:
        path = corpus / "batches" / row["batch"]
        if file_hash(path) != row["sha256"]:
            raise ValueError("Frozen capture hash mismatch")
        messages.extend(
            m for m in ImportBatch.model_validate_json(path.read_text()).messages if not m.bot
        )
        if len(messages) >= 300:
            break
    store = Store(root / "store", ledger_dir=root / "ledger")
    store.add_user("recovery-validator", secrets.token_urlsafe(24), admin=True)
    account = store.create_account("recovery-validator", "Real-process recovery test")
    case = store.create_case(
        "recovery-validator",
        account["id"],
        "Merged real payload load fixture; not a natural thread",
    )
    store.import_messages(
        "recovery-validator",
        case["id"],
        ImportBatch(
            messages=messages[:300],
            complete=False,
            gaps=["Labelled merged-history recovery fixture"],
        ),
    )
    conv = store.conversation("recovery-validator", case["id"])
    job = store.enqueue(
        "recovery-validator",
        conv["id"],
        conv["session"]["id"],
        "What was reported before the worker restarted?",
        "recovery",
    )
    env = os.environ.copy()
    env.update(
        {
            "RELAYDESK_DATA_DIR": str(store.root),
            "RELAYDESK_ERASURE_LEDGER_DIR": str(store.ledger_dir),
            "RELAYDESK_EMBEDDING_DIR": str(Path("var/models/relaydesk-minilm").resolve()),
        }
    )
    report = {
        "started_at": now(),
        "classification": "real worker process crash; source bodies real but merged fixture; lease expiry explicitly injected",
        "checks": [],
    }

    def check(name, passed, detail=None):
        report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})

    log = (root / "worker.log").open("ab")
    process = None

    def start():
        return subprocess.Popen(
            [sys.executable, "-m", "relaydesk_api.worker"],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    try:
        process = start()
        old_lease = None
        before = 0
        until = time.monotonic() + 30
        while time.monotonic() < until:
            with store.connect() as db:
                row = db.execute(
                    "SELECT status,lease FROM jobs WHERE id=?", (job["id"],)
                ).fetchone()
                before = db.execute("SELECT count(*) FROM vectors").fetchone()[0]
            if row["status"] == "running" and before > 0:
                old_lease = row["lease"]
                break
            time.sleep(0.02)
        check(
            "real worker observed mid-index",
            bool(old_lease) and before > 0,
            {"vectors_before_crash": before},
        )
        process.kill()
        process.wait(timeout=10)
        with store.connect() as db:
            original = db.execute(
                "SELECT model_calls,deadline FROM jobs WHERE id=?", (job["id"],)
            ).fetchone()
            # Avoid waiting 150 seconds: this is a documented injected expiry,
            # not an observed 150-second watchdog timing measurement.
            db.execute(
                "UPDATE jobs SET lease_until=? WHERE id=?",
                ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), job["id"]),
            )
        process = start()
        until = time.monotonic() + 90
        while time.monotonic() < until:
            result = store.job("recovery-validator", job["id"])
            if result["status"] not in ["queued", "running"]:
                break
            time.sleep(0.1)
        check(
            "restarted worker finishes durable job", result["status"] == "partial", result["status"]
        )
        check(
            "lease rotated without resetting deadline or usage",
            result["lease"] != old_lease
            and result["deadline"] == original["deadline"]
            and result["model_calls"] == original["model_calls"] == 0,
        )
        with store.connect() as db:
            total = db.execute("SELECT count(*) FROM vectors").fetchone()[0]
            turns = db.execute(
                "SELECT role,count(*) FROM turns WHERE conversation_id=? GROUP BY role",
                (conv["id"],),
            ).fetchall()
        check(
            "committed vectors survive and remaining indexing completes",
            total > before
            and result.get("output", {}).get("payload", {}).get("recall", {}).get("mode")
            == "semantic_hybrid",
            {"vectors_before": before, "vectors_after": total},
        )
        check(
            "restart does not duplicate committed turns",
            dict(turns) == {"user": 1, "assistant": 1},
            dict(turns),
        )
        report["finished_at"] = now()
        report["summary"] = {
            "checks": len(report["checks"]),
            "failed": [c for c in report["checks"] if not c["passed"]],
        }
        (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    main()
