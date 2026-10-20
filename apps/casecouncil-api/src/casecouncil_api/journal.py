"""Fsynced usage authority outside SQLite snapshots; not tamper-proof against host admins."""

import json
import os

from .consensus import canonical, digest


def read(path, store_id):
    head = "genesis"
    events = []
    if not path.exists():
        return head, events
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                value = json.loads(line)
                supplied = value.pop("hash")
                if (
                    value["store_id"] != store_id
                    or value["previous"] != head
                    or digest(value) != supplied
                ):
                    raise ValueError("usage journal integrity")
                head = supplied
                events.append(value)
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("usage journal integrity") from exc
    return head, events


def append(db, path, event):
    meta = db.execute("SELECT store_id,journal_head,quarantine FROM meta WHERE id=1").fetchone()
    head, _ = read(path, meta["store_id"])
    if head != meta["journal_head"] or meta["quarantine"]:
        raise ValueError("usage authority mismatch or restore quarantine")
    value = {"store_id": meta["store_id"], "previous": head, **event}
    value["hash"] = digest(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(canonical(value) + "\n")
        f.flush()
        os.fsync(f.fileno())
    db.execute("UPDATE meta SET journal_head=? WHERE id=1", (value["hash"],))


def assert_current(db, path):
    meta = db.execute("SELECT store_id,journal_head,quarantine FROM meta WHERE id=1").fetchone()
    head, events = read(path, meta["store_id"])
    if head != meta["journal_head"] or meta["quarantine"]:
        raise ValueError("usage authority mismatch or quarantine")
    return events
