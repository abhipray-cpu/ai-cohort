"""Verified local backups and new-root quarantined restore. Protect the output volume."""

import json
import shutil
import sqlite3
import time
from pathlib import Path

from . import journal
from .consensus import canonical, digest
from .evidence import sha
from .store import Store, ident


def verify_audit(db):
    previous = "genesis"
    for row in db.execute("SELECT * FROM audit ORDER BY seq"):
        body = {
            "workspace": row["workspace"],
            "case_id": row["case_id"],
            "actor": row["actor"],
            "action": row["action"],
            "detail": json.loads(row["detail"]),
            "occurred": row["occurred"],
            "previous": row["previous"],
        }
        if row["previous"] != previous or digest(body) != row["hash"]:
            raise ValueError("audit integrity")
        previous = row["hash"]
    return previous


def backup(store, destination):
    destination = Path(destination).resolve()
    manifest_path = destination.with_suffix(destination.suffix + ".manifest.json")
    if destination.exists() or manifest_path.exists() or destination.suffix != ".sqlite3":
        raise ValueError("new .sqlite3 target required")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive target creation prevents accidentally overwriting another backup.
    with destination.open("xb"):
        pass
    with store.connect() as source, sqlite3.connect(destination) as target:
        source.backup(target)
        target.execute("PRAGMA journal_mode=DELETE")
    with sqlite3.connect(destination) as db:
        db.row_factory = sqlite3.Row
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("backup integrity")
        meta = dict(db.execute("SELECT * FROM meta WHERE id=1").fetchone())
        head = verify_audit(db)
        for row in db.execute("SELECT body,raw FROM sources"):
            value = json.loads(row["body"])
            if (
                sha(bytes(row["raw"])) != value["original_hash"]
                or sha(value["text"].encode()) != value["text_hash"]
            ):
                raise ValueError("source integrity")
    manifest = {
        **meta,
        "audit_head": head,
        "sha256": sha(destination.read_bytes()),
        "created": time.time(),
        "scope": "plaintext SQLite snapshot; source BLOBs included; external usage authority must be retained separately",
    }
    with manifest_path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(manifest, indent=2) + "\n")
    return manifest


def restore(source, target_root, authority_path=None):
    source = Path(source).resolve()
    target_root = Path(target_root).resolve()
    if target_root.exists():
        raise ValueError("restore requires a new nonexistent data directory")
    if any(Path(str(source) + suffix).exists() for suffix in ("-wal", "-journal")):
        raise ValueError("backup must be a sealed standalone artifact, without a live journal")
    manifest = json.loads(source.with_suffix(source.suffix + ".manifest.json").read_text())
    if sha(source.read_bytes()) != manifest["sha256"]:
        raise ValueError("backup digest mismatch")
    with sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        if (
            db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
            or verify_audit(db) != manifest["audit_head"]
        ):
            raise ValueError("backup integrity")
        meta = dict(db.execute("SELECT * FROM meta WHERE id=1").fetchone())
        if meta["schema_version"] != 2 or meta["store_id"] != manifest["store_id"]:
            raise ValueError("unsupported backup schema")
    authority = Path(authority_path) if authority_path else source.parent / "NONEXISTENT_AUTHORITY"
    head, events = journal.read(authority, meta["store_id"])
    if manifest["journal_head"] != "genesis" and not any(
        digest(e) == manifest["journal_head"] for e in events
    ):
        raise ValueError("current usage authority required; database rollback alone is unsafe")
    target_root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source, target_root / "casecouncil.sqlite3")
    if authority.exists():
        (target_root / "authority").mkdir()
        shutil.copyfile(authority, target_root / "authority" / "usage.jsonl")
    store = Store(target_root)
    with store.write() as db:
        db.execute(
            "UPDATE meta SET epoch=?,journal_head=?,quarantine=1 WHERE id=1", (ident(), head)
        )
        db.execute("DELETE FROM sessions")
        db.execute("UPDATE jobs SET state='stale',token=NULL,lease_until=0")
        db.execute(
            "UPDATE workspaces SET hold='restore quarantine: verify external usage authority'"
        )
        store.record(
            db,
            "operator",
            "restore_quarantined",
            detail={"source_hash": manifest["sha256"], "authority_head": head},
        )
    return {"data_root": str(target_root), "quarantine": True, "authority_head": head}


