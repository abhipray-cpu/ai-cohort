"""Independent scoped SQLite store, immutable memory versions and erasure-safe derivations."""

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from contracts.relaydesk import ImportBatch, SourceMessage

from relaydesk_api.common import digest, ident, now
from relaydesk_api.ledger import register, verify


class Store:
    def __init__(self, directory="var/relaydesk", *, ledger_dir=None):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "relaydesk.sqlite3"
        self.ledger_dir = Path(ledger_dir or self.root.parent / "relaydesk-erasure")
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY,salt TEXT,hash TEXT,admin INTEGER);
            CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY,actor TEXT,csrf TEXT,expires TEXT);
            CREATE TABLE IF NOT EXISTS login_failures(actor TEXT,at TEXT);
            CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY,name TEXT,owner TEXT,revision INTEGER DEFAULT 1);
            CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY,account_id TEXT,name TEXT,owner TEXT,revision INTEGER DEFAULT 1,policy TEXT DEFAULT '{}',created_at TEXT);
            CREATE TABLE IF NOT EXISTS members(case_id TEXT,actor TEXT,roles TEXT,PRIMARY KEY(case_id,actor));
            CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,case_id TEXT,source_key TEXT,revision INTEGER,body TEXT,sha256 TEXT,author TEXT,created_at TEXT,updated_at TEXT,observed_at TEXT,active INTEGER DEFAULT 1,erased INTEGER DEFAULT 0,UNIQUE(case_id,source_key,revision));
            CREATE TABLE IF NOT EXISTS imports(id TEXT PRIMARY KEY,case_id TEXT,origin TEXT,counts TEXT,gaps TEXT,at TEXT);
            CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY,case_id TEXT,revision INTEGER,state TEXT,promoted INTEGER DEFAULT 0,fingerprint TEXT,UNIQUE(case_id,fingerprint));
            CREATE TABLE IF NOT EXISTS versions(memory_id TEXT,revision INTEGER,body TEXT,kind TEXT,state TEXT,source_id TEXT,start INTEGER,end INTEGER,available_at TEXT,reason TEXT,PRIMARY KEY(memory_id,revision));
            CREATE TABLE IF NOT EXISTS vectors(memory_id TEXT,revision INTEGER,start INTEGER,end INTEGER,model TEXT,value BLOB,PRIMARY KEY(memory_id,revision,start,model));
            CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,case_id TEXT,actor TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS chat_sessions(id TEXT PRIMARY KEY,conversation_id TEXT,actor TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS turns(id TEXT PRIMARY KEY,conversation_id TEXT,session_id TEXT,source_id TEXT,output_id TEXT,seq INTEGER,role TEXT);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,case_id TEXT,conversation_id TEXT,session_id TEXT,actor TEXT,question TEXT,key TEXT,request_hash TEXT,status TEXT,lease TEXT,lease_until TEXT,deadline TEXT,model_calls INTEGER DEFAULT 0,grant INTEGER DEFAULT 1,cancelled INTEGER DEFAULT 0,output_id TEXT,reason TEXT,created_at TEXT,UNIQUE(case_id,key));
            CREATE TABLE IF NOT EXISTS continuations(job_id TEXT,key TEXT,PRIMARY KEY(job_id,key));
            CREATE TABLE IF NOT EXISTS outputs(id TEXT PRIMARY KEY,case_id TEXT,job_id TEXT,case_revision INTEGER,payload TEXT,sha256 TEXT,state TEXT,reviewer TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS summaries(id TEXT PRIMARY KEY,case_id TEXT,case_revision INTEGER,payload TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,case_id TEXT,kind TEXT,detail TEXT,at TEXT);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
            """)
            if "options" not in {r[1] for r in db.execute("PRAGMA table_info(jobs)")}:
                db.execute("ALTER TABLE jobs ADD COLUMN options TEXT DEFAULT '{}'")
            initialized = db.execute("SELECT value FROM settings WHERE key='store_id'").fetchone()
            if initialized:
                self.store_id = initialized[0]
                if not (self.ledger_dir / "ledger.sqlite3").exists():
                    raise RuntimeError(
                        "Independent erasure ledger is required; restore fails closed"
                    )
            else:
                self.store_id = ident()
                db.execute("INSERT INTO settings VALUES('store_id',?)", (self.store_id,))
                db.execute("INSERT INTO settings VALUES('epoch',?)", (ident(),))
        if initialized:
            self.ledger_binding = verify(
                self.ledger_dir / "ledger.sqlite3", self.store_id, self.setting("ledger_binding")
            )
        else:
            self.ledger_binding = register(self.ledger_dir / "ledger.sqlite3", self.store_id)
            self.set_setting("ledger_binding", self.ledger_binding)
        self.reconcile_erasures()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def setting(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return (
            json.loads(row[0])
            if row and key not in ("epoch", "store_id")
            else row[0]
            if row
            else default
        )

    def set_setting(self, key, value):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, json.dumps(value)))

    def add_user(self, name, password, admin=False):
        if not name or len(name) > 80 or len(password) < 12 or password == "replace-me":
            raise ValueError("Use a unique 12+ character password")
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()
        with self.connect() as db:
            try:
                db.execute("INSERT INTO users VALUES(?,?,?,?)", (name, salt, hashed, int(admin)))
            except sqlite3.IntegrityError as error:
                raise ValueError("User already exists") from error

    def user(self, actor):
        with self.connect() as db:
            row = db.execute("SELECT name,admin FROM users WHERE name=?", (actor,)).fetchone()
        if not row:
            raise PermissionError("Unknown actor")
        return dict(row)

    def login(self, actor, password):
        cutoff = (datetime.now(UTC) - timedelta(minutes=15)).isoformat()
        with self.connect() as db:
            if (
                db.execute(
                    "SELECT count(*) FROM login_failures WHERE actor=? AND at>?", (actor, cutoff)
                ).fetchone()[0]
                >= 5
            ):
                raise PermissionError("Login temporarily limited")
            row = db.execute("SELECT * FROM users WHERE name=?", (actor,)).fetchone()
            hashed = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(),
                (row["salt"] if row else "invalid-user").encode(),
                310000,
            ).hex()
            if not row or not secrets.compare_digest(hashed, row["hash"]):
                db.execute("INSERT INTO login_failures VALUES(?,?)", (actor, now()))
            else:
                token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                db.execute("DELETE FROM login_failures WHERE actor=?", (actor,))
                db.execute(
                    "INSERT INTO sessions VALUES(?,?,?,?)",
                    (
                        digest(token),
                        actor,
                        csrf,
                        (datetime.now(UTC) + timedelta(hours=8)).isoformat(),
                    ),
                )
                return {
                    "token": token,
                    "csrf": csrf,
                    "username": actor,
                    "admin": bool(row["admin"]),
                }
        raise PermissionError("Invalid credentials")

    def authenticate(self, token):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM sessions WHERE hash=? AND expires>?", (digest(token), now())
            ).fetchone()
        if not row:
            raise PermissionError("Sign in required")
        return {
            "username": row["actor"],
            "admin": bool(self.user(row["actor"])["admin"]),
            "csrf": row["csrf"],
        }

    def logout(self, token):
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE hash=?", (digest(token),))

    def create_account(self, actor, name):
        self.user(actor)
        aid = ident()
        with self.connect() as db:
            db.execute("INSERT INTO accounts(id,name,owner) VALUES(?,?,?)", (aid, name, actor))
        return {"id": aid, "name": name, "owner": actor}

    def accounts(self, actor):
        self.user(actor)
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT DISTINCT a.* FROM accounts a LEFT JOIN cases c ON c.account_id=a.id LEFT JOIN members m ON m.case_id=c.id WHERE a.owner=? OR (m.actor=? AND m.roles!='[]') ORDER BY a.name",
                    (actor, actor),
                )
            ]

    def create_case(self, actor, aid, name):
        with self.connect() as db:
            account = db.execute("SELECT * FROM accounts WHERE id=?", (aid,)).fetchone()
            if not account or account["owner"] != actor:
                raise PermissionError("Account owner required")
            cid = ident()
            db.execute(
                "INSERT INTO cases(id,account_id,name,owner,policy,created_at) VALUES(?,?,?,?,?,?)",
                (
                    cid,
                    aid,
                    name,
                    actor,
                    json.dumps({"model_egress": False, "github_repositories": []}),
                    now(),
                ),
            )
            db.execute(
                "INSERT INTO members VALUES(?,?,?)",
                (cid, actor, json.dumps(["investigator", "reviewer"])),
            )
            self._event(db, cid, "case_created", {})
        return self.case(actor, cid)

    def case(self, actor, cid, role=None):
        self.user(actor)
        with self.connect() as db:
            row = db.execute(
                "SELECT c.*,a.name account_name,a.revision account_revision,m.roles FROM cases c JOIN accounts a ON a.id=c.account_id JOIN members m ON m.case_id=c.id WHERE c.id=? AND m.actor=?",
                (cid, actor),
            ).fetchone()
        if not row or not json.loads(row["roles"]) or role and role not in json.loads(row["roles"]):
            raise PermissionError("Case permission required")
        result = dict(row)
        result["policy"] = json.loads(result["policy"])
        result["roles"] = json.loads(result["roles"])
        return result

    def cases(self, actor):
        self.user(actor)
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT c.id,c.name,c.account_id,c.revision,a.name account_name FROM cases c JOIN accounts a ON a.id=c.account_id JOIN members m ON m.case_id=c.id WHERE m.actor=? AND m.roles!='[]' ORDER BY c.created_at DESC",
                    (actor,),
                )
            ]

    def _event(self, db, cid, kind, detail):
        db.execute(
            "INSERT INTO events(case_id,kind,detail,at) VALUES(?,?,?,?)",
            (cid, kind, json.dumps(detail), now()),
        )

    def _bump(self, db, cid, kind, detail):
        db.execute("UPDATE cases SET revision=revision+1 WHERE id=?", (cid,))
        db.execute(
            "UPDATE accounts SET revision=revision+1 WHERE id=(SELECT account_id FROM cases WHERE id=?)",
            (cid,),
        )
        db.execute(
            "UPDATE outputs SET state='stale',reviewer=NULL WHERE case_id IN (SELECT id FROM cases WHERE account_id=(SELECT account_id FROM cases WHERE id=?)) AND state!='erased'",
            (cid,),
        )
        self._event(db, cid, kind, detail)

    def membership(self, actor, cid, username, roles):
        scope = self.case(actor, cid)
        if scope["owner"] != actor:
            raise PermissionError("Case owner required")
        self.user(username)
        if not set(roles).issubset({"investigator", "reviewer"}) or username == actor and not roles:
            raise ValueError("Invalid roles")
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO members VALUES(?,?,?)", (cid, username, json.dumps(roles))
            )
            self._bump(db, cid, "membership_changed", {"actor": username})

    def policy(self, actor, cid, value):
        scope = self.case(actor, cid)
        if scope["owner"] != actor:
            raise PermissionError("Case owner required")
        import re

        if any(
            not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", r)
            for r in value.github_repositories
        ):
            raise ValueError("Invalid repository")
        with self.connect() as db:
            if (
                db.execute(
                    "UPDATE cases SET policy=? WHERE id=? AND revision=?",
                    (
                        json.dumps(value.model_dump(exclude={"expected_revision"})),
                        cid,
                        value.expected_revision,
                    ),
                ).rowcount
                != 1
            ):
                raise ValueError("Stale policy revision")
            self._bump(db, cid, "policy_changed", {})
        return self.case(actor, cid)

    def _source(self, db, cid, msg):
        old = db.execute(
            "SELECT * FROM sources WHERE case_id=? AND source_key=? ORDER BY revision DESC LIMIT 1",
            (cid, msg.source_key),
        ).fetchone()
        if old and old["erased"]:
            raise ValueError("Erased source identity cannot be reimported")
        hashed = digest([msg.body, msg.author, msg.created_at, msg.updated_at])
        if old and old["sha256"] == hashed:
            return old["id"], False
        if old:
            db.execute("UPDATE sources SET active=0 WHERE id=?", (old["id"],))
            db.execute(
                "UPDATE memories SET state='superseded' WHERE id IN (SELECT memory_id FROM versions WHERE source_id=?)",
                (old["id"],),
            )
        sid = ident()
        db.execute(
            "INSERT INTO sources(id,case_id,source_key,revision,body,sha256,author,created_at,updated_at,observed_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                sid,
                cid,
                msg.source_key,
                old["revision"] + 1 if old else 1,
                msg.body,
                hashed,
                msg.author,
                msg.created_at,
                msg.updated_at,
                now(),
            ),
        )
        return sid, True

    def _memory(
        self, db, cid, sid, text, kind, state, start, end, available, reason="", fingerprint=None
    ):
        fingerprint = fingerprint or digest([sid, text, kind, start, end])
        old = db.execute(
            "SELECT id FROM memories WHERE case_id=? AND fingerprint=?", (cid, fingerprint)
        ).fetchone()
        if old:
            return old[0]
        mid = ident()
        db.execute(
            "INSERT INTO memories(id,case_id,revision,state,fingerprint) VALUES(?,?,1,?,?)",
            (mid, cid, state, fingerprint),
        )
        db.execute(
            "INSERT INTO versions VALUES(?,1,?,?,?,?,?,?,?,?)",
            (mid, text, kind, state, sid, start, end, available, reason),
        )
        return mid

    def import_messages(self, actor, cid, value):
        self.case(actor, cid, "investigator")
        value = ImportBatch.model_validate(value)
        if len({m.source_key for m in value.messages}) != len(value.messages):
            raise ValueError("Duplicate source identities in batch")
        erased = {(r["case_id"], r["source_key"]) for r in self.ledger_entries()}
        if any((cid, m.source_key) in erased for m in value.messages):
            raise ValueError("Source identity erased by independent ledger")
        inserted = bots = 0
        with self.connect() as db:
            for msg in value.messages:
                if msg.updated_at < msg.created_at:
                    raise ValueError("Source update precedes creation")
                if msg.bot:
                    bots += 1
                    continue
                sid, new = self._source(db, cid, msg)
                if new:
                    self._memory(
                        db,
                        cid,
                        sid,
                        msg.body,
                        "episode",
                        "reported",
                        0,
                        len(msg.body),
                        msg.updated_at,
                    )
                    inserted += 1
            if inserted:
                self._bump(db, cid, "sources_imported", {"inserted": inserted})
            counts = {
                "submitted": len(value.messages),
                "inserted": inserted,
                "bots_excluded": bots,
                "complete": value.complete,
            }
            db.execute(
                "INSERT INTO imports VALUES(?,?,?,?,?,?)",
                (
                    ident(),
                    cid,
                    value.origin,
                    json.dumps(counts),
                    json.dumps(
                        value.gaps
                        + ([] if value.complete else ["Source capture declared incomplete"])
                    ),
                    now(),
                ),
            )
        return {**counts, "revision": self.case(actor, cid)["revision"]}

    def sources(self, actor, cid):
        self.case(actor, cid)
        with self.connect() as db:
            rows = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM sources WHERE case_id=? ORDER BY created_at,id", (cid,)
                )
            ]
        for row in rows:
            self.validate_source(row)
        return rows

    @staticmethod
    def validate_source(row):
        if (
            not row["erased"]
            and digest([row["body"], row["author"], row["created_at"], row["updated_at"]])
            != row["sha256"]
        ):
            raise ValueError("Source integrity failure")

    def verify_source_integrity(self):
        with self.connect() as db:
            for row in db.execute("SELECT * FROM sources"):
                self.validate_source(row)

    def source(self, actor, sid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM sources WHERE id=?", (sid,)).fetchone()
        if not row:
            raise ValueError("Source not found")
        self.case(actor, row["case_id"])
        self.validate_source(row)
        return dict(row)

    def memories(self, actor, cid, *, as_of=None, history=False, account=False):
        scope = self.case(actor, cid)
        with self.connect() as db:
            rows = db.execute(
                """SELECT m.id,m.case_id,m.revision current_revision,m.state current_state,m.promoted,v.*,s.source_key,s.revision source_revision,s.author,s.created_at,s.updated_at,s.erased,s.active,s.body source_body,s.sha256 source_hash
            FROM memories m JOIN versions v ON v.memory_id=m.id JOIN sources s ON s.id=v.source_id
            JOIN cases c ON c.id=m.case_id JOIN members a ON a.case_id=c.id
            WHERE a.actor=? AND a.roles!='[]' AND (m.case_id=? OR (? AND m.promoted=1 AND c.account_id=?))
            AND m.state NOT IN ('erased','suppressed') AND s.erased=0
            AND v.revision=(SELECT max(v2.revision) FROM versions v2 WHERE v2.memory_id=m.id AND (? IS NULL OR v2.available_at<=?))
            AND (? IS NULL OR s.updated_at<=?) ORDER BY v.available_at,m.id""",
                (actor, cid, int(account), scope["account_id"], as_of, as_of, as_of, as_of),
            ).fetchall()
        result = []
        checked_sources = set()
        for raw in rows:
            r = dict(raw)
            if not as_of:
                r["state"] = r["current_state"]
                if not history and (r["state"] == "superseded" or not r["active"]):
                    continue
            if r["state"] in ("suppressed", "erased"):
                continue
            if r["source_id"] not in checked_sources:
                self.validate_source({**r, "body": r["source_body"], "sha256": r["source_hash"]})
                checked_sources.add(r["source_id"])
            result.append(r)
        return result

    def add_proposals(self, actor, cid, proposals):
        self.case(actor, cid, "investigator")
        with self.connect() as db:
            before = db.total_changes
            for p in proposals:
                src = db.execute(
                    "SELECT * FROM sources WHERE id=? AND case_id=? AND active=1 AND erased=0",
                    (p.source_id, cid),
                ).fetchone()
                if not src or p.quote not in src["body"]:
                    raise ValueError("Proposal quote/source mismatch")
                start = src["body"].index(p.quote)
                self._memory(
                    db,
                    cid,
                    src["id"],
                    p.text,
                    p.kind,
                    "proposed",
                    start,
                    start + len(p.quote),
                    now(),
                    "Model proposal, not independently verified",
                )
            if db.total_changes > before:
                self._bump(db, cid, "memory_proposals", {})

    def memory(self, actor, mid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM memories WHERE id=?", (mid,)).fetchone()
        if not row:
            raise ValueError("Memory not found")
        self.case(actor, row["case_id"])
        return dict(row)

    def correct(self, actor, mid, expected, text, kind, state, reason):
        m = self.memory(actor, mid)
        self.case(actor, m["case_id"], "reviewer")
        if m["state"] == "erased":
            raise ValueError("Erased memory cannot be corrected")
        msg = SourceMessage(
            source_key=f"correction:{mid}:{expected + 1}",
            author=actor,
            body=text,
            created_at=now(),
            updated_at=now(),
        )
        with self.connect() as db:
            if (
                db.execute(
                    "UPDATE memories SET revision=revision+1,state=? WHERE id=? AND revision=?",
                    (state, mid, expected),
                ).rowcount
                != 1
            ):
                raise ValueError("Stale memory revision")
            sid, _ = self._source(db, m["case_id"], msg)
            db.execute(
                "INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?)",
                (mid, expected + 1, text, kind, state, sid, 0, len(text), msg.updated_at, reason),
            )
            self._bump(
                db, m["case_id"], "memory_corrected", {"memory_id": mid, "revision": expected + 1}
            )
        return self.memory(actor, mid)

    def promote(self, actor, mid, expected):
        m = self.memory(actor, mid)
        scope = self.case(actor, m["case_id"], "reviewer")
        with self.connect() as db:
            if (
                db.execute(
                    "SELECT owner FROM accounts WHERE id=?", (scope["account_id"],)
                ).fetchone()[0]
                != actor
            ):
                raise PermissionError("Account owner required for promotion")
            if m["state"] in ("erased", "suppressed", "superseded"):
                raise ValueError("Memory is ineligible")
            if (
                db.execute(
                    "UPDATE memories SET promoted=1 WHERE id=? AND revision=?", (mid, expected)
                ).rowcount
                != 1
            ):
                raise ValueError("Stale memory revision")
            db.execute("UPDATE accounts SET revision=revision+1 WHERE id=?", (scope["account_id"],))
            self._bump(db, m["case_id"], "memory_promoted", {"memory_id": mid})

    def ledger_entries(self):
        verify(self.ledger_dir / "ledger.sqlite3", self.store_id, self.ledger_binding)
        with sqlite3.connect(self.ledger_dir / "ledger.sqlite3") as db:
            db.row_factory = sqlite3.Row
            return [
                dict(r)
                for r in db.execute("SELECT * FROM erased WHERE store_id=?", (self.store_id,))
            ]

    def _erase_keys(self, db, cid, keys):
        mids = set()
        for key in keys:
            mids.update(
                r[0]
                for r in db.execute(
                    "SELECT DISTINCT v.memory_id FROM versions v JOIN sources s ON s.id=v.source_id WHERE s.case_id=? AND s.source_key=?",
                    (cid, key),
                )
            )
            db.execute(
                "UPDATE sources SET body='[erased]',erased=1,active=0 WHERE case_id=? AND source_key=?",
                (cid, key),
            )
        for mid in mids:
            db.execute("UPDATE memories SET state='erased' WHERE id=?", (mid,))
            db.execute(
                "UPDATE versions SET body='[erased]',reason='',state='erased' WHERE memory_id=?",
                (mid,),
            )
            db.execute("DELETE FROM vectors WHERE memory_id=?", (mid,))
        db.execute(
            "UPDATE outputs SET payload='{}',sha256=?,state='erased',reviewer=NULL WHERE case_id IN (SELECT id FROM cases WHERE account_id=(SELECT account_id FROM cases WHERE id=?))",
            (digest({}), cid),
        )
        db.execute("DELETE FROM summaries WHERE case_id=?", (cid,))
        db.execute("UPDATE jobs SET question='[erased]',cancelled=1 WHERE case_id=?", (cid,))

    def erase(self, actor, cid, source_ids, confirmation):
        verify(self.ledger_dir / "ledger.sqlite3", self.store_id, self.ledger_binding)
        scope = self.case(actor, cid)
        if actor != scope["owner"] or confirmation != "ERASE":
            raise PermissionError("Owner and explicit ERASE confirmation required")
        sources = [self.source(actor, sid) for sid in source_ids]
        if any(s["case_id"] != cid for s in sources):
            raise PermissionError("Wrong case")
        keys = [s["source_key"] for s in sources]
        # Corrections and proposals derived from an erased source cannot retain copies.
        with self.connect() as db:
            changed = True
            while changed:
                before = len(keys)
                linked = set()
                for key in keys:
                    linked.update(
                        r[0]
                        for r in db.execute(
                            "SELECT DISTINCT v.memory_id FROM versions v JOIN sources s ON s.id=v.source_id WHERE s.case_id=? AND s.source_key=?",
                            (cid, key),
                        )
                    )
                for mid in linked:
                    keys.extend(
                        r[0]
                        for r in db.execute(
                            "SELECT DISTINCT s.source_key FROM versions v JOIN sources s ON s.id=v.source_id WHERE v.memory_id=?",
                            (mid,),
                        )
                    )
                keys = sorted(set(keys))
                changed = len(keys) != before
        # Ledger first: crash before the live transaction is repaired at startup.
        with sqlite3.connect(self.ledger_dir / "ledger.sqlite3") as ledger:
            ledger.executemany(
                "INSERT OR IGNORE INTO erased VALUES(?,?,?,?)",
                [(self.store_id, cid, k, now()) for k in keys],
            )
        with self.connect() as db:
            self._erase_keys(db, cid, keys)
            self._bump(db, cid, "source_erased", {"count": len(keys)})
        return {
            "erased_sources": len(keys),
            "derived_outputs": "invalidated and redacted",
            "backup_limitation": "Existing backup media must be governed; restores require this independent ledger.",
        }

    def reconcile_erasures(self):
        with self.connect() as db:
            for e in self.ledger_entries():
                if db.execute(
                    "SELECT 1 FROM sources WHERE case_id=? AND source_key=? AND erased=0",
                    (e["case_id"], e["source_key"]),
                ).fetchone():
                    self._erase_keys(db, e["case_id"], [e["source_key"]])

    def changes(self, actor, cid, cursor=0, epoch=None):
        scope = self.case(actor, cid)
        current_epoch = self.setting("epoch")
        reset = epoch is not None and epoch != current_epoch
        with self.connect() as db:
            rows = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM events WHERE case_id=? AND seq>? ORDER BY seq LIMIT 101",
                    (cid, 0 if reset else cursor),
                )
            ]
        more = len(rows) > 100
        rows = rows[:100]
        for r in rows:
            r["detail"] = json.loads(r["detail"])
        return {
            "events": rows,
            "cursor": rows[-1]["seq"] if rows else cursor,
            "has_more": more,
            "epoch": current_epoch,
            "reset": reset,
            "revision": scope["revision"],
            "account_revision": scope["account_revision"],
        }

    def event(self, cid, kind, detail):
        with self.connect() as db:
            self._event(db, cid, kind, detail)

    def conversation(self, actor, cid):
        self.case(actor, cid, "investigator")
        conv = ident()
        with self.connect() as db:
            db.execute("INSERT INTO conversations VALUES(?,?,?,?)", (conv, cid, actor, now()))
        return {"id": conv, "case_id": cid, "session": self.new_session(actor, conv)}

    def new_session(self, actor, conv):
        self.conversation_scope(actor, conv, "investigator")
        sid = ident()
        with self.connect() as db:
            db.execute("INSERT INTO chat_sessions VALUES(?,?,?,?)", (sid, conv, actor, now()))
        return {"id": sid, "conversation_id": conv}

    def conversation_scope(self, actor, conv, role=None):
        with self.connect() as db:
            row = db.execute("SELECT * FROM conversations WHERE id=?", (conv,)).fetchone()
        if not row:
            raise ValueError("Conversation not found")
        return self.case(actor, row["case_id"], role)

    def turns(self, actor, conv, session_id=None):
        self.conversation_scope(actor, conv)
        with self.connect() as db:
            rows = db.execute(
                "SELECT t.*,s.body,s.erased FROM turns t LEFT JOIN sources s ON s.id=t.source_id WHERE t.conversation_id=? AND (? IS NULL OR t.session_id=?) ORDER BY seq",
                (conv, session_id, session_id),
            ).fetchall()
        values = []
        for row in rows:
            r = dict(row)
            if r["output_id"]:
                output = self.output(actor, r["output_id"])
                r["body"] = output["payload"].get("summary", "[unavailable or erased]")
                r["output"] = output
            values.append(r)
        return values

    def enqueue(self, actor, conv, session_id, question, key, options=None):
        scope = self.conversation_scope(actor, conv, "investigator")
        from contracts.relaydesk import Recall

        options = Recall(question=question, **(options or {})).model_dump(exclude={"question"})
        if not key or len(key) > 160:
            raise ValueError("Use a bounded nonempty idempotency key")
        fingerprint = digest([conv, session_id, question, options])
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            valid = db.execute(
                "SELECT 1 FROM chat_sessions WHERE id=? AND conversation_id=? AND actor=?",
                (session_id, conv, actor),
            ).fetchone()
            if not valid:
                raise PermissionError("Interactive session belongs to another actor/conversation")
            old = db.execute(
                "SELECT * FROM jobs WHERE case_id=? AND key=?", (scope["id"], key)
            ).fetchone()
            if old:
                if old["request_hash"] != fingerprint:
                    raise ValueError("Idempotency key reused with different request")
                return dict(old)
            if db.execute("SELECT count(*) FROM jobs WHERE status='queued'").fetchone()[0] >= 20:
                raise ValueError("Interactive queue full")
            jid = ident()
            sid, _ = self._source(
                db,
                scope["id"],
                SourceMessage(
                    source_key="turn:" + jid,
                    author=actor,
                    body=question,
                    created_at=now(),
                    updated_at=now(),
                ),
            )
            self._memory(
                db,
                scope["id"],
                sid,
                question,
                "episode",
                "proposed",
                0,
                len(question),
                now(),
                "User conversation; not automatically verified",
            )
            seq = db.execute(
                "SELECT coalesce(max(seq),0)+1 FROM turns WHERE conversation_id=?", (conv,)
            ).fetchone()[0]
            db.execute(
                "INSERT INTO turns VALUES(?,?,?,?,?,?,?)",
                (ident(), conv, session_id, sid, None, seq, "user"),
            )
            db.execute(
                "INSERT INTO jobs(id,case_id,conversation_id,session_id,actor,question,key,request_hash,status,created_at,options) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    jid,
                    scope["id"],
                    conv,
                    session_id,
                    actor,
                    question,
                    key,
                    fingerprint,
                    "queued",
                    now(),
                    json.dumps(options),
                ),
            )
            self._bump(db, scope["id"], "turn_queued", {"job_id": jid})
        return self.job(actor, jid)

    def job(self, actor, jid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        if not row:
            raise ValueError("Job not found")
        self.case(actor, row["case_id"])
        result = dict(row)
        if result["output_id"]:
            result["output"] = self.output(actor, result["output_id"])
        return result

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM jobs WHERE status='running' AND lease_until>?", (now(),)
            ).fetchone():
                return None
            row = db.execute(
                "SELECT * FROM jobs WHERE status='queued' OR (status='running' AND lease_until<=?) ORDER BY created_at LIMIT 1",
                (now(),),
            ).fetchone()
            if not row:
                return None
            deadline = row["deadline"] or (datetime.now(UTC) + timedelta(seconds=600)).isoformat()
            lease = ident()
            db.execute(
                "UPDATE jobs SET status='running',lease=?,lease_until=?,deadline=? WHERE id=?",
                (
                    lease,
                    (datetime.now(UTC) + timedelta(seconds=150)).isoformat(),
                    deadline,
                    row["id"],
                ),
            )
            return {**dict(row), "status": "running", "lease": lease, "deadline": deadline}

    def fence(self, db, jid, lease):
        row = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        if not row or row["status"] != "running" or row["lease"] != lease:
            raise ValueError("Stale worker lease")
        if row["cancelled"] or row["deadline"] <= now():
            raise ValueError("Cancelled or deadline exceeded")
        return row

    def reserve(self, jid, lease):
        with self.connect() as db:
            row = self.fence(db, jid, lease)
            if row["model_calls"] >= 4 * row["grant"]:
                raise ValueError("Model budget exhausted")
            db.execute(
                "UPDATE jobs SET model_calls=model_calls+1,lease_until=? WHERE id=?",
                ((datetime.now(UTC) + timedelta(seconds=150)).isoformat(), jid),
            )

    def cancel(self, actor, jid):
        value = self.job(actor, jid)
        self.case(actor, value["case_id"], "investigator")
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET cancelled=1,status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END WHERE id=?",
                (jid,),
            )
            self._event(db, value["case_id"], "cancel_requested", {"job_id": jid})

    def continue_job(self, actor, jid, key):
        value = self.job(actor, jid)
        self.case(actor, value["case_id"], "investigator")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM continuations WHERE job_id=? AND key=?", (jid, key)
            ).fetchone():
                return value
            if (
                value["status"] in ("queued", "running")
                or value["grant"] >= 2
                or not value["deadline"]
                or value["deadline"] <= now()
            ):
                raise ValueError("Continuation unavailable; create a new explicit question")
            db.execute("INSERT INTO continuations VALUES(?,?)", (jid, key))
            db.execute(
                "UPDATE jobs SET status='queued',grant=grant+1,cancelled=0 WHERE id=?", (jid,)
            )
        return self.job(actor, jid)

    def finish(self, job, payload, revision, reason):
        scope = self.case(job["actor"], job["case_id"], "investigator")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.fence(db, job["id"], job["lease"])
            self.case(job["actor"], job["case_id"], "investigator")
            current = db.execute(
                "SELECT revision FROM cases WHERE id=?", (job["case_id"],)
            ).fetchone()[0]
            if (
                current != revision
                or payload.get("context_manifest", {}).get(
                    "account_revision", scope["account_revision"]
                )
                != scope["account_revision"]
            ):
                payload = {
                    "summary": "Case changed during generation. Ask again using the latest revision.",
                    "claims": [],
                    "limitations": ["Stale context rejected"],
                    "status": "partial",
                }
                reason = "Stale context rejected"
            for hit in payload.get("recall", {}).get("hits", []):
                e = hit["evidence"]
                src = db.execute("SELECT * FROM sources WHERE id=?", (e["source_id"],)).fetchone()
                if not src or src["erased"]:
                    raise PermissionError("Derived source erased or unavailable")
                self.case(job["actor"], src["case_id"])
                self.validate_source(src)
                if src["sha256"] != e["sha256"] or src["body"][e["start"] : e["end"]] != e["quote"]:
                    raise ValueError("Source evidence integrity failure")
            oid = ident()
            db.execute(
                "INSERT INTO outputs VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    oid,
                    job["case_id"],
                    job["id"],
                    current,
                    json.dumps(payload),
                    digest(payload),
                    payload.get("status", "partial"),
                    None,
                    now(),
                ),
            )
            db.execute(
                "UPDATE jobs SET status=?,output_id=?,reason=?,lease_until=NULL WHERE id=?",
                (payload.get("status", "partial"), oid, reason, job["id"]),
            )
            seq = db.execute(
                "SELECT coalesce(max(seq),0)+1 FROM turns WHERE conversation_id=?",
                (job["conversation_id"],),
            ).fetchone()[0]
            db.execute(
                "INSERT INTO turns VALUES(?,?,?,?,?,?,?)",
                (ident(), job["conversation_id"], job["session_id"], None, oid, seq, "assistant"),
            )
            self._event(
                db,
                job["case_id"],
                "reply_finished",
                {"job_id": job["id"], "state": payload.get("status", "partial")},
            )
        return oid

    def output(self, actor, oid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM outputs WHERE id=?", (oid,)).fetchone()
        if not row:
            raise ValueError("Output not found")
        self.case(actor, row["case_id"])
        r = dict(row)
        r["payload"] = json.loads(r["payload"])
        if digest(r["payload"]) != r["sha256"]:
            raise ValueError("Output integrity failure")
        for hit in r["payload"].get("recall", {}).get("hits", []):
            self.case(actor, hit["case_id"])
            source = self.source(actor, hit["evidence"]["source_id"])
            if source["erased"]:
                raise PermissionError("Derived source erased")
            e = hit["evidence"]
            if (
                source["sha256"] != e["sha256"]
                or source["body"][e["start"] : e["end"]] != e["quote"]
            ):
                raise ValueError("Output source evidence integrity failure")
        return r

    def review(self, actor, oid, acknowledge):
        output = self.output(actor, oid)
        scope = self.case(actor, output["case_id"], "reviewer")
        if output["case_revision"] != scope["revision"] or output["state"] in ("stale", "erased"):
            raise ValueError("Stale output cannot be reviewed")
        if output["state"] != "complete_for_declared_scope" and not acknowledge:
            raise ValueError("Acknowledge partial limits")
        with self.connect() as db:
            db.execute("UPDATE outputs SET reviewer=? WHERE id=?", (actor, oid))
        return self.output(actor, oid)

    def export(self, actor, oid):
        out = self.output(actor, oid)
        scope = self.case(actor, out["case_id"], "reviewer")
        if (
            not out["reviewer"]
            or out["state"] in ("stale", "erased")
            or scope["revision"] != out["case_revision"]
        ):
            raise ValueError("Review current exact output before export")
        return out
