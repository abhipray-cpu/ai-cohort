"""Consistent backup/restore with hash verification and publication quarantine."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from patchdesk_api.common import digest, now


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Database integrity check failed")
        for payload, expected in db.execute("SELECT payload,sha256 FROM objects"):
            if digest(json.loads(payload)) != expected:
                raise ValueError("Evidence object hash mismatch")
        for payload, expected in db.execute("SELECT payload,payload_hash FROM publications"):
            if digest(json.loads(payload)) != expected:
                raise ValueError("Publication payload hash mismatch")


def backup(source, destination):
    original = Path(source) / "patchdesk.sqlite3"
    target = Path(destination)
    if not original.is_file() or target.exists():
        raise ValueError("Choose an existing store and a new backup directory")
    target.mkdir(parents=True)
    copied = target / "patchdesk.sqlite3"
    with (
        sqlite3.connect(original.resolve().as_uri() + "?mode=ro", uri=True) as live,
        sqlite3.connect(copied) as output,
    ):
        live.backup(output)
    verify(copied)
    (target / "manifest.json").write_text(
        json.dumps({"schema": 1, "created_at": now(), "sha256": file_hash(copied)}, indent=2),
        encoding="utf-8",
    )


def restore(source, destination):
    original = Path(source) / "patchdesk.sqlite3"
    target = Path(destination)
    if target.exists():
        raise ValueError("Restore refuses existing destination")
    manifest = json.loads((Path(source) / "manifest.json").read_text(encoding="utf-8"))
    if file_hash(original) != manifest["sha256"]:
        raise ValueError("Backup hash mismatch")
    verify(original)
    target.mkdir(parents=True)
    with (
        sqlite3.connect(original.resolve().as_uri() + "?mode=ro", uri=True) as copied,
        sqlite3.connect(target / "patchdesk.sqlite3") as restored,
    ):
        copied.backup(restored)
        restored.execute("DELETE FROM sessions")
        restored.execute("UPDATE runs SET lease_until='2000-01-01' WHERE status='running'")
        restored.execute(
            "UPDATE publications SET status='quarantined',approved_by=NULL,expires=NULL,revision=revision+1 WHERE status IN ('approved','sending','outcome_unknown')"
        )
        restored.execute("INSERT OR REPLACE INTO settings VALUES('publisher_quarantine','true')")
    verify(target / "patchdesk.sqlite3")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    (backup if args.action == "backup" else restore)(args.source, args.destination)
    print("Verified PatchDesk backup/restore completed; restore publisher is quarantined.")


if __name__ == "__main__":
    main()
