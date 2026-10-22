"""Deterministic incident detection and crash-reclaimable notification outbox."""

import hashlib
import hmac
import secrets

from contracts.releasefence import Event, Policy

from .core import canonical, detect, digest
from .errors import Conflict, Forbidden
from .network import request


class Engine:
    def __init__(self, store, *, transport=request, lab_loopback=False):
        self.store = store
        self.transport = transport
        self.lab_loopback = lab_loopback

    def scan(self, tenant):
        s = self.store
        automatic = []
        with s.db(tenant) as db:
            enrollments = s._rows(db, "enrollment")
            rollouts = s._rows(db, "rollout")
            events = s._rows(db, "event", 50001)
            for enrolled in enrollments:
                rolls = [
                    r
                    for r in rollouts
                    if enrolled["id"] in r["enrollments"]
                    and r["state"] not in {"rollback_verified", "promoted", "cancelled"}
                ]
                policy = Policy.model_validate(rolls[-1]["policy"]) if rolls else Policy()
                rows = [
                    Event.model_validate(r["event"])
                    for r in events
                    if r["enrollment"] == enrolled["id"]
                ]
                findings = detect(rows, policy, now=s.now())
                if rolls and (
                    enrolled["last_seen"] is None or s.now() - enrolled["last_seen"] > 60
                ):
                    findings.append(
                        {
                            "task": "runtime",
                            "session": "runtime",
                            "release": rolls[-1]["candidate"],
                            "rule": "telemetry_stale",
                            "severity": "warning",
                            "event": "runtime",
                        }
                    )
                for finding in findings:
                    id = digest([enrolled["id"], finding["task"], finding["rule"]])
                    if db.execute(
                        "SELECT 1 FROM records WHERE kind='incident' AND id=%s", (id,)
                    ).fetchone():
                        continue
                    roll = next(
                        (r for r in reversed(rolls) if r["candidate"] == finding["release"]), None
                    )
                    body = {
                        **finding,
                        "enrollment": enrolled["id"],
                        "application": enrolled["application"],
                        "environment": enrolled["environment"],
                        "state": "open",
                        "rollout": roll["id"] if roll else None,
                        "mitigation": "not_requested",
                    }
                    s._insert(db, "incident", id, body)
                    for dest in s._rows(db, "destination"):
                        if not dest["enabled"]:
                            continue
                        nid = digest([id, dest["id"]])
                        s._insert(
                            db,
                            "notification",
                            nid,
                            {
                                "incident": id,
                                "destination": dest["id"],
                                "state": "pending",
                                "attempts": [],
                                "due": s.now(),
                                "lease": None,
                                "lease_until": 0,
                                "replayed": False,
                                "maximum_attempts": 5,
                            },
                        )
                    s._audit(
                        db,
                        "detector",
                        "incident_opened",
                        {"incident": id, "rule": finding["rule"], "rollout": body["rollout"]},
                    )
                    if (
                        finding["severity"] == "critical"
                        and roll
                        and roll["state"]
                        in {
                            "canary_running",
                            "promotion_pending",
                            "paused_inconclusive",
                            "failed_canary",
                        }
                    ):
                        automatic.append((id, roll["id"], roll["revision"]))
        for incident, rollout, revision in automatic:
            try:
                s.control(
                    "policy",
                    tenant,
                    rollout,
                    "rollback",
                    revision,
                    "incident:" + incident,
                    automatic=True,
                )
                state = "requested"
            except (Conflict, Forbidden):
                state = "blocked_no_current_authority"
            with s.db(tenant) as db:
                row = s._get(db, "incident", incident)
                row["mitigation"] = state
                s._save(db, "incident", row)
        return len(automatic)

    def deliver(self, tenant):
        s = self.store
        claimed = None
        with s.db(tenant) as db:
            for row in s._rows(db, "notification"):
                if (
                    row["state"] in {"pending", "retry", "sending"}
                    and row["due"] <= s.now()
                    and row["lease_until"] <= s.now()
                ):
                    if row["state"] == "sending" and row["attempts"]:
                        row["attempts"][-1]["disposition"] = "unknown"
                    if len(row["attempts"]) >= row["maximum_attempts"]:
                        row.update(state="dead_letter", lease=None, lease_until=0)
                        s._save(db, "notification", row)
                        s._audit(
                            db,
                            "delivery",
                            "notification_lease_exhausted",
                            {"notification": row["id"]},
                        )
                        continue
                    destination = s._get(db, "destination", row["destination"])
                    if not destination["enabled"]:
                        continue
                    lease = secrets.token_hex(16)
                    row["attempts"].append(
                        {"at": s.now(), "status": None, "disposition": "in_flight"}
                    )
                    row.update(state="sending", lease=lease, lease_until=s.now() + 60)
                    s._save(db, "notification", row)
                    incident = s._get(db, "incident", row["incident"])
                    claimed = (row, destination, incident, lease)
                    break
        if not claimed:
            return False
        row, destination, incident, lease = claimed
        payload = canonical(
            {
                "id": row["id"],
                "schema": "releasefence-notification-v1",
                "incident": incident["id"],
                "rule": incident["rule"],
                "severity": incident["severity"],
                "release": incident["release"],
                "created": incident["created"],
            }
        ).encode()
        secret = s.box.decrypt(destination["secret_box"].encode())
        signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        status = None
        try:
            status, _ = self.transport(
                s.box.decrypt(destination["url_box"].encode()).decode(),
                payload,
                headers={"X-ReleaseFence-Signature": signature, "Idempotency-Key": row["id"]},
                lab_loopback=self.lab_loopback and destination["lab_loopback"],
            )
            disposition = "accepted" if 200 <= status < 300 else "rejected"
        except (OSError, ValueError):
            disposition = "unknown"
        with s.db(tenant) as db:
            current = s._get(db, "notification", row["id"])
            if current["lease"] != lease or current["lease_until"] <= s.now():
                raise Conflict("delivery lease fenced")
            current["attempts"][-1].update(
                {"at": s.now(), "status": status, "disposition": disposition}
            )
            n = len(current["attempts"])
            current.update(
                state="delivered"
                if disposition == "accepted"
                else "dead_letter"
                if n >= current["maximum_attempts"]
                else "retry",
                lease=None,
                lease_until=0,
                due=s.now() + [5, 30, 120, 600][min(n - 1, 3)],
            )
            s._save(db, "notification", current)
            s._audit(
                db,
                "delivery",
                "notification_attempt",
                {"notification": row["id"], "disposition": disposition, "attempt": n},
            )
        return True
