"""TEST-ONLY crash worker. Real captured data, controlled non-AI proposer/effect stand-in.

Never use as a product service. os._exit deliberately simulates abrupt process loss.
"""

import argparse
import asyncio
import json
import os
import sqlite3
from pathlib import Path

from agent_core.provider import StructuredGeneration
from buildrelay_api.queue import consume_message
from buildrelay_api.store import Store
from buildrelay_api.workflow import Workflow


class ControlledProposer:
    def __init__(self, evidence, counter):
        self.evidence, self.counter = evidence, Path(counter)

    def generate(self, **kwargs):
        count = int(self.counter.read_text()) if self.counter.exists() else 0
        self.counter.write_text(str(count + 1))
        lines = self.evidence["text"].splitlines()
        number, quote = next((i, s[:300]) for i, s in enumerate(lines, 1) if s.strip())
        return StructuredGeneration(
            text=json.dumps(
                {
                    "category": "unknown",
                    "summary": "Controlled fault-test handoff; this is not an AI diagnosis.",
                    "hypothesis": "No causal conclusion is being evaluated in this fault test.",
                    "confidence": 0,
                    "next_steps": ["Manually inspect the original real run."],
                    "citations": [{"line": number, "quote": quote}],
                    "client_update": "Controlled test draft; do not send to a client.",
                }
            ),
            exit_code=0,
            elapsed_ms=0,
        )


class RecordedSourceAndEffectStandIn:
    def __init__(self, evidence, directory, crash=None):
        self.value, self.root, self.crash = evidence, Path(directory), crash
        self.path = self.root / "external-stand-in.sqlite3"
        with sqlite3.connect(self.path) as db:
            # Deliberately no unique marker: duplicate POSTs would create duplicate rows.
            db.execute("CREATE TABLE IF NOT EXISTS issues(id INTEGER PRIMARY KEY,body TEXT)")

    def evidence(self, *_):
        return self.value

    def create_issue(self, repo, title, body):
        with sqlite3.connect(self.path) as db:
            number = db.execute("INSERT INTO issues(body) VALUES(?)", (body,)).lastrowid
        if self.crash == "external_accepted":
            os._exit(25)
        return {"number": number}

    def find_issue(self, repo, marker):
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT id,body FROM issues").fetchall()
        return next(({"number": n, "body": body} for n, body in rows if marker in body), None)

    def update_issue(self, repo, number, title, body, state):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE issues SET body=? WHERE id=?", (body, number))


async def queue_crash(root):
    import nats
    from nats.js.api import AckPolicy, ConsumerConfig

    nc = await nats.connect(os.environ["BUILDRELAY_FAULT_NATS_URL"])
    js = nc.jetstream()
    sub = await js.pull_subscribe(
        "fault.runs",
        durable="fault-inbox",
        stream="FAULTS",
        config=ConsumerConfig(ack_policy=AckPolicy.EXPLICIT, ack_wait=1, max_deliver=10),
    )
    msg = (await sub.fetch(1, timeout=5))[0]

    async def crash_before_ack():
        os._exit(23)

    msg.ack_sync = crash_before_ack
    await consume_message(Store(root), msg)


def workflow_crash(root, evidence_path, fault):
    root = Path(root)
    store = Store(root)
    evidence = json.loads(Path(evidence_path).read_text())
    original_claim = store.claim
    store.claim = lambda **kwargs: original_claim(lease=1)  # accelerated recovery test only
    original_checkpoint = store.checkpoint

    def checkpoint(job, step, value, **kwargs):
        original_checkpoint(job, step, value, **kwargs)
        if fault == step:
            os._exit(24)

    store.checkpoint = checkpoint
    source = RecordedSourceAndEffectStandIn(evidence, root, fault)
    Workflow(store, source, ControlledProposer(evidence, root / "proposer-count.txt")).once()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--evidence")
    p.add_argument(
        "--fault",
        required=True,
        choices=("queue_commit_before_ack", "evidence", "triage", "external_accepted"),
    )
    a = p.parse_args()
    if a.fault == "queue_commit_before_ack":
        asyncio.run(queue_crash(a.root))
    else:
        workflow_crash(a.root, a.evidence, a.fault)
