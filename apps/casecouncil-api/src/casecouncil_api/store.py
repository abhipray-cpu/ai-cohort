"""Independent SQLite authority, immutable source revisions and fenced stage ledger."""

import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from contracts.casecouncil import Context, Policy, Review, Rights

from . import journal
from .consensus import canonical, digest
from .evidence import evidence_for, extract, redact, sha


class LeaseLost(ValueError):
    pass


def ident():
    return uuid.uuid4().hex


class Store:
    def __init__(self, root, *, evaluation_only=False):
        self.evaluation_only = evaluation_only
        self._local = threading.local()
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "casecouncil.sqlite3"
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS meta(id INTEGER PRIMARY KEY CHECK(id=1),epoch TEXT NOT NULL,schema_version INTEGER NOT NULL,store_id TEXT NOT NULL,journal_head TEXT NOT NULL DEFAULT 'genesis',quarantine INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY,salt TEXT NOT NULL,password TEXT NOT NULL,admin INTEGER NOT NULL,revision INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,name TEXT NOT NULL REFERENCES users(name),csrf TEXT NOT NULL,expires REAL NOT NULL,revision INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY,name TEXT NOT NULL,auth_revision INTEGER NOT NULL DEFAULT 1,policy TEXT NOT NULL,policy_revision INTEGER NOT NULL DEFAULT 1,hold TEXT);
            CREATE TABLE IF NOT EXISTS members(workspace TEXT REFERENCES workspaces(id),name TEXT REFERENCES users(name),role TEXT NOT NULL,PRIMARY KEY(workspace,name));
            CREATE TABLE IF NOT EXISTS rights(id TEXT PRIMARY KEY,workspace TEXT REFERENCES workspaces(id),body TEXT NOT NULL,expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY,workspace TEXT REFERENCES workspaces(id),creator TEXT REFERENCES users(name),context TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,erased INTEGER NOT NULL DEFAULT 0,created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,case_id TEXT REFERENCES cases(id),kind TEXT NOT NULL,rights_id TEXT REFERENCES rights(id),body TEXT NOT NULL,raw BLOB NOT NULL,active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,case_id TEXT REFERENCES cases(id),actor TEXT REFERENCES users(name),binding TEXT NOT NULL,snapshot TEXT NOT NULL,state TEXT NOT NULL,created REAL NOT NULL,deadline REAL NOT NULL,calls INTEGER NOT NULL DEFAULT 0,seconds REAL NOT NULL DEFAULT 0,claims INTEGER NOT NULL DEFAULT 0,token TEXT,lease_until REAL NOT NULL DEFAULT 0,error TEXT,packet TEXT,packet_hash TEXT);
            CREATE TABLE IF NOT EXISTS checkpoints(job TEXT REFERENCES jobs(id),stage TEXT,body TEXT NOT NULL,hash TEXT NOT NULL,PRIMARY KEY(job,stage));
            CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,job TEXT REFERENCES jobs(id),stage TEXT NOT NULL,sequence INTEGER NOT NULL,prompt_hash TEXT NOT NULL,reserved REAL NOT NULL,receipt TEXT,UNIQUE(job,stage,sequence));
            CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,job TEXT REFERENCES jobs(id),actor TEXT REFERENCES users(name),body TEXT NOT NULL,binding TEXT NOT NULL,created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS operations(actor TEXT,scope TEXT,operation TEXT,key TEXT,request_hash TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(actor,scope,operation,key));
            CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,workspace TEXT,case_id TEXT,actor TEXT NOT NULL,action TEXT NOT NULL,detail TEXT NOT NULL,occurred REAL NOT NULL,previous TEXT NOT NULL,hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS heartbeat(id TEXT PRIMARY KEY,updated REAL NOT NULL,detail TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS job_claim ON jobs(state,lease_until,created);
            CREATE TABLE IF NOT EXISTS attempt_reconciliations(id TEXT PRIMARY KEY,attempt_id TEXT UNIQUE REFERENCES attempts(id),body TEXT NOT NULL,hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS attempt_incidents(id TEXT PRIMARY KEY,attempt_id TEXT UNIQUE REFERENCES attempts(id),body TEXT NOT NULL,hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS checkpoint_history(id TEXT PRIMARY KEY,job TEXT REFERENCES jobs(id),stage TEXT NOT NULL,body TEXT NOT NULL,hash TEXT NOT NULL,recovery TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS packet_history(id TEXT PRIMARY KEY,job TEXT REFERENCES jobs(id),body TEXT NOT NULL,hash TEXT NOT NULL,recovery TEXT NOT NULL);
            """)
            columns = {r[1] for r in db.execute("PRAGMA table_info(meta)")}
            if "store_id" not in columns:
                db.execute("ALTER TABLE meta ADD COLUMN store_id TEXT")
                db.execute(
                    "ALTER TABLE meta ADD COLUMN journal_head TEXT NOT NULL DEFAULT 'genesis'"
                )
                db.execute("ALTER TABLE meta ADD COLUMN quarantine INTEGER NOT NULL DEFAULT 0")
                db.execute("UPDATE meta SET store_id=?,schema_version=2", (ident(),))
                if db.execute("SELECT 1 FROM attempts LIMIT 1").fetchone():
                    db.execute("UPDATE meta SET quarantine=1")
                    db.execute(
                        "UPDATE workspaces SET hold='pre-journal usage requires reconciliation'"
                    )
            db.execute(
                "INSERT OR IGNORE INTO meta(id,epoch,schema_version,store_id) VALUES(1,?,2,?)",
                (ident(), ident()),
            )
            job_columns = {r[1] for r in db.execute("PRAGMA table_info(jobs)")}
            if "snapshot_hash" not in job_columns:
                db.execute("ALTER TABLE jobs ADD COLUMN snapshot_hash TEXT NOT NULL DEFAULT ''")
                for row in db.execute("SELECT id,snapshot FROM jobs").fetchall():
                    db.execute(
                        "UPDATE jobs SET snapshot_hash=? WHERE id=?",
                        (digest(json.loads(row["snapshot"])), row["id"]),
                    )
        self.journal_path = self.root / "authority" / "usage.jsonl"

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA secure_delete=ON")
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def write(self):
        current = getattr(self._local, "db", None)
        if current is not None:
            yield current
            return
        with self.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                self._local.db = db
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                self._local.db = None

    def admin_action(self, actor, w, operation, key, body, fn):
        with self.write() as db:
            self._access(db, actor, w, {"owner"})
            return self._idem(db, actor, w, operation, key, body, fn)

    def record(self, db, actor, action, workspace=None, case_id=None, detail=None):
        previous = db.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        previous = previous[0] if previous else "genesis"
        value = {
            "workspace": workspace,
            "case_id": case_id,
            "actor": actor,
            "action": action,
            "detail": detail or {},
            "occurred": time.time(),
            "previous": previous,
        }
        db.execute(
            "INSERT INTO audit(workspace,case_id,actor,action,detail,occurred,previous,hash) VALUES(?,?,?,?,?,?,?,?)",
            (
                workspace,
                case_id,
                actor,
                action,
                canonical(value["detail"]),
                value["occurred"],
                previous,
                digest(value),
            ),
        )

    def _idem(self, db, actor, scope, op, key, request, fn):
        if not key or len(key) > 150:
            raise ValueError("idempotency key required")
        row = db.execute(
            "SELECT * FROM operations WHERE actor=? AND scope=? AND operation=? AND key=?",
            (actor, scope, op, key),
        ).fetchone()
        if row:
            if row["request_hash"] != digest(request):
                raise ValueError("idempotency conflict")
            return json.loads(row["result"])
        value = fn()
        db.execute(
            "INSERT INTO operations VALUES(?,?,?,?,?,?)",
            (actor, scope, op, key, digest(request), canonical(value)),
        )
        return value

    def bootstrap(self, name, password):
        with self.write() as db:
            if db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                return
            self._user(db, name, password, True)
            self.record(db, name, "bootstrap")

    def _user(self, db, name, password, admin=False):
        if (
            not name
            or len(name) > 100
            or len(password) < 12
            or len(password) > 1000
            or password == "replace-me"
        ):
            raise ValueError("explicit strong credentials required")
        salt = secrets.token_hex(16)
        encoded = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), 310000
        ).hex()
        db.execute(
            "INSERT INTO users(name,salt,password,admin) VALUES(?,?,?,?)",
            (name, salt, encoded, int(admin)),
        )

    def add_user(self, actor, name, password):
        with self.write() as db:
            if not db.execute(
                "SELECT 1 FROM users WHERE name=? AND (admin=1 OR EXISTS(SELECT 1 FROM members WHERE name=? AND role='owner'))",
                (actor, actor),
            ).fetchone():
                raise PermissionError("owner required")
            self._user(db, name, password)
            self.record(db, actor, "user_created", detail={"name": name})

    def login(self, name, password):
        with self.write() as db:
            user = db.execute("SELECT * FROM users WHERE name=?", (name,)).fetchone()
            salt = user["salt"] if user else "0" * 32
            encoded = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt), 310000
            ).hex()
            if not user or not hmac.compare_digest(encoded, user["password"]):
                raise PermissionError("invalid credentials")
            token = secrets.token_urlsafe(32)
            csrf = secrets.token_urlsafe(24)
            db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?,?)",
                (sha(token.encode()), name, csrf, time.time() + 8 * 3600, user["revision"]),
            )
            self.record(db, name, "session_started")
            return {"token": token, "csrf": csrf, "name": name}

    def session(self, token):
        with self.connect() as db:
            row = db.execute(
                "SELECT sessions.name,sessions.csrf FROM sessions JOIN users USING(name) WHERE token=? AND expires>? AND sessions.revision=users.revision",
                (sha(token.encode()), time.time()),
            ).fetchone()
        return dict(row) if row else None

    def logout(self, token):
        with self.write() as db:
            db.execute("DELETE FROM sessions WHERE token=?", (sha(token.encode()),))

    def _access(self, db, actor, w, roles=None):
        row = db.execute(
            "SELECT role FROM members WHERE workspace=? AND name=?", (w, actor)
        ).fetchone()
        if not row:
            raise KeyError("not found")
        if roles and row[0] not in roles:
            raise PermissionError("capability denied")
        return row[0]

    def create_workspace(self, actor, name, key):
        if not 3 <= len(name) <= 150:
            raise ValueError("invalid workspace name")
        with self.write() as db:
            if not db.execute("SELECT 1 FROM users WHERE name=?", (actor,)).fetchone():
                raise PermissionError("user required")

            def create():
                wid = ident()
                policy = Policy(
                    name="Unapproved draft policy",
                    instructions="",
                    required_documents=["complaint", "policy"],
                ).model_dump()
                db.execute(
                    "INSERT INTO workspaces(id,name,policy) VALUES(?,?,?)",
                    (wid, name, canonical(policy)),
                )
                db.execute("INSERT INTO members VALUES(?,?,?)", (wid, actor, "owner"))
                self.record(db, actor, "workspace_created", wid)
                return wid

            return self._idem(db, actor, "global", "workspace", key, {"name": name}, create)

    def workspace(self, actor, w):
        with self.connect() as db:
            role = self._access(db, actor, w)
            row = dict(db.execute("SELECT * FROM workspaces WHERE id=?", (w,)).fetchone())
            row.update(role=role, policy=json.loads(row["policy"]))
            return row

    def workspaces(self, actor):
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT w.id,w.name,m.role FROM workspaces w JOIN members m ON m.workspace=w.id WHERE m.name=? ORDER BY w.name",
                    (actor,),
                )
            ]

    def set_member(self, actor, w, name, role):
        if role not in {"owner", "analyst", "reviewer", "viewer", None}:
            raise ValueError("invalid role")
        with self.write() as db:
            self._access(db, actor, w, {"owner"})
            old = db.execute(
                "SELECT role FROM members WHERE workspace=? AND name=?", (w, name)
            ).fetchone()
            if (old[0] if old else None) == role:
                return
            if (
                old
                and old[0] == "owner"
                and role != "owner"
                and db.execute(
                    "SELECT count(*) FROM members WHERE workspace=? AND role='owner'", (w,)
                ).fetchone()[0]
                == 1
            ):
                raise ValueError("cannot remove last owner")
            if role:
                db.execute(
                    "INSERT INTO members VALUES(?,?,?) ON CONFLICT(workspace,name) DO UPDATE SET role=excluded.role",
                    (w, name, role),
                )
            else:
                db.execute("DELETE FROM members WHERE workspace=? AND name=?", (w, name))
            db.execute("UPDATE users SET revision=revision+1 WHERE name=?", (name,))
            db.execute("UPDATE workspaces SET auth_revision=auth_revision+1 WHERE id=?", (w,))
            self._stale(db, w)
            self.record(db, actor, "membership_changed", w, detail={"name": name, "role": role})

    def members(self, actor, w):
        with self.connect() as db:
            self._access(db, actor, w, {"owner"})
            return [
                dict(r) for r in db.execute("SELECT name,role FROM members WHERE workspace=?", (w,))
            ]

    def _stale(self, db, w):
        db.execute(
            "UPDATE jobs SET state='stale',token=NULL,lease_until=0 WHERE case_id IN (SELECT id FROM cases WHERE workspace=?) AND state NOT IN ('cancelled','failed','stale')",
            (w,),
        )

    def set_policy(self, actor, w, revision, value):
        policy = Policy.model_validate(value)
        with self.write() as db:
            self._access(db, actor, w, {"owner"})
            if (
                db.execute(
                    "UPDATE workspaces SET policy=?,policy_revision=policy_revision+1 WHERE id=? AND policy_revision=?",
                    (canonical(policy.model_dump()), w, revision),
                ).rowcount
                != 1
            ):
                raise ValueError("stale policy")
            self._stale(db, w)
            self.record(
                db, actor, "policy_activated", w, detail={"hash": digest(policy.model_dump())}
            )

    def add_rights(self, actor, w, value):
        rights = Rights.model_validate(value)
        if rights.expires <= time.time():
            raise ValueError("expired rights")
        with self.write() as db:
            self._access(db, actor, w, {"owner"})
            rid = ident()
            db.execute(
                "INSERT INTO rights VALUES(?,?,?,?)",
                (rid, w, canonical(rights.model_dump()), rights.expires),
            )
            self.record(db, actor, "rights_attested", w, detail={"id": rid, "basis": rights.basis})
            return rid

    def rights(self, actor, w):
        with self.connect() as db:
            self._access(db, actor, w)
            return [
                {"id": r["id"], **json.loads(r["body"]), "expires": r["expires"]}
                for r in db.execute("SELECT * FROM rights WHERE workspace=?", (w,))
            ]

    def revoke_rights(self, actor, w, rid):
        with self.write() as db:
            self._access(db, actor, w, {"owner"})
            if not db.execute(
                "UPDATE rights SET expires=0 WHERE id=? AND workspace=?", (rid, w)
            ).rowcount:
                raise KeyError("not found")
            self._stale(db, w)
            self.record(db, actor, "rights_revoked", w, detail={"id": rid})

    def _case(self, db, actor, c, roles=None):
        row = db.execute("SELECT * FROM cases WHERE id=? AND erased=0", (c,)).fetchone()
        if not row:
            raise KeyError("not found")
        self._access(db, actor, row["workspace"], roles)
        return dict(row)

    def create_case(self, actor, w, context, key):
        context = Context.model_validate(context).model_dump()
        if context["jurisdiction"] != "UK" and not self.evaluation_only:
            raise ValueError("Non-UK source replay requires an isolated evaluation store")
        with self.write() as db:
            self._access(db, actor, w, {"owner", "analyst"})

            def create():
                cid = ident()
                db.execute(
                    "INSERT INTO cases(id,workspace,creator,context,created) VALUES(?,?,?,?,?)",
                    (cid, w, actor, canonical(context), time.time()),
                )
                self.record(db, actor, "case_created", w, cid)
                return {"id": cid, "revision": 1}

            return self._idem(db, actor, w, "case", key, context, create)

    def case(self, actor, c):
        with self.connect() as db:
            row = self._case(db, actor, c)
            row["context"] = json.loads(row["context"])
            row["sources"] = [
                {
                    "kind": s["kind"],
                    "rights_id": s["rights_id"],
                    **{k: v for k, v in json.loads(s["body"]).items() if k != "text"},
                }
                for s in db.execute(
                    "SELECT * FROM sources WHERE case_id=? AND active=1 ORDER BY id", (c,)
                )
            ]
            row["role"] = self._access(db, actor, row["workspace"])
            return row

    def cases(self, actor, w):
        with self.connect() as db:
            self._access(db, actor, w)
            return [
                {**dict(r), "context": json.loads(r["context"])}
                for r in db.execute(
                    "SELECT id,context,revision,created FROM cases WHERE workspace=? AND erased=0 ORDER BY created DESC LIMIT 500",
                    (w,),
                )
            ]

    def update_case(self, actor, c, revision, context, key):
        value = Context.model_validate(context).model_dump()
        if value["jurisdiction"] != "UK" and not self.evaluation_only:
            raise ValueError("Non-UK source replay requires an isolated evaluation store")
        with self.write() as db:
            case = self._case(db, actor, c, {"owner", "analyst"})

            def change():
                if case["revision"] != revision:
                    raise ValueError("stale case")
                db.execute(
                    "UPDATE cases SET context=?,revision=revision+1 WHERE id=?",
                    (canonical(value), c),
                )
                db.execute(
                    "UPDATE jobs SET state='stale',token=NULL,lease_until=0 WHERE case_id=? AND state NOT IN ('cancelled','failed')",
                    (c,),
                )
                self.record(db, actor, "context_revised", case["workspace"], c)
                return {"id": c, "revision": revision + 1}

            return self._idem(
                db, actor, c, "context", key, {"revision": revision, "context": value}, change
            )

    def add_source(self, actor, c, revision, name, raw, kind, rights_id, key, replaces=None):
        with self.connect() as db:
            self._case(db, actor, c, {"owner", "analyst"})
        if kind not in {"complaint", "policy", "correspondence", "other"}:
            raise ValueError("invalid source kind")
        source = extract(ident(), name, raw)
        with self.write() as db:
            case = self._case(db, actor, c, {"owner", "analyst"})

            def insert():
                if case["revision"] != revision:
                    raise ValueError("stale case")
                right = db.execute(
                    "SELECT * FROM rights WHERE id=? AND workspace=? AND expires>?",
                    (rights_id, case["workspace"], time.time()),
                ).fetchone()
                if not right:
                    raise ValueError("rights clearance required")
                existing = [
                    json.loads(r[0])
                    for r in db.execute(
                        "SELECT body FROM sources WHERE case_id=? AND active=1", (c,)
                    )
                ]
                if (
                    len(existing) >= 20
                    and not replaces
                    or sum(r["bytes"] for r in existing) + len(raw) > 40 * 1024 * 1024
                    or sum(r["pages"] for r in existing) + source["pages"] > 200
                    or sum(len(r["text"]) for r in existing) + len(source["text"]) > 1_000_000
                ):
                    raise ValueError("case input limit")
                if (
                    replaces
                    and not db.execute(
                        "UPDATE sources SET active=0 WHERE id=? AND case_id=? AND active=1",
                        (replaces, c),
                    ).rowcount
                ):
                    raise ValueError("invalid replacement")
                db.execute(
                    "INSERT INTO sources(id,case_id,kind,rights_id,body,raw) VALUES(?,?,?,?,?,?)",
                    (source["id"], c, kind, rights_id, canonical(source), raw),
                )
                db.execute("UPDATE cases SET revision=revision+1 WHERE id=?", (c,))
                db.execute(
                    "UPDATE jobs SET state='stale',token=NULL,lease_until=0 WHERE case_id=? AND state NOT IN ('cancelled','failed')",
                    (c,),
                )
                self.record(
                    db,
                    actor,
                    "source_added",
                    case["workspace"],
                    c,
                    {"id": source["id"], "hash": source["original_hash"], "rights_id": rights_id},
                )
                return {"id": source["id"], "revision": revision + 1}

            return self._idem(
                db,
                actor,
                c,
                "source",
                key,
                {
                    "revision": revision,
                    "name": name,
                    "hash": sha(raw),
                    "kind": kind,
                    "rights": rights_id,
                    "replaces": replaces,
                },
                insert,
            )

    def source(self, actor, sid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM sources WHERE id=?", (sid,)).fetchone()
            if not row:
                raise KeyError("not found")
            case = self._case(db, actor, row["case_id"])
            right = db.execute(
                "SELECT expires FROM rights WHERE id=?", (row["rights_id"],)
            ).fetchone()
            if not right or right[0] <= time.time():
                raise PermissionError("source authority expired")
            body = json.loads(row["body"])
            if (
                sha(bytes(row["raw"])) != body["original_hash"]
                or sha(body["text"].encode()) != body["text_hash"]
            ):
                raise ValueError("source integrity")
            return {"case_id": case["id"], **body}

    def _snapshot(self, db, actor, c):
        case = self._case(db, actor, c, {"owner", "analyst"})
        if json.loads(case["context"])["jurisdiction"] != "UK" and not self.evaluation_only:
            raise ValueError("Non-UK source replay requires an isolated evaluation store")
        workspace = dict(
            db.execute("SELECT * FROM workspaces WHERE id=?", (case["workspace"],)).fetchone()
        )
        policy = json.loads(workspace["policy"])
        if not policy["egress_enabled"]:
            raise ValueError("policy does not permit egress")
        sources = []
        kinds = set()
        rights = []
        for r in db.execute("SELECT * FROM sources WHERE case_id=? AND active=1 ORDER BY id", (c,)):
            right = db.execute(
                "SELECT * FROM rights WHERE id=? AND workspace=? AND expires>?",
                (r["rights_id"], case["workspace"], time.time()),
            ).fetchone()
            if not right or not json.loads(right["body"])["egress"]:
                raise ValueError("source egress authority expired or absent")
            source = json.loads(r["body"])
            if sha(bytes(r["raw"])) != source["original_hash"]:
                raise ValueError("source bytes corrupt")
            sources.append(source)
            kinds.add(r["kind"])
            rights.append({"id": right["id"], "hash": digest(json.loads(right["body"]))})
        evidence = evidence_for(sources)
        context = json.loads(case["context"])
        blockers = list(context["missing"]) + [
            "Missing required document: " + kind
            for kind in policy["required_documents"]
            if kind not in kinds
        ]
        if evidence["partial"]:
            blockers.append("Incomplete evidence coverage")
        user = db.execute("SELECT revision FROM users WHERE name=?", (actor,)).fetchone()[0]
        epoch = db.execute("SELECT epoch FROM meta WHERE id=1").fetchone()[0]
        binding = digest(
            {
                "case": c,
                "revision": case["revision"],
                "context": context,
                "evidence": evidence,
                "rights": rights,
                "policy": policy,
                "policy_revision": workspace["policy_revision"],
                "authority": workspace["auth_revision"],
                "actor_revision": user,
                "epoch": epoch,
                "protocol": "v1",
            }
        )
        return {
            "binding": binding,
            "case_id": c,
            "workspace": case["workspace"],
            "context": {
                **context,
                "facts": redact(context["facts"]),
                "draft": redact(context["draft"]),
            },
            "evidence": evidence,
            "policy": policy,
            "blockers": sorted(set(blockers)),
            "epoch": epoch,
        }

    def preview(self, actor, c):
        with self.connect() as db:
            return self._snapshot(db, actor, c)

    def start(self, actor, c, binding, key):
        with self.write() as db:
            self._case(db, actor, c, {"owner", "analyst"})

            def create():
                snapshot = self._snapshot(db, actor, c)
                journal.assert_current(db, self.journal_path)
                from .recovery import liabilities_resolved

                liabilities_resolved(self, db)
                if snapshot["binding"] != binding:
                    raise ValueError("preview changed")
                if db.execute(
                    "SELECT hold FROM workspaces WHERE id=?", (snapshot["workspace"],)
                ).fetchone()[0]:
                    raise ValueError("runtime circuit open")
                if db.execute(
                    "SELECT 1 FROM jobs WHERE case_id=? AND state IN ('queued','running')", (c,)
                ).fetchone():
                    raise ValueError("case already active")
                jid = ident()
                now = time.time()
                db.execute(
                    "INSERT INTO jobs(id,case_id,actor,binding,snapshot,state,created,deadline) VALUES(?,?,?,?,?,'queued',?,?)",
                    (jid, c, actor, binding, canonical(snapshot), now, now + 1800),
                )
                db.execute("UPDATE jobs SET snapshot_hash=? WHERE id=?", (digest(snapshot), jid))
                self.record(
                    db,
                    actor,
                    "run_authorized",
                    snapshot["workspace"],
                    c,
                    {"job": jid, "binding": binding, "max_calls": 22},
                )
                return {"id": jid, "binding": binding, "state": "queued"}

            return self._idem(db, actor, c, "start", key, {"binding": binding}, create)

    def job(self, actor, jid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            if not row:
                raise KeyError("not found")
            self._case(db, actor, row["case_id"])
            value = dict(row)
            if digest(json.loads(row["snapshot"])) != row["snapshot_hash"]:
                raise ValueError("snapshot integrity")
            for source in json.loads(row["snapshot"])["evidence"]["sources"]:
                right = db.execute(
                    "SELECT r.expires FROM rights r JOIN sources s ON s.rights_id=r.id WHERE s.id=?",
                    (source["id"],),
                ).fetchone()
                if not right or right[0] <= time.time():
                    raise PermissionError("source authority expired")
            value.pop("token")
            value["snapshot"] = json.loads(value["snapshot"])
            value["packet"] = json.loads(value["packet"]) if value["packet"] else None
            value["checkpoints"] = self._checkpoints(db, jid)
            value["attempts"] = [
                {**dict(r), "receipt": json.loads(r["receipt"]) if r["receipt"] else None}
                for r in db.execute("SELECT * FROM attempts WHERE job=? ORDER BY rowid", (jid,))
            ]
            value["reviews"] = [
                {**dict(r), "body": json.loads(r["body"])}
                for r in db.execute("SELECT * FROM reviews WHERE job=? ORDER BY created", (jid,))
            ]
            value["prior_packets"] = []
            for r in db.execute("SELECT * FROM packet_history WHERE job=? ORDER BY rowid", (jid,)):
                packet = json.loads(r["body"])
                if digest(packet) != r["hash"]:
                    raise ValueError("historical packet integrity")
                value["prior_packets"].append(
                    {
                        "id": r["id"],
                        "hash": r["hash"],
                        "recovery": r["recovery"],
                        "label": "UNAPPROVED HISTORICAL DRAFT",
                        "packet": packet,
                    }
                )
            value["reconciliations"] = [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT r.body FROM attempt_reconciliations r JOIN attempts a ON a.id=r.attempt_id WHERE a.job=? ORDER BY r.rowid",
                    (jid,),
                )
            ]
            from .recovery import incident_notices

            value["incidents"] = incident_notices(self, db, jid)
            return value

    def list_jobs(self, actor, c):
        with self.connect() as db:
            self._case(db, actor, c)
            return [
                dict(r)
                for r in db.execute(
                    "SELECT id,state,binding,calls,error,created,packet_hash FROM jobs WHERE case_id=? ORDER BY created DESC LIMIT 100",
                    (c,),
                )
            ]

    def claim(self, lease=600):
        now = time.time()
        with self.write() as db:
            for row in db.execute(
                "SELECT * FROM jobs WHERE state='running' AND lease_until<=? AND claims>=4", (now,)
            ).fetchall():
                try:
                    stages = self._checkpoints(db, row["id"])
                except (ValueError, TypeError):
                    db.execute(
                        "UPDATE jobs SET state='failed',error='checkpoint_integrity',packet=NULL,packet_hash=NULL,token=NULL,lease_until=0 WHERE id=?",
                        (row["id"],),
                    )
                    workspace = db.execute(
                        "SELECT workspace FROM cases WHERE id=?", (row["case_id"],)
                    ).fetchone()[0]
                    db.execute(
                        "UPDATE workspaces SET hold='checkpoint integrity requires operator investigation' WHERE id=?",
                        (workspace,),
                    )
                    self.record(
                        db,
                        "worker",
                        "checkpoint_integrity_failed",
                        workspace,
                        row["case_id"],
                        {"job": row["id"]},
                    )
                    continue
                packet = {
                    "job_id": row["id"],
                    "binding": row["binding"],
                    "approved": False,
                    "proposals": {
                        k.split(":", 1)[1]: v["value"]
                        for k, v in stages.items()
                        if k.startswith("proposal:") and v.get("value")
                    },
                    "checkpoints": stages,
                    "consensus": None,
                    "synthesis": None,
                    "critique": None,
                    "review_requirements": ["claim_exhausted"],
                    "review_questions": {
                        "claim_exhausted": "Four worker claims failed. Inspect all retained work and usage before relying on this packet."
                    },
                    "limitations": ["Incomplete workflow. No automatic consensus is asserted."],
                }
                db.execute(
                    "UPDATE jobs SET state='manual_required',error='claim_exhausted',packet=?,packet_hash=?,token=NULL,lease_until=0 WHERE id=?",
                    (canonical(packet), digest(packet), row["id"]),
                )
                workspace = db.execute(
                    "SELECT workspace FROM cases WHERE id=?", (row["case_id"],)
                ).fetchone()[0]
                if db.execute(
                    "SELECT 1 FROM attempts WHERE job=? AND receipt IS NULL", (row["id"],)
                ).fetchone():
                    db.execute(
                        "UPDATE workspaces SET hold='unresolved interrupted call' WHERE id=?",
                        (workspace,),
                    )
                self.record(
                    db, "worker", "claim_exhausted", workspace, row["case_id"], {"job": row["id"]}
                )
            if db.execute(
                "SELECT 1 FROM jobs WHERE state='running' AND lease_until>?", (now,)
            ).fetchone():
                return None
            row = db.execute(
                "SELECT * FROM jobs WHERE state='queued' OR (state='running' AND lease_until<=?) ORDER BY created LIMIT 1",
                (now,),
            ).fetchone()
            if not row:
                return None
            token = secrets.token_hex(24)
            db.execute(
                "UPDATE jobs SET state='running',claims=claims+1,token=?,lease_until=? WHERE id=?",
                (token, now + lease, row["id"]),
            )
            return dict(db.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone())

    def fenced(self, db, job, context=True):
        row = db.execute(
            "SELECT * FROM jobs WHERE id=? AND state='running' AND token=? AND lease_until>?",
            (job["id"], job["token"], time.time()),
        ).fetchone()
        if not row:
            raise LeaseLost("expired, cancelled or replaced job")
        if digest(json.loads(row["snapshot"])) != row["snapshot_hash"]:
            raise ValueError("snapshot integrity")
        if context:
            try:
                current_snapshot = self._snapshot(db, row["actor"], row["case_id"])
                current = current_snapshot["binding"]
            except (KeyError, ValueError, PermissionError) as exc:
                raise LeaseLost("source or authority unavailable") from exc
            if current != row["binding"]:
                raise LeaseLost("snapshot changed")
            if canonical(current_snapshot) != canonical(json.loads(row["snapshot"])):
                raise ValueError("snapshot body integrity")
        return dict(row)

    def invalidate_if_owned(self, job):
        with self.write() as db:
            db.execute(
                "UPDATE jobs SET state='stale',token=NULL,lease_until=0 WHERE id=? AND state='running' AND token=? AND lease_until>?",
                (job["id"], job["token"], time.time()),
            )

    def renew(self, job):
        with self.write() as db:
            self.fenced(db, job)
            db.execute("UPDATE jobs SET lease_until=? WHERE id=?", (time.time() + 600, job["id"]))
            self._beat(db, "worker", "active")

    def _checkpoints(self, db, jid):
        out = {}
        for r in db.execute("SELECT * FROM checkpoints WHERE job=?", (jid,)):
            body = json.loads(r["body"])
            if digest(body) != r["hash"]:
                raise ValueError("checkpoint integrity")
            out[r["stage"]] = body
        return out

    def checkpoints(self, job):
        with self.connect() as db:
            return self._checkpoints(db, job["id"])

    def checkpoint(self, job, stage, value):
        with self.write() as db:
            self.fenced(db, job)
            prior = db.execute(
                "SELECT hash FROM checkpoints WHERE job=? AND stage=?", (job["id"], stage)
            ).fetchone()
            if prior and prior[0] != digest(value):
                raise ValueError("immutable stage")
            db.execute(
                "INSERT OR IGNORE INTO checkpoints VALUES(?,?,?,?)",
                (job["id"], stage, canonical(value), digest(value)),
            )
            snapshot = json.loads(job["snapshot"])
            self.record(
                db,
                "worker",
                "stage_checkpoint",
                snapshot["workspace"],
                job["case_id"],
                {"job": job["id"], "stage": stage, "hash": digest(value)},
            )

    def note(self, job, action, detail):
        with self.write() as db:
            self.fenced(db, job)
            snapshot = json.loads(job["snapshot"])
            self.record(
                db,
                "worker",
                action,
                snapshot["workspace"],
                job["case_id"],
                {"job": job["id"], **detail},
            )

    def reserve(self, job, stage, prompt_hash, timeout=90):
        with self.write() as db:
            row = self.fenced(db, job)
            events = journal.assert_current(db, self.journal_path)
            limits = [e["max_calls"] for e in events if e["kind"] == "campaign_call_limit"]
            if limits and sum(e["kind"] == "reserved" for e in events) >= min(limits):
                raise ValueError("cumulative campaign call ceiling exhausted")
            from .recovery import liabilities_resolved

            liabilities_resolved(self, db)
            if db.execute("SELECT 1 FROM attempts WHERE receipt IS NULL LIMIT 1").fetchone():
                raise ValueError("another call is in flight or has unknown outcome")
            snapshot = json.loads(row["snapshot"])
            if db.execute(
                "SELECT hold FROM workspaces WHERE id=?", (snapshot["workspace"],)
            ).fetchone()[0]:
                raise ValueError("runtime circuit open")
            n = db.execute(
                "SELECT count(*) FROM attempts WHERE job=? AND stage=?", (job["id"], stage)
            ).fetchone()[0]
            if (
                n >= 2
                or row["calls"] >= 22
                or row["seconds"] + timeout > 1800
                or time.time() + timeout > row["deadline"]
            ):
                raise ValueError("run allowance exhausted")
            aid = ident()
            db.execute(
                "INSERT INTO attempts(id,job,stage,sequence,prompt_hash,reserved) VALUES(?,?,?,?,?,?)",
                (aid, job["id"], stage, n + 1, prompt_hash, timeout),
            )
            db.execute(
                "UPDATE jobs SET calls=calls+1,seconds=seconds+? WHERE id=?", (timeout, job["id"])
            )
            self.record(
                db,
                "worker",
                "call_reserved",
                snapshot["workspace"],
                row["case_id"],
                {"job": job["id"], "attempt": aid, "stage": stage},
            )
            journal.append(
                db,
                self.journal_path,
                {
                    "kind": "reserved",
                    "attempt": aid,
                    "job": job["id"],
                    "workspace": snapshot["workspace"],
                    "stage": stage,
                    "reserved_seconds": timeout,
                    "occurred": time.time(),
                },
            )
            return aid

    def settle(self, aid, receipt):
        from .runtime import receipt_from_events, safe_diagnostic

        receipt = dict(receipt)
        if "diagnostic" in receipt:
            receipt["diagnostic"] = safe_diagnostic(receipt["diagnostic"])
        observed = receipt_from_events(
            canonical({"type": "turn.completed", "usage": receipt.get("usage")}),
            receipt.get("elapsed_ms", 0),
            bool(receipt.get("tools_audited")),
            str(receipt.get("status", "unknown")),
        )
        receipt["usage"] = observed["usage"]
        with self.write() as db:
            row = db.execute(
                "SELECT a.*,j.snapshot,j.case_id,c.workspace FROM attempts a JOIN jobs j ON a.job=j.id JOIN cases c ON c.id=j.case_id WHERE a.id=?",
                (aid,),
            ).fetchone()
            if not row:
                raise KeyError("unknown attempt")
            if row["receipt"]:
                if row["receipt"] != canonical(receipt):
                    raise ValueError("conflicting settlement")
                return
            db.execute("UPDATE attempts SET receipt=? WHERE id=?", (canonical(receipt), aid))
            elapsed = min(row["reserved"], max(0, receipt.get("elapsed_ms", 0) / 1000))
            known = isinstance(receipt.get("usage"), dict)
            if known:
                db.execute(
                    "UPDATE jobs SET seconds=max(0,seconds-?) WHERE id=?",
                    (row["reserved"] - elapsed, row["job"]),
                )
            workspace = row["workspace"]
            if not known or not receipt.get("tools_audited"):
                db.execute(
                    "UPDATE workspaces SET hold=? WHERE id=?",
                    ("unknown usage or unsafe runtime", workspace),
                )
            self.record(
                db,
                "worker",
                "call_settled",
                workspace,
                row["case_id"],
                {
                    "job": row["job"],
                    "attempt": aid,
                    "known_usage": known,
                    "tools_audited": bool(receipt.get("tools_audited")),
                },
            )
            journal.append(
                db,
                self.journal_path,
                {
                    "kind": "settled",
                    "attempt": aid,
                    "job": row["job"],
                    "workspace": workspace,
                    "receipt": receipt,
                    "occurred": time.time(),
                },
            )

    def finish(self, job, packet, state="draft_ready", error=None):
        with self.write() as db:
            row = self.fenced(db, job)
            value = {**packet, "job_id": job["id"], "binding": row["binding"], "approved": False}
            db.execute(
                "UPDATE jobs SET state=?,error=?,packet=?,packet_hash=?,token=NULL,lease_until=0 WHERE id=?",
                (state, error, canonical(value), digest(value), job["id"]),
            )
            self.record(
                db,
                "worker",
                "packet_created",
                json.loads(row["snapshot"])["workspace"],
                row["case_id"],
                {"job": job["id"], "hash": digest(value), "state": state},
            )

    def reconcile_attempt(self, actor, aid, expected_head, evidence, reference, key):
        from .recovery import reconcile_attempt

        return reconcile_attempt(self, actor, aid, expected_head, evidence, reference, key)

    def close_incident(
        self,
        actor,
        aid,
        expected_head,
        reason,
        isolation_reference,
        acknowledge_unknown,
        runtime_isolated,
        key,
    ):
        from .recovery import close_incident

        return close_incident(
            self,
            actor,
            aid,
            expected_head,
            reason,
            isolation_reference,
            acknowledge_unknown,
            runtime_isolated,
            key,
        )

    def resume_job(self, actor, jid, packet_hash, expected_head, wall_seconds, reason, key):
        from .recovery import resume_job

        return resume_job(self, actor, jid, packet_hash, expected_head, wall_seconds, reason, key)

    def cancel(self, actor, jid):
        with self.write() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            if not row:
                raise KeyError("not found")
            case = self._case(db, actor, row["case_id"], {"owner", "analyst"})
            if row["state"] in {"queued", "running"}:
                db.execute(
                    "UPDATE jobs SET state='cancelled',token=NULL,lease_until=0 WHERE id=?", (jid,)
                )
            self.record(db, actor, "run_cancelled", case["workspace"], case["id"], {"job": jid})

    def review(self, actor, jid, value, key):
        review = Review.model_validate(value)
        with self.write() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            if not row:
                raise KeyError("not found")
            case = self._case(db, actor, row["case_id"], {"owner", "reviewer"})

            def commit():
                if actor in {row["actor"], case["creator"]}:
                    raise PermissionError("separate reviewer required")
                if (
                    row["state"] not in {"draft_ready", "manual_required"}
                    or not row["packet"]
                    or row["packet_hash"] != review.packet_hash
                    or digest(json.loads(row["packet"])) != review.packet_hash
                ):
                    raise ValueError("packet unavailable or changed")
                # Reviewers do not acquire analyst rights: currentness uses the run author.
                if self._snapshot(db, row["actor"], case["id"])["binding"] != row["binding"]:
                    raise ValueError("stale review")
                packet = json.loads(row["packet"])
                required = set(packet.get("review_requirements", []))
                if not required <= set(review.resolutions):
                    raise ValueError("resolve each named blocker explicitly")
                allowed = set(required)
                if set(review.resolutions) - allowed:
                    raise ValueError("unknown finding resolution")
                issues = {i["id"] for i in json.loads(case["context"])["issues"]}
                if set(review.overrides) - issues:
                    raise ValueError("unknown issue override")
                rid = ident()
                db.execute(
                    "INSERT INTO reviews VALUES(?,?,?,?,?,?)",
                    (rid, jid, actor, canonical(review.model_dump()), row["binding"], time.time()),
                )
                self.record(
                    db,
                    actor,
                    "packet_reviewed",
                    case["workspace"],
                    case["id"],
                    {"job": jid, "review": rid, "packet_hash": review.packet_hash},
                )
                return {"id": rid, "packet_hash": review.packet_hash}

            return self._idem(db, actor, jid, "review", key, review.model_dump(), commit)

    def export(self, actor, jid, reviewed=False):
        with self.write() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            if not row:
                raise KeyError("not found")
            case = self._case(db, actor, row["case_id"])
            if not row["packet"]:
                raise ValueError("no packet available")
            packet = json.loads(row["packet"])
            if digest(packet) != row["packet_hash"]:
                raise ValueError("packet integrity")
            current = False
            try:
                current = self._snapshot(db, row["actor"], case["id"])["binding"] == row["binding"]
            except (ValueError, PermissionError, KeyError):
                pass
            # Expired source authority blocks all exports, including historical drafts.
            for source in json.loads(row["snapshot"])["evidence"]["sources"]:
                right = db.execute(
                    "SELECT r.expires FROM rights r JOIN sources s ON s.rights_id=r.id WHERE s.id=?",
                    (source["id"],),
                ).fetchone()
                if not right or right[0] <= time.time():
                    raise PermissionError("source authority expired")
            review = db.execute(
                "SELECT * FROM reviews WHERE job=? ORDER BY created DESC LIMIT 1", (jid,)
            ).fetchone()
            if reviewed:
                self._access(db, actor, case["workspace"], {"owner", "reviewer"})
                if (
                    not current
                    or row["state"] not in {"draft_ready", "manual_required"}
                    or not review
                    or review["binding"] != row["binding"]
                ):
                    raise ValueError("current reviewed packet required")
                self._access(db, review["actor"], case["workspace"], {"owner", "reviewer"})
            self.record(
                db,
                actor,
                "packet_exported",
                case["workspace"],
                case["id"],
                {"job": jid, "reviewed": reviewed, "current": current},
            )
            from .recovery import incident_notices

            return {
                "packet": packet,
                "incidents": incident_notices(self, db, jid),
                "packet_hash": row["packet_hash"],
                "label": "HUMAN REVIEWED" if reviewed else "UNAPPROVED DRAFT",
                "approved": reviewed,
                "current": current,
                "review": {**dict(review), "body": json.loads(review["body"])}
                if reviewed
                else None,
                "exported_at": time.time(),
            }

    def audit(self, actor, w, after=0):
        with self.connect() as db:
            self._access(db, actor, w)
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM audit WHERE workspace=? AND seq>? ORDER BY seq LIMIT 200",
                    (w, after),
                )
            ]

    def _beat(self, db, name, detail):
        db.execute(
            "INSERT INTO heartbeat VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET updated=excluded.updated,detail=excluded.detail",
            (name, time.time(), detail),
        )

    def beat(self, name="worker", detail="idle"):
        with self.write() as db:
            self._beat(db, name, detail)

    def erasure_preview(self, actor, c):
        with self.connect() as db:
            case = self._case(db, actor, c, {"owner"})
            return {
                "case_id": c,
                "revision": case["revision"],
                "sources": db.execute(
                    "SELECT count(*) FROM sources WHERE case_id=?", (c,)
                ).fetchone()[0],
                "runs": db.execute("SELECT count(*) FROM jobs WHERE case_id=?", (c,)).fetchone()[0],
                "warning": "Downloaded exports, model egress and protected backups cannot be recalled by this operation. Follow the approved retention policy.",
            }

    def erase(self, actor, c, revision, reason):
        if len(reason) < 10:
            raise ValueError("reason required")
        with self.write() as db:
            case = self._case(db, actor, c, {"owner"})
            if case["revision"] != revision:
                raise ValueError("stale erasure preview")
            db.execute(
                "DELETE FROM checkpoints WHERE job IN (SELECT id FROM jobs WHERE case_id=?)", (c,)
            )
            for table in ("checkpoint_history", "packet_history"):
                db.execute(
                    f"DELETE FROM {table} WHERE job IN (SELECT id FROM jobs WHERE case_id=?)", (c,)
                )
            db.execute(
                "UPDATE reviews SET body='{}' WHERE job IN (SELECT id FROM jobs WHERE case_id=?)",
                (c,),
            )
            db.execute(
                "UPDATE jobs SET snapshot='{}',packet=NULL,packet_hash=NULL,state='cancelled',token=NULL,lease_until=0 WHERE case_id=?",
                (c,),
            )
            db.execute("DELETE FROM sources WHERE case_id=?", (c,))
            db.execute(
                "UPDATE cases SET context='{}',erased=1,revision=revision+1 WHERE id=?", (c,)
            )
            self.record(
                db,
                actor,
                "case_erased",
                case["workspace"],
                c,
                {"reason_hash": digest(reason), "backup_retention_review_required": True},
            )
