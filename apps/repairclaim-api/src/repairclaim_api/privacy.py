"""Scoped export, durable erasure barriers, invitation tokens and account removal."""

import hashlib
import io
import json
import os
import secrets
import zipfile

from repairclaim_api.errors import DomainError
from repairclaim_api.feature_utils import canonical


class PrivacyMixin:
    def _erased(self, case_id):
        path = self.path.parent / "erasure.jsonl"
        if not path.exists():
            return False
        if path.is_symlink():
            raise DomainError("erasure_ledger_invalid", 503)
        stat = path.stat()
        marker = (stat.st_mtime_ns, stat.st_size)
        if marker != getattr(self, "_erasure_cache_marker", None):
            if stat.st_size > 8 * 1024 * 1024:
                raise DomainError("erasure_ledger_invalid", 503)
            try:
                self._erasure_cache = {
                    json.loads(line).get("case_id")
                    for line in path.read_text().splitlines()
                    if line
                }
            except (ValueError, KeyError, OSError) as error:
                raise DomainError("erasure_ledger_invalid", 503) from error
            self._erasure_cache_marker = marker
        return case_id in self._erasure_cache

    def _ledger_append(self, household_id, case_id):
        record = canonical({"household_id": household_id, "case_id": case_id, "at": self._now()})
        descriptor = os.open(
            self.path.parent / "erasure.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600
        )
        with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
            stream.write(record + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _erase_features(self, db, case, *, record=True):
        if record:
            self._ledger_append(case["household_id"], case["id"])
        for row in db.execute(
            "SELECT data FROM rc_objects WHERE household_id=? AND case_id=?",
            (case["household_id"], case["id"]),
        ).fetchall():
            data = json.loads(row[0])
            for key in ("blob_id", "zip_blob", "pdf_blob"):
                name = data.get(key)
                if (
                    isinstance(name, str)
                    and len(name) == 32
                    and all(char in "0123456789abcdef" for char in name)
                ):
                    (self.blob_dir / name).unlink(missing_ok=True)
        db.execute(
            "DELETE FROM rc_objects WHERE household_id=? AND case_id=?",
            (case["household_id"], case["id"]),
        )
        db.execute("DELETE FROM rc_case_keys WHERE case_id=?", (case["id"],))

    def apply_erasure_ledger(self):
        ledger = self.path.parent / "erasure.jsonl"
        if not ledger.exists():
            descriptor = os.open(ledger, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
        if ledger.is_symlink() or ledger.stat().st_size > 8 * 1024 * 1024:
            raise DomainError("erasure_ledger_invalid", 503)
        try:
            records = [json.loads(line) for line in ledger.read_text().splitlines() if line]
            with self._transaction() as db:
                for record in records:
                    if record.get("type") == "account":
                        user_id = record.get("user_id", "")
                        if len(user_id) != 32 or any(
                            char not in "0123456789abcdef" for char in user_id
                        ):
                            raise ValueError()
                        for case_row in db.execute(
                            "SELECT * FROM cases WHERE household_id=? AND deleted=0",
                            (record["household_id"],),
                        ).fetchall():
                            self._erase_features(db, dict(case_row), record=False)
                            db.execute("DELETE FROM grants WHERE case_id=?", (case_row["id"],))
                            db.execute(
                                "DELETE FROM fact_revisions WHERE case_id=?", (case_row["id"],)
                            )
                            db.execute(
                                "UPDATE cases SET deleted=1,title='' WHERE id=?", (case_row["id"],)
                            )
                        db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
                        db.execute("DELETE FROM grants WHERE user_id=?", (user_id,))
                        db.execute(
                            "UPDATE users SET username=?,password_hash='',password_salt='' WHERE id=?",
                            ("deleted-" + user_id, user_id),
                        )
                        db.execute(
                            "UPDATE vehicles SET make='',model='',model_year=1980 WHERE household_id=?",
                            (record["household_id"],),
                        )
                        continue
                    if any(
                        not isinstance(record.get(key), str)
                        or len(record[key]) != 32
                        or any(char not in "0123456789abcdef" for char in record[key])
                        for key in ("case_id", "household_id")
                    ):
                        raise ValueError()
                    case = db.execute(
                        "SELECT * FROM cases WHERE id=? AND household_id=?",
                        (record["case_id"], record["household_id"]),
                    ).fetchone()
                    if case:
                        self._erase_features(db, dict(case), record=False)
                        db.execute("DELETE FROM grants WHERE case_id=?", (case["id"],))
                        db.execute("DELETE FROM fact_revisions WHERE case_id=?", (case["id"],))
                        db.execute("UPDATE cases SET deleted=1,title='' WHERE id=?", (case["id"],))
        except (ValueError, KeyError, OSError) as error:
            raise DomainError("erasure_ledger_invalid", 503) from error

    def private_orphans(self):
        with self._transaction() as db:
            references = set()
            for row in db.execute("SELECT data FROM rc_objects"):
                data = json.loads(row[0])
                references.update(
                    data[key] for key in ("blob_id", "zip_blob", "pdf_blob") if data.get(key)
                )
            references.update(row[0] for row in db.execute("SELECT blob_id FROM rc_captures"))
            return sorted(
                path.name
                for path in self.blob_dir.iterdir()
                if path.is_file() and path.name not in references
            )

    def export_case(self, token, case_id):
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "owner")
            items = [
                self._object(db, row[0])
                for row in db.execute(
                    "SELECT id FROM rc_objects WHERE household_id=? AND case_id=?",
                    (case["household_id"], case_id),
                )
            ]
            revisions = [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT snapshot_json FROM fact_revisions WHERE household_id=? AND case_id=? ORDER BY revision",
                    (case["household_id"], case_id),
                )
            ]
            body = {
                "type": "PRIVATE_CASE_DATA_EXPORT_NOT_APPROVED_CORRESPONDENCE",
                "case": case,
                "revisions": revisions,
                "records": [self._public(item) for item in items],
            }
            bundle = io.BytesIO()
            with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("case.json", canonical(body))
                for item in items:
                    if item["kind"] == "document":
                        name = (
                            "documents/"
                            + item["id"]
                            + "."
                            + item["data"]["filename"].rsplit(".", 1)[-1]
                        )
                        archive.writestr(name, self._blob_read(item["data"]["blob_id"]))
            if bundle.tell() > 250 * 1024 * 1024:
                raise DomainError("export_limit", 413)
            self._audit(db, actor, case, "private_case_exported")
            return bundle.getvalue()

    def create_invitation(self, token, case_id, role, *, ttl=86400):
        if role not in {"viewer", "editor"} or type(ttl) is not int or not 0 < ttl <= 86400:
            raise DomainError("invalid_invitation", 422)
        raw = secrets.token_urlsafe(32)
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "owner")
            item = self._new_object(
                db,
                case,
                "invitation",
                {
                    "token_hash": hashlib.sha256(raw.encode()).hexdigest(),
                    "role": role,
                    "expires": self._now() + ttl,
                },
                "available",
            )
            db.execute(
                "INSERT INTO rc_invite_lookup VALUES(?,?)",
                (hashlib.sha256(raw.encode()).hexdigest(), item["id"]),
            )
            self._audit(db, actor, case, "case_invitation_created")
            return {"id": item["id"], "token": raw, "role": role, "expires": self._now() + ttl}

    def accept_invitation(self, token, invitation):
        if not isinstance(invitation, str) or len(invitation) > 128:
            raise DomainError("invitation_invalid", 404)
        digest = hashlib.sha256(invitation.encode()).hexdigest()
        with self._transaction() as db:
            actor = self._actor(db, token)
            row = db.execute(
                "SELECT object_id FROM rc_invite_lookup WHERE token_hash=?", (digest,)
            ).fetchone()
            if row is None:
                raise DomainError("invitation_invalid", 404)
            item = self._object(db, row[0])
            case = db.execute(
                "SELECT * FROM cases WHERE id=? AND deleted=0", (item["case_id"],)
            ).fetchone()
            if (
                case is None
                or item["state"] != "available"
                or item["data"]["expires"] <= self._now()
                or case["household_id"] == actor["household_id"]
            ):
                raise DomainError("invitation_invalid", 404)
            db.execute(
                "INSERT OR REPLACE INTO grants VALUES(?,?,?,?,?)",
                (
                    case["household_id"],
                    case["id"],
                    actor["id"],
                    item["data"]["role"],
                    self._now() + 90 * 86400,
                ),
            )
            self._update_object(db, item, state="used")
            self._audit(db, actor, dict(case), "case_invitation_accepted")
            return {"case_id": case["id"], "role": item["data"]["role"]}

    def erase_account(self, token, confirmation):
        if confirmation != "DELETE MY ACCOUNT":
            raise DomainError("deletion_confirmation_required", 422)
        with self._transaction() as db:
            actor = self._actor(db, token)
            descriptor = os.open(
                self.path.parent / "erasure.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600
            )
            with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
                stream.write(
                    canonical(
                        {
                            "type": "account",
                            "user_id": actor["id"],
                            "household_id": actor["household_id"],
                            "at": self._now(),
                        }
                    )
                    + "\n"
                )
                stream.flush()
                os.fsync(stream.fileno())
            for row in db.execute(
                "SELECT * FROM cases WHERE household_id=? AND deleted=0", (actor["household_id"],)
            ).fetchall():
                case = dict(row)
                self._erase_features(db, case)
                db.execute("DELETE FROM grants WHERE case_id=?", (case["id"],))
                db.execute("DELETE FROM fact_revisions WHERE case_id=?", (case["id"],))
                db.execute(
                    "UPDATE cases SET deleted=1,title='',revision=revision+1 WHERE id=?",
                    (case["id"],),
                )
            db.execute("DELETE FROM sessions WHERE user_id=?", (actor["id"],))
            db.execute("DELETE FROM grants WHERE user_id=?", (actor["id"],))
            db.execute(
                "UPDATE vehicles SET make='',model='',model_year=1980 WHERE household_id=?",
                (actor["household_id"],),
            )
            db.execute(
                "UPDATE users SET username=?,password_hash='',password_salt='' WHERE id=?",
                ("deleted-" + actor["id"], actor["id"]),
            )
        self.compact_private_state()

    def compact_private_state(self):
        with self._connection() as db:
            result = db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            return {
                "checkpoint_busy": bool(result[0]),
                "backup_expiry_days": 30,
                "external_copies_recallable": False,
            }

    def create_backup(self, password):
        from repairclaim_api.operations import create_backup

        return create_backup(self, password)

    def activate_restored(self):
        self.apply_erasure_ledger()
        with self._transaction() as db:
            db.execute("UPDATE rc_meta SET value='0' WHERE key='quarantined'")

    def maintenance(self):
        self.apply_erasure_ledger()
        with self._transaction() as db:
            for row in db.execute(
                "SELECT * FROM cases WHERE deleted=0 AND retention_until>0 AND retention_until<=?",
                (self._now(),),
            ).fetchall():
                case = dict(row)
                self._erase_features(db, case)
                db.execute("DELETE FROM grants WHERE case_id=?", (case["id"],))
                db.execute("DELETE FROM fact_revisions WHERE case_id=?", (case["id"],))
                db.execute(
                    "UPDATE cases SET deleted=1,title='',revision=revision+1 WHERE id=?",
                    (case["id"],),
                )
        for name in self.private_orphans():
            path = self.blob_dir / name
            if path.stat().st_mtime < self._now() - 86400:
                path.unlink(missing_ok=True)
        backup_dir = self.path.parent / "backups"
        if backup_dir.is_dir() and not backup_dir.is_symlink():
            for path in backup_dir.iterdir():
                if (
                    path.name.startswith("repairclaim-")
                    and path.suffix == ".rcbk"
                    and path.is_file()
                    and not path.is_symlink()
                    and path.stat().st_mtime < self._now() - 30 * 86400
                ):
                    path.unlink()
        return self.compact_private_state()

    def tick(self):
        self.maintenance()
        with self._transaction() as db:
            db.execute(
                "INSERT OR REPLACE INTO rc_meta VALUES('worker_heartbeat',?)", (str(self._now()),)
            )
            for row in db.execute(
                "SELECT * FROM rc_objects WHERE kind='reminder' AND state='scheduled'"
            ).fetchall():
                item = {**dict(row), "data": json.loads(row["data"])}
                if item["data"]["due_at"] <= self._now():
                    case = db.execute(
                        "SELECT * FROM cases WHERE id=? AND deleted=0 AND retention_until>?",
                        (item["case_id"], self._now()),
                    ).fetchone()
                    if case:
                        self._update_object(db, item, state="due")
                        actor = db.execute(
                            "SELECT id FROM users WHERE household_id=? ORDER BY id LIMIT 1",
                            (case["household_id"],),
                        ).fetchone()
                        if actor:
                            db.execute(
                                "INSERT INTO audit(household_id,case_id,actor_id,action,revision,created) VALUES(?,?,?,'reminder_due',?,?)",
                                (
                                    case["household_id"],
                                    case["id"],
                                    actor[0],
                                    case["revision"],
                                    self._now(),
                                ),
                            )
        return self.rematch_monitoring()
