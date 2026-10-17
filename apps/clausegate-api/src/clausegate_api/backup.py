"""New-directory quarantined recovery; never reuse restored approval authority."""

import argparse
import json
import sqlite3
from pathlib import Path

from clausegate_api import authority
from clausegate_api.common import byte_hash, canonical, ident, now
from clausegate_api.store import Store


def backup(store, destination):
    authority.verify(store.ledger_dir, store.store_id, store.binding)
    with store.coherent_read() as db:
        for r in db.execute("SELECT id FROM documents").fetchall():
            store._document(db, r[0])
        for r in db.execute("SELECT id FROM cases").fetchall():
            store._verify(db, r[0])
        root = Path(destination)
        root.mkdir(parents=True, exist_ok=False)
        path = root / "clausegate.sqlite3"
        # Backup cannot use the connection holding BEGIN IMMEDIATE: SQLite's
        # backup API would wait on its own active write transaction. A separate
        # source connection reads the stable store while the fence blocks writers.
        with sqlite3.connect(store.path) as source, sqlite3.connect(path) as target:
            source.backup(target)
    manifest = {
        "schema": 1,
        "store_id": store.store_id,
        "binding": store.binding,
        "created_at": now(),
        "sha256": byte_hash(path.read_bytes()),
        "requires_current_independent_authority": True,
    }
    (root / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
    return manifest


def restore(snapshot, destination, *, ledger_dir):
    root, dest = Path(snapshot), Path(destination)
    manifest = json.loads((root / "manifest.json").read_text())
    path = root / "clausegate.sqlite3"
    if manifest.get("schema") != 1 or byte_hash(path.read_bytes()) != manifest["sha256"]:
        raise ValueError("Backup integrity failure")
    if dest.exists():
        raise ValueError("New nonexistent recovery directory required")
    authority.verify(ledger_dir, manifest["store_id"], manifest["binding"])
    with sqlite3.connect(path) as source:
        if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity failure")
        settings = {k: json.loads(v) for k, v in source.execute("SELECT key,value FROM settings")}
        if (
            settings["store_id"] != manifest["store_id"]
            or settings["binding"] != manifest["binding"]
        ):
            raise ValueError("Backup authority binding mismatch")
        dest.mkdir(parents=True)
        with sqlite3.connect(dest / "clausegate.sqlite3") as target:
            source.backup(target)
    store = Store(dest, ledger_dir=ledger_dir)
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        epoch = ident()
        db.execute("UPDATE settings SET value=? WHERE key='epoch'", (canonical(epoch),))
        db.execute("UPDATE settings SET value='true' WHERE key='quarantined'")
        db.execute("DELETE FROM sessions")
        db.execute("DELETE FROM members")
        db.execute(
            "UPDATE jobs SET status='cancelled',lease=NULL,lease_until=NULL,reason='Quarantined restore'"
        )
        for row in db.execute("SELECT payload FROM cases").fetchall():
            c = json.loads(row[0])
            store._verify(db, c["id"])
            if c["state"] != "erased":
                store._invalidate(db, c)
            c["epoch"] = epoch
            store._save(
                db,
                c,
                "operator",
                "store_restored_quarantined",
                {"epoch": epoch, "approvals_reusable": False},
            )
    return {"status": "quarantined", "fresh_authority_and_reviews_required": True}


def provision(directory, ledger_dir, *, username, password):
    store = Store(directory, ledger_dir=ledger_dir)
    if not store.setting("quarantined"):
        raise ValueError("Only a quarantined restored store can be reprovisioned")
    # A fresh operator identity, never a restored password or owner assertion.
    store.add_user(username, password, admin=True)
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        for w in db.execute("SELECT id FROM workspaces").fetchall():
            db.execute("UPDATE workspaces SET owner=? WHERE id=?", (username, w[0]))
            db.execute(
                "INSERT INTO members VALUES(?,?,?,?,NULL)",
                (w[0], username, canonical(["owner", "requester"]), canonical(["*"])),
            )
        db.execute("UPDATE settings SET value='false' WHERE key='quarantined'")
        for row in db.execute("SELECT payload FROM cases").fetchall():
            c = json.loads(row[0])
            c["owner"] = username
            store._save(db, c, "operator", "fresh_authority_provisioned", {"new_owner": username})
    return {"status": "provisioned", "username": username, "reviewer_grants_required": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["backup", "restore", "provision"])
    p.add_argument("path")
    p.add_argument("--data-dir", default="var/clausegate")
    p.add_argument("--ledger-dir", default="var/clausegate-authority")
    p.add_argument("--username")
    args = p.parse_args()
    if args.action == "provision":
        import getpass

        result = provision(
            args.data_dir,
            args.ledger_dir,
            username=args.username,
            password=getpass.getpass("New operator password: "),
        )
    elif args.action == "backup":
        result = backup(Store(args.data_dir, ledger_dir=args.ledger_dir), args.path)
    else:
        result = restore(args.path, args.data_dir, ledger_dir=args.ledger_dir)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
