"""Filesystem-authorized ShelfProof operations; never an unauthenticated recovery API."""

import argparse
import json

from shelfproof_api.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("status")
    backup = actions.add_parser("backup")
    backup.add_argument("--output", required=True)
    restore = actions.add_parser("restore")
    restore.add_argument("--backup", required=True)
    restore.add_argument("--current-journal", required=True)
    for name in (
        "isolate-orphans",
        "resume",
        "accept-incident",
        "reconcile-receipt",
        "amend-grant",
        "release-quarantine",
    ):
        sub = actions.add_parser(name)
        sub.add_argument("--actor", required=True)
        if name != "resume":
            sub.add_argument("--expected-head", required=True)
        if name not in {
            "isolate-orphans",
            "amend-grant",
            "reconcile-receipt",
            "release-quarantine",
        }:
            sub.add_argument("--task", required=True)
        if name != "isolate-orphans":
            sub.add_argument("--key", required=True)
        if name in {
            "isolate-orphans",
            "accept-incident",
            "reconcile-receipt",
            "release-quarantine",
        }:
            sub.add_argument("--evidence-ref", required=True)
        if name in {"accept-incident", "amend-grant"}:
            sub.add_argument("--reason", required=True)
        if name == "resume":
            sub.add_argument("--selected-hash", default=None)
        if name == "accept-incident":
            sub.add_argument("--acknowledge-unknown", action="store_true", required=True)
        if name == "reconcile-receipt":
            sub.add_argument("--attempt", required=True)
            sub.add_argument(
                "--receipt-json",
                required=True,
                help="Audited verified receipt object, not raw logs",
            )
        if name == "amend-grant":
            sub.add_argument("--workspace", required=True)
            sub.add_argument("--grant", required=True)
            sub.add_argument("--ceiling", required=True, type=int)
    args = parser.parse_args()
    if args.action == "restore":
        store = Store.restore(args.backup, args.root, args.current_journal)
        result = {"quarantined": True, "journal_head": store.journal_head()}
    else:
        store = Store(args.root)
        if args.action == "status":
            result = {"health": store.health(), "integrity": store.verify_integrity()}
        elif args.action == "backup":
            result = store.backup(args.output)
        elif args.action == "isolate-orphans":
            store.isolate_orphans(args.actor, args.evidence_ref, args.expected_head)
            result = {"isolated": True, "unknown_usage_preserved": True}
        elif args.action == "resume":
            result = {"queued": store.resume(args.actor, args.task, args.selected_hash, args.key)}
        elif args.action == "accept-incident":
            result = {
                "incident": store.accept_incident(
                    args.actor,
                    args.task,
                    args.expected_head,
                    args.reason,
                    args.evidence_ref,
                    args.acknowledge_unknown,
                    args.key,
                ),
                "dispatch_enabled": False,
            }
        elif args.action == "reconcile-receipt":
            result = {
                "supplement_appended": store.reconcile_receipt(
                    args.actor,
                    args.attempt,
                    args.expected_head,
                    json.loads(args.receipt_json),
                    args.evidence_ref,
                    args.key,
                ),
                "dispatch_enabled": False,
            }
        elif args.action == "amend-grant":
            result = {
                "amended": store.amend_grant(
                    args.actor,
                    args.workspace,
                    args.grant,
                    args.ceiling,
                    args.expected_head,
                    args.reason,
                    args.key,
                )
            }
        elif args.action == "release-quarantine":
            result = {
                "enabled": store.release_quarantine(
                    args.actor, args.expected_head, args.evidence_ref, args.key
                ),
                "old_jobs_remain_stale": True,
            }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
