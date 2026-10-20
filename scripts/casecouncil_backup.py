"""Operator-only protected-volume backup, quarantined restore and reconciliation."""

import argparse
import json

from casecouncil_api.backup import authorize_restored_runtime, backup, restore
from casecouncil_api.store import Store

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--data-dir", required=True)
    b.add_argument("--output", required=True)
    b.add_argument("--acknowledge-plaintext", action="store_true", required=True)
    r = sub.add_parser("restore")
    r.add_argument("--snapshot", required=True)
    r.add_argument("--target", required=True)
    r.add_argument("--authority", required=True)
    a = sub.add_parser("authorize-restored-runtime")
    a.add_argument("--data-dir", required=True)
    a.add_argument("--expected-head", required=True)
    a.add_argument("--reason", required=True)
    args = p.parse_args()
    if args.action == "backup":
        value = backup(Store(args.data_dir), args.output)
    elif args.action == "restore":
        value = restore(args.snapshot, args.target, args.authority)
    else:
        value = authorize_restored_runtime(Store(args.data_dir), args.expected_head, args.reason)
    print(json.dumps(value, indent=2))
