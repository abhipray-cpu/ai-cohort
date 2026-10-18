"""Scoped durable state and conservative independent usage liabilities."""

import csv
import hashlib
import io
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from contracts.catalogbridge import BatchSpec, Product, Review, Usage

from .matching import digest
from .runtime import receipt_evidence


def uid():
    return secrets.token_hex(16)


def encode(value):
    return json.dumps(value, sort_keys=True)


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class Store:
    def __init__(self, root, journal_dir=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "catalogbridge.sqlite3"
        self.journal_dir = Path(journal_dir or self.root.parent / (self.root.name + "-usage"))
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.journal = self.journal_dir / "liabilities.sqlite3"
        missing_journal = self.path.exists() and not self.journal.exists()
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS feeds(id TEXT PRIMARY KEY, workspace TEXT NOT NULL,
              kind TEXT NOT NULL, hash TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS batches(id TEXT PRIMARY KEY, workspace TEXT NOT NULL,
              spec TEXT NOT NULL, state TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, batch_id TEXT REFERENCES batches(id),
              source TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
              result TEXT NOT NULL DEFAULT '{}', review TEXT, lease TEXT, deadline REAL);
            CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, batch_id TEXT NOT NULL,
              task_id TEXT NOT NULL, route TEXT NOT NULL, reserved INTEGER NOT NULL,
              state TEXT NOT NULL, usage TEXT, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,
              batch_id TEXT, kind TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY, salt TEXT NOT NULL,
              hash TEXT NOT NULL, workspace TEXT NOT NULL, role TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, name TEXT NOT NULL,
              csrf TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS calibrations(id TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS draft_cache(workspace TEXT NOT NULL, cache_key TEXT NOT NULL,
              task_id TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL,
              PRIMARY KEY(workspace,cache_key));
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS idempotency(workspace TEXT, key TEXT, hash TEXT, batch_id TEXT,
              PRIMARY KEY(workspace,key));
            """)
            db.execute("INSERT OR IGNORE INTO meta VALUES('identity', ?)", (uid(),))
            self.identity = db.execute("SELECT value FROM meta WHERE key='identity'").fetchone()[0]
            if missing_journal:
                db.execute("INSERT OR REPLACE INTO meta VALUES('missing_journal','true')")
        with sqlite3.connect(self.journal) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS entries(id TEXT PRIMARY KEY, identity TEXT, body TEXT)"
            )

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15, factory=ClosingConnection)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    @contextmanager
    def write(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def event(self, db, batch_id, kind, body):
        db.execute(
            "INSERT INTO events(batch_id,kind,body,created) VALUES(?,?,?,?)",
            (batch_id, kind, encode(body), time.time()),
        )

    def import_feed(self, workspace, kind, rows):
        if kind not in {"master", "supplier"} or not 1 <= len(rows) <= 25000:
            raise ValueError("invalid feed")
        if len({row.id for row in rows}) != len(rows):
            raise ValueError("duplicate product id")
        body = [r.model_dump() for r in rows]
        record = {"id": uid(), "workspace": workspace, "kind": kind, "hash": digest(body)}
        with self.write() as db:
            db.execute(
                "INSERT INTO feeds VALUES(?,?,?,?,?)",
                (record["id"], workspace, kind, record["hash"], encode(body)),
            )
        return {**record, "rows": len(rows)}

    def feed(self, workspace, feed_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM feeds WHERE id=? AND workspace=?", (feed_id, workspace)
            ).fetchone()
        if not row:
            raise KeyError("feed not found")
        result = dict(row)
        result["records"] = [Product.model_validate(r) for r in json.loads(result.pop("body"))]
        if digest([r.model_dump() for r in result["records"]]) != result["hash"]:
            raise ValueError("source integrity failure")
        return result

    def create_batch(self, workspace, spec: BatchSpec, idempotency_key=None):
        if spec.budget_mode == "strict":
            raise ValueError("hard token enforcement unavailable on installed CLI")
        master, supplier = (
            self.feed(workspace, spec.master_id),
            self.feed(workspace, spec.supplier_id),
        )
        if master["kind"] != "master" or supplier["kind"] != "supplier":
            raise ValueError("feed roles mismatch")
        batch_id = uid()
        with self.write() as db:
            if idempotency_key:
                old = db.execute(
                    "SELECT hash,batch_id FROM idempotency WHERE workspace=? AND key=?",
                    (workspace, idempotency_key),
                ).fetchone()
                if old:
                    if old["hash"] != digest(spec.model_dump()):
                        raise ValueError("idempotency payload conflict")
                    return self.batch(workspace, old["batch_id"])
                db.execute(
                    "INSERT INTO idempotency VALUES(?,?,?,?)",
                    (workspace, idempotency_key, digest(spec.model_dump()), batch_id),
                )
            db.execute(
                "INSERT INTO batches VALUES(?,?,?,?,?)",
                (batch_id, workspace, spec.model_dump_json(), "draft", time.time()),
            )
            for row in supplier["records"]:
                db.execute(
                    "INSERT INTO tasks(id,batch_id,source,state) VALUES(?,?,?,?)",
                    (uid(), batch_id, row.model_dump_json(), "queued"),
                )
            self.event(
                db, batch_id, "batch_created", {"source_hashes": [master["hash"], supplier["hash"]]}
            )
        return self.batch(workspace, batch_id)

    def batch(self, workspace, batch_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM batches WHERE id=? AND workspace=?", (batch_id, workspace)
            ).fetchone()
        if not row:
            raise KeyError("batch not found")
        return {**dict(row), "spec": json.loads(row["spec"])}

    def batches(self, workspace):
        with self.connect() as db:
            return [
                self.batch(workspace, r[0])
                for r in db.execute(
                    "SELECT id FROM batches WHERE workspace=? ORDER BY created DESC LIMIT 100",
                    (workspace,),
                )
            ]

    def tasks(self, workspace, batch_id, offset=0, limit=50):
        self.batch(workspace, batch_id)
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM tasks WHERE batch_id=? ORDER BY rowid LIMIT ? OFFSET ?",
                (batch_id, min(100, limit), max(0, offset)),
            ).fetchall()
        return [
            {
                **dict(r),
                "source": json.loads(r["source"]),
                "result": json.loads(r["result"]),
                "review": json.loads(r["review"]) if r["review"] else None,
            }
            for r in rows
        ]

    def start(self, workspace, batch_id):
        self.batch(workspace, batch_id)
        with self.write() as db:
            state = db.execute("SELECT state FROM batches WHERE id=?", (batch_id,)).fetchone()[0]
            if state not in {"draft", "partial"}:
                raise ValueError("batch not startable")
            if (
                db.execute(
                    "SELECT count(*) FROM batches WHERE state IN ('queued','running')"
                ).fetchone()[0]
                >= 20
            ):
                raise ValueError("batch queue capacity reached")
            db.execute("UPDATE batches SET state='queued' WHERE id=?", (batch_id,))
            if state == "partial":
                db.execute(
                    "UPDATE tasks SET state='queued' WHERE batch_id=? AND state='failed'",
                    (batch_id,),
                )
            self.event(db, batch_id, "batch_started", {})

    def cancel(self, workspace, batch_id):
        self.batch(workspace, batch_id)
        with self.write() as db:
            db.execute("UPDATE batches SET state='cancelled' WHERE id=?", (batch_id,))
            db.execute(
                "UPDATE tasks SET state='cancelled',lease=NULL WHERE batch_id=? AND state IN ('queued','running')",
                (batch_id,),
            )
            self.event(db, batch_id, "cancelled", {})

    def journal_write(self, attempt_id, body):
        with sqlite3.connect(self.journal, timeout=15) as db:
            db.execute(
                "INSERT INTO entries VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                (attempt_id, self.identity, encode(body)),
            )

    def journal_ok(self, db):
        if db.execute("SELECT 1 FROM meta WHERE key='missing_journal'").fetchone():
            return False
        if not self.journal.exists():
            return False
        with sqlite3.connect(self.journal) as journal:
            entries = dict(
                journal.execute("SELECT id,body FROM entries WHERE identity=?", (self.identity,))
            )
        rows = db.execute("SELECT id,state,usage FROM attempts").fetchall()
        actual = {r["id"]: encode({"state": r["state"], "usage": r["usage"]}) for r in rows}
        return actual == entries

    def _runtime_status(self, db, workspace):
        unknown = db.execute(
            "SELECT count(*) FROM attempts a JOIN batches b ON b.id=a.batch_id "
            "WHERE b.workspace=? AND a.state='usage_unknown'",
            (workspace,),
        ).fetchone()[0]
        row = db.execute(
            "SELECT value FROM meta WHERE key=?", ("runtime_circuit:" + workspace,)
        ).fetchone()
        return {
            "open": bool(unknown or row),
            "unknown_attempts": unknown,
            "reason": "unknown_usage"
            if unknown
            else (json.loads(row[0])["category"] if row else None),
        }

    def runtime_status(self, workspace):
        with self.connect() as db:
            return self._runtime_status(db, workspace)

    def open_runtime_circuit(self, workspace, batch_id, evidence):
        with self.write() as db:
            if not db.execute(
                "SELECT 1 FROM batches WHERE id=? AND workspace=?", (batch_id, workspace)
            ).fetchone():
                raise KeyError("batch not found")
            key = "runtime_circuit:" + workspace
            if not db.execute("SELECT 1 FROM meta WHERE key=?", (key,)).fetchone():
                db.execute(
                    "INSERT INTO meta VALUES(?,?)", (key, encode(evidence | {"batch_id": batch_id}))
                )
                self.event(db, batch_id, "provider_circuit_opened", evidence)

    def acknowledge_runtime(self, workspace, actor, reason):
        if len(reason.strip()) < 12:
            raise ValueError("investigation reason required")
        with self.write() as db:
            if not self.journal_ok(db):
                raise ValueError("unknown usage journal divergence")
            if db.execute("SELECT 1 FROM meta WHERE key='restore_quarantine'").fetchone():
                raise ValueError("restore quarantine blocks retry")
            active = db.execute(
                "SELECT 1 FROM attempts a JOIN batches b ON b.id=a.batch_id WHERE b.workspace=? AND a.state IN ('usage_unknown','reserved') LIMIT 1",
                (workspace,),
            ).fetchone()
            if active:
                raise ValueError("unknown or in-flight usage must be reconciled first")
            key = "runtime_circuit:" + workspace
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            if row:
                evidence = json.loads(row[0])
                db.execute("DELETE FROM meta WHERE key=?", (key,))
                self.event(
                    db,
                    evidence.get("batch_id"),
                    "runtime_retry_authorized",
                    {"actor": actor, "reason": reason, "health_verified": False},
                )

    def reserve(self, batch_id, task_id, route, amount, *, expected_lease=None):
        if amount <= 0 or route not in {"economy", "strong", "repair"}:
            raise ValueError("invalid reservation")
        with self.write() as db:
            if db.execute("SELECT 1 FROM meta WHERE key='restore_quarantine'").fetchone():
                raise ValueError("restore quarantine blocks dispatch")
            if not self.journal_ok(db):
                raise ValueError("unknown usage journal divergence")
            b = db.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
            task = db.execute(
                "SELECT * FROM tasks WHERE id=? AND batch_id=?", (task_id, batch_id)
            ).fetchone()
            if not b or not task or b["state"] == "cancelled":
                raise ValueError("cancelled or missing task")
            if self._runtime_status(db, b["workspace"])["open"]:
                raise ValueError("unknown usage or provider failure circuit blocks dispatch")
            if expected_lease and (
                task["lease"] != expected_lease
                or task["state"] != "running"
                or task["deadline"] <= time.time()
            ):
                raise ValueError("stale worker lease before dispatch")
            spec = BatchSpec.model_validate_json(b["spec"])
            attempts = db.execute("SELECT * FROM attempts WHERE batch_id=?", (batch_id,)).fetchall()
            if any(a["state"] == "usage_unknown" for a in attempts):
                raise ValueError("unknown usage blocks dispatch")
            if any(a["state"] == "reserved" for a in attempts):
                raise ValueError("in-flight usage must settle before further dispatch")

            def cost(a):
                return Usage.model_validate_json(a["usage"]).total if a["usage"] else a["reserved"]

            own = [a for a in attempts if a["task_id"] == task_id]
            if (
                sum(map(cost, attempts)) + amount > spec.token_budget
                or sum(map(cost, own)) + amount > spec.row_token_budget
                or len(attempts) >= spec.call_budget
                or len(own) >= 3
            ):
                raise ValueError("budget exhausted")
            attempt = uid()
            self.journal_write(attempt, {"state": "reserved", "usage": None})
            db.execute(
                "INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)",
                (attempt, batch_id, task_id, route, amount, "reserved", None, time.time()),
            )
            self.event(
                db,
                batch_id,
                "reserved",
                {"attempt": attempt, "task": task_id, "tokens": amount, "route": route},
            )
        return attempt

    def settle(self, attempt_id, usage: Usage | None, *, runtime_evidence=None):
        with self.write() as db:
            row = db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
            if not row:
                raise KeyError("attempt not found")
            serialized = usage.model_dump_json() if usage else None
            if row["state"] == "settled":
                if row["usage"] != serialized:
                    raise ValueError("settlement conflict")
                return
            state = "settled" if usage else "usage_unknown"
            self.journal_write(attempt_id, {"state": state, "usage": serialized})
            db.execute(
                "UPDATE attempts SET state=?,usage=? WHERE id=?", (state, serialized, attempt_id)
            )
            if runtime_evidence is not None:
                self.event(
                    db,
                    row["batch_id"],
                    "runtime_receipt",
                    {"attempt": attempt_id, "diagnostics": receipt_evidence(runtime_evidence)},
                )
            self.event(
                db,
                row["batch_id"],
                state,
                {
                    "attempt": attempt_id,
                    "usage": usage.model_dump() if usage else None,
                    "overrun": bool(usage and usage.total > row["reserved"]),
                },
            )

    def analytics(self, workspace, batch_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            scoped = db.execute(
                "SELECT * FROM batches WHERE id=? AND workspace=?", (batch_id, workspace)
            ).fetchone()
            if not scoped:
                raise KeyError("batch not found")
            batch = {**dict(scoped), "spec": json.loads(scoped["spec"])}
            rows = db.execute("SELECT * FROM attempts WHERE batch_id=?", (batch_id,)).fetchall()
            states = dict(
                db.execute(
                    "SELECT state,count(*) FROM tasks WHERE batch_id=? GROUP BY state", (batch_id,)
                )
            )
            journal_ok = self.journal_ok(db)
            runtime_circuit = self._runtime_status(db, workspace)
        measured = [Usage.model_validate_json(r["usage"]) for r in rows if r["usage"]]
        tokens = sum(u.total for u in measured)
        reserved = sum(r["reserved"] for r in rows if not r["usage"])
        spec = BatchSpec.model_validate(batch["spec"])
        rate = spec.rate_card
        unknown = sum(r["state"] == "usage_unknown" for r in rows)
        numerator = 0
        bases, units = set(), set()
        for attempt in rows:
            model = spec.strong_model if attempt["route"] == "strong" else spec.economy_model
            applied = spec.model_rates.get(model, rate)
            bases.add(applied.basis)
            units.add(applied.unit)
            if attempt["usage"]:
                u = Usage.model_validate_json(attempt["usage"])
                numerator += (
                    (u.input_tokens - u.cached_input_tokens) * applied.input_microunits_per_million
                    + u.cached_input_tokens * applied.cached_microunits_per_million
                    + u.output_tokens * applied.output_microunits_per_million
                )
        priced = (
            bool(rows)
            and bases != {"unpriced"}
            and "unpriced" not in bases
            and len(units) == 1
            and len(bases) == 1
            and not reserved
        )
        estimate = (numerator + 999999) // 1000000 if priced else None
        return {
            "tokens": tokens,
            "reserved_tokens": reserved,
            "unknown_attempts": unknown,
            "attempts": len(rows),
            "rows": sum(states.values()),
            "states": states,
            "remaining_tokens": max(0, batch["spec"]["token_budget"] - tokens - reserved),
            "journal_consistent": journal_ok,
            "runtime_circuit": runtime_circuit,
            "budget_mode": batch["spec"]["budget_mode"],
            "cost_basis": next(iter(bases)) if len(bases) == 1 else "unpriced",
            "cost_unit": next(iter(units)) if len(units) == 1 else rate.unit,
            "estimated_microunits": estimate,
            "cost_per_input_row_microunits": (estimate + sum(states.values()) - 1)
            // sum(states.values())
            if estimate is not None and states
            else None,
            "actual_charge": None,
            "routes": {
                route: sum(r["route"] == route for r in rows)
                for route in ("economy", "strong", "repair")
            },
        }

    def claim(self):
        with self.write() as db:
            # Interrupted dispatches retain liabilities; never automatic redispatch.
            expired = db.execute(
                "SELECT * FROM tasks WHERE state='running' AND deadline<?", (time.time(),)
            ).fetchall()
            for row in expired:
                db.execute(
                    "UPDATE tasks SET state='failed',lease=NULL,result=? WHERE id=?",
                    (
                        encode({"reason": "worker interrupted; inspect usage liabilities"}),
                        row["id"],
                    ),
                )
                db.execute(
                    "UPDATE batches SET state='partial' WHERE id=? AND state!='cancelled'",
                    (row["batch_id"],),
                )
                self.event(db, row["batch_id"], "worker_interrupted", {"task": row["id"]})
            row = db.execute(
                "SELECT tasks.*,batches.workspace,batches.spec FROM tasks JOIN batches ON batches.id=tasks.batch_id WHERE tasks.state='queued' AND batches.state IN ('queued','running') ORDER BY tasks.rowid LIMIT 1"
            ).fetchone()
            if not row:
                return None
            lease = uid()
            db.execute(
                "UPDATE tasks SET state='running',lease=?,deadline=? WHERE id=?",
                (lease, time.time() + 260, row["id"]),
            )
            db.execute("UPDATE batches SET state='running' WHERE id=?", (row["batch_id"],))
            return {
                **dict(row),
                "lease": lease,
                "spec": BatchSpec.model_validate_json(row["spec"]),
                "source": Product.model_validate_json(row["source"]),
            }

    def cached_draft(self, workspace, cache_key):
        with self.connect() as db:
            row = db.execute(
                "SELECT t.result,t.id,t.batch_id,c.created,c.expires FROM draft_cache c "
                "JOIN tasks t ON t.id=c.task_id JOIN batches b ON b.id=t.batch_id "
                "WHERE c.workspace=? AND b.workspace=? AND c.cache_key=? AND c.expires>? "
                "AND t.review IS NULL AND t.state IN ('needs_review','recommended_match') "
                "AND b.state!='cancelled'",
                (workspace, workspace, cache_key, time.time()),
            ).fetchone()
        return dict(row) if row else None

    def checkpoint(self, task, result, state="needs_review", *, draft_cache_key=None):
        with self.write() as db:
            changed = db.execute(
                "UPDATE tasks SET state=?,result=?,revision=revision+1,lease=NULL WHERE id=? AND lease=? AND state='running' AND deadline>?",
                (state, encode(result), task["id"], task["lease"], time.time()),
            ).rowcount
            if not changed:
                raise ValueError("stale worker lease")
            if draft_cache_key:
                now = time.time()
                db.execute(
                    "DELETE FROM draft_cache WHERE workspace=? AND expires<=?",
                    (task["workspace"], now),
                )
                db.execute(
                    "INSERT OR REPLACE INTO draft_cache VALUES(?,?,?,?,?)",
                    (task["workspace"], draft_cache_key, task["id"], now, now + 86400),
                )
                db.execute(
                    "DELETE FROM draft_cache WHERE workspace=? AND rowid IN "
                    "(SELECT rowid FROM draft_cache WHERE workspace=? ORDER BY created DESC,rowid DESC LIMIT -1 OFFSET 5000)",
                    (task["workspace"], task["workspace"]),
                )
            self.event(
                db,
                task["batch_id"],
                "checkpoint",
                {"task": task["id"], "state": state, "reason": result.get("reason")},
            )
            active = db.execute(
                "SELECT count(*) FROM tasks WHERE batch_id=? AND state IN ('queued','running')",
                (task["batch_id"],),
            ).fetchone()[0]
            if not active:
                failed = db.execute(
                    "SELECT count(*) FROM tasks WHERE batch_id=? AND state='failed'",
                    (task["batch_id"],),
                ).fetchone()[0]
                db.execute(
                    "UPDATE batches SET state=? WHERE id=? AND state!='cancelled'",
                    ("partial" if failed else "review_ready", task["batch_id"]),
                )

    def review(self, workspace, task_id, actor, review: Review):
        with self.write() as db:
            row = db.execute(
                "SELECT tasks.*,batches.workspace,batches.spec FROM tasks JOIN batches ON batches.id=tasks.batch_id WHERE tasks.id=? AND workspace=?",
                (task_id, workspace),
            ).fetchone()
            if not row:
                raise KeyError("task not found")
            if (
                row["state"] in {"queued", "running", "cancelled"}
                or row["revision"] != review.expected_revision
            ):
                raise ValueError("stale or unfinished task")
            spec = BatchSpec.model_validate_json(row["spec"])
            gallery = self.feed(workspace, spec.master_id)["records"]
            result = json.loads(row["result"])
            candidate = review.candidate_id or result.get("candidate_id")
            if review.action != "reject" and candidate not in {r.id for r in gallery}:
                raise ValueError("candidate required from current master")
            payload = {
                **review.model_dump(),
                "candidate_id": candidate,
                "actor": actor,
                "created": time.time(),
            }
            db.execute(
                "UPDATE tasks SET review=?,revision=revision+1 WHERE id=?",
                (encode(payload), task_id),
            )
            self.event(db, row["batch_id"], "review", {"task": task_id, **payload})

    def export(self, workspace, batch_id):
        batch = self.batch(workspace, batch_id)
        master = self.feed(workspace, batch["spec"]["master_id"])
        supplier = self.feed(workspace, batch["spec"]["supplier_id"])
        with self.write() as db:
            tasks = db.execute(
                "SELECT * FROM tasks WHERE batch_id=? ORDER BY rowid", (batch_id,)
            ).fetchall()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["supplier_id", "master_id", "reviewer", "review_revision"])
            included = 0
            for task in tasks:
                if not task["review"]:
                    continue
                review = json.loads(task["review"])
                if review["action"] == "reject":
                    continue

                def safe(value):
                    value = str(value)
                    return (
                        "'" + value
                        if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
                        else value
                    )

                writer.writerow(
                    [
                        safe(json.loads(task["source"])["id"]),
                        safe(review["candidate_id"]),
                        safe(review["actor"]),
                        task["revision"],
                    ]
                )
                included += 1
            self.event(
                db,
                batch_id,
                "export",
                {
                    "included": included,
                    "total": len(tasks),
                    "hash": hashlib.sha256(output.getvalue().encode()).hexdigest(),
                },
            )
            return output.getvalue(), {
                "included": included,
                "total": len(tasks),
                "excluded": len(tasks) - included,
                "master_hash": master["hash"],
                "supplier_hash": supplier["hash"],
                "batch_id": batch_id,
                "task_revisions": {t["id"]: t["revision"] for t in tasks},
                "unresolved": [
                    {
                        "supplier_id": json.loads(t["source"])["id"],
                        "state": t["state"],
                        "reason": json.loads(t["result"]).get("reason", ""),
                    }
                    for t in tasks
                    if not t["review"]
                ],
            }

    def audit(self, workspace, batch_id):
        self.batch(workspace, batch_id)
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM events WHERE batch_id=? ORDER BY seq DESC LIMIT 100", (batch_id,)
                )
            ]
