"""Behavioral tests written before the PropertyBrief implementation."""

from datetime import UTC, datetime, timedelta

import pytest
from contracts.propertybrief import AgentDecision, PropertyInput
from fastapi.testclient import TestClient
from propertybrief_api.api import create_app
from propertybrief_api.evidence import normalize_record, validate_draft
from propertybrief_api.sources import DEFINITIONS, SourceClient, candidate, derive_bbl
from propertybrief_api.store import Store
from pydantic import ValidationError

BUILDING = {
    "buildingid": "375411",
    "boroid": "3",
    "block": "3031",
    "lot": "15",
    "bin": "3327904",
    "housenumber": "22 FRONT",
    "streetname": "STAGG STREET",
    "boro": "BROOKLYN",
    "recordstatus": "Active",
}
VIOLATION = {
    "violationid": "10081311",
    "buildingid": "375411",
    "boroid": "3",
    "block": "3031",
    "lot": "15",
    "class": "C",
    "violationstatus": "Close",
    "currentstatus": "VIOLATION CLOSED",
    "novdescription": "Historical hot water record",
}


def test_strict_contracts():
    with pytest.raises(ValidationError):
        PropertyInput(address="22 FRONT STAGG STREET", borough="Brooklyn", surprise=True)
    with pytest.raises(ValidationError):
        PropertyInput(address="", borough="Brooklyn")
    with pytest.raises(ValidationError):
        AgentDecision(action="shell", tool="curl", summary="bad", reflection="", record_ids=[])


def test_identifier_and_candidate_scope():
    assert derive_bbl("3", "3031", "15") == "3030310015"
    for values in [("0", "3031", "15"), ("3", "0", "0"), ("3", "999999", "15")]:
        with pytest.raises(ValueError):
            derive_bbl(*values)
    result = candidate(BUILDING)
    assert result["bbl"] == "3030310015"
    assert result["address"] == "22 FRONT STAGG STREET"
    with pytest.raises(ValueError):
        candidate({**BUILDING, "recordstatus": "Inactive"})


def test_closed_violations_and_temporal_conflicts():
    row = normalize_record("hpd_violations", VIOLATION, candidate(BUILDING))
    assert row["status"] == "historical"
    assert row["scope"] == "building"
    order = normalize_record(
        "vacate",
        {
            "building_id": "375411",
            "vacate_order_number": "260021",
            "vacate_effective_date": "2025-10-15T00:00:00.000",
            "actual_rescind_date": "2025-01-07T00:00:00.000",
        },
        candidate(BUILDING),
    )
    assert "temporal_conflict" in order["flags"]
    assert order["status"] == "unknown"


def test_wrong_building_rejected_and_parcel_scope_retained():
    with pytest.raises(ValueError):
        normalize_record("hpd_violations", {**VIOLATION, "buildingid": "999"}, candidate(BUILDING))
    row = normalize_record(
        "dob_violations",
        {
            "isn_dob_bis_viol": "1",
            "boro": "3",
            "block": "03031",
            "lot": "0015",
            "violation_category": "V-DOB VIOLATION - ACTIVE",
        },
        candidate(BUILDING),
    )
    assert row["scope"] == "parcel"
    assert "parcel_scope" in row["flags"]


def test_test_records_never_become_active_findings():
    row = normalize_record(
        "dob_violations",
        {
            "isn_dob_bis_viol": "24174",
            "bin": "3327904",
            "violation_category": "V-DOB VIOLATION - ACTIVE",
            "disposition_comments": "DELETED BY CES BECAUSE TEST RECORD",
        },
        candidate(BUILDING),
    )
    assert "test_or_deleted_record" in row["flags"]
    assert row["status"] == "unknown"


def test_paging_deduplicates_and_reports_caps():
    requests = []

    def get(url, params):
        requests.append(params)
        return [VIOLATION] if params["$offset"] == 0 else []

    client = SourceClient(get=get, page_size=1, max_pages=2, metadata=False)
    result = client.fetch("hpd_violations", candidate(BUILDING))
    assert result["completeness"] == "complete_for_query"
    assert len(result["records"]) == 1
    assert requests[0]["buildingid"] == "375411"
    capped = SourceClient(get=lambda *_: [VIOLATION], page_size=1, max_pages=1, metadata=False)
    assert capped.fetch("hpd_violations", candidate(BUILDING))["completeness"] == "truncated"


def test_source_failure_is_not_zero_results():
    def get(*_):
        raise TimeoutError("network failure")

    result = SourceClient(get=get, metadata=False).fetch("hpd_violations", candidate(BUILDING))
    assert result["outcome"] == "unavailable"
    assert result["completeness"] == "unknown"


def test_complete_empty_source_and_unknown_tool():
    client = SourceClient(get=lambda *_: [], metadata=False)
    assert client.fetch("hpd_violations", candidate(BUILDING))["outcome"] == "no_records"
    with pytest.raises(ValueError):
        client.fetch("https://evil.invalid", candidate(BUILDING))


def make_case(store):
    item = store.create_case(
        PropertyInput(address="22 FRONT STAGG STREET", borough="Brooklyn"), "tester"
    )
    store.save_candidates(item["id"], [candidate(BUILDING)])
    store.confirm_identity(item["id"], "375411", 1, "tester")
    return store.case(item["id"])


def test_identity_confirmation_and_run_idempotency(tmp_path):
    store = Store(tmp_path)
    item = make_case(store)
    a = store.enqueue(item["id"], "Investigate public records", "key", "tester")
    assert store.enqueue(item["id"], "Investigate public records", "key", "tester")["id"] == a["id"]
    with pytest.raises(ValueError):
        store.enqueue(item["id"], "Different intent", "key", "tester")
    with pytest.raises(ValueError):
        store.confirm_identity(item["id"], "375411", 1, "tester")


