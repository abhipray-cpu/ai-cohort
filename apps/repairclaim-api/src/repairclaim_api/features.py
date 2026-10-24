"""Durable documents, reviewed source registry and bounded investigation jobs."""

import hashlib
import json
import os

from contracts.repairclaim import CaseSnapshot, EvidenceAnchor, Fact, ProgrammeRevision
from cryptography.fernet import Fernet, InvalidToken

from repairclaim_api.continuity import ContinuityMixin
from repairclaim_api.core import verify_anchor
from repairclaim_api.errors import DomainError
from repairclaim_api.feature_utils import canonical, fingerprint, identifier
from repairclaim_api.packets import PacketMixin
from repairclaim_api.privacy import PrivacyMixin
from repairclaim_api.sources import classify_change, validate_source_url

FEATURE_SCHEMA = """
CREATE TABLE IF NOT EXISTS rc_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
INSERT OR IGNORE INTO rc_meta VALUES('registry_epoch','0');
INSERT OR IGNORE INTO rc_meta VALUES('quarantined','0');
CREATE TABLE IF NOT EXISTS rc_case_keys(case_id TEXT PRIMARY KEY REFERENCES cases(id),wrapped_key BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS rc_objects(
 id TEXT PRIMARY KEY,household_id TEXT NOT NULL,case_id TEXT NOT NULL,kind TEXT NOT NULL,
 state TEXT NOT NULL,data TEXT NOT NULL,created REAL NOT NULL,
 FOREIGN KEY(household_id,case_id) REFERENCES cases(household_id,id)
);
CREATE INDEX IF NOT EXISTS rc_objects_case ON rc_objects(household_id,case_id,kind);
CREATE TABLE IF NOT EXISTS rc_invite_lookup(token_hash TEXT PRIMARY KEY,object_id TEXT NOT NULL REFERENCES rc_objects(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS rc_idempotency(
 household_id TEXT NOT NULL,case_id TEXT NOT NULL,kind TEXT NOT NULL,key TEXT NOT NULL,
 request_hash TEXT NOT NULL,object_id TEXT NOT NULL REFERENCES rc_objects(id) ON DELETE CASCADE,
 PRIMARY KEY(household_id,case_id,kind,key),
 FOREIGN KEY(household_id,case_id) REFERENCES cases(household_id,id)
);
CREATE TABLE IF NOT EXISTS rc_sources(
 id TEXT PRIMARY KEY,url TEXT NOT NULL,current_hash TEXT NOT NULL,state TEXT NOT NULL,
 last_success REAL NOT NULL,updated REAL NOT NULL,text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rc_captures(
 source_id TEXT NOT NULL REFERENCES rc_sources(id),hash TEXT NOT NULL,
 parsed TEXT NOT NULL,blob_id TEXT NOT NULL,created REAL NOT NULL,
 PRIMARY KEY(source_id,hash)
);
CREATE TABLE IF NOT EXISTS rc_programmes(
 family TEXT NOT NULL,revision TEXT NOT NULL,payload TEXT NOT NULL,
 active INTEGER NOT NULL,created REAL NOT NULL,PRIMARY KEY(family,revision)
);
CREATE UNIQUE INDEX IF NOT EXISTS rc_programme_current ON rc_programmes(family) WHERE active=1;
CREATE TABLE IF NOT EXISTS rc_changes(
 id INTEGER PRIMARY KEY AUTOINCREMENT,epoch INTEGER NOT NULL,family TEXT NOT NULL,
 old_revision TEXT,new_revision TEXT NOT NULL,reason TEXT NOT NULL,created REAL NOT NULL
);
"""


