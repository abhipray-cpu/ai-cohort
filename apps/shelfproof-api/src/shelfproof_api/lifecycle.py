"""Transactional batch, policy, human-edit, review-export and erasure operations."""

import csv
import io
import json
import secrets
from collections import Counter
from contextlib import nullcontext

from contracts.shelfproof import FactPack

from .core import canonical, code_fingerprint, digest
from .errors import Conflict, Forbidden


class Lifecycle:
    def _batch_binding(self, batch, workspace, frozen, rows, epoch, grant):
        return digest(
            {
                "batch": batch,
                "workspace": workspace,
                "source": frozen["fact_hash"],
                "raw_source": frozen["raw_hash"],
                "mapping": digest(frozen["mapping"]),
                "rows": rows,
                "epoch": epoch,
                "grant": grant,
                "protocol": "reflection-v1",
                "code_fingerprint": code_fingerprint(),
            }
        )

    def rights(self, actor, workspace):
        with self.db() as db:
            self._role(db, actor, workspace)
            return [
                dict(r)
                for r in db.execute(
                    "SELECT id,expires,max_calls,calls,egress FROM grants "
                    "WHERE workspace=? ORDER BY expires DESC LIMIT 100",
                    (workspace,),
                )
            ]

    def imports(self, actor, workspace):
        with self.db() as db:
            self._role(db, actor, workspace)
            return [
                {
                    "id": r["id"],
                    "created": r["created"],
                    "rows": len(json.loads(r["frozen"])["facts"]),
                    "fact_hash": json.loads(r["frozen"])["fact_hash"],
                }
                for r in db.execute(
                    "SELECT id,created,frozen FROM imports WHERE workspace=? ORDER BY created DESC LIMIT 50",
                    (workspace,),
                )
            ]

    def batches(self, actor, workspace):
        with self.db() as db:
            self._role(db, actor, workspace)
            ids = [
                r[0]
                for r in db.execute(
                    "SELECT id FROM batches WHERE workspace=? ORDER BY created DESC LIMIT 50",
                    (workspace,),
                )
            ]
        return [self.batch(actor, batch) for batch in ids]

    def _intent(self, db, actor, workspace, operation, key, payload):
        if not isinstance(key, str) or not 1 <= len(key) <= 128:
            raise ValueError("idempotency key required")
        row = db.execute(
            "SELECT * FROM idem WHERE actor=? AND workspace=? AND operation=? AND key=?",
            (actor, workspace, operation, key),
        ).fetchone()
        if row and row["hash"] != digest(payload):
            raise Conflict("conflicting idempotency key")
        return json.loads(row["result"]) if row else None

    def _remember(self, db, actor, workspace, operation, key, payload, result):
        db.execute(
            "INSERT INTO idem VALUES(?,?,?,?,?,?)",
            (actor, workspace, operation, key, digest(payload), canonical(result)),
        )

    def policy(self, actor, workspace):
        with self.db() as db:
            self._role(db, actor, workspace)
            row = db.execute(
                "SELECT * FROM policies WHERE workspace=? ORDER BY revision DESC LIMIT 1",
                (workspace,),
            ).fetchone()
            return (
                {**dict(row), "body": json.loads(row["body"])}
                if row
                else {
                    "revision": 0,
                    "body": {"brief": "Neutral factual copy."},
                    "hash": digest({"brief": "Neutral factual copy."}),
                }
            )

    def activate_policy(self, actor, workspace, policy, key):
        # Rubric/profile/hard gates are deliberately not client-configurable in v1.
        if (
            set(policy) != {"brief"}
            or not isinstance(policy["brief"], str)
            or not 1 <= len(policy["brief"]) <= 2000
        ):
            raise ValueError("only a bounded brand brief can be activated")
        with self.db() as db:
            self._role(db, actor, workspace, {"owner"})
            prior = self._intent(db, actor, workspace, "policy", key, policy)
            if prior is not None:
                return prior
            revision = db.execute(
                "SELECT COALESCE(MAX(revision),0)+1 FROM policies WHERE workspace=?", (workspace,)
            ).fetchone()[0]
            db.execute(
                "INSERT INTO policies VALUES(?,?,?,?)",
                (workspace, revision, canonical(policy), digest(policy)),
            )
            self._invalidate(db, workspace)
            self._audit(
                db,
                "policy_activated",
                actor=actor,
                workspace=workspace,
                body={"revision": revision, "hash": digest(policy)},
            )
            self._remember(db, actor, workspace, "policy", key, policy, revision)
            return revision

    def create_batch(self, actor, workspace, source_id, rows, grant, key):
        if (
            not isinstance(rows, list)
            or not 1 <= len(rows) <= 100
            or len(set(rows)) != len(rows)
            or any(type(row) is not int or not 0 <= row <= 999 for row in rows)
        ):
            raise ValueError("select 1..100 unique row indices")
        payload = {"source": source_id, "rows": rows, "grant": grant}
        with self.db() as db:
            self._role(db, actor, workspace, {"owner", "editor"})
            prior = self._intent(db, actor, workspace, "batch", key, payload)
            if prior is not None:
                return prior
            source = db.execute(
                "SELECT * FROM imports WHERE id=? AND workspace=?", (source_id, workspace)
            ).fetchone()
            authority = db.execute(
                "SELECT * FROM grants WHERE id=? AND workspace=?", (grant, workspace)
            ).fetchone()
            if (
                not source
                or not authority
                or not authority["egress"]
                or authority["expires"] <= self.now()
            ):
                raise Conflict("current source/egress authority required")
            frozen = json.loads(source["frozen"])
            if max(rows) >= len(frozen["facts"]):
                raise ValueError("row outside frozen import")
            epoch = db.execute("SELECT epoch FROM workspaces WHERE id=?", (workspace,)).fetchone()[
                0
            ]
            batch = secrets.token_hex(16)
            binding = self._batch_binding(batch, workspace, frozen, rows, epoch, grant)
            db.execute(
                "INSERT INTO batches VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    batch,
                    workspace,
                    actor,
                    source_id,
                    canonical(rows),
                    grant,
                    epoch,
                    binding,
                    "prepared",
                    self.now(),
                ),
            )
            self._remember(db, actor, workspace, "batch", key, payload, batch)
            self._audit(
                db,
                "batch_prepared",
                actor=actor,
                workspace=workspace,
                body={"batch": batch, "binding": binding, "count": len(rows)},
            )
            return batch

    def _batch_row(self, db, actor, batch, roles=None):
        row = db.execute("SELECT * FROM batches WHERE id=?", (batch,)).fetchone()
        if not row:
            raise Forbidden("object unavailable")
        self._role(db, actor, row["workspace"], roles)
        return row

    def batch_preview(self, actor, batch):
        with self.db() as db:
            row = self._batch_row(db, actor, batch)
            source = db.execute(
                "SELECT frozen FROM imports WHERE id=?", (row["source_id"],)
            ).fetchone()
            if not source:
                raise Conflict("source erased")
            selected = [json.loads(source[0])["facts"][i] for i in json.loads(row["rows"])]
            authority = db.execute("SELECT * FROM grants WHERE id=?", (row["grant_id"],)).fetchone()
            return {
                "binding": row["binding"],
                "facts": selected,
                "rows": len(selected),
                "maximum_calls": 16 * len(selected),
                "grant_remaining": authority["max_calls"] - authority["calls"],
                "expires": authority["expires"],
                "destination": "installed-codex-configured-service",
                "state": row["state"],
                "raw_archive_sent": False,
            }

    def start_batch(self, actor, batch, binding):
        with self.db() as db:
            row = self._batch_row(db, actor, batch, {"owner", "editor"})
            if row["binding"] != binding or row["state"] not in {"prepared", "started"}:
                raise Conflict("batch context differs")
            epoch = db.execute(
                "SELECT epoch FROM workspaces WHERE id=?", (row["workspace"],)
            ).fetchone()[0]
            if epoch != row["epoch"]:
                raise Conflict("stale batch")
            if row["state"] == "started":
                return [
                    r[0]
                    for r in db.execute(
                        "SELECT task FROM task_links WHERE batch_id=? ORDER BY rowid", (batch,)
                    )
                ]
            source = db.execute(
                "SELECT frozen FROM imports WHERE id=?", (row["source_id"],)
            ).fetchone()
            authority = db.execute("SELECT * FROM grants WHERE id=?", (row["grant_id"],)).fetchone()
            if not source or authority["calls"] >= authority["max_calls"] or self._liability(db):
                raise Conflict("source or budget unavailable")
            expected = self._batch_binding(
                batch,
                row["workspace"],
                json.loads(source[0]),
                json.loads(row["rows"]),
                row["epoch"],
                row["grant_id"],
            )
            if expected != row["binding"]:
                raise Conflict("preview code/source/mapping context changed")
            facts = json.loads(source[0])["facts"]
            tasks = [
                self.create_task(
                    actor,
                    row["workspace"],
                    FactPack.model_validate(facts[i]),
                    row["grant_id"],
                    f"{batch}:{i}",
                    source_id=row["source_id"],
                    batch_id=batch,
                    _db=db,
                )
                for i in json.loads(row["rows"])
            ]
            db.execute("UPDATE batches SET state='started' WHERE id=?", (batch,))
            self._audit(
                db,
                "batch_started",
                actor=actor,
                workspace=row["workspace"],
                body={"batch": batch, "binding": binding, "tasks": tasks},
            )
            return tasks

    def batch(self, actor, batch):
        with self.db() as db:
            row = self._batch_row(db, actor, batch)
            tasks = [
                dict(r)
                for r in db.execute(
                    "SELECT t.id,t.state,t.calls FROM tasks t JOIN task_links l "
                    "ON t.id=l.task WHERE l.batch_id=?",
                    (batch,),
                )
            ]
            attempts = [
                dict(r)
                for r in db.execute(
                    "SELECT a.* FROM attempts a JOIN task_links l "
                    "ON a.task=l.task WHERE l.batch_id=?",
                    (batch,),
                )
            ]
            known = [json.loads(a["receipt"]) for a in attempts if a["status"] == "known"]
            return {
                "id": batch,
                "source_id": row["source_id"],
                "state": row["state"],
                "tasks": tasks,
                "counts": dict(Counter(t["state"] for t in tasks)),
                "calls": len(attempts),
                "known_input_tokens": sum(a["input_tokens"] for a in known),
                "known_output_tokens": sum(a["output_tokens"] for a in known),
                "unknown_attempts": len(attempts) - len(known),
                "total_rows": len(json.loads(row["rows"])),
            }

    def cancel_batch(self, actor, batch):
        with self.db() as db:
            row = self._batch_row(db, actor, batch, {"owner", "editor"})
            db.execute("UPDATE batches SET state='cancelled' WHERE id=?", (batch,))
            db.execute(
                "UPDATE tasks SET state='cancelled',lease=NULL WHERE id IN "
                "(SELECT task FROM task_links WHERE batch_id=?)",
                (batch,),
            )
            self._audit(
                db,
                "batch_cancelled",
                actor=actor,
                workspace=row["workspace"],
                body={"batch": batch},
            )

    def edit(self, actor, task, selected_hash, draft, grant, key):
        with self.db() as db:
            row = self._scoped_task(db, actor, task, {"owner", "editor"})
            self._role(db, actor, row["workspace"], {"owner", "editor"})
            payload = {
                "task": task,
                "selected": selected_hash,
                "draft": draft.model_dump(mode="json"),
                "grant": grant,
            }
            prior = self._intent(db, actor, row["workspace"], "edit", key, payload)
            if prior is not None:
                return prior
            if (
                not self._current(db, row)
                or row["selected_hash"] != selected_hash
                or row["state"] in {"running", "stale", "cancelled"}
                or row["calls"] >= 16
                or row["claims"] >= 4
            ):
                raise Conflict("current editable version required")
            link = db.execute("SELECT * FROM task_links WHERE task=?", (task,)).fetchone()
            edited = self.create_task(
                actor,
                row["workspace"],
                FactPack.model_validate(row["facts"]),
                grant,
                f"edit:{key}",
                original=draft,
                source_id=link["source_id"] if link else None,
                parent_task=task,
                _db=db,
            )
            db.execute("UPDATE tasks SET state='stale',lease=NULL WHERE id=?", (task,))
            db.execute(
                "UPDATE tasks SET calls=?,claims=? WHERE id=?",
                (row["calls"], row["claims"], edited),
            )
            self._remember(db, actor, row["workspace"], "edit", key, payload, edited)
            self._audit(
                db,
                "human_edit",
                actor=actor,
                task=edited,
                body={"parent": task, "version": digest(draft)},
            )
            return edited

    def erasure_preview(self, actor, source, _db=None):
        with nullcontext(_db) if _db is not None else self.db() as db:
            row = db.execute("SELECT * FROM imports WHERE id=?", (source,)).fetchone()
            if not row:
                raise Forbidden("object unavailable")
            self._role(db, actor, row["workspace"], {"owner"})
            hashes = {digest(f) for f in json.loads(row["frozen"])["facts"]}
            tasks = [
                r["id"]
                for r in db.execute(
                    "SELECT id,fact_hash FROM tasks WHERE workspace=?", (row["workspace"],)
                )
                if r["fact_hash"] in hashes
            ]
            return {
                "source": source,
                "tasks": tasks,
                "binding": digest({"source": source, "raw": digest(row["raw"]), "tasks": tasks}),
                "limits": "Logical erasure; operator must expire backups and external downloads. "
                "Active SQLite WAL/backups may retain historical bytes until storage maintenance.",
            }

    def erase_import(self, actor, source, binding, key):
        with self.db() as db:
            row = db.execute("SELECT workspace FROM imports WHERE id=?", (source,)).fetchone()
            if not row:
                row = db.execute(
                    "SELECT workspace FROM erased_sources WHERE source=?", (source,)
                ).fetchone()
            if not row:
                raise Forbidden("object unavailable")
            self._role(db, actor, row[0], {"owner"})
            payload = {"source": source, "binding": binding}
            prior = self._intent(db, actor, row[0], "erase", key, payload)
            if prior is not None:
                return prior
            preview = self.erasure_preview(actor, source, _db=db)
            if preview["binding"] != binding:
                raise Conflict("erasure dependencies changed")
            self._append_journal(
                {
                    "event": "source_erased",
                    "source": source,
                    "workspace": row[0],
                    "tasks": preview["tasks"],
                    "binding": binding,
                    "actor": actor,
                }
            )
            # Cancellation/deletion is fenced by the same write transaction as all worker artifacts.
            for task in preview["tasks"]:
                for table in ("artifacts", "reviews", "task_links"):
                    db.execute(f"DELETE FROM {table} WHERE task=?", (task,))
                db.execute("DELETE FROM snapshots WHERE task=?", (task,))
                db.execute("DELETE FROM selections WHERE task=?", (task,))
                db.execute("DELETE FROM tasks WHERE id=?", (task,))
                db.execute("DELETE FROM audit WHERE task=?", (task,))
            db.execute("DELETE FROM batches WHERE source_id=?", (source,))
            db.execute("DELETE FROM imports WHERE id=?", (source,))
            db.execute("INSERT INTO erased_sources VALUES(?,?)", (source, row[0]))
            self._remember(db, actor, row[0], "erase", key, payload, {"erased": True})
            self._audit(
                db,
                "source_erased",
                actor=actor,
                workspace=row[0],
                body={"source_hash": digest(source.encode()), "tasks": len(preview["tasks"])},
            )

    def review_csv(self, actor, workspace):
        def safe(value):
            text = str(value)
            return (
                "'" + text
                if text
                and (
                    text.lstrip()[:1] in {"=", "+", "-", "@"}
                    or text[0] in "\t\r\n"
                    or text.isdigit()
                )
                else text
            )

        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            ["status", "task", "product_id_text", "title", "description", "version_hash"]
        )
        with self.db() as db:
            self._role(db, actor, workspace)
            for stub in db.execute(
                "SELECT id FROM tasks WHERE workspace=? ORDER BY created", (workspace,)
            ):
                task = self._task(db, stub[0])
                version = next(
                    (v for v in task["versions"] if v["draft_hash"] == task["selected_hash"]), None
                )
                writer.writerow(
                    [
                        "UNAPPROVED_REVIEW_ONLY",
                        task["id"],
                        safe(task["facts"]["product_id"]),
                        safe(version["draft"]["title"]) if version else "",
                        safe(version["draft"]["description"]) if version else "",
                        task["selected_hash"] or "",
                    ]
                )
        return output.getvalue()
