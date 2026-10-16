"""Scoped SQLite persistence, session auth, fenced jobs and immutable evidence/reports."""

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from patchdesk_api.common import digest, identifier, now
from patchdesk_api.inventory import NAME, parse_inventory


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()


class Store:
    def __init__(self, directory):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "patchdesk.sqlite3"
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,salt TEXT NOT NULL,password_hash TEXT NOT NULL,admin INTEGER NOT NULL,disabled INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,username TEXT NOT NULL,csrf TEXT NOT NULL,expires TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS login_attempts(username TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT,client TEXT,owner TEXT,revision INTEGER DEFAULT 1,policy TEXT,latest_input TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS memberships(project_id TEXT,username TEXT,roles TEXT,PRIMARY KEY(project_id,username));
            CREATE TABLE IF NOT EXISTS objects(id TEXT PRIMARY KEY,kind TEXT,project_id TEXT,payload TEXT,sha256 TEXT,revision INTEGER DEFAULT 1,reviewed_by TEXT,notes TEXT DEFAULT '',created_at TEXT);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,project_id TEXT,actor TEXT,input_id TEXT,question TEXT,idempotency_key TEXT,request_hash TEXT,status TEXT,registry TEXT,results TEXT DEFAULT '{}',state TEXT DEFAULT '{}',created_at TEXT,deadline TEXT,lease TEXT,lease_until TEXT,actions INTEGER DEFAULT 0,model_calls INTEGER DEFAULT 0,http_attempts INTEGER DEFAULT 0,acquired_bytes INTEGER DEFAULT 0,bases TEXT DEFAULT '{}',grant INTEGER DEFAULT 1,cancelled INTEGER DEFAULT 0,stop_reason TEXT,report_id TEXT,UNIQUE(project_id,idempotency_key));
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,run_id TEXT,project_id TEXT,stage TEXT,outcome TEXT,detail TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
            CREATE TABLE IF NOT EXISTS resume_keys(run_id TEXT,key TEXT,PRIMARY KEY(run_id,key));
            CREATE TABLE IF NOT EXISTS publications(id TEXT PRIMARY KEY,project_id TEXT,report_id TEXT,report_revision INTEGER,payload TEXT,payload_hash TEXT,policy_revision INTEGER,revision INTEGER DEFAULT 1,status TEXT DEFAULT 'draft',approved_by TEXT,expires TEXT,receipt TEXT,created_at TEXT);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def add_user(self, username, password, admin=False):
        if not username or len(username) > 80 or len(password) < 12 or password == "replace-me":
            raise ValueError("Use a username and a password of at least 12 characters")
        salt = secrets.token_hex(16)
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO users(username,salt,password_hash,admin) VALUES(?,?,?,?)",
                    (username, salt, password_hash(password, salt), int(admin)),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("User already exists") from error

    def user(self, username):
        with self.connect() as db:
            row = db.execute(
                "SELECT username,admin,disabled FROM users WHERE username=?", (username,)
            ).fetchone()
        if not row or row["disabled"]:
            raise PermissionError("Unknown or disabled actor")
        return dict(row)

    def login(self, username, password):
        cutoff = (datetime.now(UTC) - timedelta(minutes=15)).isoformat()
        with self.connect() as db:
            if (
                db.execute(
                    "SELECT COUNT(*) FROM login_attempts WHERE username=? AND created_at>?",
                    (username, cutoff),
                ).fetchone()[0]
                >= 5
            ):
                raise PermissionError("Login temporarily limited")
            row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            valid = secrets.compare_digest(
                password_hash(password, row["salt"] if row else "invalid-user-salt"),
                row["password_hash"] if row else "0" * 64,
            )
            if not row or row["disabled"] or not valid:
                db.execute("INSERT INTO login_attempts VALUES(?,?)", (username, now()))
            else:
                token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                db.execute("DELETE FROM login_attempts WHERE username=?", (username,))
                db.execute(
                    "INSERT INTO sessions VALUES(?,?,?,?)",
                    (
                        digest(token),
                        username,
                        csrf,
                        (datetime.now(UTC) + timedelta(hours=8)).isoformat(),
                    ),
                )
                return {
                    "token": token,
                    "csrf": csrf,
                    "username": username,
                    "admin": bool(row["admin"]),
                }
        raise PermissionError("Invalid credentials")

    def authenticate(self, token):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM sessions WHERE token_hash=? AND expires>?", (digest(token), now())
            ).fetchone()
        if not row:
            raise PermissionError("Sign in required")
        return {**self.user(row["username"]), "csrf": row["csrf"]}

    def logout(self, token):
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (digest(token),))

    def create_project(self, actor, value):
        self.user(actor)
        pid = identifier()
        policy = {
            "public_packages": [],
            "model_egress": False,
            "repository": "",
            "repository_id": None,
            "node_version": "",
            "connector_epoch": "default",
        }
        with self.connect() as db:
            db.execute(
                "INSERT INTO projects(id,name,client,owner,policy,created_at) VALUES(?,?,?,?,?,?)",
                (pid, value.name, value.client, actor, json.dumps(policy), now()),
            )
            db.execute(
                "INSERT INTO memberships VALUES(?,?,?)",
                (pid, actor, json.dumps(["analyst", "reviewer", "publisher"])),
            )
        return self.project(actor, pid)

    def scope(self, actor, pid, role=None):
        self.user(actor)
        with self.connect() as db:
            row = db.execute(
                "SELECT p.*,m.roles FROM projects p JOIN memberships m ON p.id=m.project_id WHERE p.id=? AND m.username=?",
                (pid, actor),
            ).fetchone()
        if not row:
            raise PermissionError("Project access denied")
        result = dict(row)
        result["roles"] = json.loads(result["roles"])
        if not result["roles"]:
            raise PermissionError("Project membership revoked")
        result["policy"] = json.loads(result["policy"])
        if role and role not in result["roles"]:
            raise PermissionError(f"Project {role} permission required")
        return result

    def project(self, actor, pid):
        result = self.scope(actor, pid)
        with self.connect() as db:
            result["inputs"] = [
                {k: r[k] for k in ("id", "created_at", "sha256")}
                for r in db.execute(
                    "SELECT * FROM objects WHERE project_id=? AND kind='input' ORDER BY created_at DESC",
                    (pid,),
                )
            ]
            result["runs"] = [
                dict(r)
                for r in db.execute(
                    "SELECT id,status,question,actions,model_calls,created_at,stop_reason FROM runs WHERE project_id=? ORDER BY created_at DESC LIMIT 40",
                    (pid,),
                )
            ]
            result["members"] = [
                {"username": r[0], "roles": json.loads(r[1])}
                for r in db.execute(
                    "SELECT username,roles FROM memberships WHERE project_id=?", (pid,)
                )
            ]
        return result

    def projects(self, actor):
        self.user(actor)
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT p.id,p.name,p.client,p.revision,p.latest_input FROM projects p JOIN memberships m ON p.id=m.project_id WHERE m.username=? AND m.roles!='[]' ORDER BY p.created_at DESC",
                    (actor,),
                )
            ]

    def set_membership(self, actor, pid, username, roles):
        project = self.scope(actor, pid)
        if project["owner"] != actor:
            raise PermissionError("Only project owner manages membership")
        self.user(username)
        if not set(roles).issubset({"analyst", "reviewer", "publisher"}):
            raise ValueError("Invalid role")
        if username == actor and not roles:
            raise ValueError("Project owner cannot remove their final role")
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO memberships VALUES(?,?,?)",
                (pid, username, json.dumps(roles)),
            )
            db.execute("UPDATE projects SET revision=revision+1 WHERE id=?", (pid,))

    def update_policy(self, actor, pid, value):
        project = self.scope(actor, pid)
        if project["owner"] != actor:
            raise PermissionError("Only project owner changes egress policy")
        if any(not NAME.fullmatch(name) for name in value.public_packages):
            raise ValueError("Invalid package identity")
        payload = value.model_dump(exclude={"expected_revision"})
        with self.connect() as db:
            changed = db.execute(
                "UPDATE projects SET policy=?,revision=revision+1 WHERE id=? AND revision=?",
                (json.dumps(payload), pid, value.expected_revision),
            ).rowcount
            if not changed:
                raise ValueError("Stale policy revision")
        return self.project(actor, pid)

    def put_object(self, kind, pid, payload, db=None):
        oid = identifier()
        values = (oid, kind, pid, json.dumps(payload), digest(payload), now())
        if db is not None:
            db.execute(
                "INSERT INTO objects(id,kind,project_id,payload,sha256,created_at) VALUES(?,?,?,?,?,?)",
                values,
            )
        else:
            with self.connect() as connection:
                connection.execute(
                    "INSERT INTO objects(id,kind,project_id,payload,sha256,created_at) VALUES(?,?,?,?,?,?)",
                    values,
                )
        return oid

    def _object(self, oid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM objects WHERE id=?", (oid,)).fetchone()
        if not row:
            raise ValueError("Artifact not found")
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        if digest(result["payload"]) != result["sha256"]:
            raise ValueError("Artifact integrity failure")
        return result

    def object(self, actor, oid):
        result = self._object(oid)
        self.scope(actor, result["project_id"])
        return result

    def import_input(self, actor, pid, value):
        self.scope(actor, pid, "analyst")
        if (
            len(json.dumps(value.manifest).encode()) > 10 * 1024**2
            or len(json.dumps(value.lockfile).encode()) > 10 * 1024**2
        ):
            raise ValueError("Input byte limit exceeded")
        inventory = parse_inventory(value.manifest, value.lockfile)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            oid = self.put_object("input", pid, {**value.model_dump(), "inventory": inventory}, db)
            db.execute("UPDATE projects SET latest_input=? WHERE id=?", (oid, pid))
        return self.object(actor, oid)

    def enqueue(self, actor, pid, question, key, registry, refresh=False):
        project = self.scope(actor, pid, "analyst")
        if not project["latest_input"]:
            raise ValueError("Import a manifest and lockfile first")
        if not key or len(key) > 150 or not 3 <= len(question) <= 4000:
            raise ValueError("Bounded idempotency key and question required")
        request_hash = digest([question, project["latest_input"], refresh])
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT * FROM runs WHERE project_id=? AND idempotency_key=?", (pid, key)
            ).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise ValueError("Idempotency key reused for different work")
                return self._decode_run(prior)
            if db.execute(
                "SELECT 1 FROM runs WHERE project_id=? AND status IN ('queued','running')", (pid,)
            ).fetchone():
                raise ValueError("Project already has active work")
            if db.execute("SELECT COUNT(*) FROM runs WHERE status='queued'").fetchone()[0] >= 20:
                raise ValueError("Investigation queue full")
            results = {}
            if not refresh:
                old = db.execute(
                    "SELECT results FROM runs WHERE project_id=? AND input_id=? AND status IN ('completed','partial') ORDER BY created_at DESC LIMIT 1",
                    (pid, project["latest_input"]),
                ).fetchone()
                if old:
                    results = json.loads(old[0])
            rid = identifier()
            db.execute(
                "INSERT INTO runs(id,project_id,actor,input_id,question,idempotency_key,request_hash,status,registry,results,created_at) VALUES(?,?,?,?,?,?,?,'queued',?,?,?)",
                (
                    rid,
                    pid,
                    actor,
                    project["latest_input"],
                    question,
                    key,
                    request_hash,
                    json.dumps(registry),
                    json.dumps(results),
                    now(),
                ),
            )
        self.event(rid, pid, "queue", "queued", "Project-scoped investigation queued")
        return self.run(actor, rid)

    def _decode_run(self, row):
        result = dict(row)
        for field in ("registry", "results", "state", "bases"):
            result[field] = json.loads(result[field])
        return result

    def _run(self, rid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
            events = [
                dict(r)
                for r in db.execute("SELECT * FROM events WHERE run_id=? ORDER BY id", (rid,))
            ]
        if not row:
            raise ValueError("Run not found")
        result = self._decode_run(row)
        result["events"] = events
        result["report"] = self._object(result["report_id"]) if result["report_id"] else None
        return result

    def run(self, actor, rid):
        result = self._run(rid)
        self.scope(actor, result["project_id"])
        return result

    def claim(self, seconds=900):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM runs WHERE status='running' AND lease_until>?", (now(),)
            ).fetchone():
                return None
            row = db.execute(
                "SELECT * FROM runs WHERE status='queued' OR (status='running' AND lease_until<=?) ORDER BY created_at LIMIT 1",
                (now(),),
            ).fetchone()
            if not row:
                return None
            lease = identifier()
            db.execute(
                "UPDATE runs SET status='running',lease=?,lease_until=?,deadline=COALESCE(deadline,?) WHERE id=?",
                (
                    lease,
                    (datetime.now(UTC) + timedelta(seconds=150)).isoformat(),
                    (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat(),
                    row["id"],
                ),
            )
        return self._run(row["id"])

    def _fence(self, db, rid, lease):
        row = db.execute(
            "SELECT * FROM runs WHERE id=? AND status='running' AND lease=? AND lease_until>?",
            (rid, lease, now()),
        ).fetchone()
        if not row:
            raise ValueError("Stale worker lease")
        return row

    def reserve(self, rid, lease, counter, limit, amount=1):
        if (
            counter not in ("actions", "model_calls", "http_attempts", "acquired_bytes")
            or amount < 0
        ):
            raise ValueError("Invalid counter")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._fence(db, rid, lease)
            base = json.loads(row["bases"]).get(counter, 0)
            if row["cancelled"] or row["deadline"] <= now():
                raise ValueError("Investigation cancelled or deadline exceeded")
            if row[counter] + amount - base > limit or row[counter] + amount > limit * 2:
                raise ValueError(f"{counter} budget exceeded")
            db.execute(
                f"UPDATE runs SET {counter}={counter}+?,lease_until=? WHERE id=?",
                (amount, (datetime.now(UTC) + timedelta(seconds=150)).isoformat(), rid),
            )

    def checkpoint(self, rid, lease, key, value):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._fence(db, rid, lease)
            results = json.loads(row["results"])
            oid = self.put_object("snapshot", row["project_id"], value, db)
            results[key] = {**value, "snapshot_id": oid}
            db.execute("UPDATE runs SET results=? WHERE id=?", (json.dumps(results), rid))

    def save_state(self, rid, lease, state):
        with self.connect() as db:
            self._fence(db, rid, lease)
            db.execute("UPDATE runs SET state=? WHERE id=?", (json.dumps(state), rid))

    def event(self, rid, pid, stage, outcome, detail):
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(run_id,project_id,stage,outcome,detail,created_at) VALUES(?,?,?,?,?,?)",
                (rid, pid, stage, outcome, str(detail)[:2500], now()),
            )

    def finish(self, rid, lease, payload, reason):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._fence(db, rid, lease)
            payload = {
                **payload,
                "run_id": rid,
                "input_id": row["input_id"],
                "question": row["question"],
                "stop_reason": reason,
            }
            oid = self.put_object("report", row["project_id"], payload, db)
            db.execute(
                "UPDATE runs SET status=?,stop_reason=?,report_id=?,lease=NULL,lease_until=NULL WHERE id=?",
                (payload["status"], reason, oid, rid),
            )
        self.event(rid, row["project_id"], "finalize", payload["status"], reason)
        return self._object(oid)

    def latest_report(self, actor, pid):
        self.scope(actor, pid)
        with self.connect() as db:
            row = db.execute(
                "SELECT id FROM objects WHERE project_id=? AND kind='report' ORDER BY created_at DESC LIMIT 1",
                (pid,),
            ).fetchone()
        return self.object(actor, row[0]) if row else None

    def review(self, actor, oid, value):
        original = self.object(actor, oid)
        self.scope(actor, original["project_id"], "reviewer")
        if original["kind"] != "report" or original["revision"] != value.expected_revision:
            raise ValueError("Stale report revision")
        if (
            original["payload"]["status"] != "completed" or value.narrative is not None
        ) and not value.acknowledge_limits:
            raise ValueError("Acknowledge partial limitations before review")
        if value.narrative:
            from patchdesk_api.reconcile import validate_narrative

            validate_narrative(value.narrative, original["payload"]["findings"])
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT revision FROM objects WHERE id=?", (oid,)).fetchone()
            if current[0] != value.expected_revision:
                raise ValueError("Stale report revision")
            if value.narrative:
                payload = {
                    **original["payload"],
                    "narrative": value.narrative.model_dump(),
                    "parent_report_id": oid,
                    "status": "partial",
                    "review_state": "edited_by_human",
                }
                oid = self.put_object("report", original["project_id"], payload, db)
            db.execute(
                "UPDATE objects SET reviewed_by=?,notes=?,revision=revision+1 WHERE id=?",
                (actor, value.notes, oid),
            )
        return self.object(actor, oid)

    def export(self, actor, oid):
        report = self.object(actor, oid)
        self.scope(actor, report["project_id"], "reviewer")
        if report["kind"] != "report" or not report["reviewed_by"]:
            raise ValueError("Review exact report before export")
        payload = {"report": report, "exported_by": actor, "created_at": now()}
        eid = self.put_object("export", report["project_id"], payload)
        return {"id": eid, **payload}

    def cancel(self, actor, rid):
        run = self.run(actor, rid)
        self.scope(actor, run["project_id"], "analyst")
        if run["status"] not in ("queued", "running"):
            raise ValueError("Run is not active")
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET cancelled=1,status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END WHERE id=?",
                (rid,),
            )

    def resume(self, actor, rid, key):
        run = self.run(actor, rid)
        self.scope(actor, run["project_id"], "analyst")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM resume_keys WHERE run_id=? AND key=?", (rid, key)
            ).fetchone():
                return self._decode_run(
                    db.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
                )
            row = db.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
            if row["grant"] >= 2 or row["status"] not in ("partial", "cancelled"):
                raise ValueError("No further resume grant available")
            if db.execute(
                "SELECT 1 FROM runs WHERE project_id=? AND status IN ('queued','running')",
                (run["project_id"],),
            ).fetchone():
                raise ValueError("Project already has active work")
            bases = {
                counter: row[counter]
                for counter in ("actions", "model_calls", "http_attempts", "acquired_bytes")
            }
            db.execute("INSERT INTO resume_keys VALUES(?,?)", (rid, key))
            db.execute(
                "UPDATE runs SET status='queued',grant=grant+1,cancelled=0,deadline=NULL,lease=NULL,lease_until=NULL,bases=? WHERE id=?",
                (json.dumps(bases), rid),
            )
        self.event(rid, run["project_id"], "resume", "granted", "Explicit second bounded grant")
        return self.run(actor, rid)

    def setting(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(self, key, value):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, json.dumps(value)))
