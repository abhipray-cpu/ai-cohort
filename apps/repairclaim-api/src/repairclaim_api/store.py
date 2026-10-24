"""Transactional SQLite identity/case foundations; no HTTP or external side effects."""

import hashlib
import hmac
import math
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from contracts.repairclaim import CaseSnapshot, Fact

from repairclaim_api.errors import DomainError
from repairclaim_api.features import FeatureStore

SCHEMA = """
CREATE TABLE households(id TEXT PRIMARY KEY);
CREATE TABLE users(
 id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id),
 username TEXT NOT NULL UNIQUE, password_salt TEXT NOT NULL, password_hash TEXT NOT NULL
);
CREATE TABLE sessions(
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
 csrf_hash TEXT NOT NULL, expires REAL NOT NULL
);
CREATE TABLE login_limits(username_key TEXT PRIMARY KEY, failures INTEGER NOT NULL, started REAL NOT NULL);
CREATE TABLE vehicles(
 id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id),
 make TEXT NOT NULL, model TEXT NOT NULL, model_year INTEGER NOT NULL,
 jurisdiction TEXT NOT NULL, UNIQUE(household_id,id)
);
CREATE TABLE cases(
 id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id),
 vehicle_id TEXT NOT NULL, title TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>=1),
 deleted INTEGER NOT NULL CHECK(deleted IN (0,1)), UNIQUE(household_id,id),
 FOREIGN KEY(household_id,vehicle_id) REFERENCES vehicles(household_id,id)
);
CREATE TABLE fact_revisions(
 household_id TEXT NOT NULL, case_id TEXT NOT NULL, revision INTEGER NOT NULL,
 snapshot_json TEXT NOT NULL, actor_id TEXT NOT NULL REFERENCES users(id), created REAL NOT NULL,
 PRIMARY KEY(household_id,case_id,revision),
 FOREIGN KEY(household_id,case_id) REFERENCES cases(household_id,id)
);
CREATE TABLE grants(
 household_id TEXT NOT NULL, case_id TEXT NOT NULL, user_id TEXT NOT NULL REFERENCES users(id),
 role TEXT NOT NULL CHECK(role IN ('viewer','editor')), expires REAL NOT NULL,
 PRIMARY KEY(household_id,case_id,user_id),
 FOREIGN KEY(household_id,case_id) REFERENCES cases(household_id,id)
);
CREATE TABLE audit(
 id INTEGER PRIMARY KEY AUTOINCREMENT, household_id TEXT NOT NULL, case_id TEXT NOT NULL,
 actor_id TEXT NOT NULL REFERENCES users(id), action TEXT NOT NULL, revision INTEGER NOT NULL,
 created REAL NOT NULL,
 FOREIGN KEY(household_id,case_id) REFERENCES cases(household_id,id)
);
CREATE INDEX cases_household ON cases(household_id,deleted);
CREATE INDEX grants_user ON grants(user_id,expires);
PRAGMA user_version=1;
PRAGMA application_id=0x52504331;
"""


def _id():
    return uuid4().hex


def _digest(value: str):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _password(password: str, salt: str):
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt),
        n=32768,
        r=8,
        p=1,
        maxmem=64 * 1024 * 1024,
    ).hex()


@dataclass(frozen=True)
class LoginSession:
    token: str = field(repr=False)
    csrf_token: str = field(repr=False)
    expires_at: float


