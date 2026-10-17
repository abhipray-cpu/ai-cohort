"""Offline restore into a NEW directory only; never roll back the independent erasure ledger."""

import argparse
import json
import sqlite3
from pathlib import Path

from relaydesk_api.common import file_hash, ident, now
from relaydesk_api.ledger import verify
from relaydesk_api.store import Store


def backup(store, destination):
    verify(store.ledger_dir / "ledger.sqlite3", store.store_id, store.ledger_binding)
    store.verify_source_integrity()
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    target = destination / "relaydesk.sqlite3"
    with store.connect() as source, sqlite3.connect(target) as dest:
        source.backup(dest)
    manifest = {
        "schema": 2,
        "store_id": store.store_id,
        "ledger_binding": store.ledger_binding,
        "created_at": now(),
        "sha256": file_hash(target),
        "requires_live_erasure_ledger": True,
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def restore(snapshot, destination, *, ledger_dir):
    snapshot, destination, ledger_dir = Path(snapshot), Path(destination), Path(ledger_dir)
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    source = snapshot / "relaydesk.sqlite3"
    if manifest.get("schema") != 2 or file_hash(source) != manifest["sha256"]:
        raise ValueError("Backup integrity failure")
    if destination.exists():
        raise ValueError(
            "Restore requires a new destination; stop services and switch paths explicitly"
        )
    if not (ledger_dir / "ledger.sqlite3").is_file():
        raise ValueError("Current independent erasure ledger required")
    with sqlite3.connect(source) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity failure")
        if (
            db.execute("SELECT value FROM settings WHERE key='store_id'").fetchone()[0]
            != manifest["store_id"]
        ):
            raise ValueError("Store identity mismatch")
        row = db.execute("SELECT value FROM settings WHERE key='ledger_binding'").fetchone()
        binding = json.loads(row[0]) if row else None
        if binding != manifest.get("ledger_binding"):
            raise ValueError("Backup ledger binding mismatch")
        verify(ledger_dir / "ledger.sqlite3", manifest["store_id"], binding)
    destination.mkdir(parents=True)
    with (
        sqlite3.connect(source) as db,
        sqlite3.connect(destination / "relaydesk.sqlite3") as target,
    ):
        db.backup(target)
    store = Store(destination, ledger_dir=ledger_dir)
    store.verify_source_integrity()
    with store.connect() as db:
        db.execute("DELETE FROM sessions")
        db.execute("DELETE FROM vectors")
        db.execute(
            "UPDATE jobs SET status='cancelled',cancelled=1,lease=NULL,lease_until=NULL WHERE status IN ('queued','running')"
        )
        db.execute("UPDATE outputs SET state='stale',reviewer=NULL WHERE state!='erased'")
        db.execute("UPDATE settings SET value=? WHERE key='epoch'", (ident(),))
    store.set_setting("encoder", None)
    store.set_setting("heartbeat", None)
    return {
        "status": "restored",
        "erasure_entries_applied": len(store.ledger_entries()),
        "reindex_required": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("path")
    parser.add_argument("--data-dir", default="var/relaydesk")
    parser.add_argument("--ledger-dir", default="var/relaydesk-erasure")
    args = parser.parse_args()
    result = (
        backup(Store(args.data_dir, ledger_dir=args.ledger_dir), args.path)
        if args.action == "backup"
        else restore(args.path, args.data_dir, ledger_dir=args.ledger_dir)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
