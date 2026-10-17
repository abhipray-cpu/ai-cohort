"""Independent, identity-bound erasure authority and externally retained audit heads."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from clausegate_api.common import ident, now


@contextmanager
def connection(path):
    db = sqlite3.connect(path, timeout=10, uri=str(path).startswith("file:"))
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize(directory, store_id, expected=None):
    root = Path(directory)
    path = root / "authority.sqlite3"
    if expected:
        return verify(directory, store_id, expected)
    root.mkdir(parents=True, exist_ok=True)
    with connection(path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS stores(id TEXT PRIMARY KEY,nonce TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS erased(store_id TEXT,case_id TEXT,at TEXT,PRIMARY KEY(store_id,case_id));
        CREATE TABLE IF NOT EXISTS anchors(store_id TEXT,case_id TEXT,seq INTEGER,hash TEXT,at TEXT,PRIMARY KEY(store_id,case_id));
        """)
        db.execute("INSERT OR IGNORE INTO metadata VALUES('identity',?)", (ident(),))
        db.execute("INSERT OR IGNORE INTO stores VALUES(?,?)", (store_id, ident()))
        return {
            "identity": db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()[0],
            "nonce": db.execute("SELECT nonce FROM stores WHERE id=?", (store_id,)).fetchone()[0],
        }


def verify(directory, store_id, expected):
    path = Path(directory) / "authority.sqlite3"
    if not path.is_file():
        raise RuntimeError("Current independent authority required")
    try:
        with connection(f"file:{path.resolve()}?mode=ro") as db:
            identity = db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()[0]
            nonce = db.execute("SELECT nonce FROM stores WHERE id=?", (store_id,)).fetchone()[0]
    except (sqlite3.DatabaseError, TypeError) as error:
        raise RuntimeError("Independent authority identity unavailable") from error
    if expected != {"identity": identity, "nonce": nonce}:
        raise RuntimeError("Independent authority identity mismatch")
    return expected


def erase(directory, store_id, expected, cid):
    verify(directory, store_id, expected)
    with connection(Path(directory) / "authority.sqlite3") as db:
        db.execute("INSERT OR IGNORE INTO erased VALUES(?,?,?)", (store_id, cid, now()))


def erased(directory, store_id, expected):
    verify(directory, store_id, expected)
    with connection(Path(directory) / "authority.sqlite3") as db:
        return {
            r[0] for r in db.execute("SELECT case_id FROM erased WHERE store_id=?", (store_id,))
        }


def anchor(directory, store_id, expected, cid, seq, sha):
    verify(directory, store_id, expected)
    with connection(Path(directory) / "authority.sqlite3") as db:
        old = db.execute(
            "SELECT seq FROM anchors WHERE store_id=? AND case_id=?", (store_id, cid)
        ).fetchone()
        if old and old[0] > seq:
            raise ValueError("Audit head rollback")
        db.execute(
            "INSERT OR REPLACE INTO anchors VALUES(?,?,?,?,?)", (store_id, cid, seq, sha, now())
        )


def head(directory, store_id, expected, cid):
    verify(directory, store_id, expected)
    with connection(Path(directory) / "authority.sqlite3") as db:
        row = db.execute(
            "SELECT * FROM anchors WHERE store_id=? AND case_id=?", (store_id, cid)
        ).fetchone()
        return dict(row) if row else None
