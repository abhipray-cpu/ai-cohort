from datetime import UTC, datetime, timedelta

import pytest
from contracts.relaydesk import Recall, SourceMessage
from relaydesk_api.recall import RecallEngine, index_case
from relaydesk_api.worker import run_once
from test_relaydesk_core import batch, setup
from test_relaydesk_worker import Provider, queued


def test_idle_index_advances_past_already_indexed_memories(tmp_path):
    from relaydesk_api.embeddings import Encoder

    path = "var/models/relaydesk-minilm"
    from pathlib import Path

    if not (Path(path) / "manifest.json").exists():
        pytest.skip("Provision real encoder first")
    store, case = setup(tmp_path)
    for i in range(3):
        value = batch(f"Reported failure {i}")
        value.messages[0].source_key = str(i)
        store.import_messages("alice", case["id"], value)
    encoder = Encoder(path)
    for _ in range(3):
        assert index_case(store, "alice", case["id"], encoder, limit=1)["saved"] == 1
    assert (
        RecallEngine(store, encoder).search("alice", case["id"], Recall(question="failure"))[
            "coverage"
        ]["indexed"]
        == 3
    )


def test_old_source_body_unavailable_before_its_edit(tmp_path):
    store, case = setup(tmp_path)
    value = batch("Current edited content")
    value.messages[0].updated_at = "2025-02-01T00:00:00+00:00"
    store.import_messages("alice", case["id"], value)
    assert not store.memories("alice", case["id"], as_of="2025-01-15T00:00:00+00:00")
    assert store.memories("alice", case["id"], as_of="2025-03-01T00:00:00+00:00")


def test_account_promoted_context_revocation_and_erasure(tmp_path):
    store, origin = setup(tmp_path)
    store.import_messages("alice", origin["id"], batch())
    memory = store.memories("alice", origin["id"])[0]
    store.promote("alice", memory["id"], 1)
    target = store.create_case("alice", origin["account_id"], "Related escalation")
    store.membership("alice", origin["id"], "bob", ["investigator"])
    store.membership("alice", target["id"], "bob", ["investigator"])
    conv = store.conversation("bob", target["id"])
    job = store.enqueue(
        "bob", conv["id"], conv["session"]["id"], "What rollback failed?", "related"
    )
    run_once(store, encoder=None, provider=Provider([]))
    result = store.job("bob", job["id"])
    assert result["output"]["payload"]["recall"]["hits"]
    oid = result["output_id"]
    store.membership("alice", origin["id"], "bob", [])
    with pytest.raises(PermissionError):
        store.output("bob", oid)
    source = store.sources("alice", origin["id"])[0]
    store.erase("alice", origin["id"], [source["id"]], "ERASE")
    assert store.output("alice", oid)["payload"] == {}


def test_cancelled_job_never_calls_provider(tmp_path):
    store, _, _, job = queued(tmp_path, True)
    store.cancel("alice", job["id"])
    assert run_once(store, encoder=None, provider=Provider([])) is False
    assert store.job("alice", job["id"])["status"] == "cancelled"


def test_expired_lease_is_fenced_and_budget_survives_reclaim(tmp_path):
    store, _, _, job = queued(tmp_path, True)
    old = store.claim()
    store.reserve(old["id"], old["lease"])
    with store.connect() as db:
        db.execute(
            "UPDATE jobs SET lease_until=? WHERE id=?",
            ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), job["id"]),
        )
    new = store.claim()
    assert new["model_calls"] == 1 and new["lease"] != old["lease"]
    with store.connect() as db, pytest.raises(ValueError):
        store.fence(db, old["id"], old["lease"])


def test_source_utf8_byte_cap_is_not_character_cap():
    with pytest.raises(ValueError):
        SourceMessage(
            source_key="large",
            author="author",
            body="😀" * 9000,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )


def test_reply_timeout_retains_successful_extraction(tmp_path):
    from agent_core.provider import ProviderTimeoutError

    store, case, _, job = queued(tmp_path, True)
    source = store.sources("alice", case["id"])[0]
    quote = source["body"]
    run_once(
        store,
        encoder=None,
        provider=Provider(
            [
                {
                    "proposals": [
                        {
                            "source_id": source["id"],
                            "quote": quote,
                            "text": "Reporter says rollback failed",
                            "kind": "outcome",
                        }
                    ]
                },
                ProviderTimeoutError("timeout"),
            ]
        ),
    )
    result = store.job("alice", job["id"])
    assert result["status"] == "partial" and not result["output"]["payload"]["ai_succeeded"]
    assert any(
        m["kind"] == "outcome" and m["state"] == "proposed"
        for m in store.memories("alice", case["id"])
    )
    assert any(
        e["kind"] == "provider_timeout" and e["detail"]["stage"] == "Reply"
        for e in store.changes("alice", case["id"])["events"]
    )


def test_model_proposals_are_not_backdated_into_past(tmp_path):
    from contracts.relaydesk import Proposal

    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    source = store.sources("alice", case["id"])[0]
    store.add_proposals(
        "alice",
        case["id"],
        [
            Proposal(
                source_id=source["id"],
                quote=source["body"],
                text="Derived interpretation today",
                kind="hypothesis",
            )
        ],
    )
    past = store.memories("alice", case["id"], as_of="2025-02-01T00:00:00+00:00")
    assert all(m["kind"] != "hypothesis" for m in past)


def test_unaudited_provider_output_is_rejected(tmp_path):
    from agent_core.provider import StructuredGeneration

    store, _, _, job = queued(tmp_path, True)

    class Unaudited:
        def generate(self, **kwargs):
            return StructuredGeneration(
                text='{"proposals": []}', exit_code=0, elapsed_ms=1, tools_audited=False
            )

    run_once(store, encoder=None, provider=Unaudited())
    result = store.job("alice", job["id"])
    assert result["status"] == "partial" and result["model_calls"] == 1
    assert "audit" in result["reason"].lower()
