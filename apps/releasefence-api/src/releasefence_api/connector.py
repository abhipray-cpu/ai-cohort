"""Customer-side crash-safe session router and outbound command connector."""

import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from contracts.releasefence import Attestation, Command

from .core import assignment, canonical, digest
from .crypto import public_key, signed, verify


class Router:
    def __init__(
        self,
        path,
        enrollment,
        application,
        environment,
        server_public,
        runtime_private,
        bundles,
        stable,
        *,
        now=time.time,
        probe=None,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.enrollment = enrollment
        self.application = application
        self.environment = environment
        self.server_public = server_public
        self.private = runtime_private
        self.bundles = set(bundles)
        self.now = now
        self.probe = probe
        if stable not in self.bundles:
            raise ValueError("stable bundle unavailable")
        binding = digest(
            [enrollment, application, environment, server_public, public_key(runtime_private)]
        )
        with self.db() as db:
            db.executescript(
                "CREATE TABLE IF NOT EXISTS state(k TEXT PRIMARY KEY,v TEXT NOT NULL); CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY,hash TEXT NOT NULL,result TEXT NOT NULL); CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,release TEXT NOT NULL,active INTEGER NOT NULL,created REAL NOT NULL,probe INTEGER NOT NULL);"
            )
            prior = db.execute("SELECT v FROM state WHERE k='binding'").fetchone()
            if prior and prior[0] != binding:
                raise ValueError("router identity changed")
            db.execute("INSERT OR IGNORE INTO state VALUES('binding',?)", (binding,))
            db.execute(
                "INSERT OR IGNORE INTO state VALUES('routing',?)",
                (
                    canonical(
                        {
                            "stable": stable,
                            "candidate": stable,
                            "weight": 0,
                            "seed": "initial",
                            "revision": 0,
                            "epoch": 0,
                        }
                    ),
                ),
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,session TEXT NOT NULL,release TEXT NOT NULL,terminal INTEGER NOT NULL DEFAULT 0,accepted_at REAL NOT NULL,terminal_at REAL)"
            )

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

    def state(self):
        with self.db() as db:
            return json.loads(db.execute("SELECT v FROM state WHERE k='routing'").fetchone()[0])

    def applied(self, envelope):
        command = Command.model_validate(verify(envelope, self.server_public))
        with self.db() as db:
            row = db.execute("SELECT hash FROM commands WHERE id=?", (command.id,)).fetchone()
            if row and row[0] != digest(command):
                raise ValueError("command ID conflict")
            return bool(row)

    def apply(self, envelope):
        command = Command.model_validate(verify(envelope, self.server_public))
        with self.db() as db:
            previous = db.execute(
                "SELECT hash,result FROM commands WHERE id=?", (command.id,)
            ).fetchone()
            if previous:
                if previous[0] != digest(command):
                    raise ValueError("command ID conflict")
                return json.loads(previous[1])
            state = json.loads(db.execute("SELECT v FROM state WHERE k='routing'").fetchone()[0])
            if (
                command.enrollment != self.enrollment
                or command.application != self.application
                or command.environment != self.environment
                or command.expires <= self.now()
                or command.epoch <= state["epoch"]
                or command.expected_revision != state["revision"]
                or not {command.stable, command.candidate} <= self.bundles
                or command.action == "rollback"
                and command.weight != 0
                or command.action == "promote"
                and command.weight != 100
                or command.action == "canary"
                and command.weight not in {5, 25}
            ):
                raise ValueError("command context or capability invalid")
            updated = {
                "stable": command.stable,
                "candidate": command.candidate,
                "weight": command.weight,
                "seed": command.seed,
                "revision": state["revision"] + 1,
                "epoch": command.epoch,
            }
            db.execute("UPDATE state SET v=? WHERE k='routing'", (canonical(updated),))
            if command.weight in {0, 100}:
                retired = command.candidate if command.weight == 0 else command.stable
                if retired != (command.stable if command.weight == 0 else command.candidate):
                    db.execute(
                        "UPDATE sessions SET active=-1 WHERE active=0 AND release=? AND probe=0",
                        (retired,),
                    )
            db.execute(
                "INSERT INTO commands VALUES(?,?,?)",
                (command.id, digest(command), canonical(updated)),
            )
            return updated

    def open_session(self, session, *, probe=False):
        with self.db() as db:
            return self._open_session(db, session, probe=probe)

    def _open_session(self, db, session, *, probe=False):
        if not 1 <= len(session) <= 128:
            raise ValueError("bounded session required")
        state = json.loads(db.execute("SELECT v FROM state WHERE k='routing'").fetchone()[0])
        previous = db.execute(
            "SELECT release,active FROM sessions WHERE id=?", (session,)
        ).fetchone()
        if previous:
            if previous[1] == -1:
                raise ValueError("retired release session; start a new session")
            excluded = (
                state["weight"] == 0
                and previous[0] != state["stable"]
                or state["weight"] == 100
                and previous[0] != state["candidate"]
            )
            if excluded and not previous[1]:
                raise ValueError("retired release session; start a new session")
            return previous[0]
        if db.execute("SELECT count(*) FROM sessions").fetchone()[0] >= 50000:
            raise ValueError("router session capacity reached")
        arm = assignment(
            f"{self.enrollment}:{self.application}:{self.environment}",
            session,
            state["seed"],
            state["weight"],
        )
        chosen = state[arm]
        db.execute(
            "INSERT INTO sessions VALUES(?,?,1,?,?)", (session, chosen, self.now(), int(probe))
        )
        return chosen

    def finish_session(self, session):
        with self.db() as db:
            if db.execute(
                "SELECT 1 FROM tasks WHERE session=? AND terminal=0", (session,)
            ).fetchone():
                raise ValueError("in-flight tasks have not drained")
            self._close_session(db, session)

    def _close_session(self, db, session):
        state = json.loads(db.execute("SELECT v FROM state WHERE k='routing'").fetchone()[0])
        db.execute(
            "UPDATE sessions SET active=CASE WHEN active=-1 OR (release<>? AND ?=0) OR (release<>? AND ?=100) THEN -1 ELSE 0 END WHERE id=?",
            (state["stable"], state["weight"], state["candidate"], state["weight"], session),
        )

    def begin_task(self, task, session):
        from contracts.releasefence import Identifier
        from pydantic import TypeAdapter

        TypeAdapter(Identifier).validate_python(task)
        TypeAdapter(Identifier).validate_python(session)
        with self.db() as db:
            if db.execute("SELECT 1 FROM tasks WHERE id=?", (task,)).fetchone():
                raise ValueError("task identity already accepted")
            if db.execute("SELECT count(*) FROM tasks").fetchone()[0] >= 50000:
                raise ValueError("lifecycle capacity reached")
            release = self._open_session(db, session)
            db.execute(
                "INSERT INTO tasks(id,session,release,accepted_at) VALUES(?,?,?,?)",
                (task, session, release, self.now()),
            )
            db.execute("UPDATE sessions SET active=1 WHERE id=?", (session,))
        return release

    def end_task(self, task):
        with self.db() as db:
            row = db.execute("SELECT session,terminal FROM tasks WHERE id=?", (task,)).fetchone()
            if not row:
                raise ValueError("unknown task")
            if row[1]:
                return  # Reconciliation cannot rewrite completion or reopen a retired session.
            db.execute("UPDATE tasks SET terminal=1,terminal_at=? WHERE id=?", (self.now(), task))
            if not db.execute(
                "SELECT 1 FROM tasks WHERE session=? AND terminal=0", (row[0],)
            ).fetchone():
                self._close_session(db, row[0])

    def attest(self, command_id, *, window=None):
        state = self.state()
        probe = "probe:" + secrets.token_hex(12)
        chosen = self.open_session(probe, probe=True)
        self.finish_session(probe)
        available = []
        for identity in sorted(self.bundles):
            try:
                if self.probe:
                    self.probe(identity, probe + ":" + identity[:8])
                available.append(identity)
            except (OSError, ValueError):
                continue
        receipt = self.probe(chosen, probe) if self.probe else None
        with self.db() as db:
            db.execute("DELETE FROM sessions WHERE probe=1 AND active=0")
            active = db.execute(
                "SELECT count(*) FROM sessions WHERE active=1 AND release=?", (state["candidate"],)
            ).fetchone()[0]
            counters = [
                {"release": r[0], "accepted": r[1], "terminal": r[2]}
                for r in db.execute(
                    "SELECT release,count(*),sum(terminal) FROM tasks WHERE accepted_at>=? AND accepted_at<? GROUP BY release",
                    window or (0, 4102444800),
                )
            ]
        return signed(
            Attestation(
                command=command_id,
                enrollment=self.enrollment,
                revision=state["revision"],
                epoch=state["epoch"],
                at=self.now(),
                stable=state["stable"],
                candidate=state["candidate"],
                weight=state["weight"],
                probe_session=probe,
                probe_release=chosen,
                active_candidate=active,
                available_bundles=available,
                probe_kind="http_bundle" if self.probe else "routing_only",
                probe_receipt=receipt,
                counters=counters,
                window_start=window[0] if window else None,
                window_end=window[1] if window else None,
            ),
            self.private,
        )


class Connector:
    """Polling transport is injected; no deployment on startup or model calls."""

    def __init__(self, router, client, enrollment):
        self.router = router
        self.client = client
        self.enrollment = enrollment

    def tick(self):
        prefix = f"/connector/v1/{self.enrollment}"
        self.client.post(
            prefix + "/heartbeat", json=self.router.attest("heartbeat")
        ).raise_for_status()
        response = self.client.post(prefix + "/poll")
        response.raise_for_status()
        pending = response.json()
        if pending.get("window"):
            self.client.post(
                prefix + "/heartbeat",
                json=self.router.attest("heartbeat", window=tuple(pending["window"])),
            ).raise_for_status()
        for envelope in pending["commands"]:
            command = Command.model_validate(envelope["body"])
            if not self.router.applied(envelope):
                approval = self.client.post(prefix + f"/commands/{command.id}/authorize")
                approval.raise_for_status()  # Fail closed for new execution.
                self.router.apply(envelope)
            proof = self.router.attest(command.id)
            response = self.client.post(prefix + "/attest", json=proof)
            response.raise_for_status()
        return len(pending["commands"])
