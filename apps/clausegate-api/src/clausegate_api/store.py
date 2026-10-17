"""Independent transactional approval domain. Human waiting never holds a worker."""

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from contracts.clausegate import DecisionInput, Finding, Playbook

from clausegate_api import authority
from clausegate_api.common import (
    ANALYSIS_VERSION,
    byte_hash,
    canonical,
    digest,
    ident,
    later,
    now,
    timestamp,
)
from clausegate_api.intake import resolve_evidence, text_document


class Store:
    def __init__(self, directory="var/clausegate", *, ledger_dir=None):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "clausegate.sqlite3"
        self.ledger_dir = Path(ledger_dir or self.root.parent / (self.root.name + "-authority"))
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY,salt TEXT,hash TEXT,admin INTEGER);
            CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY,actor TEXT,csrf TEXT,expires TEXT);
            CREATE TABLE IF NOT EXISTS login_failures(actor TEXT,at TEXT);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY,name TEXT,owner TEXT);
            CREATE TABLE IF NOT EXISTS members(workspace_id TEXT,actor TEXT,roles TEXT,scope TEXT,expires TEXT,PRIMARY KEY(workspace_id,actor));
            CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY,workspace_id TEXT,owner TEXT,name TEXT,revision INTEGER,payload TEXT);
            CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,case_id TEXT,text TEXT,payload TEXT,raw BLOB);
            CREATE TABLE IF NOT EXISTS history(case_id TEXT,revision INTEGER,payload TEXT,PRIMARY KEY(case_id,revision));
            CREATE TABLE IF NOT EXISTS events(case_id TEXT,seq INTEGER,payload TEXT,hash TEXT,PRIMARY KEY(case_id,seq));
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,case_id TEXT,actor TEXT,kind TEXT,key TEXT,request_hash TEXT,snapshot TEXT,status TEXT,lease TEXT,lease_until TEXT,deadline TEXT,calls INTEGER DEFAULT 0,cursor INTEGER DEFAULT 0,results TEXT DEFAULT '[]',reason TEXT DEFAULT '',created_at TEXT,UNIQUE(case_id,key));
            """)
            existing = db.execute("SELECT value FROM settings WHERE key='store_id'").fetchone()
            self.store_id = json.loads(existing[0]) if existing else ident()
            if not existing:
                binding = authority.initialize(self.ledger_dir, self.store_id)
                for key, value in {
                    "store_id": self.store_id,
                    "epoch": ident(),
                    "binding": binding,
                    "quarantined": False,
                }.items():
                    db.execute("INSERT INTO settings VALUES(?,?)", (key, canonical(value)))
            self.binding = json.loads(
                db.execute("SELECT value FROM settings WHERE key='binding'").fetchone()[0]
            )
        authority.verify(self.ledger_dir, self.store_id, self.binding)
        self.reconcile_erasures()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def setting(self, key):
        with self.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else None

    @contextmanager
    def coherent_read(self):
        """Short, serialized snapshot including independently published audit heads.

        Anchor publication also takes this domain lock. No model calls, PDF
        parsing or network IO may run inside this boundary. A deferred WAL read
        alone would still race an external anchor advancing beyond its snapshot.
        """
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            yield db

    def add_user(self, name, password, admin=False):
        from contracts.clausegate import Login

        Login(username=name, password=password)
        if len(password) < 12 or password == "replace-me":
            raise ValueError("Unique 12+ character password required")
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()
        with self.connect() as db:
            try:
                db.execute("INSERT INTO users VALUES(?,?,?,?)", (name, salt, hashed, int(admin)))
            except sqlite3.IntegrityError as error:
                raise ValueError("User exists") from error

    def user(self, actor):
        with self.connect() as db:
            row = db.execute("SELECT name,admin FROM users WHERE name=?", (actor,)).fetchone()
            if not row:
                raise PermissionError("Unknown user")
            return dict(row)

    def login(self, actor, password):
        with self.connect() as db:
            if (
                db.execute(
                    "SELECT count(*) FROM login_failures WHERE actor=? AND at>?",
                    (actor, later(-900)),
                ).fetchone()[0]
                >= 5
            ):
                raise PermissionError("Login temporarily limited")
            row = db.execute("SELECT * FROM users WHERE name=?", (actor,)).fetchone()
            hashed = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(),
                (row["salt"] if row else "unknown-user").encode(),
                310000,
            ).hex()
            if row and secrets.compare_digest(hashed, row["hash"]):
                token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                db.execute("DELETE FROM login_failures WHERE actor=?", (actor,))
                db.execute(
                    "INSERT INTO sessions VALUES(?,?,?,?)",
                    (digest(token), actor, csrf, later(28800)),
                )
                return {
                    "token": token,
                    "csrf": csrf,
                    "username": actor,
                    "admin": bool(row["admin"]),
                }
            db.execute("INSERT INTO login_failures VALUES(?,?)", (actor, now()))
        raise PermissionError("Invalid credentials")

    def authenticate(self, token):
        with self.connect() as db:
            row = db.execute(
                "SELECT actor,csrf FROM sessions WHERE hash=? AND expires>?", (digest(token), now())
            ).fetchone()
            if not row:
                raise PermissionError("Sign in required")
            return {
                "username": row["actor"],
                "csrf": row["csrf"],
                "admin": bool(self.user(row["actor"])["admin"]),
            }

    def logout(self, token):
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE hash=?", (digest(token),))

    def _roles(self, db, actor, wid, cid=None, role=None):
        row = db.execute(
            "SELECT * FROM members WHERE workspace_id=? AND actor=?", (wid, actor)
        ).fetchone()
        if not row or (row["expires"] and row["expires"] <= now()):
            raise PermissionError("Workspace/case access denied")
        roles, scope = json.loads(row["roles"]), json.loads(row["scope"])
        if not roles or (cid and "owner" not in roles and "*" not in scope and cid not in scope):
            raise PermissionError("Case access denied")
        if role and role not in roles:
            raise PermissionError(f"{role} capability required")
        return roles

    def create_workspace(self, actor, name):
        self.user(actor)
        from contracts.clausegate import Named

        Named(name=name)
        wid = ident()
        with self.connect() as db:
            db.execute("INSERT INTO workspaces VALUES(?,?,?)", (wid, name, actor))
            db.execute(
                "INSERT INTO members VALUES(?,?,?,?,NULL)",
                (wid, actor, canonical(["owner", "requester"]), canonical(["*"])),
            )
        return {"id": wid, "name": name, "owner": actor}

    def workspaces(self, actor):
        with self.connect() as db:
            rows = db.execute(
                "SELECT w.* FROM workspaces w JOIN members m ON m.workspace_id=w.id WHERE m.actor=?",
                (actor,),
            ).fetchall()
            return [dict(r) for r in rows if self._visible_workspace(db, actor, r["id"])]

    def _visible_workspace(self, db, actor, wid):
        try:
            self._roles(db, actor, wid)
            return True
        except PermissionError:
            return False

    def create_case(self, actor, wid, name):
        from contracts.clausegate import Named

        Named(name=name)
        cid = ident()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._roles(db, actor, wid, role="requester")
            c = {
                "id": cid,
                "workspace_id": wid,
                "owner": actor,
                "name": name,
                "revision": 1,
                "state": "draft",
                "document_id": None,
                "playbook": None,
                "context": {"side": "unknown", "purpose": ""},
                "context_revision": 1,
                "findings_revision": 0,
                "findings": [],
                "requests": [],
                "decisions": [],
                "packet": None,
                "checkpoint": None,
                "egress": False,
                "epoch": self.setting("epoch"),
                "created_at": now(),
            }
            db.execute(
                "INSERT INTO cases VALUES(?,?,?,?,?,?)", (cid, wid, actor, name, 1, canonical(c))
            )
            row = db.execute(
                "SELECT * FROM members WHERE workspace_id=? AND actor=?", (wid, actor)
            ).fetchone()
            scope = json.loads(row["scope"])
            if "*" not in scope and cid not in scope:
                db.execute(
                    "UPDATE members SET scope=? WHERE workspace_id=? AND actor=?",
                    (canonical(scope + [cid]), wid, actor),
                )
            self._event(db, c, actor, "case_created", {})
        return c

    def _load(self, db, actor, cid, role=None):
        row = db.execute("SELECT payload FROM cases WHERE id=?", (cid,)).fetchone()
        if not row:
            raise PermissionError("Case access denied")
        c = json.loads(row[0])
        self._roles(db, actor, c["workspace_id"], cid, role)
        if c["state"] != "erased" and cid in authority.erased(
            self.ledger_dir, self.store_id, self.binding
        ):
            raise PermissionError("Erased content unavailable pending reconciliation")
        return c

    def case(self, actor, cid):
        with self.coherent_read() as db:
            c = self._load(db, actor, cid)
            self._verify(db, cid)
            c["roles"] = self._roles(db, actor, c["workspace_id"], cid)
            if set(c["roles"]) <= {"auditor"}:
                c.update(
                    document_id=None,
                    findings=[],
                    requests=[],
                    decisions=[],
                    context={},
                    playbook=None,
                    packet=None,
                    checkpoint=None,
                )
            return c

    def cases(self, actor):
        rows = []
        with self.coherent_read() as db:
            for r in db.execute("SELECT id FROM cases ORDER BY rowid DESC"):
                try:
                    c = self._load(db, actor, r[0])
                    rows.append(
                        {
                            k: c[k]
                            for k in [
                                "id",
                                "name",
                                "workspace_id",
                                "state",
                                "revision",
                                "created_at",
                            ]
                        }
                    )
                except PermissionError:
                    continue
        return rows

    def _event(self, db, c, actor, kind, detail):
        previous = db.execute(
            "SELECT seq,hash FROM events WHERE case_id=? ORDER BY seq DESC LIMIT 1", (c["id"],)
        ).fetchone()
        seq = previous[0] + 1 if previous else 1
        value = {
            "schema": 1,
            "case_id": c["id"],
            "seq": seq,
            "actor": actor,
            "kind": kind,
            "detail": detail,
            "at": now(),
            "previous": previous[1] if previous else "0" * 64,
            "revision": c["revision"],
            "state_hash": digest({k: v for k, v in c.items() if k != "roles"}),
        }
        db.execute(
            "INSERT INTO events VALUES(?,?,?,?)", (c["id"], seq, canonical(value), digest(value))
        )

    def _verify(self, db, cid):
        previous, seq = "0" * 64, 0
        rows = db.execute("SELECT * FROM events WHERE case_id=? ORDER BY seq", (cid,)).fetchall()
        hashes = {}
        for row in rows:
            value = json.loads(row["payload"])
            if (
                row["seq"] != seq + 1
                or value["seq"] != row["seq"]
                or value["case_id"] != cid
                or value["previous"] != previous
                or digest(value) != row["hash"]
            ):
                raise ValueError("Audit integrity failure")
            seq, previous = row["seq"], row["hash"]
            hashes[seq] = previous
        external = authority.head(self.ledger_dir, self.store_id, self.binding, cid)
        if external and hashes.get(external["seq"]) != external["hash"]:
            raise ValueError("Audit anchor rollback/integrity failure")
        current = db.execute("SELECT payload FROM cases WHERE id=?", (cid,)).fetchone()
        if (
            rows
            and current
            and json.loads(rows[-1]["payload"])["state_hash"] != digest(json.loads(current[0]))
        ):
            raise ValueError("Domain state integrity failure against audit head")
        return {
            "valid": True,
            "seq": seq,
            "hash": previous,
            "anchored_seq": external["seq"] if external else 0,
            "assurance": "external-head-checked"
            if external
            else "local-chain-only; privileged rewrite/truncation not excluded",
        }

    def verify_audit(self, actor, cid):
        with self.coherent_read() as db:
            self._load(db, actor, cid)
            return self._verify(db, cid)

    def audit(self, actor, cid, offset=0, limit=100):
        if offset < 0 or not 1 <= limit <= 200:
            raise ValueError("Invalid page bounds")
        with self.coherent_read() as db:
            self._load(db, actor, cid)
            return {
                "items": [
                    dict(json.loads(r[0]), sha256=r[1])
                    for r in db.execute(
                        "SELECT payload,hash FROM events WHERE case_id=? ORDER BY seq LIMIT ? OFFSET ?",
                        (cid, limit, offset),
                    )
                ],
                "verification": self._verify(db, cid),
                "epoch": self.setting("epoch"),
            }

    def anchor(self, actor, cid):
        with self.coherent_read() as db:
            self._load(db, actor, cid, "owner")
            result = self._verify(db, cid)
            authority.anchor(
                self.ledger_dir, self.store_id, self.binding, cid, result["seq"], result["hash"]
            )
            return result

    def _save(self, db, c, actor, kind, detail=None):
        c.pop("roles", None)
        c["revision"] += 1
        db.execute(
            "UPDATE cases SET revision=?,payload=? WHERE id=?",
            (c["revision"], canonical(c), c["id"]),
        )
        db.execute("INSERT INTO history VALUES(?,?,?)", (c["id"], c["revision"], canonical(c)))
        self._event(db, c, actor, kind, detail or {})

    @contextmanager
    def mutation(self, actor, cid, expected=None, role=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if self.setting("quarantined"):
                raise PermissionError(
                    "Restored store quarantined; operator authority provisioning required"
                )
            if cid in authority.erased(self.ledger_dir, self.store_id, self.binding):
                raise ValueError("Case erased")
            c = self._load(db, actor, cid, role)
            self._verify(db, cid)
            if expected is not None and c["revision"] != expected:
                raise ValueError("Revision conflict; refresh current context")
            yield db, c

    def _invalidate(self, db, c):
        for request in c["requests"]:
            if request["state"] in {"pending", "answered"}:
                request["state"] = "stale"
                request["revision"] += 1
        c["packet"] = None
        c["checkpoint"] = None
        c["state"] = "stale" if c["document_id"] else "draft"
        db.execute(
            "UPDATE jobs SET status='cancelled',lease=NULL,reason='Context changed' WHERE case_id=? AND status IN ('queued','running')",
            (c["id"],),
        )

    def membership(self, actor, wid, username, roles, case_ids, expires_at=None):
        from contracts.clausegate import Membership

        value = Membership(username=username, roles=roles, case_ids=case_ids, expires_at=expires_at)
        self.user(username)
        expires = timestamp(value.expires_at) if value.expires_at else None
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._roles(db, actor, wid, role="owner")
            owner = db.execute("SELECT owner FROM workspaces WHERE id=?", (wid,)).fetchone()[0]
            if username == owner and ("owner" not in roles or "requester" not in roles):
                raise ValueError("Workspace owner must retain owner/requester roles")
            for cid in case_ids:
                if (
                    cid != "*"
                    and not db.execute(
                        "SELECT 1 FROM cases WHERE id=? AND workspace_id=?", (cid, wid)
                    ).fetchone()
                ):
                    raise ValueError("Foreign case grant")
            db.execute(
                "INSERT OR REPLACE INTO members VALUES(?,?,?,?,?)",
                (wid, username, canonical(roles), canonical(case_ids), expires),
            )
            for row in db.execute(
                "SELECT payload FROM cases WHERE workspace_id=?", (wid,)
            ).fetchall():
                c = json.loads(row[0])
                if c["state"] == "erased":
                    continue
                self._verify(db, c["id"])
                self._invalidate(db, c)
                self._save(
                    db,
                    c,
                    actor,
                    "authority_changed",
                    {"actor": username, "roles": roles, "expires": expires},
                )

    def members(self, actor, wid):
        with self.connect() as db:
            self._roles(db, actor, wid, role="owner")
            return [
                {
                    "username": r["actor"],
                    "roles": json.loads(r["roles"]),
                    "case_ids": json.loads(r["scope"]),
                    "expires_at": r["expires"],
                }
                for r in db.execute("SELECT * FROM members WHERE workspace_id=?", (wid,))
            ]

    def set_context(self, actor, cid, expected, side, purpose):
        from contracts.clausegate import ContextInput

        ContextInput(expected_revision=expected, side=side, purpose=purpose)
        with self.mutation(actor, cid, expected, "requester") as (db, c):
            self._invalidate(db, c)
            c["context"] = {"side": side, "purpose": purpose}
            c["context_revision"] += 1
            c["findings"] = []
            self._save(
                db, c, actor, "business_context_changed", {"context_hash": digest(c["context"])}
            )
        return self.case(actor, cid)

    def set_playbook(self, actor, cid, expected, playbook, *, activate=True):
        value = Playbook.model_validate(playbook)
        with self.mutation(actor, cid, expected, "owner") as (db, c):
            self._invalidate(db, c)
            c["playbook"] = {
                **value.model_dump(),
                "revision": (c.get("playbook") or {}).get("revision", 0) + 1,
                "active": activate,
                "approved_by": actor,
            }
            c["findings"] = []
            self._save(
                db,
                c,
                actor,
                "playbook_activated" if activate else "playbook_drafted",
                {"playbook_hash": digest(c["playbook"])},
            )
        return self.case(actor, cid)

    def set_egress(self, actor, cid, expected, allowed):
        if type(allowed) is not bool:
            raise ValueError("Boolean grant required")
        with self.mutation(actor, cid, expected, "owner") as (db, c):
            self._invalidate(db, c)
            c["egress"] = allowed
            self._save(db, c, actor, "model_egress_changed", {"allowed": allowed})
        return self.case(actor, cid)

    def import_text(self, actor, cid, expected, text, name):
        return self.import_document(actor, cid, expected, text_document(text, name))

    def import_document(self, actor, cid, expected, document, raw=None):
        with self.mutation(actor, cid, expected, "requester") as (db, c):
            self._invalidate(db, c)
            did = ident()
            value = dict(document, id=did, case_id=cid)
            text = value.pop("text")
            if digest(text) != value["text_hash"]:
                raise ValueError("Source integrity mismatch")
            if raw is not None and byte_hash(raw) != value["bytes_hash"]:
                raise ValueError("Original bytes integrity mismatch")
            db.execute(
                "INSERT INTO documents VALUES(?,?,?,?,?)", (did, cid, text, canonical(value), raw)
            )
            c["document_id"], c["findings"] = did, []
            self._save(
                db,
                c,
                actor,
                "document_imported",
                {"source_id": did, "text_hash": value["text_hash"], "complete": value["complete"]},
            )
        return self.case(actor, cid)

    def _document(self, db, did):
        row = db.execute("SELECT * FROM documents WHERE id=?", (did,)).fetchone()
        if not row:
            raise ValueError("Source unavailable")
        value = json.loads(row["payload"])
        if digest(row["text"]) != value["text_hash"] or (
            row["raw"] is not None and byte_hash(row["raw"]) != value["bytes_hash"]
        ):
            raise ValueError("Source integrity failure")
        for span in value["spans"]:
            if row["text"][span["start"] : span["end"]] != span["quote"]:
                raise ValueError("Source span integrity failure")
        return dict(value, text=row["text"])

    def _read_document(self, db, actor, did):
        row = db.execute("SELECT case_id FROM documents WHERE id=?", (did,)).fetchone()
        if not row:
            raise PermissionError("Document access denied")
        c = self._load(db, actor, row[0])
        roles = self._roles(db, actor, c["workspace_id"], c["id"])
        if set(roles) <= {"auditor"}:
            raise PermissionError("Document reading capability required")
        return self._document(db, did)

    def document(self, actor, did):
        with self.coherent_read() as db:
            return self._read_document(db, actor, did)

    def original(self, actor, did):
        with self.coherent_read() as db:
            doc = self._read_document(db, actor, did)
            raw = db.execute("SELECT raw FROM documents WHERE id=?", (did,)).fetchone()[0]
            return raw if raw is not None else doc["text"].encode()

    def _binding(self, db, c):
        if not c["document_id"] or not c["playbook"] or not c["playbook"]["active"]:
            raise ValueError("Document and approved playbook required")
        doc = self._document(db, c["document_id"])
        return digest(
            {
                "schema": 1,
                "case": c["id"],
                "document": doc["id"],
                "bytes": doc["bytes_hash"],
                "text": doc["text_hash"],
                "coverage": [doc["complete"], doc["gaps"]],
                "playbook": c["playbook"],
                "context": c["context"],
                "context_revision": c["context_revision"],
                "findings_revision": c["findings_revision"],
                "findings": c["findings"],
                "epoch": self.setting("epoch"),
            }
        )

    def _validated_findings(self, db, c, findings):
        doc = self._document(db, c["document_id"])
        spans = {s["id"]: s for s in doc["spans"]}
        expected = {r["id"] for r in c["playbook"]["rules"]}
        values = [Finding.model_validate(f).model_dump() for f in findings]
        if len(values) != len(expected) or {f["check_id"] for f in values} != expected:
            raise ValueError("Every configured hypothesis must be assessed exactly once")
        for finding in values:
            ids = finding["evidence_ids"]
            if len(set(ids)) != len(ids) or any(i not in spans for i in ids):
                raise ValueError("Unknown or duplicate evidence ID")
            if (
                finding["label"] != "NotMentioned"
                and not ids
                and finding["assessment"] == "supported"
            ):
                raise ValueError("Supported interpretation requires source evidence")
            if (
                finding["label"] == "NotMentioned"
                and finding["assessment"] == "supported"
                and not doc["complete"]
            ):
                raise ValueError("Incomplete source cannot establish absence")
            finding["evidence"] = resolve_evidence(doc["spans"], finding)
        return values

    def _request(self, db, c, *, kind, check_id, role, question, reason, hours=168):
        binding = c["checkpoint"]
        key = digest([binding, kind, check_id, role])
        if any(r["key"] == key and r["state"] == "pending" for r in c["requests"]):
            return
        allowed = {
            "clarification": ["clarify", "reject", "request_revision"],
            "interpretation": [
                "confirm_interpretation",
                "correct_interpretation",
                "reject",
                "request_revision",
            ],
            "exception": ["approve_exception", "reject", "request_revision"],
            "hard_block": ["reject", "request_revision"],
        }[kind]
        r = {
            "id": ident(),
            "key": key,
            "revision": 1,
            "binding": binding,
            "kind": kind,
            "check_id": check_id,
            "role": role,
            "question": question,
            "reason": reason,
            "allowed": allowed,
            "assignee": c["owner"] if kind == "clarification" else None,
            "assignment_expires": None,
            "expires_at": later(hours * 3600),
            "due_at": later(86400),
            "created_at": now(),
            "state": "pending",
        }
        c["requests"].append(r)
        self._event(
            db,
            c,
            "system",
            "approval_requested",
            {
                "request_id": r["id"],
                "kind": kind,
                "check_id": check_id,
                "required_role": role,
                "binding": binding,
            },
        )

    def _evaluate(self, db, c):
        if len(c["requests"]) > 1000:
            raise ValueError("Case request-history limit; archive and create a new case")
        c["checkpoint"] = self._binding(db, c)
        c["packet"] = None
        doc = self._document(db, c["document_id"])
        if not doc["complete"]:
            self._request(
                db,
                c,
                kind="hard_block",
                check_id="coverage",
                role="reviewer",
                question="Provide a readable complete source; extraction gaps cannot be approved away.",
                reason="document_incomplete",
            )
        if (
            c["context"].get("side") in (None, "unknown")
            or not c["context"].get("purpose", "").strip()
        ):
            self._request(
                db,
                c,
                kind="clarification",
                check_id="business_context",
                role="requester",
                question="Specify company side and intended disclosure purpose.",
                reason="missing_business_context",
            )
        lookup = {f["check_id"]: f for f in c["findings"]}
        for rule in c["playbook"]["rules"]:
            f = lookup.get(rule["id"])
            if not f or f["assessment"] != "supported":
                self._request(
                    db,
                    c,
                    kind="interpretation",
                    check_id=rule["id"],
                    role="reviewer",
                    question="Resolve the interpretation with original evidence: "
                    + rule["hypothesis"],
                    reason="unsupported_interpretation" if not f else f["assessment"],
                )
            elif f["label"] in rule["trigger_labels"]:
                if rule["action"] == "block":
                    self._request(
                        db,
                        c,
                        kind="hard_block",
                        check_id=rule["id"],
                        role="reviewer",
                        question="Non-waivable playbook block: request a source revision or reject.",
                        reason="hard_block",
                        hours=rule["expiry_hours"],
                    )
                elif rule["action"] == "require_exception":
                    for role in rule["roles"]:
                        self._request(
                            db,
                            c,
                            kind="exception",
                            check_id=rule["id"],
                            role=role,
                            question="Accept this exact policy deviation or request changes: "
                            + rule["hypothesis"],
                            reason="mandatory_exception",
                            hours=rule["expiry_hours"],
                        )
                elif rule["action"] == "require_review" and not f.get("reviewed_by"):
                    self._request(
                        db,
                        c,
                        kind="interpretation",
                        check_id=rule["id"],
                        role="reviewer",
                        question="Review this source-linked interpretation: " + rule["hypothesis"],
                        reason="mandatory_review",
                        hours=rule["expiry_hours"],
                    )
        c["state"] = (
            "waiting_human"
            if any(r["state"] == "pending" for r in c["requests"])
            else "review_ready"
        )
        if c["state"] == "review_ready":
            self._packet(db, c)

    def submit_findings(self, actor, cid, expected, findings, rationale):
        if not rationale.strip() or len(rationale) > 1800:
            raise ValueError("Review rationale required")
        with self.mutation(actor, cid, expected, "reviewer") as (db, c):
            if not c["playbook"] or not c["playbook"]["active"]:
                raise ValueError("Approved playbook required")
            values = self._validated_findings(db, c, findings)
            self._invalidate(db, c)
            c["findings_revision"] += 1
            c["findings"] = [
                dict(f, reviewed_by=actor, human_rationale=rationale, origin="human")
                for f in values
            ]
            self._evaluate(db, c)
            self._save(
                db,
                c,
                actor,
                "manual_findings_recorded",
                {
                    "findings_hash": digest(c["findings"]),
                    "rationale_hash": digest(rationale),
                    "state": c["state"],
                },
            )
        return self.case(actor, cid)

    def inbox(self, actor):
        result = []
        for summary in self.cases(actor):
            c = self.case(actor, summary["id"])
            for r in c["requests"]:
                if r["state"] == "pending":
                    result.append(
                        dict(
                            r,
                            case_id=c["id"],
                            case_name=c["name"],
                            can_act=r["role"] in c["roles"]
                            and (r["kind"] == "clarification" or actor != c["owner"])
                            and (not r["assignee"] or r["assignee"] == actor)
                            and r["expires_at"] > now(),
                        )
                    )
        return result

    def _request_case(self, actor, rid):
        # Only traverse authorized cases; foreign IDs never resolve into visible metadata.
        for row in self.cases(actor):
            c = self.case(actor, row["id"])
            if any(r["id"] == rid for r in c["requests"]):
                return c["id"]
        raise PermissionError("Request access denied")

    def _live_decisions(self, db, c):
        if c["checkpoint"] != self._binding(db, c):
            raise ValueError("Context binding changed")
        for finding in c["findings"]:
            if finding.get("reviewed_by"):
                self._roles(db, finding["reviewed_by"], c["workspace_id"], c["id"], "reviewer")
        active = [
            r for r in c["requests"] if r["binding"] == c["checkpoint"] and r["state"] != "stale"
        ]
        actors_by_check = {}
        valid = []
        for r in active:
            if r["expires_at"] <= now() or r["state"] != "answered":
                raise ValueError("Required human input pending or expired")
            d = next(
                (
                    d
                    for d in reversed(c["decisions"])
                    if d["request_id"] == r["id"] and not d["withdrawn"]
                ),
                None,
            )
            if not d or d["binding"] != c["checkpoint"] or d["expires_at"] <= now():
                raise ValueError("Human decision missing, withdrawn or expired")
            self._roles(db, d["actor"], c["workspace_id"], c["id"], r["role"])
            if r["assignment_expires"] and r["assignment_expires"] <= now():
                raise ValueError("Assignment expired")
            if r["assignee"] and r["assignee"] != d["actor"]:
                raise PermissionError("Assignment changed")
            if r["kind"] == "hard_block" or d["kind"] in {"reject", "request_revision"}:
                raise ValueError("Rejected or non-waivable blocker")
            if r["kind"] != "clarification" and d["actor"] == c["owner"]:
                raise PermissionError("Self-approval denied")
            group = actors_by_check.setdefault(r["check_id"], set())
            if d["actor"] in group:
                raise PermissionError("Distinct reviewers required for multi-role approval")
            group.add(d["actor"])
            valid.append(d)
        return valid

    def decide(self, actor, rid, value):
        value = DecisionInput.model_validate(value)
        if not value.rationale.strip():
            raise ValueError("Nonempty decision rationale required")
        cid = self._request_case(actor, rid)
        with self.mutation(actor, cid) as (db, c):
            r = next(r for r in c["requests"] if r["id"] == rid)
            self._roles(db, actor, c["workspace_id"], cid, r["role"])
            request_hash = digest(value.model_dump())
            old = next(
                (d for d in c["decisions"] if d["actor"] == actor and d["key"] == value.key), None
            )
            if old:
                if old["request_hash"] != request_hash or old["request_id"] != rid:
                    raise ValueError("Idempotency key payload conflict")
                return old
            if (
                c["state"] != "waiting_human"
                or r["state"] != "pending"
                or r["revision"] != value.expected_revision
                or r["binding"] != value.binding
                or c["checkpoint"] != value.binding
                or self._binding(db, c) != value.binding
            ):
                raise ValueError("Stale request/context; refresh")
            if r["expires_at"] <= now() or (
                r["assignment_expires"] and r["assignment_expires"] <= now()
            ):
                raise ValueError("Request/assignment expired")
            if r["assignee"] and r["assignee"] != actor:
                raise PermissionError("Assigned reviewer required")
            if r["kind"] != "clarification" and actor == c["owner"]:
                raise PermissionError("Requester cannot approve own request")
            if value.kind not in r["allowed"]:
                raise ValueError("Response kind not permitted for request")
            if len(c["decisions"]) >= 1000:
                raise ValueError("Decision history limit")
            if r["kind"] == "exception" and any(
                d["actor"] == actor
                and d["binding"] == c["checkpoint"]
                and not d["withdrawn"]
                and next((x["check_id"] for x in c["requests"] if x["id"] == d["request_id"]), None)
                == r["check_id"]
                for d in c["decisions"]
            ):
                raise PermissionError("Distinct reviewers required for each required role")
            d = {
                "id": ident(),
                "request_id": rid,
                "actor": actor,
                "binding": value.binding,
                "key": value.key,
                "request_hash": request_hash,
                "kind": value.kind,
                "rationale": value.rationale,
                "response": value.model_dump(),
                "at": now(),
                "expires_at": r["expires_at"],
                "withdrawn": False,
            }
            c["decisions"].append(d)
            r["state"], r["revision"] = "answered", r["revision"] + 1
            self._event(
                db,
                c,
                actor,
                "human_decision_recorded",
                {
                    "decision_id": d["id"],
                    "request_id": rid,
                    "kind": value.kind,
                    "response_hash": request_hash,
                },
            )
            if value.kind in {"reject", "request_revision"}:
                c["state"] = "rejected" if value.kind == "reject" else "needs_revision"
                c["packet"] = None
            elif value.kind == "clarify":
                if not value.side or not value.purpose or not value.purpose.strip():
                    raise ValueError("Clarification needs company side and purpose")
                self._invalidate(db, c)
                c["context"] = {"side": value.side, "purpose": value.purpose}
                c["context_revision"] += 1
                c["findings_revision"] += 1
                for finding in c["findings"]:
                    finding["assessment"] = "uncertain"
                    finding["reviewed_by"] = None
                self._evaluate(db, c)
            elif r["kind"] == "interpretation":
                f = next(f for f in c["findings"] if f["check_id"] == r["check_id"])
                if (
                    value.kind == "confirm_interpretation"
                    and value.label
                    and value.label != f["label"]
                ):
                    raise ValueError("Use explicit correction to change an interpretation")
                if value.kind == "correct_interpretation" and not value.label:
                    raise ValueError("A correction must specify the reviewed label")
                corrected = Finding(
                    check_id=f["check_id"],
                    label=value.label or f["label"],
                    evidence_ids=value.evidence_ids or f["evidence_ids"],
                    evidence_quotes=f.get("evidence_quotes", [])
                    if value.kind == "confirm_interpretation" and not value.evidence_ids
                    else [],
                    assessment="supported",
                    rationale=value.rationale,
                )
                revised = [
                    corrected
                    if x["check_id"] == f["check_id"]
                    else Finding.model_validate({k: x[k] for k in Finding.model_fields})
                    for x in c["findings"]
                ]
                values = self._validated_findings(db, c, revised)
                old_reviewers = {x["check_id"]: x.get("reviewed_by") for x in c["findings"]}
                self._invalidate(db, c)
                c["findings_revision"] += 1
                c["findings"] = [
                    dict(
                        x,
                        reviewed_by=actor
                        if x["check_id"] == f["check_id"]
                        else old_reviewers[x["check_id"]],
                        origin="human-corrected" if x["check_id"] == f["check_id"] else "prior",
                    )
                    for x in values
                ]
                self._evaluate(db, c)
            elif not any(x["state"] == "pending" for x in c["requests"]):
                self._schedule_resume(db, c, actor)
            self._save(
                db, c, actor, "decision_transition", {"decision_id": d["id"], "state": c["state"]}
            )
        return d

    def _schedule_resume(self, db, c, actor):
        decisions = self._live_decisions(db, c)
        key = "resume:" + digest([c["checkpoint"], [d["id"] for d in decisions]])
        existing = db.execute(
            "SELECT id FROM jobs WHERE case_id=? AND key=?", (c["id"], key)
        ).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO jobs(id,case_id,actor,kind,key,request_hash,snapshot,status,created_at) VALUES(?,?,?,?,?,?,?,'queued',?)",
                (ident(), c["id"], actor, "resume", key, key, c["checkpoint"], now()),
            )
            self._event(
                db,
                c,
                actor,
                "resume_scheduled",
                {
                    "binding": c["checkpoint"],
                    "decisions_hash": digest([d["id"] for d in decisions]),
                },
            )
        c["state"] = "resume_queued"

    def resume(self, actor, cid):
        with self.mutation(actor, cid) as (db, c):
            if c["state"] not in {"waiting_human", "resume_queued"}:
                raise ValueError("No resumable current checkpoint")
            self._schedule_resume(db, c, actor)
            self._save(db, c, actor, "resume_revalidated", {"binding": c["checkpoint"]})
        return self.case(actor, cid)

    def assign(self, actor, rid, expected, username, expires_at=None):
        cid = self._request_case(actor, rid)
        with self.mutation(actor, cid, role="owner") as (db, c):
            r = next(x for x in c["requests"] if x["id"] == rid)
            if r["revision"] != expected or r["state"] != "pending":
                raise ValueError("Request revision conflict")
            self._roles(db, username, c["workspace_id"], cid, r["role"])
            if r["kind"] != "clarification" and username == c["owner"]:
                raise PermissionError("Self-approval assignment denied")
            r.update(
                assignee=username,
                assignment_expires=timestamp(expires_at) if expires_at else None,
                revision=r["revision"] + 1,
            )
            self._save(
                db,
                c,
                actor,
                "request_reassigned",
                {"request_id": rid, "assignee": username, "expires_at": r["assignment_expires"]},
            )
        return self.case(actor, cid)

    def withdraw(self, actor, cid, decision_id, expected):
        with self.mutation(actor, cid, expected) as (db, c):
            d = next((d for d in c["decisions"] if d["id"] == decision_id), None)
            if not d:
                raise ValueError("Decision unavailable")
            if d["actor"] != actor:
                self._roles(db, actor, c["workspace_id"], cid, "owner")
            d["withdrawn"] = True
            self._invalidate(db, c)
            self._evaluate(db, c)
            self._save(db, c, actor, "decision_withdrawn", {"decision_id": decision_id})
        return self.case(actor, cid)

    def _packet(self, db, c):
        self._live_decisions(db, c)
        doc = self._document(db, c["document_id"])
        payload = {
            "document_id": doc["id"],
            "text_hash": doc["text_hash"],
            "playbook_hash": digest(c["playbook"]),
            "binding": c["checkpoint"],
            "findings": c["findings"],
            "decisions": [
                d for d in c["decisions"] if d["binding"] == c["checkpoint"] and not d["withdrawn"]
            ],
            "coverage": {
                "required": len(c["playbook"]["rules"]),
                "assessed": len(c["findings"]),
                "source_complete": doc["complete"],
            },
            "limitations": [
                "Internal review only, not legal advice or signature.",
                "Interpretation is not independently certified; exact citations establish provenance, not legal truth.",
                "Uncertainty routing is conservative and uncalibrated.",
            ],
            "reviewer": None,
        }
        c["packet"] = dict(payload, sha256=digest(payload))
        c["state"] = "review_ready"

    def finalize(self, actor, cid, expected, packet_hash, rationale, acknowledge_limits):
        if not acknowledge_limits or not rationale.strip():
            raise ValueError("Acknowledge limitations and provide rationale")
        with self.mutation(actor, cid, expected, "final_reviewer") as (db, c):
            if actor == c["owner"]:
                raise PermissionError("Independent final reviewer required")
            self._live_decisions(db, c)
            if (
                c["state"] != "review_ready"
                or not c["packet"]
                or c["packet"]["sha256"] != packet_hash
            ):
                raise ValueError("Current exact packet required")
            c["packet"]["reviewer"] = actor
            c["packet"]["review_rationale"] = rationale
            c["state"] = "finalized"
            self._save(
                db,
                c,
                actor,
                "packet_finalized",
                {"packet_hash": packet_hash, "rationale_hash": digest(rationale)},
            )
        return self.case(actor, cid)

    def export(self, actor, cid):
        with self.coherent_read() as db:
            c = self._load(db, actor, cid)
            if set(self._roles(db, actor, c["workspace_id"], cid)) <= {"auditor"}:
                raise PermissionError("Packet reading capability required")
            self._verify(db, cid)
            self._live_decisions(db, c)
            if c["state"] != "finalized" or not c["packet"] or not c["packet"]["reviewer"]:
                raise ValueError("Current final human review required")
            self._roles(db, c["packet"]["reviewer"], c["workspace_id"], cid, "final_reviewer")
            result = dict(
                c["packet"], case_id=cid, revision=c["revision"], epoch=self.setting("epoch")
            )
        with self.mutation(actor, cid, c["revision"]) as (db, current):
            self._live_decisions(db, current)
            self._event(db, current, actor, "packet_exported", {"packet_hash": result["sha256"]})
        return result

    def cancel(self, actor, cid, expected):
        with self.mutation(actor, cid, expected, "requester") as (db, c):
            self._invalidate(db, c)
            c["state"] = "cancelled"
            self._save(db, c, actor, "case_cancelled", {})
        return self.case(actor, cid)

    def jobs(self, actor, cid):
        with self.connect() as db:
            self._load(db, actor, cid)
            return [
                dict(r)
                for r in db.execute(
                    "SELECT id,kind,status,calls,cursor,reason,created_at FROM jobs WHERE case_id=? ORDER BY created_at DESC LIMIT 100",
                    (cid,),
                )
            ]

    def _analysis_input(self, db, c):
        if not c["document_id"] or not c["playbook"] or not c["playbook"]["active"]:
            raise ValueError("Document and active playbook required")
        doc = self._document(db, c["document_id"])
        return digest(
            [
                ANALYSIS_VERSION,
                doc["id"],
                doc["text_hash"],
                doc["bytes_hash"],
                doc["complete"],
                doc["gaps"],
                c["playbook"],
                c["context"],
                self.setting("epoch"),
            ]
        )

    def enqueue(self, actor, cid, expected, key):
        if not key or len(key) > 100:
            raise ValueError("Bounded idempotency key required")
        with self.mutation(actor, cid, role="requester") as (db, c):
            snapshot = self._analysis_input(db, c)
            request_hash = digest([snapshot, expected])
            prior = db.execute(
                "SELECT * FROM jobs WHERE case_id=? AND key=?", (cid, key)
            ).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise ValueError("Idempotency payload conflict")
                return dict(prior)
            if c["revision"] != expected:
                raise ValueError("Revision conflict")
            if (
                db.execute(
                    "SELECT count(*) FROM jobs WHERE status IN ('queued','running')"
                ).fetchone()[0]
                >= 20
            ):
                raise ValueError("Worker queue capacity reached")
            previous = db.execute(
                "SELECT * FROM jobs WHERE case_id=? AND kind='analysis' AND snapshot=? ORDER BY created_at DESC",
                (cid, snapshot),
            ).fetchall()
            if len(previous) >= 2:
                raise ValueError("Two explicit analysis grants exhausted for this context")
            if any(j["status"] in {"queued", "running"} for j in previous):
                raise ValueError("Analysis already active")
            self._invalidate(db, c)
            c["findings"], c["state"] = [], "queued"
            jid = ident()
            cursor, results = (
                (previous[0]["cursor"], previous[0]["results"])
                if previous and previous[0]["status"] == "partial"
                else (0, "[]")
            )
            db.execute(
                "INSERT INTO jobs(id,case_id,actor,kind,key,request_hash,snapshot,status,cursor,results,created_at) VALUES(?,?,?,?,?,?,?,'queued',?,?,?)",
                (jid, cid, actor, "analysis", key, request_hash, snapshot, cursor, results, now()),
            )
            self._save(
                db,
                c,
                actor,
                "analysis_queued",
                {"job_id": jid, "snapshot": snapshot, "grant": len(previous) + 1},
            )
            return {"id": jid, "status": "queued"}

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if self.setting("quarantined"):
                return None
            row = db.execute(
                "SELECT * FROM jobs WHERE status='running' AND lease_until>? LIMIT 1", (now(),)
            ).fetchone()
            if row:
                return None
            row = db.execute(
                "SELECT * FROM jobs WHERE status='queued' OR (status='running' AND lease_until<=?) ORDER BY created_at LIMIT 1",
                (now(),),
            ).fetchone()
            if not row:
                return None
            job = dict(row)
            try:
                c = self._load(db, job["actor"], job["case_id"])
            except PermissionError:
                c = json.loads(
                    db.execute(
                        "SELECT payload FROM cases WHERE id=?", (job["case_id"],)
                    ).fetchone()[0]
                )
                self._verify(db, c["id"])
                self._invalidate(db, c)
                self._save(db, c, "worker", "job_authority_expired", {"job_id": job["id"]})
                return None
            self._verify(db, c["id"])
            job.update(
                status="running",
                lease=ident(),
                lease_until=later(150),
                deadline=job["deadline"] or later(600),
            )
            db.execute(
                "UPDATE jobs SET status='running',lease=?,lease_until=?,deadline=? WHERE id=?",
                (job["lease"], job["lease_until"], job["deadline"], job["id"]),
            )
            self._event(
                db,
                c,
                "worker",
                "job_claimed",
                {"job_id": job["id"], "kind": job["kind"], "calls_reserved": job["calls"]},
            )
            return job

    def _check_job(self, db, job):
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job["id"],)).fetchone()
        if (
            not row
            or row["status"] != "running"
            or row["lease"] != job["lease"]
            or row["lease_until"] <= now()
            or row["deadline"] <= now()
        ):
            raise ValueError("Job lease/deadline invalid")
        c = self._load(db, job["actor"], job["case_id"])
        self._verify(db, c["id"])
        if self.setting("quarantined") or c["state"] in {
            "cancelled",
            "rejected",
            "needs_revision",
            "erased",
            "stale",
        }:
            raise ValueError("Workflow unavailable or stale")
        if job["kind"] == "analysis":
            self._roles(db, job["actor"], c["workspace_id"], c["id"], "requester")
            if self._analysis_input(db, c) != job["snapshot"]:
                raise ValueError("Analysis context changed")
        elif job["snapshot"] != c["checkpoint"]:
            raise ValueError("Resume context changed")
        return c, dict(row)

    def check_job(self, job):
        with self.coherent_read() as db:
            return self._check_job(db, job)[0]

    def reserve(self, job):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            c, row = self._check_job(db, job)
            if not c["egress"]:
                raise PermissionError("Explicit model-context egress required")
            if row["calls"] >= 4:
                raise ValueError("Active grant call allowance exhausted")
            db.execute(
                "UPDATE jobs SET calls=calls+1,lease_until=? WHERE id=?", (later(150), job["id"])
            )
            self._event(
                db,
                c,
                "worker",
                "model_call_reserved",
                {"job_id": job["id"], "number": row["calls"] + 1},
            )

    def job_event(self, job, kind, detail):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            c, _ = self._check_job(db, job)
            self._event(db, c, "worker", kind, {"job_id": job["id"], **detail})

    def checkpoint_chunk(self, job, cursor, values):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            c, row = self._check_job(db, job)
            results = json.loads(row["results"])
            if row["cursor"] != cursor:
                raise ValueError("Stage checkpoint conflict")
            results.append(values)
            db.execute(
                "UPDATE jobs SET cursor=?,results=?,lease_until=? WHERE id=?",
                (cursor + 1, canonical(results), later(150), job["id"]),
            )
            self._event(
                db,
                c,
                "worker",
                "analysis_chunk_saved",
                {"cursor": cursor + 1, "result_hash": digest(values), "job_id": job["id"]},
            )

    def complete_analysis(self, job, findings, *, complete, reason):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            c, _ = self._check_job(db, job)
            c["findings"] = [
                dict(f, origin="model", reviewed_by=None)
                for f in self._validated_findings(db, c, findings)
            ]
            c["findings_revision"] += 1
            self._evaluate(db, c)
            if not complete:
                c["state"] = "partial"
                c["packet"] = None
            db.execute(
                "UPDATE jobs SET status=?,lease=NULL,lease_until=NULL,reason=? WHERE id=?",
                ("completed" if complete else "partial", reason, job["id"]),
            )
            self._save(
                db,
                c,
                "worker",
                "analysis_completed" if complete else "analysis_partial",
                {
                    "job_id": job["id"],
                    "reason": reason,
                    "findings_hash": digest(c["findings"]),
                    "prompt_version": ANALYSIS_VERSION,
                },
            )

    def complete_resume(self, job):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            c, _ = self._check_job(db, job)
            self._live_decisions(db, c)
            self._packet(db, c)
            db.execute(
                "UPDATE jobs SET status='completed',lease=NULL,lease_until=NULL,reason='Validated decision context' WHERE id=?",
                (job["id"],),
            )
            self._save(
                db,
                c,
                "worker",
                "resume_completed",
                {"job_id": job["id"], "packet_hash": c["packet"]["sha256"]},
            )

    def fail_job(self, job, reason):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status,lease FROM jobs WHERE id=?", (job["id"],)).fetchone()
            if not row or row["status"] != "running" or row["lease"] != job["lease"]:
                return
            try:
                c = self._load(db, job["actor"], job["case_id"])
            except PermissionError:
                c = json.loads(
                    db.execute(
                        "SELECT payload FROM cases WHERE id=?", (job["case_id"],)
                    ).fetchone()[0]
                )
                self._verify(db, c["id"])
                self._invalidate(db, c)
                self._save(db, c, "worker", "inflight_authority_expired", {"job_id": job["id"]})
                return
            self._verify(db, c["id"])
            db.execute(
                "UPDATE jobs SET status='partial',lease=NULL,lease_until=NULL,reason=? WHERE id=?",
                (reason, job["id"]),
            )
            if c["state"] not in {"stale", "cancelled", "erased", "rejected", "needs_revision"}:
                c["state"], c["packet"] = "partial", None
            self._save(db, c, "worker", "job_failed", {"job_id": job["id"], "reason": reason})

    def erase_preview(self, actor, cid):
        with self.connect() as db:
            c = self._load(db, actor, cid, "owner")
            return {
                "case_id": cid,
                "revision": c["revision"],
                "documents": db.execute(
                    "SELECT count(*) FROM documents WHERE case_id=?", (cid,)
                ).fetchone()[0],
                "decisions": len(c["decisions"]),
                "limitations": "Downloaded packets and backup media require separate disposal. Non-content audit receipts remain.",
            }

    def erase(self, actor, cid, expected, confirmation):
        if confirmation != "ERASE":
            raise ValueError("Explicit ERASE confirmation required")
        with self.mutation(actor, cid, expected, "owner") as (db, c):
            authority.erase(self.ledger_dir, self.store_id, self.binding, cid)
            self._event(db, c, actor, "erasure_recorded", {"dependency_closure": True})
        self.reconcile_erasures()
        return {"status": "erased", "case_id": cid}

    def reconcile_erasures(self):
        for cid in authority.erased(self.ledger_dir, self.store_id, self.binding):
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT payload FROM cases WHERE id=?", (cid,)).fetchone()
                if not row:
                    continue
                c = json.loads(row[0])
                if c["state"] == "erased":
                    continue
                db.execute("DELETE FROM documents WHERE case_id=?", (cid,))
                db.execute("DELETE FROM history WHERE case_id=?", (cid,))
                db.execute("DELETE FROM jobs WHERE case_id=?", (cid,))
                c.update(
                    state="erased",
                    name="Erased case",
                    document_id=None,
                    findings=[],
                    requests=[],
                    decisions=[],
                    checkpoint=None,
                    packet=None,
                    context={},
                    playbook=None,
                )
                db.execute(
                    "UPDATE cases SET name=?,payload=? WHERE id=?", (c["name"], canonical(c), cid)
                )
                self._save(db, c, "system", "erasure_reconciled", {"content_removed": True})
