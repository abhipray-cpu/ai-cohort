"""Filesystem-operator recovery. Deliberately absent from the public HTTP surface."""

import json
import os
import sqlite3
from pathlib import Path

from .core import canonical, digest
from .errors import Conflict
from .runtime import runtime_lock


class Operations:
    def release_quarantine(self, actor, expected_head, evidence_ref, key):
        if not 1 <= len(evidence_ref) <= 2000:
            raise ValueError("restore verification evidence required")
        with runtime_lock(self.root) as acquired:
            if not acquired:
                raise Conflict("stop runtime before restore release")
            self.verify_integrity()
            with self.db() as db:
                for workspace in db.execute("SELECT id FROM workspaces"):
                    self._role(db, actor, workspace[0], {"owner"})
                if (
                    self.journal_head() != expected_head
                    or self._liability(db, ignore_quarantine=True)
                    or db.execute(
                        "SELECT 1 FROM tasks WHERE state IN ('queued','running')"
                    ).fetchone()
                ):
                    raise Conflict("restore authority, accounting or runtime not reconciled")
                self._intent(
                    db,
                    actor,
                    "store",
                    "restore-release",
                    key,
                    {"head": expected_head, "evidence": evidence_ref},
                )
                self._append_journal(
                    {
                        "event": "restore_enabled",
                        "actor": actor,
                        "previous_head": expected_head,
                        "evidence": evidence_ref,
                    }
                )
                db.execute("DELETE FROM controls WHERE key='quarantine'")
                self._audit(db, "restore_enabled", actor=actor, body={"evidence": evidence_ref})
                return True

    def journal_head(self):
        return self._journal_records()[1]

    def verify_integrity(self):
        with self.db() as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise Conflict("database integrity failure")
            artifacts = db.execute("SELECT * FROM artifacts").fetchall()
            for artifact in artifacts:
                if digest(json.loads(artifact["body"])) != artifact["hash"]:
                    raise Conflict("artifact integrity failure")
            for task in db.execute("SELECT fact_json,fact_hash FROM tasks"):
                if digest(json.loads(task[0])) != task[1]:
                    raise Conflict("fact integrity failure")
            for source in db.execute("SELECT raw,frozen FROM imports"):
                frozen = json.loads(source[1])
                if (
                    digest(source[0]) != frozen["raw_hash"]
                    or digest(frozen["facts"]) != frozen["fact_hash"]
                ):
                    raise Conflict("source integrity failure")
            self._journal_records()
            return {"artifact_count": len(artifacts), "journal_head": self.journal_head()}

    def backup(self, destination):
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=False)
        with runtime_lock(self.root) as acquired:
            if not acquired:
                raise Conflict("stop worker before backup")
            integrity = self.verify_integrity()
            with self.db() as db:
                # Separate read connection provides SQLite's online backup semantics while
                # the write lock freezes DB+journal operations from cooperating processes.
                with (
                    sqlite3.connect(self.path) as source,
                    sqlite3.connect(destination / "shelfproof.sqlite3") as target,
                ):
                    source.backup(target)
                journal = self.journal.read_bytes() if self.journal.exists() else b""
                (destination / "usage.jsonl").write_bytes(journal)
                manifest = {
                    **integrity,
                    "schema": "shelfproof-backup-v1",
                    "created": self.now(),
                    "database_hash": digest((destination / "shelfproof.sqlite3").read_bytes()),
                    "journal_hash": digest(journal),
                    "encryption": "none-protect-at-rest",
                }
                (destination / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
                for path in destination.iterdir():
                    with path.open("rb") as file:
                        os.fsync(file.fileno())
                self._audit(db, "backup_created", body={"manifest_hash": digest(manifest)})
        return manifest

    @classmethod
    def restore(cls, backup, destination, current_journal):
        backup, destination, current_journal = (
            Path(backup),
            Path(destination),
            Path(current_journal),
        )
        manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
        db_bytes, old_journal = (
            (backup / "shelfproof.sqlite3").read_bytes(),
            (backup / "usage.jsonl").read_bytes(),
        )
        if (
            digest(db_bytes) != manifest["database_hash"]
            or digest(old_journal) != manifest["journal_hash"]
        ):
            raise Conflict("backup hash mismatch")
        authority = current_journal.read_bytes() if current_journal.exists() else b""
        if not authority.startswith(old_journal):
            raise Conflict("current independent authority is not a descendant of backup")
        destination.mkdir(parents=True, exist_ok=False)
        (destination / "shelfproof.sqlite3").write_bytes(db_bytes)
        (destination / "usage.jsonl").write_bytes(authority)
        restored = cls(destination)
        restored.verify_integrity()
        with restored.db() as db:
            for event in restored._journal_records()[0]:
                if event.get("event") == "source_erased":
                    for task in event["tasks"]:
                        for table in (
                            "artifacts",
                            "reviews",
                            "snapshots",
                            "task_links",
                            "selections",
                        ):
                            db.execute(f"DELETE FROM {table} WHERE task=?", (task,))
                        db.execute("DELETE FROM tasks WHERE id=?", (task,))
                        db.execute("DELETE FROM audit WHERE task=?", (task,))
                    db.execute("DELETE FROM imports WHERE id=?", (event["source"],))
                    db.execute("DELETE FROM batches WHERE source_id=?", (event["source"],))
                    db.execute(
                        "INSERT OR IGNORE INTO erased_sources VALUES(?,?)",
                        (event["source"], event["workspace"]),
                    )
            db.execute("DELETE FROM sessions")
            db.execute("DELETE FROM heartbeat")
            db.execute("UPDATE workspaces SET epoch=epoch+1")
            db.execute("UPDATE tasks SET state='stale',lease=NULL")
            db.execute("INSERT OR REPLACE INTO controls VALUES('quarantine','restore')")
            restored._audit(db, "restored_quarantined", body={"manifest": digest(manifest)})
        return restored

    def isolate_orphans(self, actor, isolation_evidence, expected_head):
        if not 1 <= len(isolation_evidence) <= 2000:
            raise ValueError("process-tree isolation evidence required")
        with runtime_lock(self.root) as acquired:
            if not acquired:
                raise Conflict("runtime must be stopped")
            with self.db() as db:
                if self.journal_head() != expected_head:
                    raise Conflict("journal head changed")
                rows = db.execute("SELECT * FROM tasks WHERE state='running'").fetchall()
                if any(row["lease_until"] > self.now() for row in rows):
                    raise Conflict("lease still live; verify isolation and allow expiry")
                for row in rows:
                    self._role(db, actor, row["workspace"], {"owner"})
                    for attempt in db.execute(
                        "SELECT * FROM attempts WHERE task=? AND status='reserved'", (row["id"],)
                    ).fetchall():
                        receipt = {
                            "audited": False,
                            "input_tokens": None,
                            "output_tokens": None,
                            "elapsed_ms": None,
                        }
                        self._append_journal(
                            {
                                "attempt": attempt["id"],
                                "task": row["id"],
                                "status": "unknown",
                                "receipt": receipt,
                                "isolation_ref": isolation_evidence,
                            }
                        )
                        db.execute(
                            "UPDATE attempts SET status='unknown',receipt=? WHERE id=?",
                            (canonical(receipt), attempt["id"]),
                        )
                    db.execute(
                        "UPDATE tasks SET state='manual_required',lease=NULL WHERE id=?",
                        (row["id"],),
                    )
                    self._audit(
                        db,
                        "orphan_isolated",
                        actor=actor,
                        task=row["id"],
                        body={"evidence": isolation_evidence},
                    )

    def resume(self, actor, task, selected_hash, key):
        with self.db() as db:
            row = self._task(db, task)
            self._role(db, actor, row["workspace"], {"owner"})
            payload = {"task": task, "selected": selected_hash}
            prior = self._intent(db, actor, row["workspace"], "resume", key, payload)
            if prior is not None:
                return prior
            if (
                row["state"] not in {"manual_required", "failed"}
                or row["selected_hash"] != selected_hash
                or not self._current(db, row)
                or self._liability(db, ignore_pause=True)
                or row["calls"] >= 16
                or row["claims"] >= 4
            ):
                raise Conflict("current bounded resumable context required")
            grant = db.execute("SELECT * FROM grants WHERE id=?", (row["grant_id"],)).fetchone()
            if grant["calls"] >= grant["max_calls"]:
                raise Conflict("grant exhausted")
            if db.execute("SELECT 1 FROM reviews WHERE task=?", (task,)).fetchone():
                raise Conflict("reviewed task cannot resume")
            db.execute(
                "UPDATE tasks SET state='queued',deadline=?,lease=NULL WHERE id=?",
                (min(self.now() + 1800, grant["expires"]), task),
            )
            pause = db.execute("SELECT value FROM controls WHERE key='dispatch_pause'").fetchone()
            if pause:
                if pause[0] != task:
                    raise Conflict("resume must target the accepted incident")
                db.execute("DELETE FROM controls WHERE key='dispatch_pause'")
            self._remember(db, actor, row["workspace"], "resume", key, payload, True)
            self._audit(
                db,
                "bounded_resume",
                actor=actor,
                task=task,
                body={"calls_retained": row["calls"], "claims_retained": row["claims"]},
            )
            return True

    def accept_incident(
        self, actor, task, expected_head, reason, isolation_evidence, acknowledge_unknown, key
    ):
        if (
            not acknowledge_unknown
            or not 1 <= len(reason) <= 2000
            or not 1 <= len(isolation_evidence) <= 2000
        ):
            raise ValueError(
                "explicit unknown-usage and historical-safety acknowledgement required"
            )
        with runtime_lock(self.root) as acquired:
            if not acquired:
                raise Conflict("stop and isolate runtime first")
            self.verify_integrity()
            with self.db() as db:
                row = self._task(db, task)
                self._role(db, actor, row["workspace"], {"owner"})
                payload = {
                    "task": task,
                    "head": expected_head,
                    "reason": reason,
                    "isolation": isolation_evidence,
                    "acknowledge_unknown": True,
                }
                prior = self._intent(db, actor, row["workspace"], "incident", key, payload)
                if prior is not None:
                    return prior
                records, _ = self._journal_records()
                if (
                    self.journal_head() != expected_head
                    or any(r.get("event") == "incident_accepted" for r in records)
                    or db.execute("SELECT 1 FROM controls WHERE key='quarantine'").fetchone()
                    or db.execute(
                        "SELECT 1 FROM tasks WHERE state IN ('running','queued')"
                    ).fetchone()
                    or db.execute("SELECT 1 FROM reviews WHERE task=?", (task,)).fetchone()
                ):
                    raise Conflict("incident policy preconditions not met")
                unknown = [a for a in row["attempts"] if a["status"] == "unknown"]
                if (
                    not unknown
                    or any(a["receipt"] and a["receipt"].get("unsafe_tool_event") for a in unknown)
                    or any(a["status"] == "reserved" for a in row["attempts"])
                ):
                    raise Conflict("no eligible irrecoverable unknown attempt")
                incident = digest(payload)
                body = {
                    "event": "incident_accepted",
                    "id": incident,
                    "task": task,
                    "attempts": [a["id"] for a in unknown],
                    "actor": actor,
                    "reason": reason,
                    "isolation": isolation_evidence,
                    "previous_head": expected_head,
                    "unknown_preserved": True,
                    "reservation_refunded": False,
                }
                self._append_journal(body)
                db.execute("INSERT INTO incidents VALUES(?,?,?)", (incident, task, canonical(body)))
                db.execute("INSERT OR REPLACE INTO controls VALUES('dispatch_pause',?)", (task,))
                self._remember(db, actor, row["workspace"], "incident", key, payload, incident)
                self._audit(
                    db, "incident_accepted", actor=actor, task=task, body={"incident": incident}
                )
                return incident

    def amend_grant(self, actor, workspace, grant, ceiling, expected_head, reason, key):
        if type(ceiling) is not int or not 1 <= ceiling <= 100000 or not 1 <= len(reason) <= 2000:
            raise ValueError("invalid explicit grant amendment")
        with self.db() as db:
            self._role(db, actor, workspace, {"owner"})
            payload = {"grant": grant, "ceiling": ceiling, "head": expected_head, "reason": reason}
            prior = self._intent(db, actor, workspace, "amend", key, payload)
            if prior is not None:
                return prior
            if self.journal_head() != expected_head:
                raise Conflict("journal head changed")
            row = db.execute(
                "SELECT * FROM grants WHERE id=? AND workspace=?", (grant, workspace)
            ).fetchone()
            if not row or ceiling <= row["max_calls"]:
                raise Conflict("ceiling must grow without resetting usage")
            self._append_journal(
                {
                    "event": "grant_amended",
                    "grant": grant,
                    "ceiling": ceiling,
                    "old_ceiling": row["max_calls"],
                    "spent": row["calls"],
                    "actor": actor,
                    "reason": reason,
                }
            )
            db.execute("UPDATE grants SET max_calls=? WHERE id=?", (ceiling, grant))
            self._remember(db, actor, workspace, "amend", key, payload, True)
            self._audit(db, "grant_amended", actor=actor, workspace=workspace, body=payload)
            return True

    def reconcile_receipt(self, actor, attempt, expected_head, receipt, evidence_ref, key):
        if (
            set(receipt) != {"audited", "input_tokens", "output_tokens"}
            or receipt["audited"] is not True
            or any(
                type(receipt[k]) is not int or not 0 <= receipt[k] <= 10**9
                for k in ("input_tokens", "output_tokens")
            )
            or not 1 <= len(evidence_ref) <= 2000
        ):
            raise ValueError("bounded independently verified audited receipt required")
        with runtime_lock(self.root) as acquired:
            if not acquired:
                raise Conflict("stop and isolate runtime first")
            self.verify_integrity()
            with self.db() as db:
                original = db.execute("SELECT * FROM attempts WHERE id=?", (attempt,)).fetchone()
                if not original:
                    raise Conflict("attempt unavailable")
                row = self._task(db, original["task"])
                self._role(db, actor, row["workspace"], {"owner"})
                payload = {
                    "attempt": attempt,
                    "head": expected_head,
                    "receipt": receipt,
                    "evidence": evidence_ref,
                }
                prior = self._intent(db, actor, row["workspace"], "reconcile", key, payload)
                if prior is not None:
                    return prior
                if (
                    self.journal_head() != expected_head
                    or original["status"] != "unknown"
                    or json.loads(original["receipt"] or "{}").get("unsafe_tool_event")
                    or db.execute(
                        "SELECT 1 FROM tasks WHERE state IN ('running','queued')"
                    ).fetchone()
                    or db.execute(
                        "SELECT 1 FROM supplements WHERE attempt=?", (attempt,)
                    ).fetchone()
                ):
                    raise Conflict("receipt reconciliation preconditions not met")
                body = {
                    "event": "receipt_reconciled",
                    "target_attempt": attempt,
                    "task": row["id"],
                    "original_receipt_hash": digest(original["receipt"].encode()),
                    "receipt": receipt,
                    "evidence_ref": evidence_ref,
                    "actor": actor,
                    "previous_head": expected_head,
                    "basis": "trusted-operator-independent-verification",
                    "reservation_refunded": False,
                }
                self._append_journal(body)
                db.execute("INSERT INTO supplements VALUES(?,?)", (attempt, canonical(body)))
                db.execute(
                    "INSERT OR REPLACE INTO controls VALUES('dispatch_pause',?)", (row["id"],)
                )
                self._remember(db, actor, row["workspace"], "reconcile", key, payload, True)
                self._audit(
                    db,
                    "receipt_reconciled",
                    actor=actor,
                    task=row["id"],
                    body={"attempt": attempt, "evidence": evidence_ref},
                )
                return True
