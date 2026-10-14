"""Single-host durable storage, immutable source revisions, and lexical retrieval."""

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from contracts.resolvedesk import AnswerDraft, CaseInput, ChatCreate, ChatMessage

from resolvedesk_api.ingest import normalize, passages


def now():
    return datetime.now(UTC).isoformat()


def identifier():
    return str(uuid.uuid4())


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "resolvedesk.sqlite3"
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value INTEGER NOT NULL);
                INSERT OR IGNORE INTO meta VALUES('index_revision',0);
                CREATE TABLE IF NOT EXISTS sources(
                    id TEXT PRIMARY KEY,url TEXT NOT NULL,title TEXT NOT NULL,version TEXT NOT NULL,
                    visibility TEXT NOT NULL,sha256 TEXT NOT NULL,text TEXT NOT NULL,
                    origin TEXT NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS passages(
                    id TEXT PRIMARY KEY,snapshot_id TEXT NOT NULL REFERENCES sources(id),
                    start INTEGER NOT NULL,end INTEGER NOT NULL,text TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sections(
                    snapshot_id TEXT REFERENCES sources(id),start INTEGER NOT NULL,
                    heading TEXT NOT NULL,anchor TEXT NOT NULL,PRIMARY KEY(snapshot_id,start));
                CREATE VIRTUAL TABLE IF NOT EXISTS passage_fts USING fts5(id UNINDEXED,text);
                CREATE TABLE IF NOT EXISTS publications(
                    snapshot_id TEXT NOT NULL REFERENCES sources(id),start_rev INTEGER NOT NULL,
                    end_rev INTEGER,PRIMARY KEY(snapshot_id,start_rev));
                CREATE TABLE IF NOT EXISTS cases(
                    id TEXT PRIMARY KEY,input_json TEXT NOT NULL,revision INTEGER NOT NULL,
                    actor TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs(
                    id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id),input_json TEXT NOT NULL,
                    case_revision INTEGER NOT NULL,index_revision INTEGER NOT NULL,
                    request_key TEXT NOT NULL,status TEXT NOT NULL,error TEXT,
                    created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(case_id,request_key));
                CREATE TABLE IF NOT EXISTS checkpoints(
                    run_id TEXT NOT NULL REFERENCES runs(id),stage TEXT NOT NULL,payload TEXT NOT NULL,
                    PRIMARY KEY(run_id,stage));
                CREATE TABLE IF NOT EXISTS events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT REFERENCES runs(id),
                    stage TEXT NOT NULL,outcome TEXT NOT NULL,detail TEXT NOT NULL,
                    elapsed_ms INTEGER NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS answers(
                    id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),revision INTEGER NOT NULL,
                    draft_json TEXT NOT NULL,evidence_json TEXT NOT NULL,parent_id TEXT REFERENCES answers(id),
                    approved_at TEXT,approved_by TEXT,review_reason TEXT,allow_internal INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,UNIQUE(run_id,revision));
                CREATE TABLE IF NOT EXISTS exports(
                    id TEXT PRIMARY KEY,answer_id TEXT REFERENCES answers(id),snapshot TEXT NOT NULL,
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS chats(
                    id TEXT PRIMARY KEY,title TEXT NOT NULL,environment_json TEXT NOT NULL,
                    actor TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS chat_turns(
                    id TEXT PRIMARY KEY,chat_id TEXT NOT NULL REFERENCES chats(id),position INTEGER NOT NULL,
                    content TEXT NOT NULL,case_id TEXT NOT NULL REFERENCES cases(id),
                    run_id TEXT NOT NULL UNIQUE REFERENCES runs(id),request_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,created_at TEXT NOT NULL,
                    UNIQUE(chat_id,position),UNIQUE(chat_id,request_key));
            """)

    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def index_revision(self):
        with self.connect() as db:
            return db.execute("SELECT value FROM meta WHERE key='index_revision'").fetchone()[0]

    def import_source(
        self,
        *,
        title,
        url,
        version,
        text,
        visibility="public",
        indexed=True,
        origin="indexed",
        sections=None,
    ):
        if version not in ("16", "17") or visibility not in ("public", "internal"):
            raise ValueError("Unsupported source version or visibility")
        text = normalize(text)
        if len(text) < 20 or len(text) > 2_000_000:
            raise ValueError("Source text must contain 20 to 2,000,000 characters")
        digest = hashlib.sha256(text.encode()).hexdigest()
        sid = hashlib.sha256(f"{url}|{version}|{visibility}|{digest}".encode()).hexdigest()[:32]
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            exists = db.execute("SELECT id FROM sources WHERE id=?", (sid,)).fetchone()
            if not exists:
                db.execute(
                    "INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?)",
                    (sid, url, title[:200], version, visibility, digest, text, origin, now()),
                )
                for start, end, part in passages(text):
                    pid = f"{sid}-{start}"
                    db.execute(
                        "INSERT INTO passages VALUES(?,?,?,?,?)", (pid, sid, start, end, part)
                    )
                    db.execute("INSERT INTO passage_fts(id,text) VALUES(?,?)", (pid, part))
            for section in sections or []:
                start = section["start"]
                heading = section["heading"]
                anchor = section["anchor"]
                if text[start : start + len(heading)] != heading or not re.fullmatch(
                    r"[\w.:-]*", anchor
                ):
                    raise ValueError("Section metadata does not match source text")
                db.execute(
                    "INSERT OR IGNORE INTO sections VALUES(?,?,?,?)", (sid, start, heading, anchor)
                )
            current = db.execute(
                "SELECT 1 FROM publications WHERE snapshot_id=? AND end_rev IS NULL", (sid,)
            ).fetchone()
            if indexed and not current:
                db.execute("UPDATE meta SET value=value+1 WHERE key='index_revision'")
                rev = db.execute("SELECT value FROM meta WHERE key='index_revision'").fetchone()[0]
                db.execute(
                    """UPDATE publications SET end_rev=? WHERE end_rev IS NULL AND snapshot_id IN
                           (SELECT id FROM sources WHERE url=? AND visibility=?)""",
                    (rev, url, visibility),
                )
                db.execute("INSERT INTO publications VALUES(?,?,NULL)", (sid, rev))
        return self.source(sid)

    def source(self, sid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM sources WHERE id=?", (sid,)).fetchone()
            return dict(row) if row else None

    def sources(self):
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute("""SELECT s.id,s.url,s.title,s.version,s.visibility,s.sha256,
                s.origin,s.created_at,EXISTS(SELECT 1 FROM publications p WHERE p.snapshot_id=s.id
                AND p.end_rev IS NULL) AS indexed FROM sources s ORDER BY s.created_at DESC""")
            ]

    def promote_source(self, sid):
        source = self.source(sid)
        if not source:
            raise ValueError("Source not found")
        return self.import_source(
            **{k: source[k] for k in ("title", "url", "version", "text", "visibility")}
        )

    def source_passages(self, sid):
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    """SELECT p.*,s.title,s.url,s.version,s.visibility,s.origin,
                COALESCE((SELECT heading FROM sections WHERE snapshot_id=s.id AND start<=p.start ORDER BY start DESC LIMIT 1),s.title) AS heading,
                COALESCE((SELECT anchor FROM sections WHERE snapshot_id=s.id AND start<=p.start ORDER BY start DESC LIMIT 1),'') AS anchor
                FROM passages p JOIN sources s ON s.id=p.snapshot_id WHERE s.id=? ORDER BY p.start""",
                    (sid,),
                )
            ]

    def validate_passage(self, passage, revision, search_ids):
        with self.connect() as db:
            stored = db.execute(
                "SELECT p.*,s.version,s.visibility,s.url FROM passages p JOIN sources s ON s.id=p.snapshot_id WHERE p.id=?",
                (passage["id"],),
            ).fetchone()
            if not stored or any(
                stored[k] != passage[k]
                for k in ("snapshot_id", "start", "end", "version", "visibility", "url")
            ):
                raise ValueError("Retrieved passage identity did not match its stored snapshot")
            if not stored["text"].startswith(passage["text"]):
                raise ValueError("Retrieved passage content was changed")
            publication = db.execute(
                "SELECT 1 FROM publications WHERE snapshot_id=? AND start_rev<=? AND (end_rev IS NULL OR end_rev>?)",
                (passage["snapshot_id"], revision, revision),
            ).fetchone()
            if not publication and passage["id"] not in search_ids:
                raise ValueError("Retrieved passage is outside the pinned source collection")

    def retrieve(
        self,
        query,
        versions,
        *,
        index_revision=None,
        include_internal=False,
        limit=8,
        snapshot_ids=None,
    ):
        revision = self.index_revision() if index_revision is None else index_revision
        tokens = list(dict.fromkeys(re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,40}", query.lower())))[:30]
        stop = {"the", "and", "with", "from", "that", "this", "does", "have", "what", "please"}
        tokens = [t for t in tokens if t not in stop]
        versions = [v.split(".")[0] for v in versions if v and v.split(".")[0] in ("16", "17")]
        if not tokens or not versions:
            return []
        expression = " OR ".join(f'"{t}"' for t in tokens)
        utility_pages = {
            "pg_dump": "app-pgdump.html",
            "pg_restore": "app-pgrestore.html",
            "pg_dumpall": "app-pg-dumpall.html",
            "pg_upgrade": "pgupgrade.html",
        }
        preferred = ["%/" + page for tool, page in utility_pages.items() if tool in tokens]
        preference = " OR ".join("s.url LIKE ?" for _ in preferred) or "0"
        placeholders = ",".join("?" for _ in versions)
        scope_join = "JOIN publications pub ON pub.snapshot_id=s.id"
        scope_where = "AND pub.start_rev<=? AND (pub.end_rev IS NULL OR pub.end_rev>?)"
        scope_values = (revision, revision)
        if snapshot_ids is not None:
            if not snapshot_ids:
                return []
            scope_join = ""
            scope_where = "AND s.id IN (" + ",".join("?" for _ in snapshot_ids) + ")"
            scope_values = tuple(snapshot_ids)
        with self.connect() as db:
            rows = db.execute(
                f"""SELECT p.*,s.title,s.url,s.version,s.visibility,s.origin,
                COALESCE((SELECT heading FROM sections WHERE snapshot_id=s.id AND start<=p.start ORDER BY start DESC LIMIT 1),s.title) AS heading,
                COALESCE((SELECT anchor FROM sections WHERE snapshot_id=s.id AND start<=p.start ORDER BY start DESC LIMIT 1),'') AS anchor,
                bm25(passage_fts) AS score FROM passage_fts
                JOIN passages p ON p.id=passage_fts.id JOIN sources s ON s.id=p.snapshot_id
                {scope_join}
                WHERE passage_fts MATCH ? AND s.version IN ({placeholders})
                {scope_where}
                AND (s.visibility='public' OR ?=1)
                ORDER BY CASE WHEN ({preference}) THEN 0 ELSE 1 END,score,p.id LIMIT ?""",
                (
                    expression,
                    *versions,
                    *scope_values,
                    int(include_internal),
                    *preferred,
                    min(limit, 8),
                ),
            )
            return [dict(row) for row in rows]

    def create_case(self, value: CaseInput, actor):
        cid = identifier()
        with self.connect() as db:
            db.execute(
                "INSERT INTO cases VALUES(?,?,1,?,?,?)",
                (cid, value.model_dump_json(), actor, now(), now()),
            )
        return self.case(cid)

    def case(self, cid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()
            if not row:
                return None
            return {**dict(row), **json.loads(row["input_json"])}

    def cases(self):
        with self.connect() as db:
            ids = [r[0] for r in db.execute("SELECT id FROM cases ORDER BY updated_at DESC")]
        return [self.case(cid) for cid in ids]

    def update_environment(self, cid, expected_revision, changes, actor):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()
            if not row or row["revision"] != expected_revision:
                raise ValueError("Case revision changed; reload before editing")
            data = json.loads(row["input_json"])
            if set(changes) - {"server_version", "client_version", "os"}:
                raise ValueError("Only environment fields can be changed")
            data.update(changes)
            value = CaseInput.model_validate(data)
            db.execute(
                "UPDATE cases SET input_json=?,revision=revision+1,actor=?,updated_at=? WHERE id=?",
                (value.model_dump_json(), actor, now(), cid),
            )
        return self.case(cid)

    def create_run(self, cid, request_key):
        if not request_key or len(request_key) > 100:
            raise ValueError("An idempotency key of at most 100 characters is required")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            item = db.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()
            if not item:
                raise ValueError("Case not found")
            existing = db.execute(
                "SELECT * FROM runs WHERE case_id=? AND request_key=?", (cid, request_key)
            ).fetchone()
            if existing:
                if existing["case_revision"] != item["revision"]:
                    raise ValueError("Idempotency key belongs to a different case revision")
                rid = existing["id"]
            else:
                rid = identifier()
                rev = db.execute("SELECT value FROM meta WHERE key='index_revision'").fetchone()[0]
                db.execute(
                    "INSERT INTO runs VALUES(?,?,?,?,?,?,'queued',NULL,?,?)",
                    (
                        rid,
                        cid,
                        item["input_json"],
                        item["revision"],
                        rev,
                        request_key,
                        now(),
                        now(),
                    ),
                )
        return self.run(rid)

    def claim(self):
        stale = (datetime.now(UTC) - timedelta(minutes=12)).isoformat()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM runs WHERE status='queued' OR (status='running' AND updated_at<?) ORDER BY created_at LIMIT 1",
                (stale,),
            ).fetchone()
            if row:
                db.execute(
                    "UPDATE runs SET status='running',updated_at=? WHERE id=?", (now(), row["id"])
                )
                return dict(row)
        return None

    def event(self, rid, stage, outcome, detail="", elapsed_ms=0):
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(run_id,stage,outcome,detail,elapsed_ms,created_at) VALUES(?,?,?,?,?,?)",
                (rid, stage, outcome, str(detail)[:1500], elapsed_ms, now()),
            )
            db.execute("UPDATE runs SET updated_at=? WHERE id=?", (now(), rid))

    def checkpoint(self, rid, stage):
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM checkpoints WHERE run_id=? AND stage=?", (rid, stage)
            ).fetchone()
            return json.loads(row[0]) if row else None

    def save_checkpoint(self, rid, stage, value):
        with self.connect() as db:
            db.execute(
                "INSERT INTO checkpoints VALUES(?,?,?) ON CONFLICT(run_id,stage) DO UPDATE SET payload=excluded.payload",
                (rid, stage, json.dumps(value)),
            )
            db.execute("UPDATE runs SET updated_at=? WHERE id=?", (now(), rid))

    def finish(self, rid, draft: AnswerDraft, evidence, status):
        aid = identifier()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            revision = db.execute(
                "SELECT COALESCE(MAX(revision),0)+1 FROM answers WHERE run_id=?", (rid,)
            ).fetchone()[0]
            db.execute(
                "INSERT INTO answers(id,run_id,revision,draft_json,evidence_json,created_at) VALUES(?,?,?,?,?,?)",
                (aid, rid, revision, draft.model_dump_json(), json.dumps(evidence), now()),
            )
            db.execute(
                "UPDATE runs SET status=?,error=NULL,updated_at=? WHERE id=?", (status, now(), rid)
            )
        return self.answer(aid)

    def fail(self, rid, message):
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET status='failed',error=?,updated_at=? WHERE id=?",
                (message[:500], now(), rid),
            )

    def retry(self, rid):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            turn = db.execute("SELECT * FROM chat_turns WHERE run_id=?", (rid,)).fetchone()
            if (
                turn
                and db.execute(
                    "SELECT MAX(position) FROM chat_turns WHERE chat_id=?", (turn["chat_id"],)
                ).fetchone()[0]
                != turn["position"]
            ):
                raise ValueError("Only the latest conversation turn can be retried")
            cursor = db.execute(
                "UPDATE runs SET status='queued',error=NULL,updated_at=? WHERE id=? AND status='failed'",
                (now(), rid),
            )
            if cursor.rowcount != 1:
                raise ValueError("Only failed runs can be retried")

    def create_chat(self, value: ChatCreate, actor):
        cid = identifier()
        environment = value.model_dump(exclude={"title"})
        with self.connect() as db:
            db.execute(
                "INSERT INTO chats VALUES(?,?,?,?,?,?)",
                (cid, value.title, json.dumps(environment), actor, now(), now()),
            )
        return self.chat(cid)

    def chats(self):
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT id,title,created_at,updated_at,(SELECT COUNT(*) FROM chat_turns t WHERE t.chat_id=chats.id) AS turn_count FROM chats ORDER BY updated_at DESC"
                )
            ]

    def chat(self, cid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM chats WHERE id=?", (cid,)).fetchone()
            if not row:
                return None
            turns = [
                dict(t)
                for t in db.execute(
                    "SELECT id,position,content,run_id,created_at FROM chat_turns WHERE chat_id=? ORDER BY position",
                    (cid,),
                )
            ]
        result = dict(row)
        result["environment"] = json.loads(result.pop("environment_json"))
        result["turns"] = [{**t, "run": self.run(t["run_id"])} for t in turns]
        return result

    def send_message(self, cid, value: ChatMessage, request_key, actor):
        if not request_key or len(request_key) > 100:
            raise ValueError("An idempotency key of at most 100 characters is required")
        digest = hashlib.sha256(value.model_dump_json().encode()).hexdigest()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            chat = db.execute("SELECT * FROM chats WHERE id=?", (cid,)).fetchone()
            if not chat:
                raise ValueError("Conversation not found")
            existing = db.execute(
                "SELECT * FROM chat_turns WHERE chat_id=? AND request_key=?", (cid, request_key)
            ).fetchone()
            if existing:
                if existing["request_hash"] != digest:
                    raise ValueError("Idempotency key belongs to a different message")
            else:
                latest = db.execute(
                    "SELECT t.position,r.status FROM chat_turns t JOIN runs r ON r.id=t.run_id WHERE t.chat_id=? ORDER BY t.position DESC LIMIT 1",
                    (cid,),
                ).fetchone()
                if latest and latest["status"] in ("queued", "running"):
                    raise ValueError("Wait for the current response before sending another message")
                count = latest["position"] if latest else 0
                if value.expected_turn_count != count:
                    raise ValueError("Conversation changed; reload before sending")
                environment = json.loads(chat["environment_json"])
                case = CaseInput(
                    title="Chat: " + value.content.strip()[:100],
                    question=value.content,
                    **environment,
                )
                case_id, rid = identifier(), identifier()
                revision = db.execute(
                    "SELECT value FROM meta WHERE key='index_revision'"
                ).fetchone()[0]
                db.execute(
                    "INSERT INTO cases VALUES(?,?,1,?,?,?)",
                    (case_id, case.model_dump_json(), actor, now(), now()),
                )
                db.execute(
                    "INSERT INTO runs VALUES(?,?,?,?,?,?,'queued',NULL,?,?)",
                    (rid, case_id, case.model_dump_json(), 1, revision, request_key, now(), now()),
                )
                db.execute(
                    "INSERT INTO chat_turns VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        identifier(),
                        cid,
                        count + 1,
                        value.content,
                        case_id,
                        rid,
                        request_key,
                        digest,
                        now(),
                    ),
                )
                title = (
                    value.content.strip().replace("\n", " ")[:65]
                    if count == 0 and chat["title"] == "New conversation"
                    else chat["title"]
                )
                db.execute("UPDATE chats SET title=?,updated_at=? WHERE id=?", (title, now(), cid))
        return self.chat(cid)

    def chat_context(self, rid):
        with self.connect() as db:
            turn = db.execute(
                "SELECT t.*,c.environment_json FROM chat_turns t JOIN chats c ON c.id=t.chat_id WHERE t.run_id=?",
                (rid,),
            ).fetchone()
            if not turn:
                return None
            earlier = [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM chat_turns WHERE chat_id=? AND position<? ORDER BY position DESC LIMIT 6",
                    (turn["chat_id"], turn["position"]),
                )
            ]
        history = []
        remaining = 8000
        environment = json.loads(turn["environment_json"])
        if earlier:
            previous = self.checkpoint(earlier[0]["run_id"], "chat_resolution")
            if previous:
                for key in ("server_version", "client_version", "os"):
                    if previous.get(key) is not None:
                        environment[key] = previous[key]
        for previous in reversed(earlier):
            run = self.run(previous["run_id"])
            history.append({"role": "user", "content": previous["content"][:1200]})
            if run["answer"]:
                draft = run["answer"]["draft"]
                text = "\n".join(
                    [
                        *[c["text"] for c in draft["claims"]],
                        *draft["questions"],
                        *draft["limitations"],
                    ]
                )
                history.append(
                    {
                        "role": "assistant",
                        "content": text[:1200],
                        "evidence_state": draft["evidence_state"],
                        "status": run["status"],
                    }
                )
        trimmed = []
        for message in reversed(history):
            if remaining < 1:
                break
            content = message["content"][:remaining]
            trimmed.append({**message, "content": content})
            remaining -= len(content)
        return {
            "message": turn["content"],
            "history": list(reversed(trimmed)),
            "environment": environment,
        }

    def run(self, rid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
            if not row:
                return None
            aid = db.execute(
                "SELECT id FROM answers WHERE run_id=? ORDER BY revision DESC LIMIT 1", (rid,)
            ).fetchone()
            events = [
                dict(e)
                for e in db.execute("SELECT * FROM events WHERE run_id=? ORDER BY id", (rid,))
            ]
        return {
            **dict(row),
            "input": json.loads(row["input_json"]),
            "events": events,
            "answer": self.answer(aid[0]) if aid else None,
        }

    def latest_run(self, cid):
        with self.connect() as db:
            row = db.execute(
                "SELECT id FROM runs WHERE case_id=? ORDER BY created_at DESC LIMIT 1", (cid,)
            ).fetchone()
        return self.run(row[0]) if row else None

    def answer(self, aid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM answers WHERE id=?", (aid,)).fetchone()
        if not row:
            return None
        data = dict(row)
        data["draft"] = json.loads(data.pop("draft_json"))
        data["evidence"] = json.loads(data.pop("evidence_json"))
        return data

    def review(
        self,
        aid,
        expected_revision,
        action,
        reason,
        actor,
        *,
        claim_texts=None,
        acknowledge_limits=False,
        allow_internal=False,
    ):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM answers WHERE id=?", (aid,)).fetchone()
            if not row or row["revision"] != expected_revision:
                raise ValueError("Answer revision changed; reload")
            if row["approved_at"] and action == "approve":
                return self.answer(aid)
            latest = db.execute(
                "SELECT MAX(revision) FROM answers WHERE run_id=?", (row["run_id"],)
            ).fetchone()[0]
            if row["revision"] != latest:
                raise ValueError("A newer answer revision exists")
            draft = AnswerDraft.model_validate_json(row["draft_json"])
            evidence = json.loads(row["evidence_json"])
            if action == "approve":
                run = db.execute("SELECT * FROM runs WHERE id=?", (row["run_id"],)).fetchone()
                case_revision = db.execute(
                    "SELECT revision FROM cases WHERE id=?", (run["case_id"],)
                ).fetchone()[0]
                if run["status"] == "failed" or run["case_revision"] != case_revision:
                    raise ValueError("Finish a current investigation before approval")
                if draft.evidence_state in ("conflicting", "insufficient") or not draft.claims:
                    raise ValueError("Resolve evidence gaps or export an escalation packet")
                if (
                    draft.questions or draft.limitations or draft.evidence_state == "partial"
                ) and not acknowledge_limits:
                    raise ValueError("Explicitly acknowledge the answer limitations")
                used = {c.passage_id for claim in draft.claims for c in claim.citations}
                if (
                    any(p["visibility"] == "internal" and p["id"] in used for p in evidence)
                    and not allow_internal
                ):
                    raise ValueError("Authorize internal evidence before exporting its content")
                db.execute(
                    "UPDATE answers SET approved_at=?,approved_by=?,review_reason=?,allow_internal=? WHERE id=?",
                    (now(), actor, reason, int(allow_internal), aid),
                )
            elif action == "edit":
                texts = claim_texts or {}
                if not texts or set(texts) - {c.id for c in draft.claims}:
                    raise ValueError("Provide known claim IDs to edit")
                for claim in draft.claims:
                    if claim.id in texts:
                        claim.text = texts[claim.id]
                draft.evidence_state = "partial"
                draft.limitations = list(
                    dict.fromkeys(
                        [*draft.limitations, "Edited text requires human evidence review."]
                    )
                )
                draft = AnswerDraft.model_validate(draft.model_dump())
                new_id = identifier()
                db.execute(
                    "INSERT INTO answers(id,run_id,revision,draft_json,evidence_json,parent_id,review_reason,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (
                        new_id,
                        row["run_id"],
                        latest + 1,
                        draft.model_dump_json(),
                        row["evidence_json"],
                        aid,
                        reason,
                        now(),
                    ),
                )
                aid = new_id
            elif action == "escalate":
                draft.evidence_state = "insufficient"
                draft.limitations.append(
                    "A reviewer requested expert review before sending a resolved answer."
                )
                new_id = identifier()
                db.execute(
                    "INSERT INTO answers(id,run_id,revision,draft_json,evidence_json,parent_id,review_reason,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (
                        new_id,
                        row["run_id"],
                        latest + 1,
                        draft.model_dump_json(),
                        row["evidence_json"],
                        aid,
                        reason,
                        now(),
                    ),
                )
                aid = new_id
                db.execute(
                    "UPDATE runs SET status='escalated',updated_at=? WHERE id=?",
                    (now(), row["run_id"]),
                )
            else:
                raise ValueError("Unknown review action")
            db.execute(
                "INSERT INTO events(run_id,stage,outcome,detail,elapsed_ms,created_at) VALUES(?,?,'succeeded',?,0,?)",
                (
                    row["run_id"],
                    f"review_{action}",
                    f"actor={actor}; revision={expected_revision}",
                    now(),
                ),
            )
        return self.answer(aid)

    def export(self, aid, format="json", *, escalation=False):
        answer = self.answer(aid)
        if not answer:
            raise ValueError("Answer not found")
        if not escalation and not answer["approved_at"]:
            raise ValueError("Approve this revision before export")
        if escalation:
            # An escalation packet contains public evidence and limitations, never private excerpts.
            answer["approved_at"] = None
            answer["approved_by"] = None
        allowed = {
            p["id"]: p
            for p in answer["evidence"]
            if p["visibility"] == "public" or (answer["allow_internal"] and not escalation)
        }
        claims = []
        for claim in answer["draft"]["claims"]:
            citations = [
                {
                    **c,
                    "url": allowed[c["passage_id"]]["url"],
                    "title": allowed[c["passage_id"]]["title"],
                }
                for c in claim["citations"]
                if c["passage_id"] in allowed
            ]
            if citations:
                claims.append({**claim, "citations": citations})
        snapshot = {
            k: answer[k] for k in ("id", "run_id", "revision", "approved_at", "approved_by")
        }
        run = self.run(answer["run_id"])
        snapshot.update(
            {
                "kind": "escalation" if escalation else "approved_reply",
                "claims": claims,
                "limitations": answer["draft"]["limitations"],
                "questions": answer["draft"]["questions"],
                "evidence_state": answer["draft"]["evidence_state"],
                "exported_at": now(),
                "environment": run["input"],
                "index_revision": run["index_revision"],
                "source_hashes": {
                    p["snapshot_id"]: self.source(p["snapshot_id"])["sha256"]
                    for p in allowed.values()
                },
            }
        )
        if escalation and any(p["visibility"] == "internal" for p in answer["evidence"]):
            snapshot["limitations"] = [
                "Internal investigation details require authorized review in ResolveDesk."
            ]
            snapshot["questions"] = []
        with self.connect() as db:
            db.execute(
                "INSERT INTO exports VALUES(?,?,?,?)",
                (identifier(), aid, json.dumps(snapshot), now()),
            )
        if format == "markdown":
            lines = ["# ResolveDesk " + snapshot["kind"].replace("_", " "), ""]
            for claim in claims:
                lines += [claim["text"], ""]
                lines += [
                    f"Source: [{c['title']}]({c['url']}) — {c['quote']}" for c in claim["citations"]
                ]
                lines.append("")
            lines += ["Limitations: " + s for s in snapshot["limitations"]]
            lines += ["Question: " + s for s in snapshot["questions"]]
            return "\n".join(lines)
        return snapshot

    def backup(self, destination):
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / "resolvedesk.sqlite3"
        if target.exists() or target.resolve() == self.db_path.resolve():
            raise ValueError("Backup requires a new destination")
        with self.connect() as source, sqlite3.connect(target) as output:
            source.backup(output)
        with sqlite3.connect(target) as check:
            if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Backup integrity check failed")
