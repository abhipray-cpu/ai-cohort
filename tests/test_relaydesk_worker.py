import json

from agent_core.provider import ProviderTimeoutError, StructuredGeneration
from relaydesk_api.worker import run_once
from test_relaydesk_core import batch, setup


class Provider:
    def __init__(self, values):
        self.values = iter(values)

    def generate(self, **kwargs):
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return StructuredGeneration(
            text=json.dumps(value), exit_code=0, elapsed_ms=1, tools_audited=True
        )


def queued(tmp_path, egress=False):
    from contracts.relaydesk import Policy

    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    store.policy(
        "alice",
        case["id"],
        Policy(expected_revision=store.case("alice", case["id"])["revision"], model_egress=egress),
    )
    conv = store.conversation("alice", case["id"])
    job = store.enqueue(
        "alice", conv["id"], conv["session"]["id"], "What failed in this investigation?", "question"
    )
    return store, case, conv, job


def test_denied_model_egress_uses_explicit_fallback(tmp_path):
    store, _case, _conv, job = queued(tmp_path)
    run_once(store, provider=Provider([]), encoder=None)
    result = store.job("alice", job["id"])
    assert result["status"] == "partial" and result["model_calls"] == 0
    assert result["output"]["payload"]["recall"]["mode"] == "lexical_only"
    assert "egress" in result["reason"].lower()


def test_late_timeout_preserves_sources_and_stage_event(tmp_path):
    store, case, _conv, job = queued(tmp_path, True)
    run_once(
        store, provider=Provider([ProviderTimeoutError("labelled test timeout")]), encoder=None
    )
    result = store.job("alice", job["id"])
    assert result["status"] == "partial" and store.sources("alice", case["id"])
    assert any(
        e["kind"] == "provider_timeout" for e in store.changes("alice", case["id"], 0)["events"]
    )


def test_foreign_memory_references_get_bounded_repair(tmp_path):
    store, case, _conv, job = queued(tmp_path, True)
    bad = {
        "summary": "Unsupported claim",
        "claims": [{"text": "a fact", "memory_ids": ["foreign"]}],
        "questions": [],
        "limitations": [],
    }
    good = {
        "summary": "No verified resolution is established.",
        "claims": [],
        "questions": ["Confirm the current environment."],
        "limitations": ["Evidence is participant reported."],
    }
    run_once(store, provider=Provider([{"proposals": []}, bad, good]), encoder=None)
    result = store.job("alice", job["id"])
    assert result["model_calls"] == 3
    assert result["output"]["payload"]["ai_succeeded"] is True
    assert any(
        e["kind"] == "validation_failed" for e in store.changes("alice", case["id"], 0)["events"]
    )


def test_changed_context_cannot_be_published_as_current(tmp_path):
    store, case, _, job = queued(tmp_path, True)

    class MutatingProvider(Provider):
        def generate(self, **kwargs):
            result = super().generate(**kwargs)
            if '"summary"' in result.text:
                store.import_messages("alice", case["id"], batch("New contradictory evidence"))
            return result

    run_once(
        store,
        encoder=None,
        provider=MutatingProvider(
            [
                {"proposals": []},
                {"summary": "Old context answer", "claims": [], "questions": [], "limitations": []},
            ]
        ),
    )
    result = store.job("alice", job["id"])
    assert "Stale context rejected" in result["output"]["payload"]["limitations"]


def test_historical_query_does_not_send_future_context(tmp_path):
    store, _case, conv, _ = queued(tmp_path, True)
    job = store.enqueue(
        "alice",
        conv["id"],
        conv["session"]["id"],
        "What was known?",
        "historical",
        options={"as_of": "2024-01-01T00:00:00+00:00"},
    )
    # Cancel the earlier current-time question so the historical job is next.
    with store.connect() as db:
        db.execute("UPDATE jobs SET status='cancelled' WHERE key='question'")

    class InspectProvider(Provider):
        def generate(self, **kwargs):
            assert "Rollback was attempted" not in kwargs["prompt"]
            assert "What failed in this investigation?" not in kwargs["prompt"]
            return super().generate(**kwargs)

    run_once(
        store,
        encoder=None,
        provider=InspectProvider(
            [
                {
                    "summary": "No evidence before cutoff",
                    "claims": [],
                    "questions": [],
                    "limitations": [],
                }
            ]
        ),
    )
    assert store.job("alice", job["id"])["output"]["payload"]["recall"]["hits"] == []
