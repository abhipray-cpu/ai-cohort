import json

import pytest
from agent_core.provider import ProviderTimeoutError
from contracts.propertybrief import ReportDraft, Review
from fastapi.testclient import TestClient
from propertybrief_api.api import create_app
from propertybrief_api.sources import SourceClient
from propertybrief_api.store import Store
from propertybrief_api.worker import context, run_once
from test_propertybrief import BUILDING, VIOLATION, make_case
from test_propertybrief_agent import Scripted, decision, fake_sources


def test_review_edits_create_new_revision_and_revalidate(tmp_path):
    store = Store(tmp_path)
    case = make_case(store)
    run = store.enqueue(case["id"], "Investigate", "k", "tester")
    run_once(
        store,
        provider=Scripted([decision(), ProviderTimeoutError("later timeout")]),
        sources=fake_sources(),
    )
    original = store.run(run["id"])["report"]
    draft = ReportDraft.model_validate(original["payload"]["draft"])
    draft.findings[0].evidence[0].value = "Open"
    with pytest.raises(ValueError, match="Citation"):
        store.review(
            original["id"],
            Review(expected_revision=1, acknowledge_limits=True, draft=draft),
            "reviewer",
        )
    draft = ReportDraft.model_validate(original["payload"]["draft"])
    draft.limitations.append("Analyst requested a current inspection.")
    edited = store.review(
        original["id"],
        Review(expected_revision=1, acknowledge_limits=True, draft=draft),
        "reviewer",
    )
    assert edited["id"] != original["id"]
    assert store.report(original["id"])["payload"] == original["payload"]
    assert edited["payload"]["critique"]["outcome"] == "not_assessed_after_edit"


def test_context_does_not_starve_later_sources():
    from propertybrief_api.sources import candidate

    result = SourceClient(get=lambda *_: [VIOLATION], max_pages=1, metadata=False).fetch(
        "hpd_violations", candidate(BUILDING)
    )
    row = result["records"][0]
    row["fields"]["long"] = "x" * 6000
    result["records"] = [dict(row, id=str(i)) for i in range(20)]
    result["count"] = 20
    other = {
        **result,
        "source": "hpd_complaints",
        "records": [dict(row, id="other", fields={"status": "CLOSE", "detail": "y" * 3000})],
        "count": 1,
    }
    run = {
        "identity": candidate(BUILDING),
        "question": "Investigate",
        "observations": {"hpd_violations": result, "hpd_complaints": other},
        "state": {},
        "actions": 0,
        "model_calls": 0,
    }
    observed = context(run)
    assert observed["observations"]["hpd_complaints"]["records"]
    assert len(json.dumps(observed["observations"])) < 24000


def test_api_does_not_expose_worker_lease_or_full_raw_payloads(tmp_path):
    app = create_app(data_dir=tmp_path, username="tester", password="real-test-password")
    case = make_case(app.state.store)
    run = app.state.store.enqueue(case["id"], "Investigate", "k", "tester")
    claim = app.state.store.claim()
    response = TestClient(app).get(f"/v1/runs/{run['id']}", auth=("tester", "real-test-password"))
    assert response.status_code == 200
    assert claim["lease"] not in response.text
    assert "observations" not in response.json()


def test_metadata_failure_after_rows_keeps_completeness_unknown():
    calls = 0

    def get(url, params):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"rowsUpdatedAt": 1}
        if calls == 2:
            return [VIOLATION]
        raise TimeoutError("metadata failed")

    from propertybrief_api.sources import candidate

    result = SourceClient(get=get).fetch("hpd_violations", candidate(BUILDING))
    assert result["outcome"] == "partial"
    assert result["completeness"] == "unknown"


def test_negated_complaint_warning_is_valid_but_positive_claim_is_rejected():
    from propertybrief_api.evidence import validate_draft
    from propertybrief_api.sources import candidate

    raw = {"problem_id": "1", "building_id": "375411", "complaint_status": "CLOSE"}
    observation = SourceClient(get=lambda *_: [raw], max_pages=1, metadata=False).fetch(
        "hpd_complaints", candidate(BUILDING)
    )
    draft = ReportDraft(
        summary="Recorded evidence.",
        findings=[
            {
                "id": "f1",
                "text": "This complaint is not a verified violation.",
                "kind": "recorded_fact",
                "evidence": [
                    {
                        "source": "hpd_complaints",
                        "record_id": "1",
                        "field": "complaint_status",
                        "value": "CLOSE",
                    }
                ],
            }
        ],
    )
    validate_draft(draft, {"hpd_complaints": observation})
    draft.findings[0].text = "This complaint is a verified violation."
    with pytest.raises(ValueError):
        validate_draft(draft, {"hpd_complaints": observation})


