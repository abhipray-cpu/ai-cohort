"""Non-destructive new-directory snapshots and quarantined restore."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

from .store import Store, uid


def backup(store: Store, destination):
    target = Path(destination)
    if target.exists():
        raise ValueError("backup destination exists")
    target.mkdir(parents=True)
    with store.connect() as source, sqlite3.connect(target / "catalogbridge.sqlite3") as output:
        source.backup(output)
    data = (target / "catalogbridge.sqlite3").read_bytes()
    manifest = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "identity": store.identity,
        "usage_journal_included": False,
        "restore_requires_current_journal": True,
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def restore(snapshot, destination, journal_dir):
    source, target, journal = Path(snapshot), Path(destination), Path(journal_dir)
    if target.exists():
        raise ValueError("restore destination exists")
    if not (journal / "liabilities.sqlite3").is_file():
        raise ValueError("current usage journal required")
    manifest = json.loads((source / "manifest.json").read_text())
    if (
        hashlib.sha256((source / "catalogbridge.sqlite3").read_bytes()).hexdigest()
        != manifest["sha256"]
    ):
        raise ValueError("snapshot integrity failure")
    target.mkdir(parents=True)
    shutil.copyfile(source / "catalogbridge.sqlite3", target / "catalogbridge.sqlite3")
    store = Store(target, journal)
    with store.write() as db:
        db.execute("DELETE FROM sessions")
        db.execute("UPDATE tasks SET review=NULL,lease=NULL,state='failed',revision=revision+1")
        db.execute("UPDATE batches SET state='partial'")
        db.execute("INSERT OR REPLACE INTO meta VALUES('restore_epoch',?)", (uid(),))
        db.execute("INSERT OR REPLACE INTO meta VALUES('restore_quarantine','true')")
        store.event(db, None, "restored_quarantined", {"identity": store.identity})
    return target
