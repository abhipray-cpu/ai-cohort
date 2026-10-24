"""Full local workflow mechanics with authored programme/documents; no live data."""

import hashlib
from datetime import UTC, datetime

import pymupdf
import pytest
from contracts.repairclaim import Condition, EvidenceAnchor, Fact, ProgrammeRevision
from repairclaim_api.documents import parse_document, sanitized_attachment
from repairclaim_api.errors import DomainError
from repairclaim_api.store import Store
from repairclaim_api.worker import run_once


class FixtureParser:
    """Only injected by tests, never the production factory."""

    def run(self, operation, data, filename, **options):
        if operation == "parse":
            return parse_document(data, filename, ocr=False)
        if operation == "sanitize":
            return sanitized_attachment(data, filename, options.get("redactions", []))
        if operation == "preview":
            with pymupdf.open(stream=data, filetype="pdf") as document:
                return document[options.get("page", 1) - 1].get_pixmap().tobytes("png")
        raise AssertionError(operation)


def make_pdf(text):
    document = pymupdf.open()
    document.new_page().insert_text((50, 70), text)
    data = document.tobytes()
    document.close()
    return data


@pytest.fixture
def flow(tmp_path):
    clock = [1_000_000.0]
    store = Store(tmp_path / "rc.sqlite3", clock=lambda: clock[0])
    store.provision_owner("owner", "workflow-test-password")
    store.provision_owner("other", "workflow-test-password")
    owner = store.login("owner", "workflow-test-password")
    other = store.login("other", "workflow-test-password")
    vehicle = store.create_vehicle(
        owner.token, make="Honda", model="Fixture", model_year=2018, jurisdiction="US"
    )
    case = store.create_case(owner.token, vehicle["id"], "Compressor repair")
    facts = (
        *store.snapshot(owner.token, case["id"]).facts,
        Fact(field="component", value="compressor", status="user_reported"),
    )
    store.replace_facts(owner.token, case["id"], 1, facts)
    return store, clock, owner, other, vehicle, case


def register(store, limit="100000", revision="r1"):
    text = f"Fixture programme only. At most {limit} miles at repair. Component compressor."
    raw = make_pdf(text)
    parsed = parse_document(raw, "fixture.pdf")
    store.capture_source("fixture-source", "https://static.nhtsa.gov/odi/fixture.pdf", raw, parsed)
    anchor = EvidenceAnchor(
        document_id="fixture-source",
        sha256=hashlib.sha256(raw).hexdigest(),
        page=1,
        quote=f"At most {limit} miles at repair.",
    )
    programme = ProgrammeRevision(
        family_id="fixture-family",
        revision=revision,
        category="warranty_extension",
        jurisdiction="US",
        make="Honda",
        reviewer_id="fixture-reviewer",
        reviewed_at=datetime(2026, 10, 22, tzinfo=UTC),
        conditions=(
            Condition(
                id="mileage",
                field="repair_mileage",
                operator="at_most",
                expected=limit,
                unit="mi",
                anchor=anchor,
            ),
        ),
    )
    store.activate_programme(programme)
    return programme


def investigate(store, token, case_id, key="first"):
    job = store.start_investigation(
        token, case_id, store.get_case(token, case_id)["revision"], key, mode="rules", allowance=0
    )
    run_once(store, parser=FixtureParser())
    return store.get_job(token, job["id"])


@pytest.mark.parametrize(
    ("mileage", "expected"),
    [
        (None, "missing evidence"),
        ("90000", "potentially applicable"),
        ("110000", "appears outside conditions"),
    ],
)
def test_packet_headings_preserve_actual_assessment_not_blanket_potential(flow, mileage, expected):
    store, _, owner, _, _, case = flow
    register(store)
    if mileage is not None:
        snapshot = store.snapshot(owner.token, case["id"])
        store.replace_facts(
            owner.token,
            case["id"],
            snapshot.revision,
            (
                *snapshot.facts,
                Fact(field="repair_mileage", value=mileage, unit="mi", status="user_reported"),
            ),
        )
    job = investigate(store, owner.token, case["id"])
    packet = store.create_packet(
        owner.token, case["id"], job["id"], "Dealer", [], "enquiry", "assessment-heading"
    )
    headings = [line for line in packet["paragraphs"] if "programme" in line.lower()]
    assert len(headings) == 1
    assert f"Assessment: {expected}." in headings[0]
    assert "Potential programme reference:" not in headings[0]


def test_upload_is_explicitly_associated_encrypted_and_correctable(flow):
    store, _, owner, other, _, case = flow
    raw = make_pdf("Repair mileage: 90000 mi\nPRIVATE-ADDRESS")
    result = store.add_document(owner.token, case["id"], "invoice.pdf", "invoice", raw, 2)
    assert result["status"] == "queued"
    run_once(store, parser=FixtureParser())
    document = store.get_document(owner.token, result["id"])
    assert document["status"] == "ready"
    assert document["parsed"]["proposals"][0]["status"] == "extracted"
    assert not any(b"PRIVATE-ADDRESS" in path.read_bytes() for path in store.blob_dir.glob("*"))
    with pytest.raises(DomainError):
        store.get_document(other.token, result["id"])
    store.confirm_proposals(
        owner.token, result["id"], [0], store.get_case(owner.token, case["id"])["revision"]
    )
    assert any(
        f.field == "repair_mileage" and f.status == "confirmed"
        for f in store.snapshot(owner.token, case["id"]).facts
    )


