"""Authenticated application surface; public registry mutation is deliberately absent."""

from typing import Annotated, Literal

from contracts.repairclaim import Contract, EvidenceAnchor, Fact, Identifier, OutcomeEvent
from fastapi import Depends, Query, Request, Response
from pydantic import Field, StrictInt

BASE = "/api/repairclaim/v1"
Revision = Annotated[StrictInt, Field(ge=1)]
Key = Annotated[str, Field(min_length=1, max_length=128)]


class Confirm(Contract):
    expected_revision: Revision
    selected: Annotated[list[StrictInt], Field(max_length=100)]


class Correction(Contract):
    expected_revision: Revision
    index: Annotated[StrictInt, Field(ge=0)] | None = None
    replacement: Fact | None = None


class Investigation(Contract):
    expected_revision: Revision
    key: Key
    mode: Literal["rules", "codex", "jev"] = "rules"
    allowance: Annotated[StrictInt, Field(ge=0, le=6)] = 0
    egress_fingerprint: Annotated[str, Field(max_length=64)] | None = None


class Attachment(Contract):
    document_id: Identifier
    mode: Literal["sanitized", "original"] = "sanitized"
    redactions: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=200)]], Field(max_length=40)
    ] = Field(default_factory=list)


class Packet(Contract):
    job_id: Identifier
    recipient: Annotated[str, Field(min_length=1, max_length=200)]
    key: Key
    attachments: Annotated[list[Attachment], Field(max_length=20)] = Field(default_factory=list)
    purpose: Literal["enquiry", "reimbursement", "records_request", "followup"] = "enquiry"
    notes: Annotated[str, Field(max_length=2000)] = ""


class Approval(Contract):
    fingerprint: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class Monitoring(Contract):
    case_ids: Annotated[list[Identifier], Field(min_length=1, max_length=10)]
    ttl: Annotated[StrictInt, Field(gt=0, le=90 * 86400)]


class ResponseInput(Contract):
    document_id: Identifier
    key: Key


class Submission(Contract):
    packet_id: Identifier
    channel: Literal["portal", "email", "postal_mail", "in_person", "other"]
    sent_at: Annotated[str, Field(max_length=80)]
    key: Key


class Outcome(Contract):
    event: OutcomeEvent
    key: Key
    evidence_page: Annotated[StrictInt, Field(ge=1, le=100)] | None = None
    evidence_quote: Annotated[str, Field(max_length=2000)] | None = None


class Reminder(Contract):
    due_at: Annotated[str, Field(max_length=80)]
    timezone: Annotated[str, Field(max_length=80)]
    provenance: Literal["user_entered", "suggested_followup", "programme_documented"]
    label: Annotated[str, Field(min_length=1, max_length=200)]
    source_anchor: EvidenceAnchor | None = None


class Lifecycle(Contract):
    expected_revision: Revision
    state: Literal["closed", "paused", "fact_review"]


class Invite(Contract):
    role: Literal["viewer", "editor"]
    ttl: Annotated[StrictInt, Field(gt=0, le=86400)] = 86400


class Accept(Contract):
    invitation: Annotated[str, Field(min_length=20, max_length=128)]


class Acknowledge(Contract):
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class Answer(Contract):
    answer: Literal["unknown", "later", "answered"]


class Erase(Contract):
    confirmation: Literal["DELETE MY ACCOUNT"]


