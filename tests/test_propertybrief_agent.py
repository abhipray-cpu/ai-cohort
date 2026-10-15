"""Adaptive loop, critique, recovery, and export acceptance."""

import json

import pytest
from agent_core.provider import ProviderTimeoutError, StructuredGeneration
from contracts.propertybrief import Review
from propertybrief_api.sources import REQUIRED, SourceClient
from propertybrief_api.store import Store
from propertybrief_api.worker import run_once
from test_propertybrief import VIOLATION, make_case


def decision(
    tool="hpd_violations", action="query", reflection="Previous evidence determines this check."
):
    return {
        "action": action,
        "tool": tool,
        "summary": f"Check {tool or 'completion'}.",
        "reflection": reflection,
        "record_ids": [],
    }


class Scripted:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []

    def generate(self, *, prompt, schema):
        self.prompts.append(prompt)
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return StructuredGeneration(
            text=value if isinstance(value, str) else json.dumps(value), exit_code=0, elapsed_ms=1
        )


def fake_sources():
    def get(url, params):
        if "wvxf-dwi5" in url:
            return [VIOLATION]
        return []

    return SourceClient(get=get, metadata=False)


def enqueue(tmp_path):
    store = Store(tmp_path)
    item = make_case(store)
    run = store.enqueue(item["id"], "Investigate", "agent-test", "tester")
    return store, item, run


def test_later_timeout_preserves_preview_and_failure_history(tmp_path):
    store, _, run = enqueue(tmp_path)
    provider = Scripted([decision(), ProviderTimeoutError("later timeout")])
    assert run_once(store, provider=provider, sources=fake_sources())
    result = store.run(run["id"])
    assert result["status"] == "partial"
    assert result["preview"]["sources"][0]["records"][0]["id"] == "10081311"
    assert any(
        e["stage"] == "provider_timeout" and e["outcome"] == "failed" for e in result["events"]
    )
    assert result["report"]["payload"]["critique"]["outcome"] == "not_assessed"


def test_all_sources_critique_review_and_export(tmp_path):
    store, _, run = enqueue(tmp_path)
    draft = {
        "summary": "Historical records require review; the listed checks are complete.",
        "findings": [
            {
                "id": "f1",
                "text": "A captured housing violation is historical.",
                "kind": "recorded_fact",
                "evidence": [
                    {
                        "source": "hpd_violations",
                        "record_id": "10081311",
                        "field": "violationstatus",
                        "value": "Close",
                    }
                ],
            }
        ],
        "tasks": [
            {
                "title": "Request correction documentation",
                "recipient": "seller",
                "priority": "medium",
                "reason": "Clarify the historical record.",
                "finding_ids": ["f1"],
                "verification": "Compare supplied documentation with the recorded notice.",
            }
        ],
        "limitations": ["Public records do not establish physical condition."],
    }
    provider = Scripted(
        [
            *(decision(key) for key in REQUIRED),
            decision("", "finish"),
            draft,
            {"outcome": "pass", "unsupported_finding_ids": [], "issues": [], "next_check": ""},
        ]
    )
    run_once(store, provider=provider, sources=fake_sources())
    result = store.run(run["id"])
    assert result["status"] == "completed"
    assert result["actions"] == 8
    assert result["model_calls"] == 11
    report = result["report"]
    with pytest.raises(ValueError, match="Review"):
        store.export(report["id"])
    store.review(report["id"], Review(expected_revision=1), "reviewer")
    exported = store.export(report["id"])
    assert exported["report"]["payload"]["coverage"] == {
        key: "complete_for_query" for key in REQUIRED
    }
    assert len(exported["report"]["payload"]["source_manifest"]) == 9
    assert "reflection" in provider.prompts[1]


def test_repeat_loop_stops_with_hard_budget(tmp_path):
    store, _, run = enqueue(tmp_path)
    provider = Scripted([decision()] * 10)
    run_once(store, provider=provider, sources=fake_sources())
    result = store.run(run["id"])
    assert result["status"] == "partial"
    assert "repeat" in result["stop_reason"].lower()
    assert result["actions"] <= 3
    assert result["model_calls"] <= 4


def test_malformed_decision_repairs_once_and_counts_calls(tmp_path):
    store, _, run = enqueue(tmp_path)
    provider = Scripted(["not JSON", "still not JSON"])
    run_once(store, provider=provider, sources=fake_sources())
    result = store.run(run["id"])
    assert result["model_calls"] == 2
    assert result["status"] == "partial"
    assert len([e for e in result["events"] if e["stage"] == "validation"]) == 2


def test_wrong_tool_cannot_dispatch(tmp_path):
    store, _, run = enqueue(tmp_path)
    provider = Scripted([decision("shell"), decision("shell")])
    run_once(store, provider=provider, sources=fake_sources())
    result = store.run(run["id"])
    assert result["status"] == "partial"
    assert not result["observations"]
    assert any(e["stage"] == "tool_arguments" for e in result["events"])