def test_investigation_unknown_resume_and_packet_require_exact_approval(flow):
    store, _, owner, _, _, case = flow
    register(store)
    first = investigate(store, owner.token, case["id"])
    assert first["status"] == "awaiting_evidence"
    assert first["result"]["next_question"]["field"] == "repair_mileage"
    snapshot = store.snapshot(owner.token, case["id"])
    store.replace_facts(
        owner.token,
        case["id"],
        snapshot.revision,
        (
            *snapshot.facts,
            Fact(field="repair_mileage", value="90000", unit="mi", status="user_reported"),
        ),
    )
    second = investigate(store, owner.token, case["id"], "second")
    assert second["status"] == "review_ready"
    packet = store.create_packet(
        owner.token, case["id"], second["id"], "Dealer service desk", [], "enquiry", "packet-1"
    )
    with pytest.raises(DomainError, match="approval_required"):
        store.download_packet(owner.token, packet["id"])
    store.render_packet(owner.token, packet["id"], parser=FixtureParser())
    packet = store.get_packet(owner.token, packet["id"])
    store.approve_packet(owner.token, packet["id"], packet["fingerprint"])
    result = store.download_packet(owner.token, packet["id"])
    assert result.startswith(b"PK")
    assert store.case_details(owner.token, case["id"])["manual_submissions"] == []
    snapshot = store.snapshot(owner.token, case["id"])
    store.replace_facts(owner.token, case["id"], snapshot.revision, snapshot.facts)
    with pytest.raises(DomainError, match="stale_artifact"):
        store.download_packet(owner.token, packet["id"])


def test_programme_changes_invalidate_approval_and_notify_only_consented_cases(flow):
    store, _, owner, _, vehicle, case = flow
    register(store)
    snapshot = store.snapshot(owner.token, case["id"])
    store.replace_facts(
        owner.token,
        case["id"],
        snapshot.revision,
        (
            *snapshot.facts,
            Fact(field="repair_mileage", value="95000", unit="mi", status="user_reported"),
        ),
    )
    job = investigate(store, owner.token, case["id"])
    store.set_monitoring(owner.token, vehicle["id"], [case["id"]], 86400)
    register(store, "90000", "r2")
    store.rematch_monitoring()
    notifications = store.notifications(owner.token)
    assert len(notifications) == 1
    assert notifications[0]["change"]["old_revision"] == "r1"
    assert notifications[0]["change"]["new_revision"] == "r2"
    assert store.get_job(owner.token, job["id"])["stale"] is True
    store.rematch_monitoring()
    assert len(store.notifications(owner.token)) == 1
    store.revoke_monitoring(owner.token, vehicle["id"])
    assert store.notifications(owner.token) == []


def test_idempotency_cancellation_and_deleted_authority_fence_worker(flow):
    store, _, owner, _, _, case = flow
    register(store)
    revision = store.get_case(owner.token, case["id"])["revision"]
    job = store.start_investigation(
        owner.token, case["id"], revision, "once", mode="rules", allowance=0
    )
    again = store.start_investigation(
        owner.token, case["id"], revision, "once", mode="rules", allowance=0
    )
    assert job["id"] == again["id"]
    with pytest.raises(DomainError, match="idempotency_conflict"):
        store.start_investigation(
            owner.token, case["id"], revision, "once", mode="codex", allowance=1
        )
    store.cancel_job(owner.token, job["id"])
    assert run_once(store, parser=FixtureParser()) is None
    assert store.get_job(owner.token, job["id"])["status"] == "cancelled"


def test_no_inventory_is_not_a_completed_negative_and_no_automatic_paid_fallback(flow):
    store, _, owner, _, _, case = flow
    job = investigate(store, owner.token, case["id"])
    assert job["result"]["search"]["search_status"] == "unavailable"
    assert job["result"]["search"]["state"] is None
    assert job["attempts"] == []


def test_queued_packet_renews_lease_between_bounded_attachment_stages(flow):
    store, clock, owner, _, _, case = flow
    documents = []
    for number in range(4):
        document = store.add_document(
            owner.token,
            case["id"],
            f"fixture-{number}.pdf",
            "invoice",
            make_pdf("Repair mileage: 90000 mi"),
            store.get_case(owner.token, case["id"])["revision"],
        )
        run_once(store, parser=FixtureParser())
        documents.append({"document_id": document["id"], "mode": "sanitized", "redactions": []})
    register(store)
    job = investigate(store, owner.token, case["id"])
    packet = store.create_packet(
        owner.token, case["id"], job["id"], "Fixture dealer", documents, "enquiry", "long-render"
    )
    render = store.queue_packet(owner.token, packet["id"])

    class SlowStages(FixtureParser):
        def run(self, operation, *args, **kwargs):
            result = super().run(operation, *args, **kwargs)
            if operation == "sanitize":
                clock[0] += 55
            return result

    run_once(store, parser=SlowStages())
    assert store.get_packet(owner.token, packet["id"])["status"] == "rendered"
    assert store.get_job(owner.token, render["id"])["status"] == "review_ready"
