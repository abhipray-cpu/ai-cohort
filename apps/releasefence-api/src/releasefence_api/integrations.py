"""Encrypted backend enrollment and durable, bounded trace export work."""

import secrets

from .backends import Backend
from .core import digest
from .errors import Conflict
from .network import request, resolve_destination


class Integrations:
    def set_connection(self, actor, tenant, kind, id, enabled):
        if kind not in {"backend", "destination"} or type(enabled) is not bool:
            raise ValueError("explicit connection state required")
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            row = self._get(db, kind, id)
            row["enabled"] = enabled
            if kind == "backend":
                row.update(status="unverified" if enabled else "disabled", verified_releases={})
            self._save(db, kind, row)
            self._audit(
                db, actor, "connection_state_changed", {"kind": kind, "id": id, "enabled": enabled}
            )

    def replay_trace(self, actor, tenant, id):
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            row = self._get(db, "trace_export", id)
            if row["state"] != "dead_letter" or row.get("replayed"):
                raise Conflict("one bounded trace replay only")
            row.update(state="retry", replayed=True, maximum_attempts=10, due=self.now())
            self._save(db, "trace_export", row)
            self._audit(db, actor, "trace_export_replayed", {"id": id})

    def backend(
        self, actor, tenant, kind, export_url, read_url, secret, project, key, *, lab_loopback=False
    ):
        if (
            kind not in {"langsmith", "phoenix", "mlflow"}
            or not 1 <= len(secret) <= 512
            or not 1 <= len(project) <= 128
        ):
            raise ValueError("invalid backend")
        for url in (export_url, read_url):
            resolve_destination(url, lab_loopback=lab_loopback)
        Backend(kind, export_url, read_url, secret, project, lab_loopback=lab_loopback)
        payload = {
            "kind": kind,
            "export_hash": digest(export_url.encode()),
            "read_hash": digest(read_url.encode()),
            "secret_hash": digest(secret.encode()),
            "project": project,
            "lab_loopback": lab_loopback,
        }
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            prior = self._intent(db, "backend:" + actor, key, payload)
            if prior:
                return prior
            if len(self._rows(db, "backend")) >= 2:
                raise Conflict("two customer-owned backends maximum")
            if any(r["kind"] == kind for r in self._rows(db, "backend")):
                raise Conflict("one backend per vendor")
            id = secrets.token_hex(16)
            self._insert(
                db,
                "backend",
                id,
                {
                    "kind": kind,
                    "project": project,
                    "export_box": self.box.encrypt(export_url.encode()).decode(),
                    "read_box": self.box.encrypt(read_url.encode()).decode(),
                    "secret_box": self.box.encrypt(secret.encode()).decode(),
                    "lab_loopback": lab_loopback,
                    "status": "unverified",
                    "proof": None,
                    "enabled": True,
                },
            )
            self._remember(db, "backend:" + actor, key, payload, id)
            self._audit(db, actor, "backend_registered", {"id": id, "kind": kind})
            return id

    def export_backend(self, tenant, id, *, transport=request):
        with self.db(tenant) as db:
            config = self._get(db, "backend", id)
            if not config["enabled"]:
                return None
            db.execute(
                """UPDATE records SET body=body||'{"state":"dead_letter","reason":"lease_expired_unknown"}'::jsonb,revision=revision+1
              WHERE kind='trace_export' AND body->>'backend'=%s AND body->>'state'='leased'
              AND (body->>'due')::double precision<=%s AND (body->>'attempts')::int>=COALESCE((body->>'maximum_attempts')::int,5)""",
                (id, self.now()),
            )
            # One bounded batch per backend. Cursor is per span identity, never event time.
            work = db.execute(
                """SELECT s.id,s.body FROM records s WHERE s.kind='span' AND NOT EXISTS
              (SELECT 1 FROM records e WHERE e.kind='trace_export' AND e.id=%s||':'||s.id
               AND (e.body->>'state' IN ('verified','dead_letter') OR (e.body->>'due')::double precision>%s))
              ORDER BY s.created,s.id LIMIT 10""",
                (id, self.now()),
            ).fetchall()
            if not work:
                return None
            lease = secrets.token_hex(16)
            for item in work:
                eid = id + ":" + item["id"]
                found = db.execute(
                    "SELECT 1 FROM records WHERE kind='trace_export' AND id=%s", (eid,)
                ).fetchone()
                row = self._get(db, "trace_export", eid) if found else None
                body = {
                    "backend": id,
                    "span": item["id"],
                    "state": "leased",
                    "lease": lease,
                    "due": self.now() + 120,
                    "attempts": row["attempts"] + 1 if row else 1,
                }
                if row:
                    row.update(body)
                    self._save(db, "trace_export", row)
                else:
                    self._insert(db, "trace_export", eid, body)
        spans = [item["body"]["span"] for item in work]
        backend = Backend(
            config["kind"],
            self.box.decrypt(config["export_box"].encode()).decode(),
            self.box.decrypt(config["read_box"].encode()).decode(),
            self.box.decrypt(config["secret_box"].encode()).decode(),
            config["project"],
            transport=transport,
            lab_loopback=config["lab_loopback"],
        )
        try:
            backend.export(spans)
            result = backend.verify(spans)
        except (OSError, ValueError):
            result = {
                "verified": False,
                "reason": "export_unavailable",
                "checked": [],
                "expected": len(spans),
            }
        with self.db(tenant) as db:
            current = self._get(db, "backend", id)
            committed = False
            for item in work:
                row = self._get(db, "trace_export", id + ":" + item["id"])
                if row["lease"] != lease:
                    continue
                committed = True
                row.update(
                    state="verified"
                    if result["verified"]
                    else "dead_letter"
                    if row["attempts"] >= row.get("maximum_attempts", 5)
                    else "retry",
                    due=self.now() + min(600, 5 * 2 ** row["attempts"]),
                    result=result,
                )
                self._save(db, "trace_export", row)
            if not committed:
                return result
            current.update(
                status=("verified" if result["verified"] else "degraded")
                if current["enabled"]
                else "disabled",
                proof={**result, "at": self.now(), "span_ids": [s["span_id"] for s in spans]},
            )
            if result["verified"]:
                releases = current.get("verified_releases", {})
                for item in work:
                    span = item["body"]["span"]
                    scope = (
                        item["body"]["application"]
                        + ":"
                        + item["body"]["environment"]
                        + ":"
                        + span["release"]
                    )
                    releases[scope] = {
                        "at": self.now(),
                        "started_ns": span["started_ns"],
                        "span_id": span["span_id"],
                        "trace_id": span["trace_id"],
                    }
                current["verified_releases"] = dict(
                    sorted(
                        releases.items(), key=lambda item: (item[1]["at"], item[0]), reverse=True
                    )[:128]
                )
            self._save(db, "backend", current)
        return result
