"""Consistent SQLite snapshot; restore only to a new directory with workers stopped."""

import sqlite3
from pathlib import Path


def backup(root, destination):
    source = Path(root) / "buildrelay.sqlite3"
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb"):
        pass
    with (
        sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True) as src,
        sqlite3.connect(destination) as dst,
    ):
        src.backup(dst)
        if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("snapshot failed integrity check")
    return destination


def restore(source, destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(source)
    with sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True) as src:
        if src.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("corrupt backup")
        src.execute("SELECT count(*) FROM events").fetchone()
        destination.mkdir(parents=True)
        with sqlite3.connect(destination / "buildrelay.sqlite3") as dst:
            src.backup(dst)
            dst.execute("DELETE FROM sessions")
            dst.execute(
                "UPDATE events SET state='retry',lease_token=NULL,lease_until=0,due=0 WHERE state='processing'"
            )
    return destination
