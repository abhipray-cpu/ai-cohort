"""Owned encrypted snapshots and new-directory quarantined restores."""

import base64
import hashlib
import io
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from repairclaim_api.errors import DomainError


def _cipher(password, salt):
    if not isinstance(password, str) or not 12 <= len(password.encode()) <= 256:
        raise DomainError("backup_passphrase_required", 422)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600000, 32)
    return Fernet(base64.urlsafe_b64encode(key))


def create_backup(store, password):
    import zipfile

    with tempfile.TemporaryDirectory(prefix="rc-backup-", dir=store.path.parent) as temporary:
        destination = Path(temporary) / "repairclaim.sqlite3"
        with store._transaction():
            # A separate read connection sees the committed snapshot while the
            # write reservation fences app writers and blob erasure during capture.
            with store._connection() as source, sqlite3.connect(destination) as output:
                source.backup(output)
            bundle = io.BytesIO()
            files = [
                ("repairclaim.sqlite3", destination),
                ("content.key", store.path.parent / "content.key"),
            ]
            files += [
                ("blobs/" + path.name, path)
                for path in store.blob_dir.iterdir()
                if path.is_file() and not path.is_symlink()
            ]
            if sum(path.stat().st_size for _, path in files) > 1024 * 1024 * 1024:
                raise DomainError("backup_capacity", 413)
            with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, path in files:
                    archive.write(path, name)
                archive.writestr(
                    "backup.json",
                    json.dumps(
                        {
                            "product": "repairclaim",
                            "version": 1,
                            "created": store._now(),
                            "erasure_ledger_required": True,
                        }
                    ),
                )
        salt = os.urandom(16)
        return b"RCBK1" + salt + _cipher(password, salt).encrypt(bundle.getvalue())


def restore_backup(data, password, target, erasure_ledger, *, clock=None):
    import zipfile

    from repairclaim_api.store import Store

    target, erasure_ledger = Path(target), Path(erasure_ledger)
    if target.exists() or target.is_symlink():
        raise DomainError("restore_target_exists", 409)
    if not erasure_ledger.is_file() or erasure_ledger.is_symlink():
        raise DomainError("current_erasure_ledger_required", 422)
    if len(data) > 1500 * 1024 * 1024 or not data.startswith(b"RCBK1"):
        raise DomainError("invalid_backup", 422)
    try:
        raw = _cipher(password, data[5:21]).decrypt(data[21:])
    except InvalidToken as error:
        raise DomainError("backup_decryption_failed", 403) from error
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rc-restore-", dir=target.parent) as temporary:
        stage = Path(temporary) / "state"
        stage.mkdir(mode=0o700)
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                if (
                    len(archive.infolist()) > 10000
                    or sum(item.file_size for item in archive.infolist()) > 1024 * 1024 * 1024
                ):
                    raise DomainError("backup_capacity", 413)
                names = set()
                for item in archive.infolist():
                    name = item.filename
                    allowed = name in {"repairclaim.sqlite3", "content.key", "backup.json"} or (
                        name.startswith("blobs/")
                        and len(name) == 38
                        and all(char in "0123456789abcdef" for char in name[6:])
                    )
                    if (
                        not allowed
                        or name in names
                        or (item.external_attr >> 16) & 0o170000 == 0o120000
                    ):
                        raise DomainError("invalid_backup_member", 422)
                    names.add(name)
                    path = stage / name
                    path.parent.mkdir(mode=0o700, exist_ok=True)
                    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(archive.read(item))
                if not {"repairclaim.sqlite3", "content.key", "backup.json"} <= names:
                    raise DomainError("incomplete_backup", 422)
                metadata = json.loads((stage / "backup.json").read_text())
                if metadata.get("product") != "repairclaim" or metadata.get("version") != 1:
                    raise DomainError("invalid_backup", 422)
            shutil.copyfile(erasure_ledger, stage / "erasure.jsonl")
            options = {"clock": clock} if clock else {}
            restored = Store(stage / "repairclaim.sqlite3", **options)
            with restored._transaction() as db:
                db.execute("UPDATE rc_meta SET value='1' WHERE key='quarantined'")
                db.execute("DELETE FROM sessions")
                db.execute(
                    "UPDATE rc_objects SET state='awaiting_authority' WHERE kind='job' AND state IN ('queued','running')"
                )
                for row in db.execute(
                    "SELECT id,data FROM rc_objects WHERE kind='packet'"
                ).fetchall():
                    value = json.loads(row["data"])
                    value.pop("approval", None)
                    value["stale"] = True
                    packet = restored._object(db, row["id"])
                    packet["data"] = value
                    restored._update_object(db, packet, state="draft")
            restored.compact_private_state()
            try:
                target.mkdir(mode=0o700)
            except FileExistsError as error:
                raise DomainError("restore_target_exists", 409) from error
            for child in stage.iterdir():
                child.rename(target / child.name)
        except (zipfile.BadZipFile, KeyError, ValueError) as error:
            raise DomainError("invalid_backup", 422) from error
    return Store(target / "repairclaim.sqlite3", **({"clock": clock} if clock else {}))
