"""Identity-bound external erasure authority. Legacy enrollment is explicit and offline."""

import argparse
import json
import sqlite3
from pathlib import Path

from relaydesk_api.common import file_hash, ident, now


def legacy_snapshot(data_dir, ledger_dir, destination):
    source = Path(data_dir) / "relaydesk.sqlite3"
    ledger = Path(ledger_dir) / "ledger.sqlite3"
    if not source.is_file() or not ledger.is_file():
        raise ValueError("Existing live store and ledger required")
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=False)
    with (
        sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True) as db,
        sqlite3.connect(root / "legacy.sqlite3") as snapshot,
    ):
        db.backup(snapshot)
        sid = db.execute("SELECT value FROM settings WHERE key='store_id'").fetchone()[0]
    manifest = {
        "kind": "quarantined-pre-enrollment-snapshot",
        "store_id": sid,
        "created_at": now(),
        "sha256": file_hash(root / "legacy.sqlite3"),
        "ledger_path": str(ledger.resolve()),
        "limitation": "Not a normal schema-2 restorable backup. Never roll back the current independent ledger.",
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def register(path, store_id):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS stores(id TEXT PRIMARY KEY,binding TEXT)")
        db.execute(
            "CREATE TABLE IF NOT EXISTS erased(store_id TEXT,case_id TEXT,source_key TEXT,at TEXT,PRIMARY KEY(store_id,case_id,source_key))"
        )
        db.execute("INSERT OR IGNORE INTO metadata VALUES('identity',?)", (ident(),))
        db.execute("INSERT OR IGNORE INTO stores VALUES(?,?)", (store_id, ident()))
        return {
            "identity": db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()[0],
            "binding": db.execute("SELECT binding FROM stores WHERE id=?", (store_id,)).fetchone()[
                0
            ],
        }


def verify(path, store_id, expected):
    if not path.is_file() or not expected:
        raise RuntimeError(
            "Identity-bound independent erasure ledger required; legacy stores need explicit offline enrollment"
        )
    try:
        with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True) as db:
            identity = db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()
            binding = db.execute("SELECT binding FROM stores WHERE id=?", (store_id,)).fetchone()
    except sqlite3.DatabaseError as error:
        raise RuntimeError("Independent erasure ledger identity unavailable") from error
    if not identity or not binding or expected != {"identity": identity[0], "binding": binding[0]}:
        raise RuntimeError("Independent erasure ledger identity mismatch")
    return expected


def enroll_legacy(data_dir, ledger_dir, confirm_store_id):
    """Operator must stop services and attest the exact live ledger path/store identity.

    Existing erased-source tombstones must be present in the chosen ledger. This
    cannot prove freshness of a stale same-identity ledger clone; protect the live
    ledger outside backups. No auto-enrollment of a restored legacy snapshot.
    """
    data = Path(data_dir) / "relaydesk.sqlite3"
    path = Path(ledger_dir) / "ledger.sqlite3"
    if not data.is_file() or not path.is_file():
        raise ValueError("Existing live store and independent ledger required")
    with sqlite3.connect(data) as db, sqlite3.connect(path) as ledger:
        db.execute("BEGIN IMMEDIATE")
        sid = db.execute("SELECT value FROM settings WHERE key='store_id'").fetchone()[0]
        if sid != confirm_store_id:
            raise ValueError("Explicit store identity confirmation mismatch")
        current = db.execute("SELECT value FROM settings WHERE key='ledger_binding'").fetchone()
        if current:
            return verify(path, sid, json.loads(current[0]))
        erased = {
            (r[0], r[1])
            for r in db.execute("SELECT case_id,source_key FROM sources WHERE erased=1")
        }
        recorded = {
            (r[0], r[1])
            for r in ledger.execute(
                "SELECT case_id,source_key FROM erased WHERE store_id=?", (sid,)
            )
        }
        if not erased.issubset(recorded):
            raise ValueError("Ledger omits existing erasures; enrollment refused")
        binding = register(path, sid)
        db.execute("INSERT INTO settings VALUES('ledger_binding',?)", (json.dumps(binding),))
        # Existing drafts predate the stricter claim-support boundary.
        db.execute("UPDATE outputs SET state='stale',reviewer=NULL WHERE state!='erased'")
        db.execute("DELETE FROM sessions")
        db.execute("UPDATE settings SET value=? WHERE key='epoch'", (ident(),))
    return binding


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--ledger-dir", required=True)
    parser.add_argument("--confirm-store-id", required=True)
    parser.add_argument("--backup-directory", required=True)
    args = parser.parse_args()
    snapshot = legacy_snapshot(args.data_dir, args.ledger_dir, args.backup_directory)
    if snapshot["store_id"] != args.confirm_store_id:
        raise ValueError("Snapshot identity confirmation mismatch")
    print(
        json.dumps(enroll_legacy(args.data_dir, args.ledger_dir, args.confirm_store_id), indent=2)
    )
