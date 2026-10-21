"""Dedicated SQLite store; immutable artifacts, fenced jobs, append-only usage journal."""

import hashlib
import hmac
import json
import os
import secrets
import shutil
import sqlite3
import time
from collections import Counter
from contextlib import contextmanager, nullcontext
from pathlib import Path

from contracts.shelfproof import Draft, FactPack

from .core import canonical, code_fingerprint, digest, ready
from .errors import Conflict, Forbidden
from .lifecycle import Lifecycle
from .operations import Operations


class Store(Lifecycle, Operations):
    def require_disk(self, extra=0):
        if shutil.disk_usage(self.root).free < 64 * 1024 * 1024 + extra:
            raise Conflict("insufficient protected write capacity")

    def __init__(self, root, clock=time.time):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "shelfproof.sqlite3"
        self.journal = self.root / "usage.jsonl"
        self.now = clock
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    name TEXT PRIMARY KEY, salt TEXT NOT NULL, password TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY, actor TEXT NOT NULL, csrf TEXT NOT NULL,
                    expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, epoch INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS members (
                    workspace TEXT NOT NULL, actor TEXT NOT NULL, role TEXT NOT NULL,
                    PRIMARY KEY(workspace, actor));
                CREATE TABLE IF NOT EXISTS grants (
                    id TEXT PRIMARY KEY, workspace TEXT NOT NULL, actor TEXT NOT NULL,
                    basis TEXT NOT NULL, expires REAL NOT NULL, max_calls INTEGER NOT NULL,
                    calls INTEGER NOT NULL DEFAULT 0, egress INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, workspace TEXT NOT NULL, maker TEXT NOT NULL,
                    epoch INTEGER NOT NULL, fact_json TEXT NOT NULL, fact_hash TEXT NOT NULL,
                    grant_id TEXT NOT NULL, state TEXT NOT NULL, calls INTEGER NOT NULL DEFAULT 0,
                    claims INTEGER NOT NULL DEFAULT 0, lease TEXT, lease_until REAL,
                    deadline REAL, selected_hash TEXT, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT NOT NULL,
                    kind TEXT NOT NULL, hash TEXT NOT NULL, body TEXT NOT NULL,
                    UNIQUE(task, kind, hash));
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY, task TEXT NOT NULL, stage TEXT NOT NULL,
                    status TEXT NOT NULL, receipt TEXT, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS reviews (
                    task TEXT NOT NULL, hash TEXT NOT NULL, actor TEXT NOT NULL,
                    decision TEXT NOT NULL, reason TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS audit (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, workspace TEXT,
                    actor TEXT NOT NULL, event TEXT NOT NULL, body TEXT NOT NULL,
                    created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS idem (
                    actor TEXT NOT NULL, workspace TEXT NOT NULL, operation TEXT NOT NULL,
                    key TEXT NOT NULL, hash TEXT NOT NULL, result TEXT NOT NULL,
                    PRIMARY KEY(actor,workspace,operation,key));
                CREATE TABLE IF NOT EXISTS imports (
                    id TEXT PRIMARY KEY, workspace TEXT NOT NULL, actor TEXT NOT NULL,
                    raw BLOB NOT NULL, frozen TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS heartbeat (
                    id INTEGER PRIMARY KEY CHECK(id=1), seen REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS policies (
                    workspace TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL,
                    hash TEXT NOT NULL, PRIMARY KEY(workspace,revision));
                CREATE TABLE IF NOT EXISTS batches (
                    id TEXT PRIMARY KEY, workspace TEXT NOT NULL, maker TEXT NOT NULL,
                    source_id TEXT NOT NULL, rows TEXT NOT NULL, grant_id TEXT NOT NULL,
                    epoch INTEGER NOT NULL, binding TEXT NOT NULL, state TEXT NOT NULL,
                    created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS task_links (
                    task TEXT PRIMARY KEY, source_id TEXT, batch_id TEXT, parent_task TEXT);
                CREATE INDEX IF NOT EXISTS tasks_workspace ON tasks(workspace,created);
                CREATE INDEX IF NOT EXISTS artifacts_task ON artifacts(task,kind);
                CREATE INDEX IF NOT EXISTS attempts_task ON attempts(task,stage);
                CREATE TABLE IF NOT EXISTS controls (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, task TEXT NOT NULL,
                    body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS snapshots (task TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS supplements (attempt TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS erased_sources (source TEXT PRIMARY KEY,workspace TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS selections (task TEXT PRIMARY KEY, revision INTEGER NOT NULL);
            """)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA secure_delete=ON")
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _audit(self, db, event, *, actor="worker", task=None, workspace=None, body=None):
        db.execute(
            "INSERT INTO audit(task,workspace,actor,event,body,created) VALUES(?,?,?,?,?,?)",
            (task, workspace, actor, event, canonical(body or {}), self.now()),
        )

    def _role(self, db, actor, workspace, roles=None):
        member = db.execute(
            "SELECT role FROM members WHERE workspace=? AND actor=?", (workspace, actor)
        ).fetchone()
        if member is None or (roles and member["role"] not in roles):
            raise Forbidden("object unavailable")
        return member["role"]

    def create_user(self, actor, password):
        if not 1 <= len(actor) <= 100 or len(password) < 12 or len(password) > 512:
            raise ValueError("username/password outside limits")
        salt = secrets.token_hex(16)
        encoded = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), 310000
        ).hex()
        with self.db() as db:
            db.execute("INSERT INTO users VALUES(?,?,?)", (actor, salt, encoded))

    def login(self, actor, password):
        with self.db() as db:
            row = db.execute("SELECT * FROM users WHERE name=?", (actor,)).fetchone()
            salt = bytes.fromhex(row["salt"]) if row else b"0" * 16
            encoded = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000).hex()
            if not row or not hmac.compare_digest(encoded, row["password"]):
                raise Forbidden("invalid credentials")
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?)",
                (digest(token.encode()), actor, csrf, self.now() + 8 * 3600),
            )
            return token, csrf

    def session(self, token):
        with self.db() as db:
            row = db.execute(
                "SELECT * FROM sessions WHERE token=? AND expires>?",
                (digest(token.encode()), self.now()),
            ).fetchone()
            if row is None:
                raise Forbidden("session unavailable")
            return dict(row)

    def logout(self, token):
        with self.db() as db:
            db.execute("DELETE FROM sessions WHERE token=?", (digest(token.encode()),))

    def create_workspace(self, actor, name):
        if not 1 <= len(name) <= 150:
            raise ValueError("invalid name")
        workspace = secrets.token_hex(16)
        with self.db() as db:
            if not db.execute("SELECT 1 FROM users WHERE name=?", (actor,)).fetchone():
                raise Forbidden("unknown actor")
            db.execute("INSERT INTO workspaces(id,name) VALUES(?,?)", (workspace, name))
            db.execute("INSERT INTO members VALUES(?,?,?)", (workspace, actor, "owner"))
            self._audit(db, "workspace_created", actor=actor, workspace=workspace)
        return workspace

    def workspaces(self, actor):
        with self.db() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT w.*,m.role FROM workspaces w JOIN members m "
                    "ON w.id=m.workspace WHERE m.actor=? ORDER BY w.name",
                    (actor,),
                )
            ]

    def add_member(self, actor, workspace, member, role):
        if role not in {"owner", "editor", "reviewer", "viewer"}:
            raise ValueError("invalid role")
        with self.db() as db:
            self._role(db, actor, workspace, {"owner"})
            if not db.execute("SELECT 1 FROM users WHERE name=?", (member,)).fetchone():
                raise ValueError("create user before membership")
            old = db.execute(
                "SELECT role FROM members WHERE workspace=? AND actor=?", (workspace, member)
            ).fetchone()
            if (
                old
                and old[0] == "owner"
                and role != "owner"
                and db.execute(
                    "SELECT count(*) FROM members WHERE workspace=? AND role='owner'", (workspace,)
                ).fetchone()[0]
                <= 1
            ):
                raise Conflict("workspace must retain an owner")
            db.execute("INSERT OR REPLACE INTO members VALUES(?,?,?)", (workspace, member, role))
            if old and old["role"] != role:
                self._invalidate(db, workspace)
            self._audit(
                db,
                "membership_changed",
                actor=actor,
                workspace=workspace,
                body={"member": member, "role": role},
            )

    def authorize(self, actor, workspace, *, basis, expires, max_calls, egress):
        if not 1 <= len(basis) <= 2000 or not self.now() < expires <= self.now() + 86400 * 365:
            raise ValueError("invalid source authority")
        if type(max_calls) is not int or not 1 <= max_calls <= 100000:
            raise ValueError("invalid cumulative allowance")
        grant = secrets.token_hex(16)
        with self.db() as db:
            self._role(db, actor, workspace, {"owner"})
            db.execute(
                "INSERT INTO grants(id,workspace,actor,basis,expires,max_calls,egress) "
                "VALUES(?,?,?,?,?,?,?)",
                (grant, workspace, actor, basis, expires, max_calls, int(egress)),
            )
            self._audit(
                db,
                "source_authorized",
                actor=actor,
                workspace=workspace,
                body={
                    "grant": grant,
                    "max_calls": max_calls,
                    "egress": egress,
                    "expires": expires,
                    "basis": basis,
                },
            )
        return grant

    def save_import(self, actor, workspace, raw, frozen):
        self.require_disk(len(raw) * 2)
        import_id = secrets.token_hex(16)
        with self.db() as db:
            self._role(db, actor, workspace, {"owner", "editor"})
            db.execute(
                "INSERT INTO imports VALUES(?,?,?,?,?,?)",
                (import_id, workspace, actor, raw, frozen.model_dump_json(), self.now()),
            )
            self._audit(
                db,
                "source_frozen",
                actor=actor,
                workspace=workspace,
                body={
                    "import": import_id,
                    "fact_hash": frozen.fact_hash,
                    "raw_hash": frozen.raw_hash,
                    "count": len(frozen.facts),
                },
            )
        return import_id

    def import_row(self, actor, workspace, import_id, index):
        with self.db() as db:
            self._role(db, actor, workspace, {"owner", "editor"})
            row = db.execute(
                "SELECT frozen FROM imports WHERE id=? AND workspace=?", (import_id, workspace)
            ).fetchone()
            if not row:
                raise Forbidden("object unavailable")
            frozen = json.loads(row[0])
            if type(index) is not int or not 0 <= index < len(frozen["facts"]):
                raise ValueError("row outside import")
            return FactPack.model_validate(frozen["facts"][index])

    def heartbeat(self):
        with self.db() as db:
            db.execute("INSERT OR REPLACE INTO heartbeat VALUES(1,?)", (self.now(),))

    def health(self):
        with self.db() as db:
            row = db.execute("SELECT seen FROM heartbeat WHERE id=1").fetchone()
            hold = self._liability(db)
            return {
                "ready": bool(row and self.now() - row[0] < 45 and not hold),
                "worker_seen": bool(row and self.now() - row[0] < 45),
                "usage_hold": hold,
            }

    def create_task(
        self,
        actor,
        workspace,
        facts: FactPack,
        grant,
        key,
        original=None,
        *,
        source_id=None,
        batch_id=None,
        parent_task=None,
        _db=None,
    ):
        if not 1 <= len(key) <= 128:
            raise ValueError("idempotency key required")
        payload = {
            "facts": facts.model_dump(mode="json"),
            "grant": grant,
            "original": original.model_dump(mode="json") if original else None,
            "source_id": source_id,
            "batch_id": batch_id,
            "parent_task": parent_task,
        }
        request_hash = digest(payload)
        with nullcontext(_db) if _db is not None else self.db() as db:
            self._role(db, actor, workspace, {"owner", "editor"})
            existing = db.execute(
                "SELECT * FROM idem WHERE actor=? AND workspace=? AND operation='task' AND key=?",
                (actor, workspace, key),
            ).fetchone()
            if existing:
                if existing["hash"] != request_hash:
                    raise Conflict("idempotency payload differs")
                return existing["result"]
            if (
                db.execute(
                    "SELECT count(*) FROM tasks WHERE state IN ('queued','running')"
                ).fetchone()[0]
                >= 1000
            ):
                raise Conflict("global queued/running row admission limit reached")
            authority = db.execute(
                "SELECT * FROM grants WHERE id=? AND workspace=?", (grant, workspace)
            ).fetchone()
            if not authority or authority["expires"] <= self.now() or not authority["egress"]:
                raise Conflict("current source/egress authority required")
            epoch = db.execute("SELECT epoch FROM workspaces WHERE id=?", (workspace,)).fetchone()[
                0
            ]
            if source_id:
                source = db.execute(
                    "SELECT frozen FROM imports WHERE id=? AND workspace=?", (source_id, workspace)
                ).fetchone()
                if not source or not any(
                    digest(f) == digest(facts) for f in json.loads(source[0])["facts"]
                ):
                    raise Conflict("frozen source binding unavailable")
            task = secrets.token_hex(16)
            db.execute(
                "INSERT INTO tasks(id,workspace,maker,epoch,fact_json,fact_hash,grant_id,"
                "state,created) VALUES(?,?,?,?,?,?,?,'queued',?)",
                (
                    task,
                    workspace,
                    actor,
                    epoch,
                    facts.model_dump_json(),
                    digest(facts),
                    grant,
                    self.now(),
                ),
            )
            if original:
                self._artifact(
                    db,
                    task,
                    "versions",
                    {
                        "draft": original.model_dump(mode="json"),
                        "draft_hash": digest(original),
                        "source": "imported",
                        "version_index": 0,
                        "producer": actor,
                    },
                )
                db.execute("UPDATE tasks SET selected_hash=? WHERE id=?", (digest(original), task))
            db.execute(
                "INSERT INTO task_links VALUES(?,?,?,?)", (task, source_id, batch_id, parent_task)
            )
            policy = db.execute(
                "SELECT body FROM policies WHERE workspace=? ORDER BY revision DESC LIMIT 1",
                (workspace,),
            ).fetchone()
            snapshot = {
                "code_fingerprint": code_fingerprint(),
                "fact_hash": digest(facts),
                "epoch": epoch,
                "policy": json.loads(policy[0]) if policy else {"brief": "Neutral factual copy."},
                "profile": "google-merchant-us-en-text-v1",
                "rubric": "weighted-five-v1",
                "source_id": source_id,
                "protocol": "reflection-v1",
            }
            db.execute("INSERT INTO snapshots VALUES(?,?)", (task, canonical(snapshot)))
            db.execute(
                "INSERT INTO idem VALUES(?,?,'task',?,?,?)",
                (actor, workspace, key, request_hash, task),
            )
            self._audit(
                db,
                "task_queued",
                actor=actor,
                task=task,
                workspace=workspace,
                body={"facts": digest(facts), "grant": grant},
            )
        return task

    def _artifact(self, db, task, kind, body):
        db.execute(
            "INSERT OR IGNORE INTO artifacts(task,kind,hash,body) VALUES(?,?,?,?)",
            (task, kind, digest(body), canonical(body)),
        )

    def _current(self, db, row):
        epoch = db.execute(
            "SELECT epoch FROM workspaces WHERE id=?", (row["workspace"],)
        ).fetchone()
        grant = db.execute("SELECT * FROM grants WHERE id=?", (row["grant_id"],)).fetchone()
        snapshot = db.execute("SELECT body FROM snapshots WHERE task=?", (row["id"],)).fetchone()
        return (
            epoch
            and epoch[0] == row["epoch"]
            and grant
            and grant["egress"]
            and grant["expires"] > self.now()
            and snapshot
            and json.loads(snapshot[0])["code_fingerprint"] == code_fingerprint()
        )

    def _fence(self, db, task, lease):
        row = db.execute("SELECT * FROM tasks WHERE id=?", (task,)).fetchone()
        if (
            not row
            or row["state"] != "running"
            or row["lease"] != lease
            or row["lease_until"] <= self.now()
            or row["deadline"] <= self.now()
            or not self._current(db, row)
        ):
            raise Conflict("lease/context unavailable")
        return row

    def claim(self):
        with self.db() as db:
            if self._liability(db):
                return None
            # Expired leases need explicit isolation/reconciliation, never automatic replay.
            if db.execute("SELECT 1 FROM tasks WHERE state='running'").fetchone():
                return None
            for row in db.execute("SELECT * FROM tasks WHERE state='queued' ORDER BY created"):
                if not self._current(db, row):
                    db.execute("UPDATE tasks SET state='stale' WHERE id=?", (row["id"],))
                    continue
                if row["claims"] >= 4 or (row["deadline"] and row["deadline"] <= self.now()):
                    db.execute("UPDATE tasks SET state='manual_required' WHERE id=?", (row["id"],))
                    continue
                lease = secrets.token_urlsafe(32)
                db.execute(
                    "UPDATE tasks SET state='running',lease=?,lease_until=?,claims=claims+1,"
                    "deadline=COALESCE(deadline,?) WHERE id=?",
                    (lease, self.now() + 600, self.now() + 1800, row["id"]),
                )
                result = dict(row)
                result["lease"] = lease
                self._audit(db, "claimed", task=row["id"])
                return result
        return None

    def renew(self, task, lease):
        with self.db() as db:
            self._fence(db, task, lease)
            db.execute("UPDATE tasks SET lease_until=? WHERE id=?", (self.now() + 600, task))

    def active(self, task, lease):
        with self.db() as db:
            self._fence(db, task, lease)
            return True

    def checkpoint(self, task, lease, kind, body):
        if kind not in {"versions", "evaluations", "plans", "metrics", "stages"}:
            raise ValueError("invalid artifact kind")
        with self.db() as db:
            row = self._fence(db, task, lease)
            binding = {
                "fact_hash": row["fact_hash"],
                "epoch": row["epoch"],
                "profile": "google-merchant-us-en-text-v1",
                "protocol": "reflection-v1",
                "rubric": "weighted-five-v1",
            }
            self._artifact(db, task, kind, {**body, "binding": binding})
            self._audit(db, "checkpoint", task=task, body={"kind": kind, "hash": digest(body)})

    def finish(self, task, lease, state, selected_hash):
        if state not in {"review_ready", "manual_required", "needs_data", "failed"}:
            raise ValueError("invalid terminal state")
        with self.db() as db:
            self._fence(db, task, lease)
            db.execute(
                "UPDATE tasks SET state=?,selected_hash=?,lease=NULL,lease_until=NULL WHERE id=?",
                (state, selected_hash, task),
            )
            self._audit(db, "task_finished", task=task, body={"state": state})

    def select(self, task, lease, selected_hash, revision=0):
        with self.db() as db:
            self._fence(db, task, lease)
            versions = self._task(db, task)["versions"]
            if not any(
                v["draft_hash"] == selected_hash and v.get("version_index", 0) == revision
                for v in versions
            ):
                raise Conflict("selected artifact unavailable")
            prior = db.execute("SELECT revision FROM selections WHERE task=?", (task,)).fetchone()
            if prior and prior[0] > revision:
                return  # Replaying known earlier stages must not erase a later retained incumbent.
            db.execute("INSERT OR REPLACE INTO selections VALUES(?,?)", (task, revision))
            db.execute("UPDATE tasks SET selected_hash=? WHERE id=?", (selected_hash, task))
            self._audit(
                db,
                "incumbent_selected",
                task=task,
                body={"version": selected_hash, "version_index": revision},
            )

    def _journal_records(self):
        records = []
        head = "0" * 64
        if self.journal.exists():
            with self.journal.open(encoding="utf-8") as file:
                for line in file:
                    record = json.loads(line)
                    if record["previous"] != head or record["hash"] != digest(record["body"]):
                        raise Conflict("usage journal integrity failure")
                    head = digest(record)
                    records.append(record["body"])
        return records, head

    def _append_journal(self, body):
        _, head = self._journal_records()
        record = {"previous": head, "body": body, "hash": digest(body)}
        existed = self.journal.exists()
        with self.journal.open("a", encoding="utf-8") as file:
            file.write(canonical(record) + "\n")
            file.flush()
            os.fsync(file.fileno())
        if not existed and os.name != "nt":
            descriptor = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def _liability(self, db, *, ignore_pause=False, ignore_quarantine=False):
        records, _ = self._journal_records()
        if (
            not ignore_quarantine
            and db.execute("SELECT 1 FROM controls WHERE key='quarantine'").fetchone()
        ):
            return True
        if (
            not ignore_pause
            and db.execute("SELECT 1 FROM controls WHERE key='dispatch_pause'").fetchone()
        ):
            return True
        accepted = set()
        reconciled = set()
        for supplement in db.execute("SELECT * FROM supplements"):
            body = json.loads(supplement["body"])
            if body not in records:
                return True
            reconciled.add(supplement["attempt"])
        for incident in db.execute("SELECT * FROM incidents"):
            body = json.loads(incident["body"])
            if body not in records:
                return True
            accepted.update(body["attempts"])
        final = {}
        for r in records:
            if "attempt" in r:
                final[r["attempt"]] = r
            if r.get("event") == "source_erased" and (
                not db.execute(
                    "SELECT 1 FROM erased_sources WHERE source=?", (r["source"],)
                ).fetchone()
                or db.execute("SELECT 1 FROM imports WHERE id=?", (r["source"],)).fetchone()
            ):
                return True
            if r.get("event") == "grant_amended":
                grant = db.execute(
                    "SELECT max_calls FROM grants WHERE id=?", (r["grant"],)
                ).fetchone()
                latest = next(
                    e
                    for e in reversed(records)
                    if e.get("grant") == r["grant"] and e.get("event") == "grant_amended"
                )
                if not grant or grant[0] != latest["ceiling"]:
                    return True
        known = {r["id"]: r for r in db.execute("SELECT * FROM attempts")}
        if set(final) != set(known):
            return True
        for attempt, record in final.items():
            row = known[attempt]
            if (
                attempt in accepted | reconciled
                and record["status"] == "unknown"
                and row["status"] == "unknown"
                and record.get("receipt") == json.loads(row["receipt"] or "null")
            ):
                continue
            if record["status"] != "known" or row["status"] != "known":
                return True
            if record.get("receipt") != json.loads(row["receipt"] or "null"):
                return True
        return False

    def liability_hold(self):
        with self.db() as db:
            return self._liability(db)

    def reserve(self, task, lease, stage, *, prompt_hash=None, schema_hash=None):
        self.require_disk()
        with self.db() as db:
            row = self._fence(db, task, lease)
            if self._liability(db):
                raise Conflict("global usage liability hold")
            grant = db.execute("SELECT * FROM grants WHERE id=?", (row["grant_id"],)).fetchone()
            if row["calls"] >= 16 or grant["calls"] >= grant["max_calls"]:
                raise Conflict("cumulative allowance exhausted")
            stage_calls = db.execute(
                "SELECT count(*) FROM attempts WHERE task=? AND stage=?", (task, stage)
            ).fetchone()[0]
            if stage_calls >= 2:
                raise Conflict("stage repair allowance exhausted")
            attempt = secrets.token_hex(16)
            db.execute("UPDATE tasks SET calls=calls+1 WHERE id=?", (task,))
            db.execute("UPDATE grants SET calls=calls+1 WHERE id=?", (row["grant_id"],))
            db.execute(
                "INSERT INTO attempts VALUES(?,?,?,'reserved',NULL,?)",
                (attempt, task, stage, self.now()),
            )
            self._append_journal(
                {
                    "attempt": attempt,
                    "task": task,
                    "stage": stage,
                    "status": "reserved",
                    "reservation_seconds": 90,
                    "prompt_hash": prompt_hash,
                    "schema_hash": schema_hash,
                }
            )
            return attempt

    def settle(self, attempt, receipt):
        # Usage survives cancellation. No artifact/selection authority is granted here.
        audited = receipt.get("audited") is True
        known = audited and all(
            type(receipt.get(k)) is int and 0 <= receipt[k] <= 10**9
            for k in ("input_tokens", "output_tokens")
        )
        clean = {
            "audited": audited,
            "unsafe_tool_event": receipt.get("unsafe_tool_event") is True,
            "input_tokens": receipt.get("input_tokens") if known else None,
            "output_tokens": receipt.get("output_tokens") if known else None,
            "elapsed_ms": receipt.get("elapsed_ms")
            if type(receipt.get("elapsed_ms")) is int
            else None,
        }
        status = "known" if known else "unknown"
        with self.db() as db:
            row = db.execute("SELECT * FROM attempts WHERE id=?", (attempt,)).fetchone()
            if not row or row["status"] != "reserved":
                raise Conflict("attempt already settled or unavailable")
            self._append_journal(
                {"attempt": attempt, "task": row["task"], "status": status, "receipt": clean}
            )
            db.execute(
                "UPDATE attempts SET status=?,receipt=? WHERE id=?",
                (status, canonical(clean), attempt),
            )

    def validation_failure(self, task, stage, category):
        if category not in {"parse", "runtime", "budget", "context", "unassessable"}:
            category = "runtime"
        with self.db() as db:
            self._audit(
                db, "validation_failure", task=task, body={"stage": stage, "category": category}
            )

    def _task(self, db, task):
        row = db.execute("SELECT * FROM tasks WHERE id=?", (task,)).fetchone()
        if row is None:
            raise Forbidden("object unavailable")
        result = dict(row)
        result["facts"] = json.loads(result.pop("fact_json"))
        if digest(result["facts"]) != result["fact_hash"]:
            raise Conflict("fact integrity failure")
        snapshot = db.execute("SELECT body FROM snapshots WHERE task=?", (task,)).fetchone()
        result["snapshot"] = json.loads(snapshot[0]) if snapshot else None
        link = db.execute("SELECT * FROM task_links WHERE task=?", (task,)).fetchone()
        result["batch_id"] = link["batch_id"] if link else None
        result["source_id"] = link["source_id"] if link else None
        selection = db.execute("SELECT revision FROM selections WHERE task=?", (task,)).fetchone()
        result["selected_revision"] = selection[0] if selection else 0
        for kind in ("versions", "evaluations", "plans", "metrics", "stages"):
            result[kind] = []
            for artifact in db.execute(
                "SELECT body,hash FROM artifacts WHERE task=? AND kind=? ORDER BY id", (task, kind)
            ):
                body = json.loads(artifact[0])
                if digest(body) != artifact[1]:
                    raise Conflict("artifact integrity failure")
                result[kind].append(body)
        selected = next(
            (
                v
                for v in result["versions"]
                if v["draft_hash"] == result["selected_hash"]
                and v.get("version_index", 0) == result["selected_revision"]
            ),
            None,
        )
        result["selected_artifact_hash"] = digest(selected) if selected else None
        result["attempts"] = [
            {**dict(r), "receipt": json.loads(r["receipt"]) if r["receipt"] else None}
            for r in db.execute("SELECT * FROM attempts WHERE task=? ORDER BY created", (task,))
        ]
        result["warnings"] = [
            {
                "code": "owner_accepted_unknown_history",
                "incident": r[0],
                "observed_safe_usage": False,
            }
            for r in db.execute(
                "WITH RECURSIVE lineage(id) AS (SELECT ? UNION "
                "SELECT l.parent_task FROM task_links l JOIN lineage a ON l.task=a.id "
                "WHERE l.parent_task IS NOT NULL) "
                "SELECT id FROM incidents WHERE task IN (SELECT id FROM lineage)",
                (task,),
            )
        ]
        result["supplements"] = [
            json.loads(r[0])
            for r in db.execute(
                "SELECT s.body FROM supplements s JOIN attempts a ON s.attempt=a.id WHERE a.task=?",
                (task,),
            )
        ]
        return result

    def internal_task(self, task):
        with self.db() as db:
            return self._task(db, task)

    def _scoped_task(self, db, actor, task, roles=None):
        row = db.execute("SELECT workspace FROM tasks WHERE id=?", (task,)).fetchone()
        if not row:
            raise Forbidden("object unavailable")
        self._role(db, actor, row[0], roles)
        return self._task(db, task)

    def task(self, actor, task):
        with self.db() as db:
            result = self._scoped_task(db, actor, task)
            self._role(db, actor, result["workspace"])
            result.pop("lease", None)
            return result

    def tasks(self, actor, workspace, limit=100, offset=0):
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("invalid pagination")
        with self.db() as db:
            self._role(db, actor, workspace)
            return [
                dict(r)
                for r in db.execute(
                    "SELECT t.id,t.state,t.selected_hash,t.calls,t.created,l.batch_id,"
                    "json_extract(t.fact_json,'$.name') AS name, json_extract(t.fact_json,'$.brand') AS brand,"
                    "json_extract(t.fact_json,'$.product_id') AS product_id FROM tasks t LEFT JOIN task_links l "
                    "ON t.id=l.task WHERE t.workspace=? ORDER BY t.created DESC LIMIT ? OFFSET ?",
                    (workspace, limit, offset),
                )
            ]

    def cancel(self, actor, task):
        with self.db() as db:
            row = self._scoped_task(db, actor, task, {"owner", "editor"})
            self._role(db, actor, row["workspace"], {"owner", "editor"})
            db.execute("UPDATE tasks SET state='cancelled',lease=NULL WHERE id=?", (task,))
            self._audit(db, "cancelled", actor=actor, task=task)

    def _invalidate(self, db, workspace):
        db.execute("UPDATE workspaces SET epoch=epoch+1 WHERE id=?", (workspace,))
        db.execute("UPDATE tasks SET state='stale',lease=NULL WHERE workspace=?", (workspace,))

    def invalidate(self, actor, workspace):
        with self.db() as db:
            self._role(db, actor, workspace, {"owner"})
            self._invalidate(db, workspace)
            self._audit(db, "context_invalidated", actor=actor, workspace=workspace)

    def review(
        self,
        actor,
        task,
        version_hash,
        decision,
        reason,
        *,
        acknowledge_unknown=False,
        artifact_hash=None,
    ):
        if decision not in {"accept", "reject", "needs_data"} or not 1 <= len(reason) <= 2000:
            raise ValueError("invalid review")
        with self.db() as db:
            row = self._scoped_task(db, actor, task, {"owner", "reviewer"})
            self._role(db, actor, row["workspace"], {"owner", "reviewer"})
            if row["maker"] == actor:
                raise Forbidden("independent reviewer required")
            if (
                row["state"] != "review_ready"
                or row["selected_hash"] != version_hash
                or not self._current(db, row)
                or self._liability(db)
            ):
                raise Conflict("current eligible version required")
            if not self._eligible(row):
                raise Conflict("hard gates cannot be waived")
            if row["warnings"] and not acknowledge_unknown:
                raise Conflict("explicit unknown-history acknowledgement required")
            if artifact_hash is not None and artifact_hash != row["selected_artifact_hash"]:
                raise Conflict("exact selected artifact required")
            db.execute(
                "INSERT INTO reviews VALUES(?,?,?,?,?,?)",
                (task, version_hash, actor, decision, reason, self.now()),
            )
            self._audit(
                db,
                "reviewed",
                actor=actor,
                task=task,
                body={
                    "version": version_hash,
                    "decision": decision,
                    "unknown_acknowledged": acknowledge_unknown,
                    "artifact_hash": row["selected_artifact_hash"],
                    "version_index": row["selected_revision"],
                },
            )

    def _eligible(self, row):
        from contracts.shelfproof import CheckFinding, JudgeEvaluation

        from .core import check_draft

        selected = next(
            (
                v
                for v in row["versions"]
                if v["draft_hash"] == row["selected_hash"]
                and v.get("version_index", 0) == row["selected_revision"]
            ),
            None,
        )
        evaluation = next(
            (
                e
                for e in row["evaluations"]
                if e["draft_hash"] == row["selected_hash"]
                and e.get("version_index", 0) == row["selected_revision"]
            ),
            None,
        )
        if not selected or not evaluation:
            return False
        checks = check_draft(
            FactPack.model_validate(row["facts"]), Draft.model_validate(selected["draft"])
        )
        checks += [CheckFinding.model_validate(f) for f in evaluation.get("extra_checks", [])]
        return ready(checks, JudgeEvaluation.model_validate(evaluation["evaluation"]))

    def export(self, actor, workspace):
        patches, unresolved = [], []
        with self.db() as db:
            self._role(db, actor, workspace)
            hold = self._liability(db)
            for stub in db.execute(
                "SELECT id FROM tasks WHERE workspace=? ORDER BY created", (workspace,)
            ):
                row = self._task(db, stub["id"])
                approval = db.execute(
                    "SELECT * FROM reviews WHERE task=? ORDER BY created DESC,rowid DESC LIMIT 1",
                    (row["id"],),
                ).fetchone()
                approved = (
                    approval
                    and approval["decision"] == "accept"
                    and approval["hash"] == row["selected_hash"]
                    and approval["actor"] != row["maker"]
                )
                if (
                    hold
                    or row["state"] != "review_ready"
                    or not self._current(db, row)
                    or not approved
                    or not self._eligible(row)
                ):
                    unresolved.append(
                        {
                            "task": row["id"],
                            "state": row["state"],
                            "reason": "not_current_independently_approved",
                        }
                    )
                    continue
                version = next(
                    v
                    for v in row["versions"]
                    if v["draft_hash"] == row["selected_hash"]
                    and v.get("version_index", 0) == row["selected_revision"]
                )
                patches.append(
                    {
                        "product_id": row["facts"]["product_id"],
                        "task": row["id"],
                        "structured_title": {
                            "content": version["draft"]["title"],
                            "digital_source_type": "trained_algorithmic_media",
                        },
                        "structured_description": {
                            "content": version["draft"]["description"],
                            "digital_source_type": "trained_algorithmic_media",
                        },
                        "fact_hash": row["fact_hash"],
                        "snapshot_hash": digest(row["snapshot"]),
                        "source_ref": row["facts"]["source_ref"],
                        "version_hash": row["selected_hash"],
                        "version_index": row["selected_revision"],
                        "artifact_hash": row["selected_artifact_hash"],
                        "reviewer": approval["actor"],
                        "warnings": row["warnings"],
                    }
                )
            duplicate_ids = {
                key for key, count in Counter(p["product_id"] for p in patches).items() if count > 1
            }
            unresolved.extend(
                {
                    "task": p["task"],
                    "state": "review_ready",
                    "reason": "duplicate_approved_product_identity",
                }
                for p in patches
                if p["product_id"] in duplicate_ids
            )
            patches = [p for p in patches if p["product_id"] not in duplicate_ids]
            self._audit(
                db,
                "patch_exported",
                actor=actor,
                workspace=workspace,
                body={"approved": len(patches), "unresolved": len(unresolved)},
            )
        return {
            "schema": "shelfproof-partial-text-patch-v1",
            "patches": patches,
            "unresolved": unresolved,
            "approved_count": len(patches),
            "total": len(patches) + len(unresolved),
        }

    def audit(self, actor, task):
        with self.db() as db:
            row = self._scoped_task(db, actor, task)
            self._role(db, actor, row["workspace"])
            return [
                {**dict(r), "body": json.loads(r["body"])}
                for r in db.execute("SELECT * FROM audit WHERE task=? ORDER BY seq", (task,))
            ]
