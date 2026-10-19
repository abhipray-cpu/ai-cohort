"""Expiring, hashed sessions with live client grants and CSRF protection."""

import hashlib
import hmac
import secrets
import time


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 310000).hex()


def add_user(store, name, password, role, clients=()):
    if (
        not name.strip()
        or len(name) > 100
        or len(password) < 12
        or role not in {"owner", "operator", "viewer"}
    ):
        raise ValueError("invalid identity; password must have at least 12 characters")
    salt = secrets.token_hex(16)
    hashed = password_hash(password, salt)
    with store.write() as db:
        for client in clients:
            if not db.execute("SELECT 1 FROM clients WHERE id=?", (client,)).fetchone():
                raise ValueError("unknown client grant")
        db.execute("INSERT INTO users VALUES(?,?,?,?)", (name, salt, hashed, role))
        db.executemany("INSERT INTO grants VALUES(?,?)", [(name, c) for c in set(clients)])


def login(store, name, password):
    with store.connect() as db:
        row = db.execute("SELECT * FROM users WHERE name=?", (name,)).fetchone()
    checked = password_hash(password, row["salt"] if row else "00" * 16)
    if not row or not hmac.compare_digest(row["hash"], checked):
        return None
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with store.write() as db:
        db.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
        db.execute(
            "INSERT INTO sessions VALUES(?,?,?,?)",
            (hashlib.sha256(token.encode()).hexdigest(), name, csrf, time.time() + 28800),
        )
    return token, csrf


def session(store, token):
    with store.connect() as db:
        row = db.execute(
            "SELECT users.name,users.role,sessions.csrf FROM sessions JOIN users ON users.name=sessions.name WHERE token=? AND expires>?",
            (hashlib.sha256(token.encode()).hexdigest(), time.time()),
        ).fetchone()
        if not row:
            return None
        return dict(row) | {
            "clients": [
                r[0]
                for r in db.execute("SELECT client_id FROM grants WHERE name=?", (row["name"],))
            ]
        }