def register_routes(
    app, store, read_token, write_token, parser, *, codex_enabled=False, jev_enabled=False
):
    read, write = Depends(read_token), Depends(write_token)

    @app.get(BASE + "/capabilities")
    def capabilities(token: str = read):
        return {
            "codex_enabled": codex_enabled,
            "jev_enabled": jev_enabled,
            "submission": "manual_download_only",
            "registry": store.registry_status(),
        }

    @app.get(BASE + "/vehicles")
    def vehicles(token: str = read):
        return store.list_vehicles(token)

    @app.get(BASE + "/sources/{source_id}/revisions/{digest}/preview")
    def source_preview(
        source_id: Identifier,
        digest: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")],
        page: Annotated[int, Query(ge=1, le=100)] = 1,
        token: str = read,
    ):
        return Response(
            parser.run(
                "preview", store.source_bytes(token, source_id, digest), "source.pdf", page=page
            ),
            media_type="image/png",
        )

    @app.delete(BASE + "/invitations/{item_id}", status_code=204)
    def revoke_invitation(item_id: Identifier, token: str = write):
        store.revoke_invitation(token, item_id)

    @app.get(BASE + "/cases/{case_id}/workspace")
    def workspace(case_id: Identifier, token: str = read):
        return {
            **store.case_details(token, case_id),
            "snapshot": store.snapshot(token, case_id).model_dump(mode="json"),
            "totals": store.outcome_totals(token, case_id),
            "timeline": store.timeline(token, case_id),
        }

    @app.post(BASE + "/cases/{case_id}/documents", status_code=202)
    async def upload(
        case_id: Identifier,
        request: Request,
        filename: Annotated[str, Query(max_length=160)],
        kind: str,
        revision: Annotated[int, Query(ge=1)],
        token: str = write,
    ):
        return store.add_document(token, case_id, filename, kind, await request.body(), revision)

    @app.get(BASE + "/documents/{document_id}")
    def document(document_id: Identifier, token: str = read):
        return store.get_document(token, document_id)

    @app.get(BASE + "/documents/{document_id}/preview")
    def document_preview(
        document_id: Identifier, page: Annotated[int, Query(ge=1, le=100)] = 1, token: str = read
    ):
        content, filename = store.document_bytes(token, document_id)
        return Response(parser.run("preview", content, filename, page=page), media_type="image/png")

    @app.post(BASE + "/documents/{document_id}/confirm")
    def confirm(document_id: Identifier, body: Confirm, token: str = write):
        return store.confirm_proposals(token, document_id, body.selected, body.expected_revision)

    @app.post(BASE + "/cases/{case_id}/corrections")
    def correct(case_id: Identifier, body: Correction, token: str = write):
        return store.correct_fact(token, case_id, **body.model_dump())

    @app.get(BASE + "/cases/{case_id}/analysis-preview")
    def analysis_preview(
        case_id: Identifier, mode: Literal["codex", "jev"] = "codex", token: str = read
    ):
        return store.analysis_preview(token, case_id, mode=mode)

    @app.post(BASE + "/cases/{case_id}/investigations", status_code=202)
    def investigate(case_id: Identifier, body: Investigation, token: str = write):
        from repairclaim_api.errors import DomainError

        if body.mode == "codex" and not codex_enabled:
            raise DomainError("provider_not_configured", 409)
        if body.mode == "jev" and not jev_enabled:
            raise DomainError("provider_not_configured", 409)
        return store.start_investigation(token, case_id, **body.model_dump())

    @app.get(BASE + "/jobs/{job_id}")
    def job(job_id: Identifier, token: str = read):
        return store.get_job(token, job_id)

    @app.post(BASE + "/jobs/{job_id}/cancel", status_code=204)
    def cancel(job_id: Identifier, token: str = write):
        store.cancel_job(token, job_id)

    @app.post(BASE + "/jobs/{job_id}/resume")
    def resume(job_id: Identifier, token: str = write):
        return store.resume_job(token, job_id)

    @app.post(BASE + "/jobs/{job_id}/answer", status_code=204)
    def answer(job_id: Identifier, body: Answer, token: str = write):
        store.answer_question(token, job_id, body.answer)

    @app.post(BASE + "/jobs/{job_id}/usage-acknowledgement", status_code=204)
    def unknown(job_id: Identifier, body: Acknowledge, token: str = write):
        store.acknowledge_unknown_usage(token, job_id, body.reason)

    @app.post(BASE + "/cases/{case_id}/packets", status_code=201)
    def packet(case_id: Identifier, body: Packet, token: str = write):
        return store.create_packet(token, case_id, **body.model_dump())

    @app.get(BASE + "/packets/{packet_id}")
    def get_packet(packet_id: Identifier, token: str = read):
        return store.get_packet(token, packet_id)

    @app.post(BASE + "/packets/{packet_id}/render", status_code=202)
    def render(packet_id: Identifier, token: str = write):
        return store.queue_packet(token, packet_id)

    @app.get(BASE + "/packets/{packet_id}/preview")
    def preview(
        packet_id: Identifier, page: Annotated[int, Query(ge=1, le=2100)] = 1, token: str = read
    ):
        return Response(
            parser.run("preview", store.packet_pdf(token, packet_id), "packet.pdf", page=page),
            media_type="image/png",
        )

    @app.post(BASE + "/packets/{packet_id}/approve")
    def approve(packet_id: Identifier, body: Approval, token: str = write):
        return store.approve_packet(token, packet_id, body.fingerprint)

    @app.post(BASE + "/packets/{packet_id}/revoke", status_code=204)
    def revoke(packet_id: Identifier, token: str = write):
        store.revoke_packet(token, packet_id)

    def zip_response(data, name):
        return Response(
            data,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{name}.zip"'},
        )

    @app.post(BASE + "/packets/{packet_id}/download")
    def download(packet_id: Identifier, token: str = write):
        return zip_response(store.download_packet(token, packet_id), "approved-packet")

    @app.post(BASE + "/vehicles/{vehicle_id}/monitoring")
    def monitoring(vehicle_id: Identifier, body: Monitoring, token: str = write):
        return store.set_monitoring(token, vehicle_id, body.case_ids, body.ttl)

    @app.delete(BASE + "/vehicles/{vehicle_id}/monitoring", status_code=204)
    def revoke_monitoring(vehicle_id: Identifier, token: str = write):
        store.revoke_monitoring(token, vehicle_id)

    @app.get(BASE + "/notifications")
    def notifications(token: str = read):
        return store.notifications(token)

    @app.post(BASE + "/notifications/{item_id}/acknowledge", status_code=204)
    def acknowledge(item_id: Identifier, token: str = write):
        store.acknowledge_notification(token, item_id)

    @app.post(BASE + "/cases/{case_id}/responses", status_code=201)
    def response(case_id: Identifier, body: ResponseInput, token: str = write):
        return store.record_response(token, case_id, **body.model_dump())

    @app.post(BASE + "/cases/{case_id}/submissions", status_code=201)
    def submission(case_id: Identifier, body: Submission, token: str = write):
        return store.record_manual_submission(token, case_id, **body.model_dump())

    @app.post(BASE + "/cases/{case_id}/outcomes", status_code=201)
    def outcome(case_id: Identifier, body: Outcome, token: str = write):
        return store.record_outcome(token, case_id, **body.model_dump())

    @app.post(BASE + "/cases/{case_id}/reminders", status_code=201)
    def reminder(case_id: Identifier, body: Reminder, token: str = write):
        return store.add_reminder(token, case_id, **body.model_dump())

    @app.delete(BASE + "/reminders/{item_id}", status_code=204)
    def cancel_reminder(item_id: Identifier, token: str = write):
        store.cancel_reminder(token, item_id)

    @app.post(BASE + "/cases/{case_id}/lifecycle")
    def lifecycle(case_id: Identifier, body: Lifecycle, token: str = write):
        return store.set_case_state(token, case_id, **body.model_dump())

    @app.get(BASE + "/cases/{case_id}/export")
    def export(case_id: Identifier, token: str = read):
        return zip_response(store.export_case(token, case_id), "private-case-export")

    @app.post(BASE + "/cases/{case_id}/invitations", status_code=201)
    def invite(case_id: Identifier, body: Invite, token: str = write):
        return store.create_invitation(token, case_id, **body.model_dump())

    @app.post(BASE + "/invitations/accept")
    def accept(body: Accept, token: str = write):
        return store.accept_invitation(token, body.invitation)

    @app.post(BASE + "/account/erase", status_code=204)
    def erase(body: Erase, token: str = write):
        store.erase_account(token, body.confirmation)
