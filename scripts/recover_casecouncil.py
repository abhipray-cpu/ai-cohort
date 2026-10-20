"""Operator-only inspect, reconciliation, bounded incident closure and same-job resume.

Never invent a receipt or invoke a model. Incident acceptance is not verification.
"""

import argparse
import json
from pathlib import Path

from casecouncil_api.store import Store


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--evaluation-only", action="store_true")
    actions = p.add_subparsers(dest="action", required=True)
    inspect = actions.add_parser("inspect")
    inspect.add_argument("--job", required=True)
    reconcile = actions.add_parser("reconcile")
    reconcile.add_argument("--attempt", required=True)
    reconcile.add_argument("--expected-head", required=True)
    reconcile.add_argument("--evidence", required=True)
    reconcile.add_argument("--reference", required=True)
    reconcile.add_argument("--key", required=True)
    reconcile.add_argument("--verified-provider-evidence", action="store_true", required=True)
    incident = actions.add_parser("close-incident")
    incident.add_argument("--attempt", required=True)
    incident.add_argument("--expected-head", required=True)
    incident.add_argument("--reason", required=True)
    incident.add_argument("--isolation-reference", required=True)
    incident.add_argument("--key", required=True)
    incident.add_argument("--acknowledge-unknown", action="store_true", required=True)
    incident.add_argument("--runtime-isolated", action="store_true", required=True)
    resume = actions.add_parser("resume")
    resume.add_argument("--job", required=True)
    resume.add_argument("--packet-hash", required=True)
    resume.add_argument("--expected-head", required=True)
    resume.add_argument("--wall-seconds", type=int, default=600)
    resume.add_argument("--reason", required=True)
    resume.add_argument("--key", required=True)
    args = p.parse_args()
    if not (Path(args.data_dir) / "casecouncil.sqlite3").is_file():
        p.error("existing explicit service store required")
    store = Store(args.data_dir, evaluation_only=args.evaluation_only)
    if args.action == "inspect":
        job = store.job(args.actor, args.job)
        with store.connect() as db:
            head = db.execute("SELECT journal_head FROM meta WHERE id=1").fetchone()[0]
        value = {
            k: job[k]
            for k in (
                "id",
                "state",
                "binding",
                "packet_hash",
                "calls",
                "seconds",
                "claims",
                "deadline",
                "attempts",
                "prior_packets",
                "reconciliations",
                "incidents",
            )
        }
        value["journal_head"] = head
        value["prior_packets"] = [
            {k: p[k] for k in ("id", "hash", "recovery", "label")} for p in job["prior_packets"]
        ]
    elif args.action == "reconcile":
        path = Path(args.evidence)
        if path.stat().st_size > 100_000:
            p.error("bounded evidence JSON required")
        evidence = json.loads(path.read_text())
        value = store.reconcile_attempt(
            args.actor, args.attempt, args.expected_head, evidence, args.reference, args.key
        )
    elif args.action == "close-incident":
        value = store.close_incident(
            args.actor,
            args.attempt,
            args.expected_head,
            args.reason,
            args.isolation_reference,
            args.acknowledge_unknown,
            args.runtime_isolated,
            args.key,
        )
    else:
        value = store.resume_job(
            args.actor,
            args.job,
            args.packet_hash,
            args.expected_head,
            args.wall_seconds,
            args.reason,
            args.key,
        )
    print(json.dumps(value, indent=2))


if __name__ == "__main__":
    main()
