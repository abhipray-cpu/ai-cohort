"""Restore a ResolveDesk backup into a NEW directory, never overwrite live data."""

import argparse
import hashlib
import sqlite3
from pathlib import Path


def restore(source_dir, destination):
    source = Path(source_dir) / "resolvedesk.sqlite3"
    target = Path(destination)
    if not source.is_file() or target.exists():
        raise ValueError("Choose an existing backup and a new destination directory")
    with sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as backup:
        if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Backup failed SQLite integrity check")
        for text, digest in backup.execute("SELECT text,sha256 FROM sources"):
            if hashlib.sha256(text.encode()).hexdigest() != digest:
                raise ValueError("Backup source content hash mismatch")
        target.mkdir(parents=True)
        with sqlite3.connect(target / "resolvedesk.sqlite3") as output:
            backup.backup(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup")
    parser.add_argument("destination")
    args = parser.parse_args()
    restore(args.backup, args.destination)
    print("Restored and verified source hashes. Start an isolated API to inspect reviewed replies.")


if __name__ == "__main__":
    main()
