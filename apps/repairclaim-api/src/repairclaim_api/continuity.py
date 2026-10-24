"""Consented retrospective checks, clear case progress and attributed financial events."""

import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from contracts.repairclaim import CaseSnapshot, EvidenceAnchor, OutcomeEvent, ProgrammeRevision

from repairclaim_api.core import (
    evaluate_programme,
    evaluate_search,
    summarize_outcomes,
    verify_anchor,
)
from repairclaim_api.errors import DomainError


class ContinuityMixin:
    def set_monitoring(self, token, vehicle_id, case_ids, ttl):
        if type(ttl) is not int or not 0 < ttl <= 90 * 86400 or not 1 <= len(case_ids) <= 10:
            raise DomainError("invalid_monitoring_consent", 422)
        with self._transaction() as db:
            actor = self._actor(db, token)
            for case_id in set(case_ids):
                case = self._case(db, actor, case_id, "owner")
                if case["vehicle_id"] != vehicle_id:
                    raise DomainError("not_found", 404)
                for row in db.execute(
                    "SELECT * FROM rc_objects WHERE case_id=? AND kind='monitoring' AND state='active'",
                    (case_id,),
                ).fetchall():
                    db.execute("UPDATE rc_objects SET state='revoked' WHERE id=?", (row["id"],))
                self._new_object(
                    db,
                    case,
                    "monitoring",
                    {
                        "vehicle_id": vehicle_id,
                        "expires": self._now() + ttl,
                        "registry_epoch": self._epoch(db),
                        "purpose": "retrospective_supported_programme_matching",
                    },
                    "active",
                )
                self._audit(db, actor, case, "monitoring_consented")
        return {"status": "active", "expires": self._now() + ttl}

    def revoke_monitoring(self, token, vehicle_id):
        with self._transaction() as db:
            actor = self._actor(db, token)
            vehicle = db.execute(
                "SELECT id FROM vehicles WHERE id=? AND household_id=?",
                (vehicle_id, actor["household_id"]),
            ).fetchone()
            if vehicle is None:
                raise DomainError("not_found", 404)
            for row in db.execute(
                "SELECT * FROM rc_objects WHERE household_id=? AND kind='monitoring' AND state='active'",
                (actor["household_id"],),
            ).fetchall():
                item = {**dict(row), "data": json.loads(row["data"])}
                if item["data"]["vehicle_id"] == vehicle_id:
                    self._update_object(db, item, state="revoked")
                    db.execute(
                        "UPDATE rc_objects SET state='cancelled' WHERE case_id=? AND kind='notification'",
                        (item["case_id"],),
                    )
                    case = self._case(db, actor, item["case_id"], "owner")
                    self._audit(db, actor, case, "monitoring_revoked")

    def rematch_monitoring(self):
        with self._transaction() as db:
            programmes, source_status, epoch = self._inventory(db)
            if source_status != "complete":
                return 0
            created = 0
            for row in db.execute(
                "SELECT * FROM rc_objects WHERE kind='monitoring' AND state='active' ORDER BY created,rowid LIMIT 100"
            ).fetchall():
                consent = {**dict(row), "data": json.loads(row["data"])}
                case_row = db.execute(
                    "SELECT * FROM cases WHERE id=? AND deleted=0", (consent["case_id"],)
                ).fetchone()
                if (
                    case_row is None
                    or case_row["retention_until"] <= self._now()
                    or self._erased(case_row["id"])
                    or consent["data"]["expires"] <= self._now()
                ):
                    self._update_object(db, consent, state="expired")
                    continue
                changes = db.execute(
                    "SELECT * FROM rc_changes WHERE epoch>? ORDER BY epoch LIMIT 50",
                    (consent["data"]["registry_epoch"],),
                ).fetchall()
                snapshot_row = db.execute(
                    "SELECT snapshot_json FROM fact_revisions WHERE case_id=? AND revision=?",
                    (case_row["id"], case_row["revision"]),
                ).fetchone()
                if snapshot_row is None:
                    continue
                snapshot = CaseSnapshot.model_validate_json(snapshot_row[0])
                for change in changes:
                    current = next(
                        (
                            programme
                            for programme in programmes
                            if programme.family_id == change["family"]
                        ),
                        None,
                    )
                    if current is None:
                        continue
                    after = evaluate_programme(snapshot, current)
                    previous = db.execute(
                        "SELECT payload FROM rc_programmes WHERE family=? AND revision=?",
                        (change["family"], change["old_revision"]),
                    ).fetchone()
                    before = (
                        evaluate_programme(
                            snapshot, ProgrammeRevision.model_validate_json(previous[0])
                        )
                        if previous
                        else None
                    )
                    if before is None and after.state == "appears_outside_conditions":
                        continue
                    dedup = f"change-{change['id']}"
                    existing = [
                        json.loads(item[0]).get("dedup")
                        for item in db.execute(
                            "SELECT data FROM rc_objects WHERE case_id=? AND kind='notification'",
                            (case_row["id"],),
                        )
                    ]
                    if dedup not in existing:
                        self._new_object(
                            db,
                            dict(case_row),
                            "notification",
                            {
                                "consent_id": consent["id"],
                                "dedup": dedup,
                                "change": {
                                    "old_revision": change["old_revision"],
                                    "new_revision": current.revision,
                                    "family": change["family"],
                                    "type": change["reason"],
                                    "discovered_at": change["created"],
                                    "publication_date": None,
                                    "label": "Newly discovered or revised evidence; not a refund promise",
                                    "before": before.model_dump(mode="json") if before else None,
                                    "after": after.model_dump(mode="json"),
                                },
                            },
                            "available",
                        )
                        created += 1
                consent["data"]["registry_epoch"] = changes[-1]["epoch"] if changes else epoch
                self._update_object(db, consent)
            return created

    def notifications(self, token):
        with self._transaction() as db:
            actor = self._actor(db, token)
            result = []
            for row in db.execute(
                "SELECT * FROM rc_objects WHERE household_id=? AND kind='notification' AND state IN ('available','read') ORDER BY created DESC",
                (actor["household_id"],),
            ):
                item = {**dict(row), "data": json.loads(row["data"])}
                consent = self._object(db, item["data"]["consent_id"])
                if consent["state"] == "active" and consent["data"]["expires"] > self._now():
                    try:
                        self._case(db, actor, item["case_id"], "owner")
                    except DomainError:
                        continue
                    result.append(self._public(item))
            return result

    def acknowledge_notification(self, token, item_id):
        with self._transaction() as db:
            item, _ = self._scoped_object(
                db, self._actor(db, token), item_id, "notification", "owner"
            )
            self._update_object(db, item, state="acknowledged")

    def record_manual_submission(self, token, case_id, packet_id, channel, sent_at, key):
        timestamp = self._timestamp(sent_at)
        if channel not in {"portal", "email", "postal_mail", "in_person", "other"}:
            raise DomainError("invalid_channel", 422)
        request = {
            "packet_id": packet_id,
            "channel": channel,
            "sent_at": timestamp,
            "attribution": "user_reported_sent",
            "delivery_verified": False,
        }
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "owner")
            packet, own_case = self._scoped_object(db, actor, packet_id, "packet")
            if own_case["id"] != case_id or not packet["data"].get("fingerprint"):
                raise DomainError("packet_not_rendered", 409)
            existing = self._idempotent(db, case, "manual_submission", key, request)
            if existing:
                return self._public(existing)
            item = self._new_object(db, case, "manual_submission", request)
            self._bind_idempotency(db, case, "manual_submission", key, request, item)
            self._audit(db, actor, case, "user_reported_sent")
            db.execute("UPDATE cases SET lifecycle='awaiting_response' WHERE id=?", (case_id,))
            return self._public(item)

    @staticmethod
    def _timestamp(value):
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                raise ValueError()
            return parsed.timestamp()
        except (ValueError, TypeError, AttributeError, OverflowError) as error:
            raise DomainError("aware_timestamp_required", 422) from error

    def record_response(self, token, case_id, document_id, key):
        request = {"document_id": document_id}
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "edit")
            document, own_case = self._scoped_object(db, actor, document_id, "document")
            if (
                own_case["id"] != case_id
                or document["state"] != "ready"
                or document["data"]["document_kind"] != "response"
            ):
                raise DomainError("response_document_required", 409)
            existing = self._idempotent(db, case, "response", key, request)
            if existing:
                return self._public(existing)
            reasons = []
            for page in document["data"]["parsed"]["pages"]:
                quote = page["text"].strip()[:2000]
                lower = quote.casefold()
                if not quote:
                    continue
                category = "unclear"
                if any(
                    word in lower
                    for word in ("provide", "missing", "additional record", "need a copy")
                ):
                    category = "missing_evidence"
                elif "partial" in lower and "approv" in lower:
                    category = "partial_approval"
                elif any(
                    word in lower for word in ("denied", "not covered", "outside", "not approved")
                ):
                    category = "condition_disagreement"
                elif "approved" in lower:
                    category = "approval_reported"
                reasons.append(
                    {
                        "category": category,
                        "page": page["page"],
                        "quote": quote,
                        "attribution": "response_text_not_independent_confirmation",
                        "next_action": "Request the specified records; do not allege fraud."
                        if category == "missing_evidence"
                        else "Review the response and documented conditions; seek clarification if uncertain.",
                    }
                )
            snapshot = CaseSnapshot.model_validate_json(
                db.execute(
                    "SELECT snapshot_json FROM fact_revisions WHERE case_id=? AND revision=?",
                    (case_id, case["revision"]),
                ).fetchone()[0]
            )
            programmes, source_status, epoch = self._inventory(db)
            comparison = {
                "case_revision": case["revision"],
                "registry_epoch": epoch,
                "assessment": evaluate_search(
                    snapshot, programmes, search_status=source_status
                ).model_dump(mode="json"),
                "manufacturer_confirmation": False,
                "interpretation": "Response text is attributed, not independent confirmation. No appeal right is inferred.",
            }
            item = self._new_object(
                db,
                case,
                "response",
                {
                    **request,
                    "reasons": reasons[:20],
                    "review_required": True,
                    "comparison": comparison,
                },
            )
            self._bind_idempotency(db, case, "response", key, request, item)
            self._audit(db, actor, case, "response_recorded")
            db.execute("UPDATE cases SET lifecycle='response_review' WHERE id=?", (case_id,))
            return self._public(item)

    def record_outcome(
        self, token, case_id, event, key, *, evidence_page=None, evidence_quote=None
    ):
        event = OutcomeEvent.model_validate(event)
        request = {
            "event": event.model_dump(mode="json"),
            "evidence_page": evidence_page,
            "evidence_quote": evidence_quote,
        }
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "owner")
            existing = self._idempotent(db, case, "outcome", key, request)
            if existing:
                return self._public(existing)
            if event.evidence_class == "documented":
                document, own_case = self._scoped_object(db, actor, event.evidence_ref, "document")
                pages = document["data"].get("parsed", {}).get("pages", [])
                page = next((page for page in pages if page["page"] == evidence_page), None)
                if (
                    own_case["id"] != case_id
                    or document["state"] != "ready"
                    or not evidence_quote
                    or page is None
                    or evidence_quote not in page["text"]
                    or str(event.amount.amount) not in evidence_quote.replace(",", "")
                ):
                    raise DomainError("outcome_evidence_required", 422)
                lower = evidence_quote.casefold()
                kinds = {
                    "received": {"receipt", "response"},
                    "approved": {"response"},
                    "confirmed_covered": {"response"},
                    "requested": {"response", "other"},
                    "avoided_cost": {"receipt", "response"},
                }
                terms = {
                    "received": r"\b(received|credited|refund paid)\b",
                    "approved": r"\bapproved\b",
                    "confirmed_covered": r"\bcovered\b",
                    "requested": r"\b(requested|request)\b",
                    "avoided_cost": r"\b(waived|not charged)\b",
                }
                if (
                    document["data"]["document_kind"] not in kinds[event.kind]
                    or event.amount.currency not in evidence_quote
                    or not re.search(terms[event.kind], lower)
                    or (
                        event.kind != "avoided_cost"
                        and re.search(r"\b(not|denied|pending|estimate)\b", lower)
                    )
                ):
                    raise DomainError("outcome_evidence_ambiguous", 422)
            events = [
                OutcomeEvent.model_validate(json.loads(row[0])["event"])
                for row in db.execute(
                    "SELECT data FROM rc_objects WHERE case_id=? AND kind='outcome' ORDER BY created,rowid",
                    (case_id,),
                )
            ]
            try:
                summarize_outcomes((*events, event))
            except ValueError as error:
                raise DomainError(str(error), 409) from error
            if any(previous.id == event.id for previous in events):
                raise DomainError("duplicate_outcome_event", 409)
            item = self._new_object(db, case, "outcome", request)
            self._bind_idempotency(db, case, "outcome", key, request, item)
            self._audit(db, actor, case, "outcome_recorded")
            return self._public(item)

    def outcome_totals(self, token, case_id):
        with self._transaction() as db:
            case = self._case(db, self._actor(db, token), case_id)
            events = tuple(
                OutcomeEvent.model_validate(json.loads(row[0])["event"])
                for row in db.execute(
                    "SELECT data FROM rc_objects WHERE household_id=? AND case_id=? AND kind='outcome' ORDER BY created,rowid",
                    (case["household_id"], case_id),
                )
            )
            return summarize_outcomes(events)

    def add_reminder(
        self, token, case_id, due_at, timezone, provenance, label, *, source_anchor=None
    ):
        due = self._timestamp(due_at)
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
            raise DomainError("invalid_timezone", 422) from error
        if provenance not in {"suggested_followup", "user_entered", "programme_documented"} or (
            source_anchor is not None and provenance != "programme_documented"
        ):
            raise DomainError("unverified_programme_deadline", 422)
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 200:
            raise DomainError("invalid_reminder", 422)
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "owner")
            anchor = None
            if provenance == "programme_documented":
                if source_anchor is None:
                    raise DomainError("unverified_programme_deadline", 422)
                anchor = EvidenceAnchor.model_validate(source_anchor)
                head = db.execute(
                    "SELECT * FROM rc_sources WHERE id=?", (anchor.document_id,)
                ).fetchone()
                capture = db.execute(
                    "SELECT parsed FROM rc_captures WHERE source_id=? AND hash=?",
                    (anchor.document_id, anchor.sha256),
                ).fetchone()
                date = datetime.fromtimestamp(due, ZoneInfo(timezone)).date().isoformat()
                if (
                    not head
                    or not capture
                    or head["state"] != "reviewed"
                    or head["current_hash"] != anchor.sha256
                    or self._now() - head["last_success"] > 48 * 3600
                    or not re.search(
                        r"(?:submit by|file by|submission deadline[: ]*)\s*" + re.escape(date),
                        anchor.quote,
                        re.IGNORECASE,
                    )
                ):
                    raise DomainError("unverified_programme_deadline", 422)
                pages = [
                    {**page, "document_id": anchor.document_id, "sha256": anchor.sha256}
                    for page in json.loads(capture[0])["pages"]
                ]
                if not verify_anchor(anchor, pages):
                    raise DomainError("source_anchor_invalid", 422)
            item = self._new_object(
                db,
                case,
                "reminder",
                {
                    "due_at": due,
                    "timezone": timezone,
                    "provenance": provenance,
                    "label": label,
                    "source_anchor": anchor.model_dump(mode="json") if anchor else None,
                },
                "scheduled",
            )
            self._audit(db, actor, case, "reminder_created")
            return self._public(item)

    def cancel_reminder(self, token, reminder_id):
        with self._transaction() as db:
            actor = self._actor(db, token)
            item, case = self._scoped_object(db, actor, reminder_id, "reminder", "owner")
            self._update_object(db, item, state="cancelled")
            self._audit(db, actor, case, "reminder_cancelled")