def test_confirmed_identity_can_be_cited_and_opened_as_evidence(tmp_path):
    from propertybrief_api.evidence import validate_draft
    from propertybrief_api.sources import candidate

    identity = candidate(BUILDING)
    draft = ReportDraft(
        summary="Confirmed property scope.",
        findings=[
            {
                "id": "f1",
                "text": "The captured building row records BIN 3327904.",
                "kind": "recorded_fact",
                "evidence": [
                    {
                        "source": "buildings",
                        "record_id": "375411",
                        "field": "bin",
                        "value": "3327904",
                    }
                ],
            }
        ],
    )
    validate_draft(draft, {}, identity)
    store = Store(tmp_path)
    case = make_case(store)
    run = store.enqueue(case["id"], "Investigate", "identity-evidence", "tester")
    source = next(row for row in run["preview"]["sources"] if row["source"] == "buildings")
    assert (
        store.snapshot(source["snapshot_id"])["payload"]["records"][0]["fields"]["bin"] == "3327904"
    )


def test_recovered_older_run_has_an_identity_snapshot(tmp_path):
    store = Store(tmp_path)
    case = make_case(store)
    run = store.enqueue(case["id"], "Investigate", "old-run", "tester")
    with store.connect() as db:
        db.execute("DELETE FROM snapshots WHERE run_id=?", (run["id"],))
    recovered = store.claim()
    assert any(
        source["source"] == "buildings" and source.get("snapshot_id")
        for source in recovered["preview"]["sources"]
    )


def test_evidence_source_aliases_are_rejected_by_schema():
    from contracts.propertybrief import EvidenceRef
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EvidenceRef(source="identity", record_id="375411", field="bbl", value="3030310015")


def test_critic_context_prioritizes_the_actual_cited_rows():
    from propertybrief_api.sources import candidate

    observation = SourceClient(get=lambda *_: [VIOLATION], max_pages=1, metadata=False).fetch(
        "hpd_violations", candidate(BUILDING)
    )
    row = observation["records"][0]
    observation["records"] = [dict(row, id=str(i)) for i in range(30)]
    observation["count"] = 30
    run = {
        "identity": candidate(BUILDING),
        "question": "Investigate",
        "observations": {"hpd_violations": observation},
        "state": {},
        "actions": 0,
        "model_calls": 0,
    }
    result = context(run, priority={"hpd_violations": {"29"}})
    assert [row["id"] for row in result["observations"]["hpd_violations"]["records"]] == ["29"]
    assert result["citation_rows_omitted"] == 0


def test_report_schema_binds_fields_to_the_actual_source():
    from propertybrief_api.sources import candidate
    from propertybrief_api.worker import report_schema

    identity = candidate(BUILDING)
    observation = SourceClient(get=lambda *_: [VIOLATION], max_pages=1, metadata=False).fetch(
        "hpd_violations", identity
    )
    schema = report_schema({"identity": identity, "observations": {"hpd_violations": observation}})
    branch = next(
        item
        for item in schema["$defs"]["EvidenceRef"]["anyOf"]
        if item["properties"]["source"]["enum"] == ["hpd_violations"]
    )
    assert "violationstatus" in branch["properties"]["field"]["enum"]
    assert "status" not in branch["properties"]["field"]["enum"]


def test_inspection_delivers_selected_rows_without_hiding_other_sources():
    from propertybrief_api.sources import candidate

    observation = SourceClient(get=lambda *_: [VIOLATION], max_pages=1, metadata=False).fetch(
        "hpd_violations", candidate(BUILDING)
    )
    template = observation["records"][0]
    rows = [dict(template, id=str(i), fields={"detail": "x" * 1500}) for i in range(8)]
    observations = {"hpd_violations": dict(observation, records=rows, count=len(rows))}
    observations.update(
        {
            key: dict(observation, source=key, records=[dict(template, id=key)], count=1)
            for key in (
                "vacate",
                "aep",
                "underlying",
                "dob_complaints",
                "dob_violations",
                "dob_ecb",
            )
        }
    )
    run = {
        "identity": candidate(BUILDING),
        "question": "Inspect selected records",
        "observations": observations,
        "state": {"last_observation": {"source": "hpd_violations", "inspected_records": rows[:4]}},
        "actions": 1,
        "model_calls": 1,
    }
    result = context(run)
    assert {row["id"] for row in result["observations"]["hpd_violations"]["records"]} >= {
        "0",
        "1",
        "2",
        "3",
    }
    assert result["observations"]["vacate"]["records"]


def test_empty_checks_do_not_consume_row_context_allowance():
    from propertybrief_api.sources import candidate

    observation = SourceClient(get=lambda *_: [VIOLATION], max_pages=1, metadata=False).fetch(
        "hpd_violations", candidate(BUILDING)
    )
    rows = [
        dict(observation["records"][0], id=str(i), fields={"detail": "x" * 2000}) for i in range(2)
    ]
    observations = {"hpd_violations": dict(observation, records=rows, count=2)}
    observations.update(
        {
            key: dict(observation, records=[], count=0)
            for key in (
                "vacate",
                "aep",
                "underlying",
                "dob_complaints",
                "dob_violations",
                "dob_ecb",
                "hpd_complaints",
            )
        }
    )
    run = {
        "identity": candidate(BUILDING),
        "question": "Review",
        "observations": observations,
        "state": {},
        "actions": 8,
        "model_calls": 9,
    }
    result = context(run)
    assert len(result["observations"]["hpd_violations"]["records"]) == 2
