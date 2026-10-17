"""Real isolated worker kill/restart while human input is pending; fixture decisions."""

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

from clausegate_api.common import byte_hash, now
from clausegate_api.store import Store
from contracts.clausegate import DecisionInput, Finding, Playbook, Rule


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--corpus", default="var/validation/clausegate-corpus-v2")
    args = p.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    corpus = Path(args.corpus)
    data = corpus / "evaluator-only.json"
    manifest = json.loads((corpus / "manifest.json").read_text())
    if byte_hash(data.read_bytes()) != manifest["normalized_sha256"]:
        raise ValueError("Corpus integrity failure")
    row = next(r for r in json.loads(data.read_text()) if r["split"] == "train")
    s = Store(root / "store", ledger_dir=root / "authority")
    for name in ["requester", "reviewer"]:
        s.add_user(name, secrets.token_urlsafe(24))
    w = s.create_workspace("requester", "Real-process recovery fixture")
    c = s.create_case("requester", w["id"], "Actual NDA, labelled manual decisions")
    s.membership(
        "requester", w["id"], "reviewer", ["reviewer", "approver", "final_reviewer"], [c["id"]]
    )
    c = s.case("requester", c["id"])
    h = next(iter(row["hypotheses"]))
    c = s.set_playbook(
        "requester",
        c["id"],
        c["revision"],
        Playbook(
            name="Recovery fixture",
            rules=[
                Rule(
                    id=h, hypothesis=row["hypotheses"][h]["hypothesis"], action="require_exception"
                )
            ],
        ),
    )
    c = s.set_context("requester", c["id"], c["revision"], "recipient", "Recovery test only")
    c = s.import_document("requester", c["id"], c["revision"], row["document"])
    # Labelled boundary fixture, not a model prediction or legal classification.
    c = s.submit_findings(
        "reviewer",
        c["id"],
        c["revision"],
        [
            Finding(
                check_id=h,
                label="NotMentioned",
                assessment="supported",
                rationale="Explicit state-machine fixture, not a semantic accuracy assertion",
            )
        ],
        "Controlled recovery fixture",
    )
    request = next(r for r in c["requests"] if r["state"] == "pending")
    env = {
        **os.environ,
        "CLAUSEGATE_DATA_DIR": str(s.root),
        "CLAUSEGATE_ERASURE_LEDGER_DIR": str(s.ledger_dir),
    }
    report = {
        "started_at": now(),
        "classification": "Actual OS process kill/restart, real source, explicitly synthetic policy/decisions; no model calls",
        "checks": [],
    }
    process = None
    with (root / "worker.log").open("ab") as log:

        def start():
            return subprocess.Popen(
                [sys.executable, "-m", "clausegate_api.worker"],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )

        def check(name, condition):
            report["checks"].append({"name": name, "passed": bool(condition)})
            if not condition:
                raise AssertionError(name)

        try:
            process = start()
            time.sleep(0.7)
            check("isolated worker runs while workflow is paused", process.poll() is None)
            process.kill()
            process.wait(timeout=5)
            check(
                "request checkpoint survives actual process kill",
                s.case("requester", c["id"])["requests"][0]["id"] == request["id"],
            )
            check("waiting consumed no model calls", not s.jobs("requester", c["id"]))
            s.decide(
                "reviewer",
                request["id"],
                DecisionInput(
                    expected_revision=request["revision"],
                    binding=request["binding"],
                    kind="approve_exception",
                    rationale="Controlled recovery decision while worker is down",
                    key="recovery",
                ),
            )
            check(
                "human response persists while worker is stopped",
                s.case("requester", c["id"])["state"] == "resume_queued",
            )
            process = start()
            until = time.monotonic() + 10
            while time.monotonic() < until:
                current = s.case("requester", c["id"])
                if current["state"] == "review_ready":
                    break
                time.sleep(0.1)
            check(
                "restarted worker completes validated continuation",
                current["state"] == "review_ready",
            )
            check(
                "one effective continuation and no inference on resume",
                len(s.jobs("requester", c["id"])) == 1
                and s.jobs("requester", c["id"])[0]["calls"] == 0,
            )
            check(
                "audit chain survives process recovery",
                s.verify_audit("requester", c["id"])["valid"],
            )
        finally:
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
    report["finished_at"] = now()
    report["summary"] = {
        "checks": len(report["checks"]),
        "failed": [r for r in report["checks"] if not r["passed"]],
    }
    (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
