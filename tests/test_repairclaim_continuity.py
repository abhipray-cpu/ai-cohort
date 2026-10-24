"""Consumer controls, replies and financial bookkeeping with fictional documents."""

import io
import json
import zipfile

import pytest
from contracts.repairclaim import Money, OutcomeEvent
from repairclaim_api.errors import DomainError
from repairclaim_api.store import Store
from repairclaim_api.worker import run_once
from test_repairclaim_workflow import FixtureParser, flow, investigate, make_pdf, register


def upload(store, token, case_id, text, kind="response"):
    result = store.add_document(
        token,
        case_id,
        "fixture.pdf",
        kind,
        make_pdf(text),
        store.get_case(token, case_id)["revision"],
    )
    run_once(store, parser=FixtureParser())
    return result


def test_response_requests_records_without_accusing_or_promising_success(flow):
    store, _, owner, _, _, case = flow
    document = upload(
        store, owner.token, case["id"], "Please provide the diagnostic code and missing invoice."
    )
    response = store.record_response(owner.token, case["id"], document["id"], "response-1")
    assert response["reasons"][0]["category"] == "missing_evidence"
    assert response["review_required"] is True
    assert (
        response["comparison"]["case_revision"]
        == store.get_case(owner.token, case["id"])["revision"]
    )
    assert response["comparison"]["manufacturer_confirmation"] is False
    assert "not_independent_confirmation" in response["reasons"][0]["attribution"]
    again = store.record_response(owner.token, case["id"], document["id"], "response-1")
    assert response["id"] == again["id"]


def test_followup_binds_response_reasons_without_accusing(flow):
    store, _, owner, _, _, case = flow
    doc = upload(store, owner.token, case["id"], "Please provide missing diagnostic code.")
    store.record_response(owner.token, case["id"], doc["id"], "reason")
    register(store)
    job = investigate(store, owner.token, case["id"])
    packet = store.create_packet(
        owner.token, case["id"], job["id"], "Dealer", [], "followup", "followup"
    )
    assert any("missing diagnostic code" in line for line in packet["paragraphs"])
    assert packet["response_refs"][0]["document_id"] == doc["id"]


def test_outcomes_keep_actual_received_separate_and_require_real_case_document_references(flow):
    store, _, owner, other, _, case = flow
    event = OutcomeEvent(
        id="payment-1",
        kind="received",
        amount=Money(amount="100.10", currency="USD"),
        evidence_class="user_reported",
        evidence_ref="user-statement",
        repair_line_id="repair-1",
    )
    store.record_outcome(owner.token, case["id"], event, "payment-1")
    approved = event.model_copy(update={"id": "approval-1", "kind": "approved"})
    store.record_outcome(owner.token, case["id"], approved, "approval-1")
    assert (
        str(store.outcome_totals(owner.token, case["id"])["USD"]["received"]["user_reported"])
        == "100.10"
    )
    with pytest.raises(DomainError):
        store.outcome_totals(other.token, case["id"])
    claimed = event.model_copy(
        update={"id": "documented", "evidence_class": "documented", "evidence_ref": "fake-doc"}
    )
    with pytest.raises(DomainError):
        store.record_outcome(owner.token, case["id"], claimed, "doc-1")


def test_estimate_cannot_be_presented_as_documented_money_received(flow):
    store, _, owner, _, _, case = flow
    document = upload(store, owner.token, case["id"], "Estimate: USD 100.10", "estimate")
    event = OutcomeEvent(
        id="claim",
        kind="received",
        amount=Money(amount="100.10", currency="USD"),
        evidence_class="documented",
        evidence_ref=document["id"],
        repair_line_id="repair",
    )
    with pytest.raises(DomainError):
        store.record_outcome(
            owner.token,
            case["id"],
            event,
            "claim",
            evidence_page=1,
            evidence_quote="Estimate: USD 100.10",
        )


