"""Consistent SQLite backups containing every source snapshot and export."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from propertybrief_api.sources import digest, now


def checksum(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify(db_path):
    with sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Database integrity check failed")
        for payload, expected in db.execute("SELECT payload_json,sha256 FROM snapshots"):
            if digest(json.loads(payload)["raw"]) != expected:
                raise ValueError("Evidence hash mismatch")


def backup(source_dir, destination):
    source = Path(source_dir) / "propertybrief.sqlite3"
    target = Path(destination)
    if not source.is_file() or target.exists():
        raise ValueError("Choose an existing database and a new backup directory")
    target.mkdir(parents=True)
    output_path = target / "propertybrief.sqlite3"
    with (
        sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as original,
        sqlite3.connect(output_path) as copied,
    ):
        original.backup(copied)
    verify(output_path)
    manifest = {"created_at": now(), "schema": 1, "sha256": checksum(output_path)}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def restore(source_dir, destination):
    source = Path(source_dir) / "propertybrief.sqlite3"
    target = Path(destination)
    if not source.is_file() or target.exists():
        raise ValueError("Choose an existing backup and a new restore directory")
    manifest = json.loads((Path(source_dir) / "manifest.json").read_text(encoding="utf-8"))
    if checksum(source) != manifest["sha256"]:
        raise ValueError("Backup file hash mismatch")
    verify(source)
    target.mkdir(parents=True)
    with (
        sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as original,
        sqlite3.connect(target / "propertybrief.sqlite3") as copied,
    ):
        original.backup(copied)
        # Restoring a backup must not revive stale worker ownership.
        copied.execute("UPDATE runs SET lease_until='2000-01-01' WHERE status='running'")
    verify(target / "propertybrief.sqlite3")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    (backup if args.action == "backup" else restore)(args.source, args.destination)
    print("Verified PropertyBrief backup/restore completed.")


if __name__ == "__main__":
    main()