class Store(FeatureStore):
    def __init__(self, path: Path, *, clock=time.time):
        self.path = Path(path)
        self.clock = clock
        if self.path.is_symlink():
            raise DomainError("invalid_store_path")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.path.exists():
            # Restrict newly created state without changing permissions of pre-existing user files.
            try:
                with self.path.open("xb"):
                    pass
                self.path.chmod(0o600)
            except FileExistsError:
                pass
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            application_id = db.execute("PRAGMA application_id").fetchone()[0]
            if application_id not in {0, 0x52504331} or (
                version != 0 and application_id != 0x52504331
            ):
                raise DomainError("foreign_store", 503)
            if version not in {0, 1}:
                raise DomainError("unsupported_schema", 503)
            if version == 0:
                if db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                    raise DomainError("foreign_store", 503)
                for statement in SCHEMA.split(";"):
                    if statement.strip():
                        db.execute(statement)
            db.commit()
            db.execute("PRAGMA journal_mode=WAL")
        self._features_init()

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:

            def materialize(cursor, values):
                from cryptography.fernet import Fernet, InvalidToken

                decoded = list(values)
                for index, value in enumerate(values):
                    if (
                        cursor.description[index][0] in {"data", "snapshot_json", "title"}
                        and isinstance(value, str)
                        and value.startswith("RCV1:")
                    ):
                        _, case_id, ciphertext = value.split(":", 2)
                        key_row = db.execute(
                            "SELECT wrapped_key FROM rc_case_keys WHERE case_id=?", (case_id,)
                        ).fetchone()
                        if key_row is None:
                            raise DomainError("erased_record", 404)
                        try:
                            key = self.content_cipher.decrypt(key_row[0])
                            decoded[index] = (
                                Fernet(key).decrypt(ciphertext.encode()).decode("utf-8")
                            )
                        except (InvalidToken, ValueError) as error:
                            raise DomainError("private_record_corrupt", 503) from error
                return sqlite3.Row(cursor, tuple(decoded))

            db.row_factory = materialize
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA secure_delete=ON")
            yield db
        finally:
            db.close()

    @contextmanager
    def _transaction(self):
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def _now(self):
        value = self.clock()
        if type(value) not in (float, int) or not math.isfinite(value):
            raise DomainError("invalid_clock", 503)
        return value

    @staticmethod
    def _credentials(username, password, *, provisioning=False):
        if (
            type(username) is not str
            or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}", username)
            or type(password) is not str
            or not 1 <= len(password.encode("utf-8")) <= 256
            or (provisioning and (len(password) < 12 or not password.strip()))
        ):
            raise DomainError(
                "invalid_credentials" if provisioning else "authentication_failed",
                400 if provisioning else 401,
            )
        return username.lower()

    def provision_owner(self, username: str, password: str):
        """Operator-only enrollment primitive. Never expose as an unauthenticated public route."""
        username = self._credentials(username, password, provisioning=True)
        salt, user_id, household = secrets.token_hex(16), _id(), _id()
        encoded = _password(password, salt)
        with self._transaction() as db:
            if db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
                raise DomainError("account_exists", 409)
            db.execute("INSERT INTO households VALUES(?)", (household,))
            db.execute(
                "INSERT INTO users VALUES(?,?,?,?,?)", (user_id, household, username, salt, encoded)
            )
        return {"id": user_id, "household_id": household, "username": username}

    def login(self, username: str, password: str) -> LoginSession:
        username = self._credentials(username, password)
        now, key = self._now(), _digest(username)
        with self._transaction() as db:
            if db.execute("SELECT value FROM rc_meta WHERE key='quarantined'").fetchone()[0] == "1":
                raise DomainError("restore_quarantined", 503)
            limit = db.execute("SELECT * FROM login_limits WHERE username_key=?", (key,)).fetchone()
            if limit and now - limit["started"] < 900 and limit["failures"] >= 5:
                raise DomainError("rate_limited", 429)
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            salt = user["password_salt"] if user else "0" * 32
            encoded = _password(password, salt)
            if user is None or not secrets.compare_digest(encoded, user["password_hash"]):
                if limit and now - limit["started"] < 900:
                    db.execute(
                        "UPDATE login_limits SET failures=failures+1 WHERE username_key=?", (key,)
                    )
                else:
                    db.execute("INSERT OR REPLACE INTO login_limits VALUES(?,1,?)", (key, now))
                # Failed attempts must persist despite the safe error returned to the caller.
                db.commit()
                raise DomainError("authentication_failed", 401)
            db.execute("DELETE FROM login_limits WHERE username_key=?", (key,))
            token, expiry = secrets.token_urlsafe(32), now + 8 * 3600
            csrf = hmac.new(self.csrf_secret, token.encode(), hashlib.sha256).hexdigest()
            db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?)",
                (_digest(token), user["id"], _digest(csrf), expiry),
            )
            return LoginSession(token, csrf, expiry)

    def _actor(self, db, token):
        if db.execute("SELECT value FROM rc_meta WHERE key='quarantined'").fetchone()[0] == "1":
            raise DomainError("restore_quarantined", 503)
        if type(token) is not str or not 20 <= len(token) <= 128:
            raise DomainError("authentication_required", 401)
        actor = db.execute(
            "SELECT u.id,u.household_id,u.username,s.csrf_hash FROM users u JOIN sessions s "
            "ON s.user_id=u.id WHERE s.token_hash=? AND s.expires>?",
            (_digest(token), self._now()),
        ).fetchone()
        if actor is None:
            raise DomainError("authentication_required", 401)
        return actor

    def authenticate(self, token):
        with self._transaction() as db:
            actor = self._actor(db, token)
            return {key: actor[key] for key in ("id", "household_id", "username")}

    def check_csrf(self, token, csrf):
        with self._transaction() as db:
            actor = self._actor(db, token)
            if (
                type(csrf) is not str
                or len(csrf) > 128
                or not secrets.compare_digest(actor["csrf_hash"], _digest(csrf))
            ):
                raise DomainError("csrf_failed", 403)

    def csrf_token(self, token):
        with self._transaction() as db:
            actor = self._actor(db, token)
            value = hmac.new(self.csrf_secret, token.encode(), hashlib.sha256).hexdigest()
            if not secrets.compare_digest(actor["csrf_hash"], _digest(value)):
                raise DomainError("reauthentication_required", 401)
            return value

    def logout(self, token):
        with self._transaction() as db:
            self._actor(db, token)
            db.execute("DELETE FROM sessions WHERE token_hash=?", (_digest(token),))

    def create_vehicle(self, token, *, make, model, model_year, jurisdiction):
        facts = tuple(
            Fact(field=key, value=value, status="user_reported")
            for key, value in (("make", make), ("model", model), ("model_year", model_year))
        )
        CaseSnapshot(case_id="validation", revision=1, jurisdiction=jurisdiction, facts=facts)
        with self._transaction() as db:
            actor, vehicle_id = self._actor(db, token), _id()
            db.execute(
                "INSERT INTO vehicles VALUES(?,?,?,?,?,?)",
                (vehicle_id, actor["household_id"], make, model, model_year, jurisdiction),
            )
            return {
                "id": vehicle_id,
                "make": make,
                "model": model,
                "model_year": model_year,
                "jurisdiction": jurisdiction,
            }

    def _case(self, db, actor, case_id, action="read"):
        row = db.execute(
            "SELECT c.*,v.jurisdiction FROM cases c JOIN vehicles v "
            "ON v.household_id=c.household_id AND v.id=c.vehicle_id "
            "WHERE c.id=? AND c.deleted=0",
            (case_id,),
        ).fetchone()
        if (
            row is None
            or self._erased(case_id)
            or (row["retention_until"] and row["retention_until"] <= self._now())
        ):
            raise DomainError("not_found", 404)
        role = "owner" if row["household_id"] == actor["household_id"] else None
        if role is None:
            grant = db.execute(
                "SELECT role FROM grants WHERE household_id=? AND case_id=? "
                "AND user_id=? AND expires>?",
                (row["household_id"], case_id, actor["id"], self._now()),
            ).fetchone()
            role = grant["role"] if grant else None
        allowed = {
            "read": {"owner", "editor", "viewer"},
            "edit": {"owner", "editor"},
            "owner": {"owner"},
        }
        if role not in allowed.get(action, set()):
            raise DomainError("not_found", 404)
        if action == "edit" and row["lifecycle"] in {"paused", "closed"}:
            raise DomainError("case_" + row["lifecycle"], 409)
        return {**dict(row), "role": role}

    def _audit(self, db, actor, case, action):
        if action in {
            "facts_replaced",
            "document_facts_confirmed",
            "fact_corrected_with_history",
            "document_uploaded",
            "case_fact_review",
            "response_recorded",
            "outcome_recorded",
        }:
            db.execute(
                "UPDATE cases SET retention_until=? WHERE id=?",
                (self._now() + 180 * 86400, case["id"]),
            )
        db.execute(
            "INSERT INTO audit(household_id,case_id,actor_id,action,revision,created) "
            "VALUES(?,?,?,?,?,?)",
            (case["household_id"], case["id"], actor["id"], action, case["revision"], self._now()),
        )

    def create_case(self, token, vehicle_id, title):
        if type(title) is not str or not 1 <= len(title.strip()) <= 200:
            raise DomainError("invalid_title")
        with self._transaction() as db:
            actor = self._actor(db, token)
            vehicle = db.execute(
                "SELECT * FROM vehicles WHERE id=? AND household_id=?",
                (vehicle_id, actor["household_id"]),
            ).fetchone()
            if vehicle is None:
                raise DomainError("not_found", 404)
            if (
                db.execute(
                    "SELECT COUNT(*) FROM cases WHERE household_id=? AND deleted=0",
                    (actor["household_id"],),
                ).fetchone()[0]
                >= 10
            ):
                raise DomainError("case_limit", 409)
            case_id = _id()
            db.execute(
                "INSERT INTO cases(id,household_id,vehicle_id,title,revision,deleted) VALUES(?,?,?,?,1,0)",
                (case_id, actor["household_id"], vehicle_id, title),
            )
            snapshot = CaseSnapshot(
                case_id=case_id,
                revision=1,
                jurisdiction=vehicle["jurisdiction"],
                facts=tuple(
                    Fact(field=key, value=vehicle[key], status="user_reported")
                    for key in ("make", "model", "model_year")
                ),
            )
            self._save_snapshot(db, actor, snapshot)
            db.execute(
                "UPDATE cases SET title=? WHERE id=?",
                (self._private_encode(db, case_id, title), case_id),
            )
            db.execute(
                "UPDATE cases SET retention_until=? WHERE id=?",
                (self._now() + 180 * 86400, case_id),
            )
            case = self._case(db, actor, case_id)
            self._audit(db, actor, case, "case_created")
            return case

    def _save_snapshot(self, db, actor, snapshot):
        household = db.execute(
            "SELECT household_id FROM cases WHERE id=?", (snapshot.case_id,)
        ).fetchone()[0]
        db.execute(
            "INSERT INTO fact_revisions VALUES(?,?,?,?,?,?)",
            (
                household,
                snapshot.case_id,
                snapshot.revision,
                self._private_encode(db, snapshot.case_id, snapshot.model_dump_json()),
                actor["id"],
                self._now(),
            ),
        )

    def get_case(self, token, case_id):
        with self._transaction() as db:
            return self._case(db, self._actor(db, token), case_id)

    def list_cases(self, token):
        with self._transaction() as db:
            actor = self._actor(db, token)
            ids = db.execute(
                "SELECT c.id FROM cases c WHERE c.deleted=0 AND (c.household_id=? "
                "OR EXISTS(SELECT 1 FROM grants g WHERE g.household_id=c.household_id "
                "AND g.case_id=c.id AND g.user_id=? AND g.expires>?)) ORDER BY c.id",
                (actor["household_id"], actor["id"], self._now()),
            ).fetchall()
            result = []
            for row in ids:
                try:
                    result.append(self._case(db, actor, row["id"]))
                except DomainError as error:
                    if error.status != 404:
                        raise
            return result

    def snapshot(self, token, case_id, *, revision=None):
        with self._transaction() as db:
            case = self._case(db, self._actor(db, token), case_id)
            row = db.execute(
                "SELECT snapshot_json FROM fact_revisions WHERE household_id=? "
                "AND case_id=? AND revision=?",
                (case["household_id"], case_id, revision or case["revision"]),
            ).fetchone()
            if row is None:
                raise DomainError("not_found", 404)
            return CaseSnapshot.model_validate_json(row[0])

    @staticmethod
    def _revision(case, expected):
        if type(expected) is not int or expected != case["revision"]:
            raise DomainError("revision_conflict", 409)

    def replace_facts(self, token, case_id, expected_revision, facts):
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "edit")
            self._revision(case, expected_revision)
            snapshot = CaseSnapshot(
                case_id=case_id,
                revision=case["revision"] + 1,
                jurisdiction=case["jurisdiction"],
                facts=facts,
            )
            if any(
                f.anchor is not None
                or f.status not in {"user_reported", "confirmed", "conflicting"}
                for f in snapshot.facts
            ):
                raise DomainError("manual_fact_authority")
            db.execute(
                "UPDATE cases SET revision=? WHERE household_id=? AND id=?",
                (snapshot.revision, case["household_id"], case_id),
            )
            self._save_snapshot(db, actor, snapshot)
            case["revision"] = snapshot.revision
            self._invalidate(db, case_id)
            self._audit(db, actor, case, "facts_replaced")
            return case

    def grant(self, token, case_id, user_id, role, *, ttl=86400):
        if (
            role not in {"viewer", "editor"}
            or type(ttl) not in (int, float)
            or not 0 < ttl <= 90 * 86400
        ):
            raise DomainError("invalid_grant")
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "owner")
            target = db.execute("SELECT household_id FROM users WHERE id=?", (user_id,)).fetchone()
            if target is None or target[0] == case["household_id"]:
                raise DomainError("invalid_grant")
            db.execute(
                "INSERT OR REPLACE INTO grants VALUES(?,?,?,?,?)",
                (case["household_id"], case_id, user_id, role, self._now() + ttl),
            )
            self._audit(db, actor, case, "grant_changed")

    def revoke_grant(self, token, case_id, user_id):
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "owner")
            db.execute(
                "DELETE FROM grants WHERE household_id=? AND case_id=? AND user_id=?",
                (case["household_id"], case_id, user_id),
            )
            self._audit(db, actor, case, "grant_revoked")

    def delete_case(self, token, case_id, expected_revision):
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "owner")
            self._revision(case, expected_revision)
            self._erase_features(db, case)
            db.execute(
                "DELETE FROM grants WHERE household_id=? AND case_id=?",
                (case["household_id"], case_id),
            )
            db.execute(
                "DELETE FROM fact_revisions WHERE household_id=? AND case_id=?",
                (case["household_id"], case_id),
            )
            db.execute(
                "UPDATE cases SET deleted=1,title='',revision=revision+1 WHERE household_id=? AND id=?",
                (case["household_id"], case_id),
            )
            case["revision"] += 1
            self._audit(db, actor, case, "case_deleted")

    def timeline(self, token, case_id):
        with self._transaction() as db:
            case = self._case(db, self._actor(db, token), case_id)
            return [
                {
                    **dict(row),
                    "actor_kind": "system_on_behalf_of_owner"
                    if row["action"] == "reminder_due"
                    else "user_or_authorized_job",
                }
                for row in db.execute(
                    "SELECT id,actor_id,action,revision,created FROM audit WHERE household_id=? "
                    "AND case_id=? ORDER BY id",
                    (case["household_id"], case_id),
                )
            ]
