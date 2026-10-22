"""Customer integration: local durable events with explicit lifecycle accounting."""

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from contracts.releasefence import Event, Usage

from .core import canonical, digest


class Spool:
    def __init__(self, path, *, capacity=50000, now=time.time):
        if not 1 <= capacity <= 50000:
            raise ValueError("bounded spool required")
        self.path = Path(path)
        self.capacity = capacity
        self.now = now
        with self.db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS spool(id TEXT PRIMARY KEY,hash TEXT NOT NULL,body TEXT NOT NULL,state TEXT NOT NULL,attempts INTEGER NOT NULL,due REAL NOT NULL,replayed INTEGER NOT NULL DEFAULT 0,lease TEXT)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)"
            )
            db.execute(
                "INSERT OR IGNORE INTO metadata VALUES('fingerprint_key',?)",
                (secrets.token_hex(32),),
            )
            self.fingerprint_key = bytes.fromhex(
                db.execute("SELECT value FROM metadata WHERE key='fingerprint_key'").fetchone()[0]
            )

    def fingerprint(self, value):
        return hmac.new(self.fingerprint_key, canonical(value).encode(), hashlib.sha256).hexdigest()

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        if os.name != "nt":
            os.chmod(self.path, 0o600)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def enqueue(self, event):
        event = Event.model_validate(event)
        with self.db() as db:
            old = db.execute("SELECT hash FROM spool WHERE id=?", (event.id,)).fetchone()
            if old:
                if old[0] != digest(event):
                    raise ValueError("event identity conflict")
                return
            if db.execute("SELECT count(*) FROM spool").fetchone()[0] >= self.capacity:
                raise ValueError("spool full; lifecycle evidence not recorded")
            db.execute(
                "INSERT INTO spool(id,hash,body,state,attempts,due) VALUES(?,?,?,'pending',0,?)",
                (event.id, digest(event), canonical(event), self.now()),
            )

    def flush(self, send):
        lease = secrets.token_hex(16)
        with self.db() as db:
            db.execute(
                "UPDATE spool SET state='dead_letter' WHERE state='leased' AND due<=? AND attempts>=CASE WHEN replayed=1 THEN 10 ELSE 5 END",
                (self.now(),),
            )
            rows = db.execute(
                "SELECT id,body,attempts FROM spool WHERE state IN ('pending','retry','leased') AND due<=? ORDER BY due,id LIMIT 100",
                (self.now(),),
            ).fetchall()
            for id, _, _ in rows:
                db.execute(
                    "UPDATE spool SET state='leased',lease=?,due=?,attempts=attempts+1 WHERE id=?",
                    (lease, self.now() + 60, id),
                )
        if not rows:
            return 0
        ok = False
        try:
            reply = send("/ingest/v1/events", {"events": [json.loads(r[1]) for r in rows]})
            ok = (
                isinstance(reply, dict)
                and type(reply.get("accepted")) is int
                and 0 <= reply["accepted"] <= len(rows)
            )
        except (OSError, ValueError):
            pass
        with self.db() as db:
            for id, _, attempts in rows:
                attempts += 1
                replayed = db.execute("SELECT replayed FROM spool WHERE id=?", (id,)).fetchone()[0]
                state = (
                    "delivered"
                    if ok
                    else "dead_letter"
                    if attempts >= (10 if replayed else 5)
                    else "retry"
                )
                db.execute(
                    "UPDATE spool SET state=?,attempts=?,due=?,lease=NULL WHERE id=? AND lease=?",
                    (state, attempts, self.now() + min(600, 5 * 2**attempts), id, lease),
                )
        return len(rows) if ok else 0

    def status(self):
        with self.db() as db:
            return dict(db.execute("SELECT state,count(*) FROM spool GROUP BY state"))

    def replay(self):
        with self.db() as db:
            return db.execute(
                "UPDATE spool SET state='retry',replayed=1,due=? WHERE state='dead_letter' AND replayed=0",
                (self.now(),),
            ).rowcount

    def prune_delivered(self):
        """Explicit local acknowledgement cleanup, never pending or dead letters."""
        with self.db() as db:
            return db.execute(
                "DELETE FROM spool WHERE state='delivered' AND due<?", (self.now() - 86400,)
            ).rowcount


class Task:
    def __init__(self, runtime, task, session, release):
        self.runtime = runtime
        self.task = task
        self.session = session
        self.release = release
        self.started = runtime.now()
        self.sequence = 0
        self.attempts = set()
        self.declared_model_calls = None
        self.outcome = "success"
        self.stop_reason = "complete"

    def emit(self, kind, **fields):
        self.sequence += 1
        self.runtime.spool.enqueue(
            Event(
                id=secrets.token_hex(16),
                task=self.task,
                session=self.session,
                release=self.release,
                kind=kind,
                at=self.runtime.now(),
                sequence=self.sequence,
                **fields,
            )
        )

    def model_attempt(self, attempt):
        self.attempts.add(attempt)

    def usage(self, attempt, **fields):
        self.model_attempt(attempt)
        self.emit("usage", usage=Usage(attempt=attempt, **fields))

    def tool(self, tool, arguments, progress, *, polling=False, iteration=None):
        self.emit(
            "tool",
            tool_fingerprint=self.runtime.spool.fingerprint([tool, arguments]),
            progress=self.runtime.spool.fingerprint(progress),
            polling=polling,
            iteration=iteration,
        )

    def wait(self, until):
        self.emit("heartbeat", waiting_until=until)


class Runtime:
    def __init__(self, router, spool, *, now=time.time):
        self.router = router
        self.spool = spool
        self.now = now

    @contextmanager
    def task(self, id, session):
        release = self.router.begin_task(id, session)
        task = Task(self, id, session, release)
        task.emit("accepted")
        try:
            yield task
        except BaseException:
            task.outcome = "failure"
            raise
        finally:
            task.emit(
                "terminal",
                outcome="failure"
                if task.stop_reason in {"iteration_exhausted", "deadline", "schema_exhausted"}
                else task.outcome,
                stop_reason=task.stop_reason,
                model_calls=task.declared_model_calls
                if task.declared_model_calls is not None
                else len(task.attempts),
                duration_ms=min(86400000, max(0, (self.now() - task.started) * 1000)),
            )
            self.router.end_task(id)