def test_documented_received_requires_literal_payment_record_and_currency(flow):
    store, _, owner, _, _, case = flow
    document = upload(store, owner.token, case["id"], "Refund received: USD 100.10", "receipt")
    event = OutcomeEvent(
        id="received",
        kind="received",
        amount=Money(amount="100.10", currency="USD"),
        evidence_class="documented",
        evidence_ref=document["id"],
        repair_line_id="repair",
    )
    result = store.record_outcome(
        owner.token,
        case["id"],
        event,
        "received",
        evidence_page=1,
        evidence_quote="Refund received: USD 100.10",
    )
    assert result["event"]["evidence_class"] == "documented"


def test_reminders_distinguish_suggestions_and_can_be_cancelled(flow):
    store, _, owner, _, _, case = flow
    reminder = store.add_reminder(
        owner.token,
        case["id"],
        "2026-11-01T09:00:00-04:00",
        "America/New_York",
        "suggested_followup",
        "Follow up if no reply",
    )
    assert reminder["provenance"] == "suggested_followup"
    store.cancel_reminder(owner.token, reminder["id"])
    assert store.case_details(owner.token, case["id"])["reminders"][0]["status"] == "cancelled"
    with pytest.raises(DomainError):
        store.add_reminder(
            owner.token, case["id"], "2026-11-01", "UTC", "programme_documented", "Must file"
        )


def test_monitoring_expiry_is_not_renewed_by_repeated_background_work(flow):
    store, clock, owner, _, vehicle, case = flow
    register(store)
    store.set_monitoring(owner.token, vehicle["id"], [case["id"]], 10)
    clock[0] += 11
    register(store, "90000", "r2")
    store.rematch_monitoring()
    assert store.notifications(owner.token) == []


def test_helper_cannot_enable_monitoring_or_claim_a_response_for_another_case(flow):
    store, _, owner, other, vehicle, case = flow
    other_id = store.authenticate(other.token)["id"]
    store.grant(owner.token, case["id"], other_id, "editor")
    with pytest.raises(DomainError):
        store.set_monitoring(other.token, vehicle["id"], [case["id"]], 10)


def test_case_export_and_delete_cover_private_features_and_worker_results(flow):
    store, _, owner, other, _, case = flow
    document = upload(store, owner.token, case["id"], "PRIVATE-CASE-CONTENT", "invoice")
    data = store.export_case(owner.token, case["id"])
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        content = json.loads(archive.read("case.json"))
        assert content["case"]["id"] == case["id"]
    store.delete_case(owner.token, case["id"], store.get_case(owner.token, case["id"])["revision"])
    with pytest.raises(DomainError):
        store.get_document(owner.token, document["id"])
    assert store.private_orphans() == []
    with pytest.raises(DomainError):
        store.export_case(other.token, case["id"])


def test_one_use_invitation_and_revocation_do_not_grant_household_wide_access(flow):
    store, _clock, owner, other, _vehicle, case = flow
    invitation = store.create_invitation(owner.token, case["id"], "viewer", ttl=60)
    assert invitation["token"] not in repr(store.case_details(owner.token, case["id"]))
    store.accept_invitation(other.token, invitation["token"])
    assert store.get_case(other.token, case["id"])["role"] == "viewer"
    with pytest.raises(DomainError):
        store.accept_invitation(other.token, invitation["token"])
    store.revoke_grant(owner.token, case["id"], store.authenticate(other.token)["id"])
    with pytest.raises(DomainError):
        store.get_case(other.token, case["id"])


def test_close_reopen_and_unknown_answers_are_durable_without_inference(flow):
    store, _, owner, _, _, case = flow
    register(store)
    result = investigate(store, owner.token, case["id"])
    store.answer_question(owner.token, result["id"], "unknown")
    assert store.get_job(owner.token, result["id"])["question_answer"] == "unknown"
    store.set_case_state(
        owner.token, case["id"], "closed", store.get_case(owner.token, case["id"])["revision"]
    )
    assert store.get_case(owner.token, case["id"])["lifecycle"] == "closed"
    store.set_case_state(
        owner.token, case["id"], "fact_review", store.get_case(owner.token, case["id"])["revision"]
    )
    restarted = Store(store.path, clock=store.clock)
    assert restarted.get_case(owner.token, case["id"])["lifecycle"] == "fact_review"