def test_lease_fencing_checkpoint_and_counters(tmp_path):
    store = Store(tmp_path)
    item = make_case(store)
    run = store.enqueue(item["id"], "Investigate", "k", "tester")
    claim = store.claim()
    assert claim["id"] == run["id"]
    store.reserve(run["id"], claim["lease"], "actions", 16)
    result = SourceClient(get=lambda *_: [], metadata=False).fetch(
        "hpd_violations", item["identity"]
    )
    store.save_observation(run["id"], claim["lease"], "hpd_violations", result)
    assert store.run(run["id"])["preview"]["coverage"]["hpd_violations"] == "complete_for_query"
    with pytest.raises(ValueError):
        store.reserve(run["id"], "stale-worker", "actions", 16)
    with store.connect() as db:
        db.execute("UPDATE runs SET lease_until=? WHERE id=?", ("2000-01-01", run["id"]))
    recovered = store.claim()
    assert recovered["lease"] != claim["lease"]
    assert recovered["actions"] == 1
    assert recovered["deadline"] == claim["deadline"]


def test_budget_hard_limit(tmp_path):
    store = Store(tmp_path)
    item = make_case(store)
    run = store.enqueue(item["id"], "Investigate", "k", "tester")
    claim = store.claim()
    store.reserve(run["id"], claim["lease"], "model_calls", 1)
    with pytest.raises(ValueError, match="budget"):
        store.reserve(run["id"], claim["lease"], "model_calls", 1)
    assert store.run(run["id"])["model_calls"] == 1


def test_cancel_and_deadline_block_new_work(tmp_path):
    store = Store(tmp_path)
    item = make_case(store)
    run = store.enqueue(item["id"], "Investigate", "k", "tester")
    claim = store.claim()
    store.cancel(run["id"])
    with pytest.raises(ValueError, match="cancel"):
        store.reserve(run["id"], claim["lease"], "actions", 16)
    with store.connect() as db:
        db.execute(
            "UPDATE runs SET cancelled=0, deadline=? WHERE id=?",
            ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), run["id"]),
        )
    with pytest.raises(ValueError, match="deadline"):
        store.reserve(run["id"], claim["lease"], "actions", 16)


def test_citation_identity_and_exact_field_validation():
    from contracts.propertybrief import ReportDraft

    observation = SourceClient(get=lambda *_: [VIOLATION], max_pages=1, metadata=False).fetch(
        "hpd_violations", candidate(BUILDING)
    )
    row = observation["records"][0]
    finding = {
        "id": "f1",
        "text": "The captured record is historical.",
        "kind": "recorded_fact",
        "evidence": [
            {
                "source": "hpd_violations",
                "record_id": row["id"],
                "field": "violationstatus",
                "value": "Close",
            }
        ],
    }
    draft = ReportDraft(
        summary="Recorded historical evidence.", findings=[finding], tasks=[], limitations=[]
    )
    validate_draft(draft, {"hpd_violations": observation})
    draft.findings[0].evidence[0].value = "Open"
    with pytest.raises(ValueError):
        validate_draft(draft, {"hpd_violations": observation})


def test_authenticated_api_csrf_and_review_gate(tmp_path):
    app = create_app(data_dir=tmp_path, username="tester", password="actual-test-password")
    client = TestClient(app)
    assert client.get("/v1/cases").status_code == 401
    client.auth = ("tester", "actual-test-password")
    assert (
        client.post(
            "/v1/cases",
            json={"address": "22 FRONT STAGG STREET", "borough": "Brooklyn"},
            headers={"Origin": "https://evil.invalid"},
        ).status_code
        == 403
    )
    item = make_case(app.state.store)
    response = client.post(
        f"/v1/cases/{item['id']}/messages",
        json={"content": "Investigate"},
        headers={"Idempotency-Key": "api-test"},
    )
    assert response.status_code == 202
    assert client.get(f"/v1/runs/{response.json()['id']}").status_code == 200
    assert client.get("/v1/runs/missing").status_code == 404


def test_registry_has_eight_required_sources():
    assert sum(value.required for value in DEFINITIONS.values()) == 8


def test_dob_queries_use_official_zero_padded_parcel_fields():
    captured = []
    client = SourceClient(get=lambda url, params: captured.append(params) or [], metadata=False)
    client.fetch("dob_violations", candidate(BUILDING))
    query = captured[0]["$where"]
    assert "bin = '3327904'" in query
    assert "block = '03031'" in query
    assert "lot = '00015'" in query


def test_dob_bin_match_preserves_historical_parcel_difference():
    row = normalize_record(
        "dob_violations",
        {
            "isn_dob_bis_viol": "285232",
            "bin": "3327904",
            "boro": "3",
            "block": "03031",
            "lot": "00001",
            "violation_category": "V*-DOB VIOLATION - DISMISSED",
        },
        candidate(BUILDING),
    )
    assert row["scope"] == "building"
    assert "parcel_identifier_differs" in row["flags"]
    assert row["status"] == "historical"


def test_conflicting_secondary_identity_is_visible_not_silently_discarded():
    row = normalize_record(
        "hpd_complaints",
        {
            "problem_id": "10530138",
            "building_id": "375411",
            "bin": "3000000",
            "bbl": "3028670001",
            "complaint_status": "CLOSE",
        },
        candidate(BUILDING),
    )
    assert "identity_conflict" in row["flags"]
    assert row["status"] == "unknown"