class FeatureStore(PacketMixin, ContinuityMixin, PrivacyMixin):
    def _features_init(self):
        self.blob_dir = self.path.parent / "blobs"
        self.blob_dir.mkdir(mode=0o700, exist_ok=True)
        if self.blob_dir.is_symlink():
            raise DomainError("invalid_blob_path", 503)
        key_path = self.path.parent / "content.key"
        with self._transaction():
            try:
                descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(Fernet.generate_key())
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError:
                pass
            if key_path.is_symlink():
                raise DomainError("invalid_key_path", 503)
            self.content_cipher = Fernet(key_path.read_bytes())
            self.csrf_secret = hashlib.sha256(key_path.read_bytes() + b"repairclaim-csrf").digest()
        with self._transaction() as db:
            for statement in FEATURE_SCHEMA.split(";"):
                if statement.strip():
                    db.execute(statement)
            columns = {row[1] for row in db.execute("PRAGMA table_info(cases)")}
            if "lifecycle" not in columns:
                db.execute(
                    "ALTER TABLE cases ADD COLUMN lifecycle TEXT NOT NULL DEFAULT 'fact_review'"
                )
            if "retention_until" not in columns:
                db.execute("ALTER TABLE cases ADD COLUMN retention_until REAL NOT NULL DEFAULT 0")
                db.execute(
                    "UPDATE cases SET retention_until=? WHERE deleted=0",
                    (self._now() + 180 * 86400,),
                )
            for table, column, where in (
                ("fact_revisions", "snapshot_json", "1=1"),
                ("rc_objects", "data", "1=1"),
                ("cases", "title", "deleted=0 AND title<>''"),
            ):
                for row in db.execute(
                    f"SELECT rowid AS migration_row,case_id,{column} FROM {table} WHERE {where} AND {column} NOT LIKE 'RCV1:%'"
                    if table != "cases"
                    else "SELECT rowid AS migration_row,id AS case_id,title FROM cases WHERE deleted=0 AND title<>'' AND title NOT LIKE 'RCV1:%'"
                ).fetchall():
                    db.execute(
                        f"UPDATE {table} SET {column}=? WHERE rowid=?",
                        (
                            self._private_encode(db, row["case_id"], row[column]),
                            row["migration_row"],
                        ),
                    )
        self.apply_erasure_ledger()

    def _private_encode(self, db, case_id, text):
        row = db.execute(
            "SELECT wrapped_key FROM rc_case_keys WHERE case_id=?", (case_id,)
        ).fetchone()
        if row is None:
            key = Fernet.generate_key()
            db.execute(
                "INSERT INTO rc_case_keys VALUES(?,?)", (case_id, self.content_cipher.encrypt(key))
            )
        else:
            key = self.content_cipher.decrypt(row[0])
        return "RCV1:" + case_id + ":" + Fernet(key).encrypt(text.encode()).decode("ascii")

    def _blob_write(self, data, *, db=None, case_id=None):
        if len(data) > 32 * 1024 * 1024:
            raise DomainError("blob_limit", 413)
        name = identifier()
        cipher, header = self.content_cipher, b"RCB0"
        if case_id:
            if db is None:
                raise DomainError("blob_transaction_required", 503)
            row = db.execute(
                "SELECT wrapped_key FROM rc_case_keys WHERE case_id=?", (case_id,)
            ).fetchone()
            if row is None:
                key = Fernet.generate_key()
                db.execute(
                    "INSERT INTO rc_case_keys VALUES(?,?)",
                    (case_id, self.content_cipher.encrypt(key)),
                )
            else:
                key = self.content_cipher.decrypt(row[0])
            cipher, header = Fernet(key), b"RCB1" + case_id.encode("ascii")
        descriptor = os.open(self.blob_dir / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(header + cipher.encrypt(data))
            stream.flush()
            os.fsync(stream.fileno())
        return name

    def _blob_read(self, name):
        if (
            not isinstance(name, str)
            or len(name) != 32
            or any(char not in "0123456789abcdef" for char in name)
        ):
            raise DomainError("invalid_blob_reference", 503)
        path = self.blob_dir / name
        if path.is_symlink():
            raise DomainError("invalid_blob_reference", 503)
        try:
            raw = path.read_bytes()
            if raw.startswith(b"RCB1"):
                case_id = raw[4:36].decode("ascii")
                with self._connection() as db:
                    key_row = db.execute(
                        "SELECT wrapped_key FROM rc_case_keys WHERE case_id=?", (case_id,)
                    ).fetchone()
                if key_row is None:
                    raise DomainError("erased_blob", 404)
                key = self.content_cipher.decrypt(key_row[0])
                return Fernet(key).decrypt(raw[36:])
            return self.content_cipher.decrypt(raw[4:] if raw.startswith(b"RCB0") else raw)
        except (ValueError, OSError, InvalidToken) as error:
            raise DomainError("blob_unavailable", 503) from error

    def _new_object(self, db, case, kind, data, state="ready"):
        if (
            db.execute(
                "SELECT COUNT(*) FROM rc_objects WHERE household_id=? AND case_id=?",
                (case["household_id"], case["id"]),
            ).fetchone()[0]
            >= 1000
        ):
            raise DomainError("case_record_limit", 409)
        name = identifier()
        encoded = canonical(data)
        if len(encoded) > 16 * 1024 * 1024:
            raise DomainError("record_limit", 413)
        db.execute(
            "INSERT INTO rc_objects VALUES(?,?,?,?,?,?,?)",
            (
                name,
                case["household_id"],
                case["id"],
                kind,
                state,
                self._private_encode(db, case["id"], encoded),
                self._now(),
            ),
        )
        return self._object(db, name)

    @staticmethod
    def _object(db, name):
        row = db.execute("SELECT * FROM rc_objects WHERE id=?", (name,)).fetchone()
        if row is None:
            raise DomainError("not_found", 404)
        return {**dict(row), "data": json.loads(row["data"])}

    def _scoped_object(self, db, actor, name, kind=None, action="read"):
        item = self._object(db, name)
        case = self._case(db, actor, item["case_id"], action)
        if case["household_id"] != item["household_id"] or (kind and item["kind"] != kind):
            raise DomainError("not_found", 404)
        return item, case

    @staticmethod
    def _public(item):
        data = dict(item["data"])
        for key in (
            "auth_hash",
            "lease",
            "lease_until",
            "blob_id",
            "zip_blob",
            "pdf_blob",
            "raw_context",
            "token_hash",
        ):
            data.pop(key, None)
        return {
            "id": item["id"],
            "case_id": item["case_id"],
            "kind": item["kind"],
            "status": item["state"],
            "created": item["created"],
            **data,
        }

    def _update_object(self, db, item, *, state=None):
        db.execute(
            "UPDATE rc_objects SET data=?,state=? WHERE id=?",
            (
                self._private_encode(db, item["case_id"], canonical(item["data"])),
                state or item["state"],
                item["id"],
            ),
        )

    def _invalidate(self, db, case_id=None):
        if case_id:
            db.execute(
                "UPDATE cases SET lifecycle='fact_review' WHERE id=? AND lifecycle NOT IN ('closed','paused')",
                (case_id,),
            )
        clause, values = (" AND case_id=?", (case_id,)) if case_id else ("", ())
        for row in db.execute(
            "SELECT * FROM rc_objects WHERE kind IN ('job','packet')" + clause, values
        ).fetchall():
            item = {**dict(row), "data": json.loads(row["data"])}
            item["data"]["stale"] = True
            if item["kind"] == "packet":
                item["data"].pop("approval", None)
            self._update_object(db, item)

    def _bump_case(self, db, actor, case, action):
        db.execute(
            "UPDATE cases SET revision=revision+1,lifecycle='fact_review' WHERE id=? AND household_id=?",
            (case["id"], case["household_id"]),
        )
        row = db.execute(
            "SELECT snapshot_json FROM fact_revisions WHERE household_id=? AND case_id=? AND revision=?",
            (case["household_id"], case["id"], case["revision"]),
        ).fetchone()
        snapshot = CaseSnapshot.model_validate_json(row[0])
        case["revision"] += 1
        self._save_snapshot(db, actor, snapshot.model_copy(update={"revision": case["revision"]}))
        self._invalidate(db, case["id"])
        self._audit(db, actor, case, action)

    def _idempotent(self, db, case, kind, key, request):
        if not isinstance(key, str) or not 1 <= len(key) <= 128:
            raise DomainError("idempotency_required", 422)
        row = db.execute(
            "SELECT * FROM rc_idempotency WHERE household_id=? AND case_id=? AND kind=? AND key=?",
            (case["household_id"], case["id"], kind, key),
        ).fetchone()
        if row:
            if row["request_hash"] != fingerprint(request):
                raise DomainError("idempotency_conflict", 409)
            return self._object(db, row["object_id"])
        return None

    def _bind_idempotency(self, db, case, kind, key, request, item):
        db.execute(
            "INSERT INTO rc_idempotency VALUES(?,?,?,?,?,?)",
            (case["household_id"], case["id"], kind, key, fingerprint(request), item["id"]),
        )

    def _queue(self, db, actor, case, token, operation, data):
        return self._new_object(
            db,
            case,
            "job",
            {
                "operation": operation,
                "creator_id": actor["id"],
                "auth_hash": hashlib.sha256(token.encode()).hexdigest(),
                "case_revision": case["revision"],
                "attempts": [],
                "stage": "queued",
                "stale": False,
                "allowance": 0,
                "deadline": self._now() + 720,
                **data,
            },
            "queued",
        )

    def add_document(self, token, case_id, filename, kind, data, expected_revision):
        if kind not in {"estimate", "invoice", "job_sheet", "receipt", "response", "other"}:
            raise DomainError("document_kind", 422)
        if (
            not isinstance(filename, str)
            or not 1 <= len(filename) <= 160
            or any(char in filename for char in "/\\\x00")
            or filename.rsplit(".", 1)[-1].lower() not in {"pdf", "png", "jpg", "jpeg"}
        ):
            raise DomainError("unsupported_document", 415)
        if not data or len(data) > 20 * 1024 * 1024:
            raise DomainError("document_size", 413)
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "edit")
            self._revision(case, expected_revision)
            documents = [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT data FROM rc_objects WHERE case_id=? AND kind='document'", (case_id,)
                )
            ]
            if (
                len(documents) >= 20
                or sum(doc["size"] for doc in documents) + len(data) > 200 * 1024 * 1024
            ):
                raise DomainError("document_limit", 413)
            self._bump_case(db, actor, case, "document_uploaded")
            item = self._new_object(
                db,
                case,
                "document",
                {
                    "filename": filename,
                    "document_kind": kind,
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "blob_id": self._blob_write(data, db=db, case_id=case_id),
                },
                "queued",
            )
            job = self._queue(db, actor, case, token, "parse", {"document_id": item["id"]})
            item["data"]["job_id"] = job["id"]
            self._update_object(db, item)
            return self._public(item)

    def get_document(self, token, document_id):
        with self._transaction() as db:
            item, _ = self._scoped_object(db, self._actor(db, token), document_id, "document")
            return self._public(item)

    def document_bytes(self, token, document_id):
        with self._transaction() as db:
            item, _ = self._scoped_object(db, self._actor(db, token), document_id, "document")
            data = self._blob_read(item["data"]["blob_id"])
            return data, item["data"]["filename"]

    def confirm_proposals(self, token, document_id, selected, expected_revision):
        with self._transaction() as db:
            actor = self._actor(db, token)
            item, case = self._scoped_object(db, actor, document_id, "document", "edit")
            self._revision(case, expected_revision)
            if item["state"] != "ready" or len(selected) > 100:
                raise DomainError("document_not_ready", 409)
            proposals = item["data"]["parsed"]["proposals"]
            if any(type(index) is not int or not 0 <= index < len(proposals) for index in selected):
                raise DomainError("invalid_selection", 422)
            row = db.execute(
                "SELECT snapshot_json FROM fact_revisions WHERE household_id=? AND case_id=? AND revision=?",
                (case["household_id"], case["id"], case["revision"]),
            ).fetchone()
            facts = list(CaseSnapshot.model_validate_json(row[0]).facts)
            for index in sorted(set(selected)):
                proposal = proposals[index]
                anchor = EvidenceAnchor(
                    document_id=document_id,
                    sha256=item["data"]["sha256"],
                    page=proposal["page"],
                    quote=proposal["quote"],
                )
                fact = Fact(
                    field=proposal["field"],
                    value=proposal["value"],
                    unit=proposal.get("unit"),
                    status="confirmed",
                    anchor=anchor,
                )
                if fact not in facts:
                    facts.append(fact)
            snapshot = CaseSnapshot(
                case_id=case["id"],
                revision=case["revision"] + 1,
                jurisdiction=case["jurisdiction"],
                facts=tuple(facts),
            )
            db.execute("UPDATE cases SET revision=? WHERE id=?", (snapshot.revision, case["id"]))
            self._save_snapshot(db, actor, snapshot)
            case["revision"] = snapshot.revision
            self._invalidate(db, case["id"])
            self._audit(db, actor, case, "document_facts_confirmed")
            return snapshot

    def list_vehicles(self, token):
        with self._transaction() as db:
            actor = self._actor(db, token)
            return [
                dict(row)
                for row in db.execute(
                    "SELECT id,make,model,model_year,jurisdiction FROM vehicles WHERE household_id=?",
                    (actor["household_id"],),
                )
            ]

    def case_details(self, token, case_id):
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id)
            items = [
                self._public({**dict(row), "data": json.loads(row["data"])})
                for row in db.execute(
                    "SELECT * FROM rc_objects WHERE household_id=? AND case_id=? ORDER BY created,rowid",
                    (case["household_id"], case_id),
                )
            ]
            result = {
                **case,
                "documents": [],
                "jobs": [],
                "packets": [],
                "responses": [],
                "manual_submissions": [],
                "outcomes": [],
                "reminders": [],
                "notifications": [],
                "monitoring": [],
            }
            names = {
                "document": "documents",
                "job": "jobs",
                "packet": "packets",
                "response": "responses",
                "manual_submission": "manual_submissions",
                "outcome": "outcomes",
                "reminder": "reminders",
                "notification": "notifications",
                "monitoring": "monitoring",
            }
            for item in items:
                if item["kind"] in names:
                    result[names[item["kind"]]].append(item)
            result["grants"] = (
                [
                    dict(row)
                    for row in db.execute(
                        "SELECT g.user_id,g.role,g.expires,u.username FROM grants g JOIN users u ON u.id=g.user_id WHERE g.case_id=? ORDER BY u.username",
                        (case_id,),
                    )
                ]
                if case["role"] == "owner"
                else []
            )
            result["invitations"] = (
                [
                    self._public(self._object(db, row[0]))
                    for row in db.execute(
                        "SELECT id FROM rc_objects WHERE case_id=? AND kind='invitation'",
                        (case_id,),
                    )
                ]
                if case["role"] == "owner"
                else []
            )
            return result

    def source_bytes(self, token, source_id, digest):
        with self._transaction() as db:
            self._actor(db, token)
            row = db.execute(
                "SELECT blob_id FROM rc_captures WHERE source_id=? AND hash=?", (source_id, digest)
            ).fetchone()
            if row is None:
                raise DomainError("not_found", 404)
            return self._blob_read(row[0])

    def revoke_invitation(self, token, item_id):
        with self._transaction() as db:
            actor = self._actor(db, token)
            item, case = self._scoped_object(db, actor, item_id, "invitation", "owner")
            self._update_object(db, item, state="revoked")
            self._audit(db, actor, case, "case_invitation_revoked")

    def correct_fact(self, token, case_id, expected_revision, index, replacement):
        from contracts.repairclaim import Fact

        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "edit")
            self._revision(case, expected_revision)
            snapshot = CaseSnapshot.model_validate_json(
                db.execute(
                    "SELECT snapshot_json FROM fact_revisions WHERE case_id=? AND revision=?",
                    (case_id, case["revision"]),
                ).fetchone()[0]
            )
            facts = list(snapshot.facts)
            if index is not None:
                if type(index) is not int or not 0 <= index < len(facts):
                    raise DomainError("invalid_fact_index", 422)
                facts.pop(index)
            if replacement is not None:
                fact = Fact.model_validate(replacement)
                if fact.status != "user_reported" or fact.anchor is not None:
                    raise DomainError("manual_fact_attribution", 422)
                facts.append(fact)
            updated = snapshot.model_copy(
                update={"revision": snapshot.revision + 1, "facts": tuple(facts)}
            )
            # Revalidation also enforces aggregate bounds.
            updated = CaseSnapshot.model_validate(updated.model_dump())
            self._save_snapshot(db, actor, updated)
            db.execute(
                "UPDATE cases SET revision=?,retention_until=? WHERE id=?",
                (updated.revision, self._now() + 180 * 86400, case_id),
            )
            self._invalidate(db, case_id)
            self._audit(db, actor, case, "fact_corrected_with_history")
            return updated

    def capture_source(self, source_id, url, raw, parsed):
        """Operator primitive: caller supplies acquired bytes; never a consumer-controlled URL."""
        validate_source_url(url)
        if len(source_id) > 80 or not source_id.replace("-", "").replace("_", "").isalnum():
            raise DomainError("source_id", 422)
        digest = hashlib.sha256(raw).hexdigest()
        if parsed.get("sha256") != digest:
            raise DomainError("source_hash_mismatch", 422)
        text = "\n".join(page["text"] for page in parsed["pages"])
        with self._transaction() as db:
            old = db.execute("SELECT * FROM rc_sources WHERE id=?", (source_id,)).fetchone()
            change = "new_capture" if not old else classify_change(old["text"], text)
            state = (
                "review_required" if change in {"new_capture", "review_required"} else old["state"]
            )
            if state == "unavailable" and change not in {"new_capture", "review_required"}:
                state = (
                    "reviewed"
                    if any(
                        condition.anchor.document_id == source_id
                        and condition.anchor.sha256 == digest
                        for row in db.execute("SELECT payload FROM rc_programmes WHERE active=1")
                        for condition in ProgrammeRevision.model_validate_json(row[0]).conditions
                    )
                    else "review_required"
                )
            db.execute(
                "INSERT INTO rc_sources VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                "url=excluded.url,current_hash=excluded.current_hash,state=excluded.state,last_success=excluded.last_success,updated=excluded.updated,text=excluded.text",
                (source_id, url, digest, state, self._now(), self._now(), text),
            )
            if not db.execute(
                "SELECT 1 FROM rc_captures WHERE source_id=? AND hash=?", (source_id, digest)
            ).fetchone():
                db.execute(
                    "INSERT INTO rc_captures VALUES(?,?,?,?,?)",
                    (source_id, digest, canonical(parsed), self._blob_write(raw), self._now()),
                )
            if old and old["current_hash"] != digest and change == "review_required":
                self._invalidate(db)
            return {"source_id": source_id, "sha256": digest, "change": change, "status": state}

    def activate_programme(self, programme):
        """Operator-reviewed programme activation; validates immutable source anchors."""
        programme = ProgrammeRevision.model_validate(programme)
        with self._transaction() as db:
            for condition in programme.conditions:
                anchor = condition.anchor
                capture = db.execute(
                    "SELECT parsed FROM rc_captures WHERE source_id=? AND hash=?",
                    (anchor.document_id, anchor.sha256),
                ).fetchone()
                head = db.execute(
                    "SELECT * FROM rc_sources WHERE id=?", (anchor.document_id,)
                ).fetchone()
                if capture is None or head is None or head["current_hash"] != anchor.sha256:
                    raise DomainError("source_revision_not_current", 409)
                pages = [
                    {**page, "document_id": anchor.document_id, "sha256": anchor.sha256}
                    for page in json.loads(capture[0])["pages"]
                ]
                if not verify_anchor(anchor, pages):
                    raise DomainError("source_anchor_invalid", 422)
            encoded = programme.model_dump_json()
            existing = db.execute(
                "SELECT payload FROM rc_programmes WHERE family=? AND revision=?",
                (programme.family_id, programme.revision),
            ).fetchone()
            if existing:
                if existing[0] != encoded:
                    raise DomainError("immutable_programme_revision", 409)
                return
            previous = db.execute(
                "SELECT revision FROM rc_programmes WHERE family=? AND active=1",
                (programme.family_id,),
            ).fetchone()
            db.execute("UPDATE rc_programmes SET active=0 WHERE family=?", (programme.family_id,))
            db.execute(
                "INSERT INTO rc_programmes VALUES(?,?,?,1,?)",
                (programme.family_id, programme.revision, encoded, self._now()),
            )
            epoch = self._epoch(db) + 1
            db.execute("UPDATE rc_meta SET value=? WHERE key='registry_epoch'", (str(epoch),))
            db.execute(
                "INSERT INTO rc_changes(epoch,family,old_revision,new_revision,reason,created) VALUES(?,?,?,?,?,?)",
                (
                    epoch,
                    programme.family_id,
                    previous[0] if previous else None,
                    programme.revision,
                    "condition_changed" if previous else "candidate_added",
                    self._now(),
                ),
            )
            for condition in programme.conditions:
                db.execute(
                    "UPDATE rc_sources SET state='reviewed' WHERE id=?",
                    (condition.anchor.document_id,),
                )
            self._invalidate(db)

    @staticmethod
    def _epoch(db):
        return int(db.execute("SELECT value FROM rc_meta WHERE key='registry_epoch'").fetchone()[0])

    def _inventory(self, db):
        programmes = tuple(
            ProgrammeRevision.model_validate_json(row[0])
            for row in db.execute(
                "SELECT payload FROM rc_programmes WHERE active=1 ORDER BY family"
            )
        )
        if not programmes:
            return (), "unavailable", self._epoch(db)
        for programme in programmes:
            for condition in programme.conditions:
                head = db.execute(
                    "SELECT * FROM rc_sources WHERE id=?", (condition.anchor.document_id,)
                ).fetchone()
                if head is None or head["state"] == "unavailable":
                    return programmes, "unavailable", self._epoch(db)
                if head["state"] != "reviewed" or self._now() - head["last_success"] > 48 * 3600:
                    return programmes, "stale", self._epoch(db)
                if head["current_hash"] != condition.anchor.sha256:
                    capture = db.execute(
                        "SELECT parsed FROM rc_captures WHERE source_id=? AND hash=?",
                        (condition.anchor.document_id, condition.anchor.sha256),
                    ).fetchone()
                    old_text = (
                        "\n".join(page["text"] for page in json.loads(capture[0])["pages"])
                        if capture
                        else ""
                    )
                    if classify_change(old_text, head["text"]) == "review_required":
                        return programmes, "stale", self._epoch(db)
        return programmes, "complete", self._epoch(db)

    def registry_status(self):
        with self._transaction() as db:
            programmes, state, epoch = self._inventory(db)
            return {
                "status": state,
                "epoch": epoch,
                "programme_count": len(programmes),
                "sources": [
                    dict(row)
                    for row in db.execute(
                        "SELECT id,url,state,last_success,updated FROM rc_sources"
                    )
                ],
            }

    def start_investigation(
        self,
        token,
        case_id,
        expected_revision,
        key,
        *,
        mode="rules",
        allowance=0,
        egress_fingerprint=None,
    ):
        if (
            mode not in {"rules", "codex", "jev"}
            or type(allowance) is not int
            or not 0 <= allowance <= 6
            or (mode in {"codex", "jev"} and allowance == 0)
        ):
            raise DomainError("invalid_allowance", 422)
        request = {
            "revision": expected_revision,
            "mode": mode,
            "allowance": allowance,
            "egress_fingerprint": egress_fingerprint,
        }
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "edit")
            existing = self._idempotent(db, case, "investigation", key, request)
            if existing:
                return self._public(existing)
            self._revision(case, expected_revision)
            approved_context = None
            if case.get("lifecycle") == "closed":
                raise DomainError("case_closed", 409)
            if mode in {"codex", "jev"}:
                self._case(db, actor, case_id, "owner")
                for row in db.execute(
                    "SELECT data FROM rc_objects WHERE household_id=? AND kind='job'",
                    (case["household_id"],),
                ):
                    previous = json.loads(row[0])
                    if any(
                        attempt.get("status") in {"provider_timeout", "provider_error", "reserved"}
                        for attempt in previous.get("attempts", [])
                    ) and not previous.get("unknown_usage_acknowledged"):
                        raise DomainError("unknown_usage_hold", 409)
                approved_context = self._analysis_context(db, case, mode=mode)
                if egress_fingerprint != fingerprint(approved_context):
                    raise DomainError("egress_approval_required", 403)
            if (
                db.execute(
                    "SELECT COUNT(*) FROM rc_objects WHERE household_id=? AND kind='job' AND state IN ('queued','running')",
                    (case["household_id"],),
                ).fetchone()[0]
                >= 2
            ):
                raise DomainError("active_job_limit", 409)
            snapshot = db.execute(
                "SELECT snapshot_json FROM fact_revisions WHERE case_id=? AND revision=?",
                (case_id, case["revision"]),
            ).fetchone()[0]
            job = self._queue(
                db,
                actor,
                case,
                token,
                "investigate",
                {
                    "snapshot": json.loads(snapshot),
                    "mode": mode,
                    "allowance": allowance,
                    "registry_epoch": self._epoch(db),
                    "approved_context": approved_context,
                },
            )
            self._bind_idempotency(db, case, "investigation", key, request, job)
            db.execute("UPDATE cases SET lifecycle='investigating' WHERE id=?", (case_id,))
            self._audit(db, actor, case, "investigation_requested")
            return self._public(job)

    def get_job(self, token, job_id):
        with self._transaction() as db:
            item, _ = self._scoped_object(db, self._actor(db, token), job_id, "job")
            return self._public(item)

    def cancel_job(self, token, job_id):
        with self._transaction() as db:
            actor = self._actor(db, token)
            item, case = self._scoped_object(db, actor, job_id, "job", "edit")
            item["data"].pop("lease", None)
            self._update_object(db, item, state="cancelled")
            self._audit(db, actor, case, "job_cancelled")

    def _job_actor(self, db, item):
        actor = db.execute(
            "SELECT u.id,u.household_id,u.username,s.csrf_hash FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires>? AND u.id=?",
            (item["data"]["auth_hash"], self._now(), item["data"]["creator_id"]),
        ).fetchone()
        if actor is None:
            raise DomainError("authority_expired", 409)
        self._case(db, actor, item["case_id"], "edit")
        return actor

    def claim_job(self):
        with self._transaction() as db:
            if any(
                json.loads(row[0]).get("lease_until", 0) > self._now()
                for row in db.execute(
                    "SELECT data FROM rc_objects WHERE kind='job' AND state='running'"
                )
            ):
                return None
            for row in db.execute(
                "SELECT * FROM rc_objects WHERE kind='job' AND state IN ('queued','running') ORDER BY created,rowid"
            ).fetchall():
                item = {**dict(row), "data": json.loads(row["data"])}
                if item["state"] == "running" and item["data"].get("lease_until", 0) > self._now():
                    continue
                if item["state"] == "running" and item["data"]["attempts"]:
                    item["data"]["error"] = "interrupted_attempt_unknown_usage"
                    self._update_object(db, item, state="partial")
                    continue
                try:
                    self._job_actor(db, item)
                except DomainError as error:
                    item["data"]["error"] = error.code
                    self._update_object(db, item, state="awaiting_authority")
                    continue
                if item["data"].get("deadline", 0) <= self._now():
                    item["data"]["error"] = "deadline_exceeded"
                    self._update_object(db, item, state="partial")
                    continue
                item["data"].update({"lease": identifier(), "lease_until": self._now() + 180})
                self._update_object(db, item, state="running")
                return item
        return None

    def commit_job(self, item, result, status, *, error=None):
        with self._transaction() as db:
            try:
                current = self._object(db, item["id"])
                actor = self._job_actor(db, current)
            except DomainError:
                return False
            if (
                current["state"] != "running"
                or current["data"].get("lease") != item["data"].get("lease")
                or current["data"].get("lease_until", 0) <= self._now()
            ):
                return False
            case = self._case(db, actor, current["case_id"], "edit")
            if current["data"]["operation"] == "investigate" and (
                current["data"].get("stale")
                or case["revision"] != current["data"]["case_revision"]
                or current["data"].get("registry_epoch") != self._epoch(db)
            ):
                status, error = "partial", "stale_inputs"
                current["data"]["stale"] = True
            if (
                current["data"]["operation"] == "investigate"
                and self._inventory(db)[1] != "complete"
                and result.get("search", {}).get("search_status") == "complete"
            ):
                status, error = "partial", "source_no_longer_current"
                current["data"]["stale"] = True
            if current["data"]["operation"] == "investigate":
                db.execute("UPDATE cases SET lifecycle=? WHERE id=?", (status, case["id"]))
            current["data"].update({"result": result, "stage": status})
            if error:
                current["data"]["error"] = error
            current["data"].pop("lease", None)
            self._update_object(db, current, state=status)
            self._audit(db, actor, case, "job_" + status)
            return True

    def checkpoint_job(self, item, result):
        with self._transaction() as db:
            current = self._object(db, item["id"])
            self._job_actor(db, current)
            if current["state"] != "running" or current["data"].get("lease") != item["data"].get(
                "lease"
            ):
                raise DomainError("lease_lost", 409)
            current["data"]["result"] = result
            current["data"]["stage"] = "rules_evaluated"
            self._update_object(db, current)

    def _analysis_context(self, db, case, *, mode="codex"):
        snapshot = json.loads(
            db.execute(
                "SELECT snapshot_json FROM fact_revisions WHERE case_id=? AND revision=?",
                (case["id"], case["revision"]),
            ).fetchone()[0]
        )
        allowed = {
            "make",
            "model",
            "model_year",
            "component",
            "repair_date",
            "repair_mileage",
            "diagnostic_code",
        }
        if mode == "jev":
            allowed.add("in_service_date")
        facts = [
            {key: fact[key] for key in ("field", "value", "unit", "status")}
            for fact in snapshot["facts"]
            if fact["field"] in allowed and fact["status"] != "extracted"
        ]
        programmes, status, epoch = self._inventory(db)
        pages, seen = [], set()
        for programme in programmes:
            for condition in programme.conditions:
                anchor = condition.anchor
                key = (anchor.document_id, anchor.sha256, anchor.page)
                if key not in seen:
                    row = db.execute(
                        "SELECT parsed FROM rc_captures WHERE source_id=? AND hash=?", key[:2]
                    ).fetchone()
                    if row:
                        page = next(
                            (
                                page
                                for page in json.loads(row[0])["pages"]
                                if page["page"] == anchor.page
                            ),
                            None,
                        )
                        if page:
                            pages.append(
                                {**page, "document_id": anchor.document_id, "sha256": anchor.sha256}
                            )
                    seen.add(key)
        context = {
            "destination": "installed_codex",
            "purpose": "advisory_condition_review",
            "facts": facts,
            "source_pages": pages,
            "registry_epoch": epoch,
            "source_status": status,
            "candidate_families": [programme.family_id for programme in programmes],
        }
        if mode == "jev":
            from repairclaim_api.jev import MODEL
            from repairclaim_api.jevmodel import route_config

            context.update(
                {
                    "destination": "vercel_ai_gateway_jev",
                    "model": MODEL,
                    "programmes": [programme.model_dump(mode="json") for programme in programmes],
                }
            )
            destination, model = route_config()
            context.update(destination=destination, model=model)
        if len(canonical(context)) > 80000:
            raise DomainError("analysis_context_limit", 413)
        return context

    def analysis_preview(self, token, case_id, *, mode="codex"):
        if mode not in {"codex", "jev"}:
            raise DomainError("invalid_analysis_mode", 422)
        with self._transaction() as db:
            case = self._case(db, self._actor(db, token), case_id, "owner")
            context = self._analysis_context(db, case, mode=mode)
            return {
                "context": context,
                "fingerprint": fingerprint(context),
                "estimated_input_tokens": (len(canonical(context)) + 3) // 4,
                "actual_billing": "unknown_until_provider_receipt",
            }

    def reserve_attempt(self, item):
        with self._transaction() as db:
            current = self._object(db, item["id"])
            actor = self._job_actor(db, current)
            if (
                current["state"] != "running"
                or current["data"].get("lease") != item["data"].get("lease")
                or current["data"].get("lease_until", 0) <= self._now()
                or current["data"].get("stale")
                or current["data"]["deadline"] <= self._now()
                or len(current["data"]["attempts"]) >= current["data"]["allowance"]
            ):
                raise DomainError("attempt_not_authorized", 409)
            case = self._case(db, actor, current["case_id"], "owner")
            if fingerprint(
                self._analysis_context(db, case, mode=current["data"]["mode"])
            ) != fingerprint(current["data"]["approved_context"]):
                raise DomainError("egress_context_changed", 409)
            name = identifier()
            current["data"]["lease_until"] = self._now() + 180
            current["data"]["attempts"].append(
                {
                    "id": name,
                    "status": "reserved",
                    "started": self._now(),
                    "input_tokens": None,
                    "output_tokens": None,
                    "cost": None,
                }
            )
            self._update_object(db, current)
            self._audit(db, actor, case, "provider_attempt_reserved")
            return name

    def settle_attempt(self, item, attempt_id, status, reason, *, receipt=None):
        with self._transaction() as db:
            try:
                current = self._object(db, item["id"])
                actor = self._job_actor(db, current)
            except DomainError:
                return False
            if (
                current["state"] != "running"
                or current["data"].get("lease") != item["data"].get("lease")
                or current["data"].get("lease_until", 0) <= self._now()
            ):
                return False
            attempt = next(
                (attempt for attempt in current["data"]["attempts"] if attempt["id"] == attempt_id),
                None,
            )
            if attempt is None or attempt["status"] != "reserved":
                raise DomainError("attempt_receipt_conflict", 409)
            attempt.update({"status": status, "reason": reason, "finished": self._now()})
            if receipt is not None:
                attempt.update(
                    {
                        "input_tokens": receipt["input_tokens"],
                        "output_tokens": receipt["output_tokens"],
                        "cost": receipt["cost_usd"],
                        "model": receipt["model"],
                        "generation_id": receipt["generation_id"],
                    }
                )
            self._update_object(db, current)
            case = self._case(db, actor, current["case_id"], "edit")
            self._audit(
                db, actor, case, "validation_failure" if status == "validation_failure" else status
            )
            return True

    def acknowledge_unknown_usage(self, token, job_id, reason):
        if not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 500:
            raise DomainError("acknowledgement_reason_required", 422)
        with self._transaction() as db:
            actor = self._actor(db, token)
            item, case = self._scoped_object(db, actor, job_id, "job", "owner")
            item["data"]["unknown_usage_acknowledged"] = {
                "actor_id": actor["id"],
                "at": self._now(),
                "reason": reason,
            }
            self._update_object(db, item)
            self._audit(db, actor, case, "unknown_usage_acknowledged_not_priced")

    def resume_job(self, token, job_id):
        with self._transaction() as db:
            actor = self._actor(db, token)
            item, case = self._scoped_object(db, actor, job_id, "job", "edit")
            if item["state"] not in {"partial", "awaiting_authority"} or item["data"].get("stale"):
                raise DomainError("job_not_resumable", 409)
            if (
                item["data"].get("mode") in {"codex", "jev"}
                and (
                    item["data"].get("error", "").endswith("unknown_usage")
                    or any(attempt["status"] == "reserved" for attempt in item["data"]["attempts"])
                )
                and not item["data"].get("unknown_usage_acknowledged")
            ):
                raise DomainError("unknown_usage_hold", 409)
            if case["revision"] != item["data"]["case_revision"]:
                raise DomainError("stale_artifact", 409)
            # A resume never resets attempts or extends the original active deadline.
            if item["data"]["deadline"] <= self._now():
                raise DomainError("deadline_exceeded", 409)
            item["data"]["auth_hash"] = hashlib.sha256(token.encode()).hexdigest()
            item["data"]["creator_id"] = actor["id"]
            item["data"].pop("lease", None)
            self._update_object(db, item, state="queued")
            self._audit(db, actor, case, "job_resumed")
            return self._public(item)

    def answer_question(self, token, job_id, answer):
        if answer not in {"unknown", "later", "answered"}:
            raise DomainError("invalid_answer", 422)
        with self._transaction() as db:
            actor = self._actor(db, token)
            item, case = self._scoped_object(db, actor, job_id, "job", "edit")
            if not item["data"].get("result", {}).get("next_question"):
                raise DomainError("question_not_available", 409)
            item["data"]["question_answer"] = answer
            self._update_object(db, item)
            self._audit(db, actor, case, "question_" + answer)

    def set_case_state(self, token, case_id, state, expected_revision):
        if state not in {"closed", "fact_review", "paused"}:
            raise DomainError("invalid_case_state", 422)
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "owner")
            self._revision(case, expected_revision)
            self._bump_case(db, actor, case, "case_" + state)
            db.execute("UPDATE cases SET lifecycle=? WHERE id=?", (state, case_id))
            if state in {"closed", "paused"}:
                db.execute(
                    "UPDATE rc_objects SET state='cancelled' WHERE case_id=? AND kind='job' AND state IN ('queued','running')",
                    (case_id,),
                )
            return {"id": case_id, "lifecycle": state, "revision": case["revision"]}

    def check_sources(self, *, parser, fetcher=None):
        from repairclaim_api.sources import SourceFetcher

        fetcher = fetcher or SourceFetcher()
        with self._transaction() as db:
            rows = [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM rc_sources WHERE updated<? ORDER BY updated LIMIT 25",
                    (self._now() - 86400,),
                )
            ]
        transferred, checked = 0, 0
        for row in rows:
            if transferred >= 100 * 1024 * 1024:
                break
            result = None
            for _ in range(3):
                try:
                    result = fetcher.fetch(row["url"])
                    transferred += len(result["body"])
                    break
                except DomainError:
                    continue
            if result is None:
                with self._transaction() as db:
                    db.execute(
                        "UPDATE rc_sources SET state='unavailable',updated=? WHERE id=?",
                        (self._now(), row["id"]),
                    )
                    self._invalidate(db)
                continue
            try:
                parsed = parser.run("parse", result["body"], "programme.pdf")
                self.capture_source(row["id"], result["url"], result["body"], parsed)
                checked += 1
            except DomainError:
                with self._transaction() as db:
                    db.execute(
                        "UPDATE rc_sources SET state='review_required',updated=? WHERE id=?",
                        (self._now(), row["id"]),
                    )
                    self._invalidate(db)
        return {"checked": checked, "bytes": transferred}
