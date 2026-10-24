"""Simulated provider failures validate the implementation, not model quality."""

import json

import pytest
from agent_core.provider import ProviderTimeoutError, StructuredGeneration
from repairclaim_api.errors import DomainError
from repairclaim_api.worker import run_once
from test_repairclaim_workflow import FixtureParser, flow, register


class Provider:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0

    def generate(self, **_):
        self.calls += 1
        result = next(self.outputs)
        if isinstance(result, Exception):
            raise result
        return StructuredGeneration(text=result, exit_code=0, elapsed_ms=1)


def start(store, owner, case):
    preview = store.analysis_preview(owner.token, case["id"])
    return store.start_investigation(
        owner.token,
        case["id"],
        store.get_case(owner.token, case["id"])["revision"],
        "agent",
        mode="codex",
        allowance=2,
        egress_fingerprint=preview["fingerprint"],
    )


def test_parse_failure_has_validation_event_and_bounded_retry(flow):
    store, _, owner, _, _, case = flow
    register(store)
    job = start(store, owner, case)
    provider = Provider(
        [
            "not-json",
            json.dumps(
                {
                    "candidate_family": "fixture-family",
                    "agrees_with_conditions": True,
                    "needs_human_review": True,
                    "confidence": 0.5,
                    "citations": [],
                }
            ),
        ]
    )
    run_once(store, parser=FixtureParser(), provider=provider)
    result = store.get_job(owner.token, job["id"])
    assert provider.calls == 2
    assert [attempt["status"] for attempt in result["attempts"]] == [
        "validation_failure",
        "success",
    ]
    assert result["status"] == "manual_review"


def test_timeout_keeps_rules_checkpoint_and_prevents_unacknowledged_paid_retry(flow):
    store, _, owner, _, _, case = flow
    register(store)
    job = start(store, owner, case)
    provider = Provider([ProviderTimeoutError("simulated")])
    run_once(store, parser=FixtureParser(), provider=provider)
    result = store.get_job(owner.token, job["id"])
    assert result["status"] == "partial"
    assert result["result"]["search"]["candidates"]
    assert result["attempts"][0]["status"] == "provider_timeout"
    preview = store.analysis_preview(owner.token, case["id"])
    with pytest.raises(DomainError, match="unknown_usage_hold"):
        store.start_investigation(
            owner.token,
            case["id"],
            store.get_case(owner.token, case["id"])["revision"],
            "new-agent",
            mode="codex",
            allowance=1,
            egress_fingerprint=preview["fingerprint"],
        )


def test_egress_requires_owner_approval_of_the_exact_minimized_context(flow):
    store, _, owner, _, _, case = flow
    register(store)
    with pytest.raises(DomainError, match="egress_approval_required"):
        store.start_investigation(
            owner.token,
            case["id"],
            store.get_case(owner.token, case["id"])["revision"],
            "no-consent",
            mode="codex",
            allowance=1,
        )
    preview = store.analysis_preview(owner.token, case["id"])
    assert "auth_hash" not in str(preview)
    assert "vin" not in [fact["field"] for fact in preview["context"]["facts"]]


def test_invalid_parser_tool_fact_is_rejected_with_validation_history(flow):
    store, _, owner, _, _, case = flow
    from test_repairclaim_workflow import make_pdf

    class BrokenParser(FixtureParser):
        def run(self, *args, **kwargs):
            result = super().run(*args, **kwargs)
            result["proposals"][0]["unit"] = "bananas"
            return result

    document = store.add_document(
        owner.token, case["id"], "fixture.pdf", "invoice", make_pdf("Repair mileage: 90000 mi"), 2
    )
    run_once(store, parser=BrokenParser())
    assert store.get_document(owner.token, document["id"])["status"] == "partial"
    assert any(
        event["action"] == "validation_failure" for event in store.timeline(owner.token, case["id"])
    )


def test_erasure_during_parsing_discards_late_result_without_crashing_worker(flow):
    store, _, owner, _, _, case = flow
    from test_repairclaim_workflow import make_pdf

    class DeleteDuringParse(FixtureParser):
        def run(self, *args, **kwargs):
            parsed = super().run(*args, **kwargs)
            store.delete_case(owner.token, case["id"], 3)
            return parsed

    store.add_document(
        owner.token, case["id"], "fixture.pdf", "invoice", make_pdf("Repair mileage: 90000 mi"), 2
    )
    assert run_once(store, parser=DeleteDuringParse()) is not None
    assert store.list_cases(owner.token) == []