def authorize_restored_runtime(store, expected_head, reason):
    from .recovery import checked_evidence, checked_incident, unsafe

    if len(reason) < 10:
        raise ValueError("operator verification reason required")
    with store.write() as db:
        meta = db.execute("SELECT * FROM meta WHERE id=1").fetchone()
        if not meta["quarantine"]:
            raise ValueError("store is not quarantined")
        head, events = journal.read(store.journal_path, meta["store_id"])
        if head != expected_head or head != meta["journal_head"]:
            raise ValueError("authority head changed")
        reservations = {e["attempt"] for e in events if e["kind"] == "reserved"}
        settlements = {e["attempt"]: e["receipt"] for e in events if e["kind"] == "settled"}
        if not reservations <= set(settlements):
            raise ValueError("unknown or unsafe usage remains unresolved")
        reconciliations = {
            e["reconciliation"]["attempt_id"]: e["reconciliation"]
            for e in events
            if e["kind"] == "attempt_reconciled"
        }
        incidents = {
            e["incident"]["attempt_id"]: e["incident"]
            for e in events
            if e["kind"] == "incident_closed"
        }
        reserved = {e["attempt"]: e for e in events if e["kind"] == "reserved"}
        for aid, receipt in settlements.items():
            if unsafe(receipt):
                raise ValueError("explicit unsafe tool incident requires investigation")
            if isinstance(receipt.get("usage"), dict) and receipt.get("tools_audited"):
                continue
            if aid in incidents:
                incident = incidents[aid]
                attempt = db.execute("SELECT * FROM attempts WHERE id=?", (aid,)).fetchone()
                checked_incident(
                    attempt
                    or {
                        "id": aid,
                        "prompt_hash": incident["prompt_hash"],
                        "receipt": canonical(receipt),
                        "reserved": reserved[aid]["reserved_seconds"],
                    },
                    incident,
                    events,
                )
                if attempt:
                    previous = db.execute(
                        "SELECT hash FROM attempt_incidents WHERE attempt_id=?", (aid,)
                    ).fetchone()
                    if previous and previous[0] != digest(incident):
                        raise ValueError("incident differs from current authority")
                    db.execute(
                        "INSERT OR IGNORE INTO attempt_incidents VALUES(?,?,?,?)",
                        (
                            incident["id"],
                            aid,
                            canonical(incident),
                            digest(incident),
                        ),
                    )
                continue
            proof = reconciliations.get(aid)
            if (
                not proof
                or proof["original_receipt_hash"] != digest(receipt)
                or receipt.get("diagnostic", {}).get("unsafe_tool_event")
                or receipt.get("diagnostic", {}).get("category") == "unsafe_tool"
            ):
                raise ValueError("unknown or unsafe usage remains unresolved")
            attempt = db.execute("SELECT * FROM attempts WHERE id=?", (aid,)).fetchone()
            checked_evidence(
                attempt or {"id": aid, "prompt_hash": proof["prompt_hash"]},
                {
                    "attempt_id": aid,
                    "prompt_hash": proof["prompt_hash"],
                    "receipt": proof["receipt"],
                },
            )
            if attempt:
                previous = db.execute(
                    "SELECT hash FROM attempt_reconciliations WHERE attempt_id=?", (aid,)
                ).fetchone()
                if previous and previous[0] != digest(proof):
                    raise ValueError("reconciliation differs from current authority")
                db.execute(
                    "INSERT OR IGNORE INTO attempt_reconciliations VALUES(?,?,?,?)",
                    (proof["id"], aid, canonical(proof), digest(proof)),
                )
        for aid, receipt in settlements.items():
            db.execute(
                "UPDATE attempts SET receipt=? WHERE id=? AND receipt IS NULL",
                (canonical(receipt), aid),
            )
        db.execute("UPDATE meta SET quarantine=0")
        db.execute(
            "UPDATE workspaces SET hold=NULL WHERE hold='restore quarantine: verify external usage authority'"
        )
        store.record(
            db,
            "operator",
            "restore_runtime_authorized",
            detail={"head": head, "reason_hash": digest(reason), "past_jobs_remain_stale": True},
        )
        journal.append(
            db,
            store.journal_path,
            {"kind": "restore_authorized", "occurred": time.time(), "reason_hash": digest(reason)},
        )
    return {"authorized": True, "past_jobs_restarted": False}
