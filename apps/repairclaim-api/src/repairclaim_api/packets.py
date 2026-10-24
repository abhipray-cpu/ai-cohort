"""Evidence-bound correspondence, exact-byte approvals and owner-controlled downloads."""

import hashlib
import io
import json
import zipfile

from repairclaim_api.documents import render_packet as render_pdf
from repairclaim_api.errors import DomainError
from repairclaim_api.feature_utils import canonical, fingerprint


class PacketMixin:
    def _fresh_packet(self, db, packet, case):
        data = packet["data"]
        if (
            data.get("stale")
            or data["case_revision"] != case["revision"]
            or data["registry_epoch"] != self._epoch(db)
        ):
            raise DomainError("stale_artifact", 409)
        if self._inventory(db)[1] != "complete":
            raise DomainError("source_not_current", 409)

    def create_packet(
        self, token, case_id, job_id, recipient, attachments, purpose, key, *, notes=""
    ):
        if (
            not isinstance(recipient, str)
            or not 1 <= len(recipient.strip()) <= 200
            or not isinstance(notes, str)
            or len(notes) > 2000
            or len(attachments) > 20
            or purpose not in {"enquiry", "reimbursement", "records_request", "followup"}
        ):
            raise DomainError("invalid_packet", 422)
        # Never turn authored accusations/promises into product assertions.
        if any(
            term in notes.casefold()
            for term in ("guaranteed refund", "committed fraud", "you qualify")
        ):
            raise DomainError("unsupported_statement", 422)
        request = {
            "job_id": job_id,
            "recipient": recipient,
            "attachments": attachments,
            "purpose": purpose,
            "notes": notes,
        }
        with self._transaction() as db:
            actor = self._actor(db, token)
            case = self._case(db, actor, case_id, "owner")
            existing = self._idempotent(db, case, "packet", key, request)
            if existing:
                return self._public(existing)
            job, job_case = self._scoped_object(db, actor, job_id, "job")
            if job_case["id"] != case_id or job["data"].get("operation") != "investigate":
                raise DomainError("not_found", 404)
            if job["state"] not in {"review_ready", "awaiting_evidence", "manual_review"}:
                raise DomainError("assessment_not_ready", 409)
            if job["data"].get("stale") or job["data"]["case_revision"] != case["revision"]:
                raise DomainError("stale_artifact", 409)
            if (
                purpose == "reimbursement"
                and job["data"]["result"]["search"]["state"] != "potentially_applicable"
            ):
                raise DomainError("reimbursement_not_supported", 409)
            selected = []
            attachment_bytes = 0
            for attachment in attachments:
                if set(attachment) - {"document_id", "mode", "redactions"}:
                    raise DomainError("invalid_attachment", 422)
                document, own_case = self._scoped_object(
                    db, actor, attachment["document_id"], "document"
                )
                if own_case["id"] != case_id or document["state"] != "ready":
                    raise DomainError("attachment_not_ready", 409)
                attachment_bytes += document["data"]["size"]
                if attachment_bytes > 20 * 1024 * 1024:
                    raise DomainError("packet_attachment_size_limit", 413)
                mode, redactions = (
                    attachment.get("mode", "sanitized"),
                    attachment.get("redactions", []),
                )
                if mode not in {"sanitized", "original"} or (mode == "original" and redactions):
                    raise DomainError("original_redaction_conflict", 422)
                if len(redactions) > 40 or any(
                    type(value) is not str or not 1 <= len(value.strip()) <= 200
                    for value in redactions
                ):
                    raise DomainError("invalid_redactions", 422)
                selected.append(
                    {
                        "document_id": document["id"],
                        "mode": mode,
                        "redactions": redactions,
                        "sha256": document["data"]["sha256"],
                        "filename": document["data"]["filename"],
                    }
                )
            if len({item["document_id"] for item in selected}) != len(selected):
                raise DomainError("duplicate_attachment", 422)
            snapshot = json.loads(
                db.execute(
                    "SELECT snapshot_json FROM fact_revisions WHERE case_id=? AND revision=?",
                    (case_id, case["revision"]),
                ).fetchone()[0]
            )
            paragraphs = [
                f"To: {recipient}",
                "Please review this enquiry. This packet does not establish eligibility or promise reimbursement.",
            ]
            if purpose == "records_request":
                question = job["data"]["result"].get("next_question")
                paragraphs.append(
                    "Please provide supporting repair records"
                    + (f" concerning {question['field'].replace('_', ' ')}." if question else ".")
                )
            for fact in snapshot["facts"]:
                if fact["status"] != "extracted":
                    paragraphs.append(
                        f"User-reported or user-confirmed {fact['field'].replace('_', ' ')}: {fact['value']} {fact.get('unit') or ''}".strip()
                    )
            sources = []
            for candidate in job["data"]["result"]["search"]["candidates"]:
                paragraphs.append(
                    f"Programme reference: {candidate['family_id']} / {candidate['programme_revision']}. "
                    f"Assessment: {candidate['state'].replace('_', ' ')}. "
                    "Manufacturer applicability requires confirmation."
                )
                for condition in candidate["conditions"]:
                    anchor = condition["anchor"]
                    head = db.execute(
                        "SELECT url FROM rc_sources WHERE id=?", (anchor["document_id"],)
                    ).fetchone()
                    source = {
                        **anchor,
                        "url": head[0] if head else "",
                        "condition_status": condition["status"],
                    }
                    sources.append(source)
                    paragraphs.append(
                        f"Condition {condition['condition_id']}: {condition['status'].replace('_', ' ')}. Source page {anchor['page']}: {anchor['quote']}"
                    )
            if purpose == "reimbursement":
                paid = [
                    fact
                    for fact in snapshot["facts"]
                    if fact["field"] == "paid_amount" and fact["status"] != "extracted"
                ]
                if not paid:
                    raise DomainError("payment_evidence_required", 409)
                paragraphs.append(
                    "Please review the reported paid repair for possible reimbursement under the documented conditions. The amount is a request, not an approved entitlement."
                )
            if notes:
                paragraphs.append(
                    "Additional statement supplied by the user (not independently verified): "
                    + notes
                )
            response_refs = []
            if purpose == "followup":
                row = db.execute(
                    "SELECT data FROM rc_objects WHERE case_id=? AND kind='response' ORDER BY created DESC,rowid DESC LIMIT 1",
                    (case_id,),
                ).fetchone()
                if row is None:
                    raise DomainError("response_required_for_followup", 409)
                response = json.loads(row[0])
                for reason in response["reasons"]:
                    paragraphs.append(
                        f"Your response states (page {reason['page']}): {reason['quote']}"
                    )
                    paragraphs.append(
                        "Please clarify the documented condition and records still required. This enquiry does not allege misconduct or assert an appeal right."
                    )
                    response_refs.append(
                        {
                            "document_id": response["document_id"],
                            "page": reason["page"],
                            "quote": reason["quote"],
                        }
                    )
            paragraphs.append(
                "Please confirm vehicle-specific applicability and identify any further records required. No legal entitlement or diagnostic conclusion is asserted by RepairClaim."
            )
            data = {
                **request,
                "attachments": selected,
                "paragraphs": paragraphs,
                "sources": sources,
                "case_revision": case["revision"],
                "registry_epoch": self._epoch(db),
                "stale": False,
                "response_refs": response_refs,
            }
            packet = self._new_object(db, case, "packet", data, "draft")
            self._bind_idempotency(db, case, "packet", key, request, packet)
            self._audit(db, actor, case, "packet_drafted")
            return self._public(packet)

    def get_packet(self, token, packet_id):
        with self._transaction() as db:
            item, _ = self._scoped_object(db, self._actor(db, token), packet_id, "packet")
            return self._public(item)

    def queue_packet(self, token, packet_id):
        with self._transaction() as db:
            actor = self._actor(db, token)
            packet, case = self._scoped_object(db, actor, packet_id, "packet", "owner")
            self._fresh_packet(db, packet, case)
            for row in db.execute(
                "SELECT id,data FROM rc_objects WHERE case_id=? AND kind='job' AND state IN ('queued','running')",
                (case["id"],),
            ):
                if json.loads(row["data"]).get("packet_id") == packet_id:
                    return self._public(self._object(db, row["id"]))
            return self._public(
                self._queue(db, actor, case, token, "render", {"packet_id": packet_id})
            )

    def render_packet(self, token, packet_id, *, parser, job=None):
        def actor_for(db):
            if job is None:
                return self._actor(db, token)
            current = self._object(db, job["id"])
            if (
                current["state"] != "running"
                or current["data"].get("lease") != job["data"].get("lease")
                or current["data"].get("lease_until", 0) <= self._now()
            ):
                raise DomainError("lease_lost", 409)
            actor = self._job_actor(db, current)
            if current["data"]["deadline"] <= self._now():
                raise DomainError("deadline_exceeded", 409)
            current["data"]["lease_until"] = min(current["data"]["deadline"], self._now() + 180)
            self._update_object(db, current)
            db.execute(
                "INSERT OR REPLACE INTO rc_meta VALUES('worker_heartbeat',?)", (str(self._now()),)
            )
            return actor

        with self._transaction() as db:
            actor = actor_for(db)
            packet, case = self._scoped_object(db, actor, packet_id, "packet", "owner")
            self._fresh_packet(db, packet, case)
            if packet["state"] in {"rendered", "approved"}:
                return self._public(packet)
            data = packet["data"]
            attachments = []
            for entry in data["attachments"]:
                document, _ = self._scoped_object(db, actor, entry["document_id"], "document")
                attachments.append((entry, self._blob_read(document["data"]["blob_id"])))
            before = fingerprint(data)
        import pymupdf

        cover = render_pdf(
            title="Repair coverage enquiry",
            paragraphs=data["paragraphs"],
            manifest_hash=before,
            approved=True,
        )
        manifest = {
            "version": 1,
            "packet_id": packet_id,
            "purpose": data["purpose"],
            "recipient": data["recipient"],
            "case_revision": data["case_revision"],
            "registry_epoch": data["registry_epoch"],
            "sources": data["sources"],
            "attachments": [],
        }
        originals = []
        with pymupdf.open(stream=cover, filetype="pdf") as document:
            for entry, raw in attachments:
                clean = parser.run(
                    "sanitize", raw, entry["filename"], redactions=entry["redactions"]
                )
                if job is not None:
                    with self._transaction() as db:
                        actor = actor_for(db)
                        current, current_case = self._scoped_object(
                            db, actor, packet_id, "packet", "owner"
                        )
                        self._fresh_packet(db, current, current_case)
                with pymupdf.open(stream=clean, filetype="pdf") as appendix:
                    document.insert_pdf(appendix)
                    if len(document) > 100:
                        raise DomainError("packet_page_limit", 413)
                manifest["attachments"].append(
                    {**entry, "derivative_sha256": hashlib.sha256(clean).hexdigest()}
                )
                if entry["mode"] == "original":
                    originals.append(
                        (
                            "original-"
                            + entry["document_id"]
                            + "."
                            + entry["filename"].rsplit(".", 1)[-1],
                            raw,
                        )
                    )
            final_pdf = document.tobytes(garbage=4, deflate=True)
            if len(final_pdf) > 20 * 1024 * 1024:
                raise DomainError("packet_size_limit", 413)
        manifest["pdf_sha256"] = hashlib.sha256(final_pdf).hexdigest()
        identity = fingerprint({"draft": before, "manifest": manifest})
        manifest["fingerprint"] = identity
        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in [
                ("packet.pdf", final_pdf),
                ("manifest.json", canonical(manifest).encode()),
                *originals,
            ]:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, content)
        with self._transaction() as db:
            actor = actor_for(db)
            current, case = self._scoped_object(db, actor, packet_id, "packet", "owner")
            self._fresh_packet(db, current, case)
            if fingerprint(current["data"]) != before:
                raise DomainError("stale_artifact", 409)
            current["data"].update(
                {
                    "fingerprint": identity,
                    "manifest": manifest,
                    "pdf_blob": self._blob_write(final_pdf, db=db, case_id=case["id"]),
                    "zip_blob": self._blob_write(bundle.getvalue(), db=db, case_id=case["id"]),
                }
            )
            self._update_object(db, current, state="rendered")
            self._audit(db, actor, case, "packet_rendered")
            return self._public(current)

    def approve_packet(self, token, packet_id, exact_fingerprint):
        with self._transaction() as db:
            actor = self._actor(db, token)
            packet, case = self._scoped_object(db, actor, packet_id, "packet", "owner")
            self._fresh_packet(db, packet, case)
            if packet["state"] != "rendered" or exact_fingerprint != packet["data"].get(
                "fingerprint"
            ):
                raise DomainError("artifact_fingerprint_mismatch", 409)
            packet["data"]["approval"] = {
                "actor_id": actor["id"],
                "fingerprint": exact_fingerprint,
                "created": self._now(),
                "expires": self._now() + 86400,
            }
            self._update_object(db, packet, state="approved")
            db.execute("UPDATE cases SET lifecycle='packet_approved' WHERE id=?", (case["id"],))
            self._audit(db, actor, case, "packet_approved")
            return self._public(packet)

    def revoke_packet(self, token, packet_id):
        with self._transaction() as db:
            actor = self._actor(db, token)
            packet, case = self._scoped_object(db, actor, packet_id, "packet", "owner")
            packet["data"].pop("approval", None)
            self._update_object(
                db, packet, state="rendered" if packet["data"].get("fingerprint") else "draft"
            )
            self._audit(db, actor, case, "packet_approval_revoked")

    def packet_pdf(self, token, packet_id):
        with self._transaction() as db:
            packet, _ = self._scoped_object(db, self._actor(db, token), packet_id, "packet")
            if not packet["data"].get("pdf_blob"):
                raise DomainError("packet_not_rendered", 409)
            return self._blob_read(packet["data"]["pdf_blob"])

    def download_packet(self, token, packet_id):
        with self._transaction() as db:
            actor = self._actor(db, token)
            packet, case = self._scoped_object(db, actor, packet_id, "packet", "owner")
            self._fresh_packet(db, packet, case)
            approval = packet["data"].get("approval")
            if (
                not approval
                or approval["expires"] <= self._now()
                or approval["fingerprint"] != packet["data"].get("fingerprint")
            ):
                raise DomainError("approval_required", 409)
            result = self._blob_read(packet["data"]["zip_blob"])
            self._audit(db, actor, case, "approved_packet_downloaded")
            return result