def test_critique_removes_unsupported_claims(tmp_path):
    store, _, run = enqueue(tmp_path)
    draft = {
        "summary": "Recorded observations.",
        "findings": [
            {
                "id": "f1",
                "text": "Overbroad interpretation.",
                "kind": "interpretation",
                "evidence": [
                    {
                        "source": "hpd_violations",
                        "record_id": "10081311",
                        "field": "violationstatus",
                        "value": "Close",
                    }
                ],
            }
        ],
        "tasks": [],
        "limitations": [],
    }
    provider = Scripted(
        [
            *(decision(key) for key in REQUIRED),
            decision("", "finish"),
            draft,
            {
                "outcome": "revise",
                "unsupported_finding_ids": ["f1"],
                "issues": ["Evidence does not establish the interpretation."],
                "next_check": "",
            },
            {
                "summary": "Historical observation only.",
                "findings": [],
                "tasks": [],
                "limitations": ["Interpretation removed after critique."],
            },
        ]
    )
    run_once(store, provider=provider, sources=fake_sources())
    result = store.run(run["id"])
    assert result["status"] == "partial"
    assert not result["report"]["payload"]["draft"]["findings"]
    assert result["report"]["payload"]["critique"]["outcome"] == "revise"


def test_resume_keeps_saved_observations_and_cumulative_calls(tmp_path):
    store, _, run = enqueue(tmp_path)
    run_once(
        store, provider=Scripted([decision(), ProviderTimeoutError("stop")]), sources=fake_sources()
    )
    before = store.run(run["id"])
    store.resume(run["id"], "grant-two")
    run_once(store, provider=Scripted([ProviderTimeoutError("stop again")]), sources=fake_sources())
    after = store.run(run["id"])
    assert after["observations"] == before["observations"]
    assert after["model_calls"] == before["model_calls"] + 1
    with pytest.raises(ValueError):
        store.resume(run["id"], "grant-three")


def test_partial_export_carries_gaps(tmp_path):
    store, _, run = enqueue(tmp_path)
    run_once(
        store, provider=Scripted([ProviderTimeoutError("unavailable")]), sources=fake_sources()
    )
    report = store.run(run["id"])["report"]
    with pytest.raises(ValueError, match="Acknowledge"):
        store.review(report["id"], Review(expected_revision=1), "reviewer")
    store.review(report["id"], Review(expected_revision=1, acknowledge_limits=True), "reviewer")
    assert len(store.export(report["id"])["report"]["payload"]["gaps"]) == 8


def test_malformed_tool_result_has_failure_event_and_partial_report(tmp_path):
    class BrokenSource:
        def fetch(self, source, identity):
            return {"source": source, "identity": identity["building_id"], "records": "invalid"}

    store, _, run = enqueue(tmp_path)
    run_once(store, provider=Scripted([decision()]), sources=BrokenSource())
    result = store.run(run["id"])
    assert result["status"] == "partial"
    assert any(
        event["stage"] == "tool_response" and event["outcome"] == "failed"
        for event in result["events"]
    )


def test_unknown_inspection_ids_are_repaired_before_dispatch(tmp_path):
    store, _, run = enqueue(tmp_path)
    bad = {**decision("hpd_violations", "inspect"), "record_ids": ["invented"]}
    draft = {
        "summary": "Captured records reviewed.",
        "findings": [],
        "tasks": [],
        "limitations": [],
    }
    provider = Scripted(
        [
            *(decision(key) for key in REQUIRED),
            bad,
            decision("", "finish"),
            draft,
            {"outcome": "pass", "unsupported_finding_ids": [], "issues": [], "next_check": ""},
        ]
    )
    run_once(store, provider=provider, sources=fake_sources())
    result = store.run(run["id"])
    assert result["status"] == "completed"
    assert result["actions"] == 8
    assert any(e["stage"] == "tool_arguments" for e in result["events"])


def test_decision_schema_limits_ids_to_supplied_records():
    from propertybrief_api.worker import decision_schema

    run = {"observations": {"hpd_violations": {"records": [{"id": "10081311"}]}}}
    schema = decision_schema(run)
    assert schema["properties"]["record_ids"]["items"]["enum"] == ["10081311"]
    assert "shell" not in schema["properties"]["tool"]["enum"]


def test_iteration_limit_uses_reserved_finalization_calls(tmp_path):
    store, _, run = enqueue(tmp_path)
    choices = [
        *(decision(key) for key in REQUIRED),
        *(decision(key, "compare") for key in REQUIRED),
    ]
    draft = {
        "summary": "Bounded investigation observations.",
        "findings": [],
        "tasks": [],
        "limitations": ["Action limit reached."],
    }
    provider = Scripted(
        [
            *choices,
            draft,
            {"outcome": "pass", "unsupported_finding_ids": [], "issues": [], "next_check": ""},
        ]
    )
    run_once(store, provider=provider, sources=fake_sources())
    result = store.run(run["id"])
    assert result["actions"] == 16
    assert result["model_calls"] == 18
    assert result["status"] == "partial"
    assert any(e["stage"] == "self_critique" for e in result["events"])
