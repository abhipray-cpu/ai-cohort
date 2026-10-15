"""Transactional cases, fenced jobs, durable evidence, reviews and exports."""

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from propertybrief_api.sources import REQUIRED, digest, now


def identifier():
    return str(uuid.uuid4())


def decoded(row):
    if row is None:
        return None
    result = dict(row)
    for key in tuple(result):
        if key.endswith("_json"):
            value = result.pop(key)
            result[key[:-5]] = json.loads(value) if value is not None else None
    return result


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "propertybrief.sqlite3"
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS cases(
                    id TEXT PRIMARY KEY,input_json TEXT NOT NULL,identity_json TEXT,
                    candidates_json TEXT NOT NULL DEFAULT '[]',revision INTEGER NOT NULL DEFAULT 1,
                    actor TEXT NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs(
                    id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id),
                    input_json TEXT NOT NULL,identity_json TEXT NOT NULL,question TEXT NOT NULL,
                    request_key TEXT NOT NULL,request_hash TEXT NOT NULL,status TEXT NOT NULL,
                    created_at TEXT NOT NULL,deadline TEXT,lease TEXT,lease_until TEXT,
                    actions INTEGER NOT NULL DEFAULT 0,model_calls INTEGER NOT NULL DEFAULT 0,
                    http_attempts INTEGER NOT NULL DEFAULT 0,cancelled INTEGER NOT NULL DEFAULT 0,
                    observations_json TEXT NOT NULL DEFAULT '{}',state_json TEXT NOT NULL DEFAULT '{}',
                    stop_reason TEXT,grant INTEGER NOT NULL DEFAULT 1,
                    action_base INTEGER NOT NULL DEFAULT 0,model_base INTEGER NOT NULL DEFAULT 0,
                    http_base INTEGER NOT NULL DEFAULT 0,UNIQUE(case_id,request_key));
                CREATE TABLE IF NOT EXISTS messages(
                    id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id),
                    run_id TEXT NOT NULL REFERENCES runs(id),content TEXT NOT NULL,actor TEXT NOT NULL,
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS snapshots(
                    id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),
                    payload_json TEXT NOT NULL,sha256 TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT NOT NULL REFERENCES runs(id),
                    stage TEXT NOT NULL,outcome TEXT NOT NULL,detail TEXT NOT NULL,
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reports(
                    id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),
                    payload_json TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,
                    reviewed_by TEXT,reviewed_at TEXT,notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS exports(
                    id TEXT PRIMARY KEY,report_id TEXT NOT NULL REFERENCES reports(id),
                    payload_json TEXT NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS heartbeat(id INTEGER PRIMARY KEY,updated_at TEXT);
                PRAGMA user_version=1;
            """)

    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def create_case(self, value, actor):
        cid = identifier()
        with self.connect() as db:
            db.execute(
                "INSERT INTO cases(id,input_json,actor,created_at) VALUES(?,?,?,?)",
                (cid, value.model_dump_json(), actor, now()),
            )
        return self.case(cid)

    def cases(self):
        with self.connect() as db:
            return [
                decoded(row)
                for row in db.execute("SELECT * FROM cases ORDER BY created_at DESC LIMIT 200")
            ]

    def case(self, cid):
        with self.connect() as db:
            result = decoded(db.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone())
            if result:
                result["messages"] = [
                    dict(row)
                    for row in db.execute(
                        "SELECT * FROM messages WHERE case_id=? ORDER BY created_at", (cid,)
                    )
                ]
                result["runs"] = [
                    dict(row)
                    for row in db.execute(
                        "SELECT id,status,question,created_at FROM runs WHERE case_id=? ORDER BY created_at DESC",
                        (cid,),
                    )
                ]
            return result

    def save_candidates(self, cid, candidates):
        with self.connect() as db:
            if not db.execute(
                "UPDATE cases SET candidates_json=? WHERE id=? AND identity_json IS NULL",
                (json.dumps(candidates), cid),
            ).rowcount:
                raise ValueError("Case missing or identity already confirmed")

    def confirm_identity(self, cid, candidate_id, revision, actor):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            item = decoded(db.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone())
            if not item or item["revision"] != revision or item["identity"]:
                raise ValueError("Identity revision conflict")
            identity = next((c for c in item["candidates"] if c["id"] == candidate_id), None)
            if not identity:
                raise ValueError("Unknown candidate")
            identity["confirmed_by"] = actor
            db.execute(
                "UPDATE cases SET identity_json=?,revision=revision+1 WHERE id=?",
                (json.dumps(identity), cid),
            )
        return self.case(cid)

    def enqueue(self, cid, question, key, actor, refresh=False):
        if not key or len(key) > 150:
            raise ValueError("Supply a bounded idempotency key")
        request_hash = digest([question, refresh])
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT id,request_hash FROM runs WHERE case_id=? AND request_key=?", (cid, key)
            ).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise ValueError("Idempotency key reused with different input")
                rid = existing["id"]
            else:
                item = decoded(db.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone())
                if not item or not item["identity"]:
                    raise ValueError("Confirm a property identity first")
                if (
                    db.execute(
                        "SELECT COUNT(*) FROM runs WHERE status IN ('queued','running')"
                    ).fetchone()[0]
                    >= 20
                ):
                    raise ValueError("Investigation queue at capacity")
                if db.execute(
                    "SELECT 1 FROM runs WHERE case_id=? AND status IN ('queued','running')", (cid,)
                ).fetchone():
                    raise ValueError("An investigation for this case is already active")
                prior = db.execute(
                    "SELECT observations_json FROM runs WHERE case_id=? ORDER BY created_at DESC LIMIT 1",
                    (cid,),
                ).fetchone()
                observations = prior[0] if prior and not refresh else "{}"
                rid = identifier()
                db.execute(
                    """INSERT INTO runs(id,case_id,input_json,identity_json,question,request_key,
                    request_hash,status,created_at,observations_json) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        rid,
                        cid,
                        json.dumps(item["input"]),
                        json.dumps(item["identity"]),
                        question,
                        key,
                        request_hash,
                        "queued",
                        now(),
                        observations,
                    ),
                )
                db.execute(
                    "INSERT INTO messages VALUES(?,?,?,?,?,?)",
                    (identifier(), cid, rid, question, actor, now()),
                )
                from propertybrief_api.evidence import identity_observation

                identity_result = identity_observation(item["identity"])
                identity_sid = digest(["identity", rid])[:32]
                identity_result["snapshot_id"] = identity_sid
                db.execute(
                    "INSERT INTO snapshots VALUES(?,?,?,?)",
                    (identity_sid, rid, json.dumps(identity_result), identity_result["sha256"]),
                )
                history = [
                    row[0]
                    for row in db.execute(
                        "SELECT content FROM messages WHERE case_id=? ORDER BY created_at DESC LIMIT 6",
                        (cid,),
                    )
                ]
                prior_report = db.execute(
                    "SELECT r.payload_json FROM reports r JOIN runs j ON j.id=r.run_id WHERE j.case_id=? ORDER BY r.created_at DESC LIMIT 1",
                    (cid,),
                ).fetchone()
                conversation = "\n".join(reversed(history))
                if prior_report:
                    conversation += (
                        "\nPrevious report (interpretation, verify against current evidence): "
                        + json.dumps(json.loads(prior_report[0])["draft"])
                    )
                db.execute(
                    "UPDATE runs SET state_json=? WHERE id=?",
                    (json.dumps({"conversation": conversation[:8000]}), rid),
                )
        return self.run(rid)

    def claim(self, seconds=900):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR REPLACE INTO heartbeat VALUES(1,?)", (now(),))
            if db.execute(
                "SELECT 1 FROM runs WHERE status='running' AND lease_until>=?", (now(),)
            ).fetchone():
                return None
            row = db.execute(
                """SELECT * FROM runs WHERE status='queued' OR
                (status='running' AND lease_until<?) ORDER BY created_at LIMIT 1""",
                (now(),),
            ).fetchone()
            if not row:
                return None
            token = identifier()
            deadline = (
                row["deadline"] or (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat()
            )
            lease_until = (datetime.now(UTC) + timedelta(seconds=150)).isoformat()
            db.execute(
                "UPDATE runs SET status='running',lease=?,lease_until=?,deadline=? WHERE id=?",
                (token, lease_until, deadline, row["id"]),
            )
            rid = row["id"]
            from propertybrief_api.evidence import identity_observation

            identity_result = identity_observation(json.loads(row["identity_json"]))
            identity_sid = digest(["identity", rid])[:32]
            identity_result["snapshot_id"] = identity_sid
            db.execute(
                "INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?)",
                (identity_sid, rid, json.dumps(identity_result), identity_result["sha256"]),
            )
        return self.run(rid)

    def _fence(self, db, rid, lease, work=False):
        row = db.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
        if not row or row["lease"] != lease or row["status"] != "running":
            raise ValueError("Worker lease lost")
        if work and row["cancelled"]:
            raise ValueError("Investigation cancelled")
        if work and row["deadline"] <= now():
            raise ValueError("Investigation deadline exceeded")
        return row

    def reserve(self, rid, lease, counter, limit):
        bases = {
            "actions": "action_base",
            "model_calls": "model_base",
            "http_attempts": "http_base",
        }
        if counter not in bases:
            raise ValueError("Invalid budget counter")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._fence(db, rid, lease, work=True)
            if (
                row[counter] - row[bases[counter]] >= limit
                or row[counter] >= {"actions": 32, "model_calls": 48, "http_attempts": 96}[counter]
            ):
                raise ValueError(f"{counter} budget exhausted")
            db.execute(
                f"UPDATE runs SET {counter}={counter}+1,lease_until=? WHERE id=?",
                ((datetime.now(UTC) + timedelta(seconds=150)).isoformat(), rid),
            )

    def event(self, rid, stage, outcome, detail):
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(run_id,stage,outcome,detail,created_at) VALUES(?,?,?,?,?)",
                (rid, stage, outcome, str(detail)[:2000], now()),
            )

    def save_state(self, rid, lease, state):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._fence(db, rid, lease)
            db.execute("UPDATE runs SET state_json=? WHERE id=?", (json.dumps(state), rid))

    def save_observation(self, rid, lease, source, result):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._fence(db, rid, lease)
            observation = dict(result)
            sid = digest([source, result["sha256"], result["retrieved_at"], rid])[:32]
            observation["snapshot_id"] = sid
            db.execute(
                "INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?)",
                (sid, rid, json.dumps(observation), result["sha256"]),
            )
            observations = json.loads(row["observations_json"])
            observations[source] = observation
            db.execute(
                "UPDATE runs SET observations_json=? WHERE id=?", (json.dumps(observations), rid)
            )

    def run(self, rid):
        with self.connect() as db:
            result = decoded(db.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone())
            if result:
                result["events"] = [
                    dict(row)
                    for row in db.execute("SELECT * FROM events WHERE run_id=? ORDER BY id", (rid,))
                ]
                report = db.execute(
                    "SELECT * FROM reports WHERE run_id=? ORDER BY created_at DESC LIMIT 1", (rid,)
                ).fetchone()
                result["report"] = decoded(report)
                result["preview"] = self.preview(result["observations"])
                identity_row = db.execute(
                    "SELECT payload_json FROM snapshots WHERE id=?",
                    (digest(["identity", rid])[:32],),
                ).fetchone()
                if identity_row:
                    result["preview"]["sources"].append(json.loads(identity_row[0]))
            return result

    @staticmethod
    def preview(observations):
        return {
            "label": "Recorded observations; narrative review pending",
            "coverage": {
                key: observations.get(key, {}).get("completeness", "not_checked")
                for key in REQUIRED
            },
            "sources": [
                {
                    "source": key,
                    "count": value["count"],
                    "outcome": value["outcome"],
                    "completeness": value["completeness"],
                    "flags": value["flags"],
                    "retrieved_at": value["retrieved_at"],
                    "snapshot_id": value.get("snapshot_id"),
                    "records": value["records"][:12],
                }
                for key, value in observations.items()
            ],
        }

    def finish(self, rid, lease, status, reason, draft, critique):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._fence(db, rid, lease)
            observations = json.loads(row["observations_json"])
            coverage = self.preview(observations)["coverage"]
            gaps = [key for key, value in coverage.items() if value != "complete_for_query"]
            if gaps or critique.get("outcome") != "pass":
                status = "cancelled" if status == "cancelled" else "partial"
            payload = {
                "identity": json.loads(row["identity_json"]),
                "question": row["question"],
                "draft": draft,
                "critique": critique,
                "coverage": coverage,
                "gaps": gaps,
                "status": status,
                "stop_reason": reason,
                "source_manifest": [
                    {
                        "source": key,
                        "snapshot_id": value.get("snapshot_id"),
                        "sha256": value["sha256"],
                        "retrieved_at": value["retrieved_at"],
                        "catalog": value["catalog"],
                    }
                    for key, value in observations.items()
                ],
            }
            identity_row = db.execute(
                "SELECT payload_json FROM snapshots WHERE id=?", (digest(["identity", rid])[:32],)
            ).fetchone()
            if identity_row:
                identity_source = json.loads(identity_row[0])
                payload["source_manifest"].append(
                    {
                        key: identity_source[key]
                        for key in ("source", "snapshot_id", "sha256", "retrieved_at", "catalog")
                    }
                )
            report_id = identifier()
            db.execute(
                "INSERT INTO reports(id,run_id,payload_json,created_at) VALUES(?,?,?,?)",
                (report_id, rid, json.dumps(payload), now()),
            )
            db.execute(
                "UPDATE runs SET status=?,stop_reason=?,lease=NULL,lease_until=NULL WHERE id=?",
                (status, reason, rid),
            )
        self.event(rid, "finalize", status, reason)
        return self.report(report_id)

    def cancel(self, rid):
        with self.connect() as db:
            row = db.execute("SELECT status FROM runs WHERE id=?", (rid,)).fetchone()
            if not row or row[0] not in ("queued", "running"):
                raise ValueError("Run is not active")
            db.execute("UPDATE runs SET cancelled=1 WHERE id=?", (rid,))
            if row[0] == "queued":
                db.execute(
                    "UPDATE runs SET status='cancelled',stop_reason='cancelled before execution' WHERE id=?",
                    (rid,),
                )
        self.event(rid, "cancel", "requested", "Cancellation requested")

    def resume(self, rid, key):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM events WHERE run_id=? AND stage='resume' AND detail=?", (rid, key)
            ).fetchone():
                return self.run(rid)
            row = db.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
            if (
                not row
                or row["status"] not in ("partial", "cancelled", "failed")
                or row["grant"] >= 2
            ):
                raise ValueError("Run cannot be resumed; create a new linked investigation")
            if db.execute(
                "SELECT 1 FROM runs WHERE case_id=? AND status IN ('queued','running')",
                (row["case_id"],),
            ).fetchone():
                raise ValueError("Another investigation for this case is active")
            if (
                db.execute(
                    "SELECT COUNT(*) FROM runs WHERE status IN ('queued','running')"
                ).fetchone()[0]
                >= 20
            ):
                raise ValueError("Investigation queue at capacity")
            if not key or len(key) > 150:
                raise ValueError("Resume requires an idempotency key")
            if db.execute(
                "SELECT 1 FROM events WHERE run_id=? AND stage='resume' AND detail=?", (rid, key)
            ).fetchone():
                raise ValueError("Resume grant already used")
            db.execute(
                """UPDATE runs SET status='queued',cancelled=0,deadline=NULL,grant=grant+1,
                action_base=actions,model_base=model_calls,http_base=http_attempts WHERE id=?""",
                (rid,),
            )
            db.execute(
                "INSERT INTO events(run_id,stage,outcome,detail,created_at) VALUES(?,?,?,?,?)",
                (rid, "resume", "granted", key, now()),
            )
        return self.run(rid)

    def report(self, report_id):
        with self.connect() as db:
            return decoded(db.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone())

    def snapshot(self, sid):
        with self.connect() as db:
            return decoded(db.execute("SELECT * FROM snapshots WHERE id=?", (sid,)).fetchone())

    def review(self, report_id, value, actor):
        from propertybrief_api.evidence import validate_draft

        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            report = decoded(
                db.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
            )
            if not report or report["revision"] != value.expected_revision:
                raise ValueError("Review revision conflict")
            payload = report["payload"]
            if value.draft is not None:
                run = decoded(
                    db.execute("SELECT * FROM runs WHERE id=?", (report["run_id"],)).fetchone()
                )
                validate_draft(value.draft, run["observations"], run["identity"])
                if not value.acknowledge_limits:
                    raise ValueError("Acknowledge limitations after a material edit")
                payload["draft"] = value.draft.model_dump()
                payload["critique"] = {
                    "outcome": "not_assessed_after_edit",
                    "issues": ["Reviewer edited this report; prior model critique does not apply."],
                    "unsupported_finding_ids": [],
                }
                payload["status"] = "partial"
                payload["parent_report_id"] = report_id
                report_id = identifier()
                db.execute(
                    "INSERT INTO reports(id,run_id,payload_json,reviewed_by,reviewed_at,notes,created_at) VALUES(?,?,?,?,?,?,?)",
                    (
                        report_id,
                        report["run_id"],
                        json.dumps(payload),
                        actor,
                        now(),
                        value.notes,
                        now(),
                    ),
                )
            else:
                if (
                    payload["gaps"] or payload["critique"]["outcome"] != "pass"
                ) and not value.acknowledge_limits:
                    raise ValueError("Acknowledge the partial report limitations")
                db.execute(
                    "UPDATE reports SET reviewed_by=?,reviewed_at=?,notes=?,revision=revision+1 WHERE id=?",
                    (actor, now(), value.notes, report_id),
                )
        self.event(report["run_id"], "review", "accepted", f"report={report_id}")
        return self.report(report_id)

    def export(self, report_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            report = decoded(
                db.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
            )
            if not report or not report["reviewed_at"]:
                raise ValueError("Review this report before export")
            eid = identifier()
            db.execute(
                "INSERT INTO exports VALUES(?,?,?,?)", (eid, report_id, json.dumps(report), now())
            )
        return {"id": eid, "report": report}

    def exported(self, eid):
        with self.connect() as db:
            return decoded(db.execute("SELECT * FROM exports WHERE id=?", (eid,)).fetchone())

    def heartbeat(self):
        with self.connect() as db:
            row = db.execute("SELECT updated_at FROM heartbeat WHERE id=1").fetchone()
            return row[0] if row else None
