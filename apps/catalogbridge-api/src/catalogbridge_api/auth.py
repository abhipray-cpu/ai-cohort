"""Local scoped identities, expiring hashed sessions and live grant checks."""

import hashlib
import hmac
import secrets
import time


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 210000).hex()


def add_user(store, name, password, workspace, role):
    if (
        not 1 <= len(name) <= 100
        or len(password) < 12
        or role not in {"owner", "operator", "reviewer", "auditor"}
    ):
        raise ValueError("invalid user or password (minimum 12 characters)")
    salt = secrets.token_hex(16)
    with store.write() as db:
        if db.execute("SELECT 1 FROM users WHERE name=?", (name,)).fetchone():
            raise ValueError("existing user cannot be overwritten")
        db.execute(
            "INSERT INTO users VALUES(?,?,?,?,?)",
            (name, salt, password_hash(password, salt), workspace, role),
        )


def login(store, name, password):
    with store.write() as db:
        row = db.execute("SELECT * FROM users WHERE name=?", (name,)).fetchone()
        salt = row["salt"] if row else "00" * 16
        checked = password_hash(password, salt)
        if not row or not hmac.compare_digest(row["hash"], checked):
            return None
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
        db.execute(
            "INSERT INTO sessions VALUES(?,?,?,?)",
            (hashlib.sha256(token.encode()).hexdigest(), name, csrf, time.time() + 28800),
        )
        return token, csrf


def session(store, token):
    hashed = hashlib.sha256(token.encode()).hexdigest()
    with store.connect() as db:
        row = db.execute(
            "SELECT users.name,users.workspace,users.role,sessions.csrf FROM sessions JOIN users ON users.name=sessions.name WHERE sessions.token=? AND sessions.expires>?",
            (hashed, time.time()),
        ).fetchone()
    return dict(row) if row else None
