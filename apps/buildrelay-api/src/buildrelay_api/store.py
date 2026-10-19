"""SQLite inbox, leased workflows, action ledger and append-only application audit.

One host, local filesystem only. Cross-process claims use BEGIN IMMEDIATE;
every worker mutation is fenced by a random lease token and expiration.
"""

import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from contracts.buildrelay import RunEvent


class LeaseLost(ValueError):
    """This worker no longer owns the event; no event mutation is permitted."""


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "buildrelay.sqlite3"
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS clients(id TEXT PRIMARY KEY,name TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS repos(
                id TEXT PRIMARY KEY,client_id TEXT NOT NULL REFERENCES clients(id),
                name TEXT UNIQUE NOT NULL,github_id INTEGER UNIQUE NOT NULL,
                secret_ref TEXT NOT NULL,token_ref TEXT NOT NULL,owner TEXT NOT NULL,
                issues INTEGER NOT NULL,version INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS events(
                id TEXT PRIMARY KEY,repo_id TEXT NOT NULL REFERENCES repos(id),payload TEXT NOT NULL,
                state TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,due REAL NOT NULL DEFAULT 0,
                lease_until REAL NOT NULL DEFAULT 0,lease_token TEXT,checkpoint TEXT NOT NULL DEFAULT '{}',
                error TEXT,created REAL NOT NULL,updated REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS event_claim ON events(state,due,lease_until);
            CREATE TABLE IF NOT EXISTS deliveries(
                repo_id TEXT,transport TEXT,delivery_id TEXT,event_id TEXT,
                PRIMARY KEY(repo_id,transport,delivery_id));
            CREATE TABLE IF NOT EXISTS incidents(
                id TEXT PRIMARY KEY,repo_id TEXT NOT NULL,run_id INTEGER NOT NULL,
                attempt INTEGER NOT NULL,state TEXT NOT NULL,owner TEXT NOT NULL,
                triage TEXT,source_url TEXT NOT NULL,updated REAL NOT NULL,
                UNIQUE(repo_id,run_id));
            CREATE TABLE IF NOT EXISTS effects(
                incident_id TEXT PRIMARY KEY,state TEXT NOT NULL,external_id INTEGER,
                updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS audit(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,occurred REAL NOT NULL,
                actor TEXT NOT NULL,action TEXT NOT NULL,repo_id TEXT,event_id TEXT,detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS users(
                name TEXT PRIMARY KEY,salt TEXT NOT NULL,hash TEXT NOT NULL,role TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS grants(name TEXT,client_id TEXT,PRIMARY KEY(name,client_id));
            CREATE TABLE IF NOT EXISTS sessions(
                token TEXT PRIMARY KEY,name TEXT NOT NULL,csrf TEXT NOT NULL,expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS heartbeat(name TEXT PRIMARY KEY,updated REAL NOT NULL,detail TEXT);
            CREATE TABLE IF NOT EXISTS cursors(repo_id TEXT PRIMARY KEY,last_scan REAL NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def write(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def record(self, db, action, *, repo_id=None, event_id=None, actor="worker", detail=None):
        db.execute(
            "INSERT INTO audit(occurred,actor,action,repo_id,event_id,detail) VALUES(?,?,?,?,?,?)",
            (time.time(), actor, action, repo_id, event_id, json.dumps(detail or {})),
        )

    def create_client(self, ident, name, *, actor="owner"):
        with self.write() as db:
            db.execute("INSERT INTO clients VALUES(?,?)", (ident, name))
            self.record(db, "client_created", actor=actor, detail={"id": ident})

    def create_repo(
        self,
        ident,
        client_id,
        name,
        github_id,
        secret_ref,
        token_ref,
        owner,
        issues,
        *,
        actor="owner",
    ):
        with self.write() as db:
            db.execute(
                "INSERT INTO repos(id,client_id,name,github_id,secret_ref,token_ref,owner,issues) VALUES(?,?,?,?,?,?,?,?)",
                (ident, client_id, name, github_id, secret_ref, token_ref, owner, int(issues)),
            )
            self.record(db, "repository_created", repo_id=ident, actor=actor)

    def repo(self, ident):
        with self.connect() as db:
            row = db.execute("SELECT * FROM repos WHERE id=?", (ident,)).fetchone()
        if not row:
            raise KeyError(ident)
        return dict(row)

    def repos(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM repos ORDER BY name")]

    def accept(self, repo_id, event: RunEvent, transport, delivery_id):
        # Revalidate internal callers too: model_copy is not a validation boundary.
        event = RunEvent.model_validate(event.model_dump())
        repo = self.repo(repo_id)
        if (
            event.repository.lower() != repo["name"].lower()
            or event.repository_id != repo["github_id"]
        ):
            raise ValueError("repository identity mismatch")
        # Conclusion distinguishes final recovery from failure without trusting delivery IDs.
        key = f"{repo_id}:{event.run_id}:{event.attempt}:{event.conclusion}:v{repo['version']}"
        ident = hashlib.sha256(key.encode()).hexdigest()
        with self.write() as db:
            prior = db.execute(
                "SELECT event_id FROM deliveries WHERE repo_id=? AND transport=? AND delivery_id=?",
                (repo_id, transport, delivery_id),
            ).fetchone()
            if prior and prior[0] != ident:
                raise ValueError("delivery identity collision")
            now = time.time()
            inserted = db.execute(
                "INSERT OR IGNORE INTO events(id,repo_id,payload,state,created,updated) VALUES(?,?,?,'pending',?,?)",
                (ident, repo_id, event.model_dump_json(), now, now),
            ).rowcount
            db.execute(
                "INSERT OR IGNORE INTO deliveries VALUES(?,?,?,?)",
                (repo_id, transport, delivery_id, ident),
            )
            self.record(
                db,
                "event_accepted" if inserted else "duplicate_ignored",
                repo_id=repo_id,
                event_id=ident,
                actor=transport,
            )
        return ident

    def claim(self, *, now=None, lease=600):
        now = time.time() if now is None else now
        with self.write() as db:
            expired = db.execute(
                "SELECT id,repo_id FROM events WHERE state='processing' AND lease_until<=? AND attempts>=4",
                (now,),
            ).fetchall()
            for row in expired:
                db.execute(
                    "UPDATE events SET state='dead',error='lease_exhausted',lease_token=NULL,lease_until=0 WHERE id=?",
                    (row["id"],),
                )
                self.record(
                    db,
                    "dead_lettered",
                    repo_id=row["repo_id"],
                    event_id=row["id"],
                    detail={"code": "lease_exhausted"},
                )
            # Single active workflow per host: bounded AI load and serialized side effects.
            if db.execute(
                "SELECT 1 FROM events WHERE state='processing' AND lease_until>?", (now,)
            ).fetchone():
                return None
            row = db.execute(
                "SELECT * FROM events WHERE (state IN ('pending','retry') AND due<=?) OR (state='processing' AND lease_until<=?) ORDER BY created LIMIT 1",
                (now, now),
            ).fetchone()
            if not row:
                return None
            token = secrets.token_hex(24)
            db.execute(
                "UPDATE events SET state='processing',lease_token=?,lease_until=?,attempts=attempts+1,updated=? WHERE id=?",
                (token, now + lease, now, row["id"]),
            )
            job = dict(db.execute("SELECT * FROM events WHERE id=?", (row["id"],)).fetchone())
            self.record(
                db,
                "workflow_claimed",
                repo_id=job["repo_id"],
                event_id=job["id"],
                detail={"attempt": job["attempts"]},
            )
            return job

    def fenced(self, db, job, now=None):
        now = time.time() if now is None else now
        row = db.execute(
            "SELECT * FROM events WHERE id=? AND state='processing' AND lease_token=? AND lease_until>?",
            (job["id"], job["lease_token"], now),
        ).fetchone()
        if not row:
            raise LeaseLost("expired or superseded lease")
        return dict(row)

    def checkpoint(self, job, step, value, *, now=None):
        with self.write() as db:
            fresh = self.fenced(db, job, now)
            checkpoint = json.loads(fresh["checkpoint"])
            checkpoint[step] = value
            db.execute(
                "UPDATE events SET checkpoint=? WHERE id=?", (json.dumps(checkpoint), job["id"])
            )
            job["checkpoint"] = json.dumps(checkpoint)
            self.record(
                db,
                "step_completed",
                repo_id=job["repo_id"],
                event_id=job["id"],
                detail={"step": step},
            )

    def renew(self, job, *, now=None, lease=600):
        now = time.time() if now is None else now
        with self.write() as db:
            self.fenced(db, job, now)
            db.execute("UPDATE events SET lease_until=? WHERE id=?", (now + lease, job["id"]))
            db.execute(
                "INSERT INTO heartbeat VALUES('workflow',?,'processing') ON CONFLICT(name) DO UPDATE SET updated=excluded.updated,detail=excluded.detail",
                (now,),
            )

    def fail(self, job, code, *, transient, now=None, max_attempts=4, retry_after=0):
        now = time.time() if now is None else now
        with self.write() as db:
            row = self.fenced(db, job, now)
            dead = not transient or row["attempts"] >= max_attempts
            delay = max(
                retry_after, min(300, 5 * 2 ** min(row["attempts"], 6)) + secrets.randbelow(5)
            )
            db.execute(
                "UPDATE events SET state=?,error=?,due=?,lease_token=NULL,lease_until=0,updated=? WHERE id=?",
                ("dead" if dead else "retry", code, now + delay, now, job["id"]),
            )
            self.record(
                db,
                "dead_lettered" if dead else "retry_scheduled",
                repo_id=job["repo_id"],
                event_id=job["id"],
                detail={"code": code, "delay": delay},
            )

    def replay(self, ident, actor, *, now=None, reason=None):
        with self.write() as db:
            row = db.execute(
                "SELECT * FROM events WHERE id=? AND state='dead'", (ident,)
            ).fetchone()
            if not row:
                raise ValueError("only dead letters can be replayed")
            db.execute(
                "UPDATE events SET state='pending',attempts=0,due=?,error=NULL WHERE id=?",
                (now or time.time(), ident),
            )
            self.record(
                db,
                "dead_letter_replayed",
                repo_id=row["repo_id"],
                event_id=ident,
                actor=actor,
                detail={"reason": reason or "explicit operator replay"},
            )

    @staticmethod
    def incident_id(repo_id, event):
        return hashlib.sha256(f"{repo_id}:{event.run_id}".encode()).hexdigest()

    def finish(self, job, triage, *, now=None, complete=True):
        now = time.time() if now is None else now
        event = RunEvent.model_validate_json(job["payload"])
        repo = self.repo(job["repo_id"])
        ident = self.incident_id(repo["id"], event)
        with self.write() as db:
            self.fenced(db, job, now)
            prior = db.execute("SELECT * FROM incidents WHERE id=?", (ident,)).fetchone()
            failed = event.conclusion in {
                "failure",
                "timed_out",
                "startup_failure",
                "action_required",
            }
            current = (
                not prior
                or event.attempt > prior["attempt"]
                or (event.attempt == prior["attempt"] and prior["state"] != "recovered")
            )
            if (failed or prior) and current:
                state = (
                    "needs_triage"
                    if failed and (not triage or triage["confidence"] < 0.75)
                    else "investigating"
                    if failed
                    else "recovered"
                    if event.conclusion == "success"
                    else "needs_triage"
                )
                db.execute(
                    "INSERT INTO incidents VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET attempt=excluded.attempt,state=excluded.state,triage=COALESCE(excluded.triage,incidents.triage),updated=excluded.updated",
                    (
                        ident,
                        repo["id"],
                        event.run_id,
                        event.attempt,
                        state,
                        repo["owner"],
                        json.dumps(triage) if triage else None,
                        event.source_url,
                        now,
                    ),
                )
            if complete:
                db.execute(
                    "UPDATE events SET state='done',lease_token=NULL,lease_until=0,error=NULL,updated=? WHERE id=?",
                    (now, job["id"]),
                )
                self.record(db, "workflow_completed", repo_id=repo["id"], event_id=job["id"])

    def incident(self, ident):
        with self.connect() as db:
            row = db.execute("SELECT * FROM incidents WHERE id=?", (ident,)).fetchone()
        return dict(row) if row else None

    def superseded(self, job, event):
        with self.connect() as db:
            return bool(
                db.execute(
                    """SELECT 1 FROM events WHERE repo_id=? AND id<>?
                AND json_extract(payload,'$.run_id')=? AND
                (json_extract(payload,'$.attempt')>? OR
                (json_extract(payload,'$.attempt')=? AND json_extract(payload,'$.conclusion')='success')) LIMIT 1""",
                    (job["repo_id"], job["id"], event.run_id, event.attempt, event.attempt),
                ).fetchone()
            )

    def rows(self, table):
        if table not in {"events", "incidents", "clients", "audit", "heartbeat"}:
            raise ValueError("invalid table")
        with self.connect() as db:
            return [
                dict(r) for r in db.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 1000")
            ]

    def events(self):
        return self.rows("events")

    def incidents(self):
        return self.rows("incidents")

    def audit(self):
        return self.rows("audit")

    def beat(self, name, detail="ok"):
        with self.write() as db:
            db.execute(
                "INSERT INTO heartbeat VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET updated=excluded.updated,detail=excluded.detail",
                (name, time.time(), detail),
            )

    def effect(self, incident_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM effects WHERE incident_id=?", (incident_id,)).fetchone()
        return dict(row) if row else None

    def effect_state(self, job, ident, state, external_id=None):
        with self.write() as db:
            self.fenced(db, job)
            db.execute(
                "INSERT INTO effects VALUES(?,?,?,?) ON CONFLICT(incident_id) DO UPDATE SET state=excluded.state,external_id=COALESCE(excluded.external_id,effects.external_id),updated=excluded.updated",
                (ident, state, external_id, time.time()),
            )
            self.record(
                db,
                "external_effect_" + state,
                repo_id=job["repo_id"],
                event_id=job["id"],
                detail={"external_id": external_id},
            )
