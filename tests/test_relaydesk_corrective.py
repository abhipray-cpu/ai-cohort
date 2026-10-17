import json
import sqlite3

import pytest
from relaydesk_api.grounding import quote_span
from relaydesk_api.ledger import enroll_legacy
from relaydesk_api.store import Store
from relaydesk_api.worker import run_once
from test_relaydesk_core import batch, setup
from test_relaydesk_worker import Provider, queued


def test_model_narrative_cannot_override_a_cited_negative_outcome(tmp_path):
    store, case, _, job = queued(tmp_path, True)
    memory = store.memories("alice", case["id"])[0]
    response = {
        "summary": "Every production environment has recovered.",
        "claims": [{"text": memory["body"], "memory_ids": [memory["id"]]}],
        "questions": [],
        "limitations": [],
    }
    run_once(store, encoder=None, provider=Provider([{"proposals": []}, response]))
    result = store.job("alice", job["id"])
    p = result["output"]["payload"]
    assert p["ai_succeeded"] and "Every production" not in json.dumps(p)
    assert p["claims"][0]["text"] == memory["body"]
    citation = p["claims"][0]["citations"][0]
    source = store.source("alice", citation["source_id"])
    assert (
        source["body"][citation["start"] : citation["end"]] == citation["quote"] == memory["body"]
    )


def test_crlf_quote_mapping_preserves_original_offsets():
    source = "Before\r\nRollback failed.\r\nStill unresolved."
    start, end = quote_span(source, "Rollback failed.\nStill unresolved.")
    assert source[start:end] == "Rollback failed.\r\nStill unresolved."
    with pytest.raises(ValueError):
        quote_span(source, "Rollback succeeded.")


def test_buffer_projects_only_turn_content_not_nested_prior_artifacts():
    from relaydesk_api.context import build_buffer

    rows = [
        {
            "id": "turn",
            "role": "assistant",
            "body": "A short qualified reply.",
            "output": {"payload": {"private_old_context": "X" * 100000}},
        }
    ]
    buffer = build_buffer(rows, 5000)
    assert "private_old_context" not in json.dumps(buffer)
    assert len(json.dumps(buffer)) <= 5000 and buffer["messages"][0]["body"] == rows[0]["body"]


def test_legacy_store_requires_explicit_identity_confirmed_enrollment(tmp_path):
    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    with store.connect() as db:
        db.execute("DELETE FROM settings WHERE key='ledger_binding'")
    with sqlite3.connect(store.ledger_dir / "ledger.sqlite3") as ledger:
        ledger.execute("DROP TABLE metadata")
        ledger.execute("DROP TABLE stores")
    with pytest.raises(RuntimeError):
        Store(store.root, ledger_dir=store.ledger_dir)
    with pytest.raises(ValueError):
        enroll_legacy(store.root, store.ledger_dir, "wrong-id")
    enroll_legacy(store.root, store.ledger_dir, store.store_id)
    restored = Store(store.root, ledger_dir=store.ledger_dir)
    assert restored.ledger_binding and restored.memories("alice", case["id"])


def test_legacy_enrollment_cannot_discard_existing_erasure_tombstones(tmp_path):
    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    source = store.sources("alice", case["id"])[0]
    store.erase("alice", case["id"], [source["id"]], "ERASE")
    with store.connect() as db:
        db.execute("DELETE FROM settings WHERE key='ledger_binding'")
    unrelated = Store(tmp_path / "unrelated", ledger_dir=tmp_path / "unrelated-ledger")
    with pytest.raises(ValueError, match="omits existing erasures"):
        enroll_legacy(store.root, unrelated.ledger_dir, store.store_id)


def test_live_ledger_replacement_is_rejected_at_erasure_boundary(tmp_path):
    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    source = store.sources("alice", case["id"])[0]
    with sqlite3.connect(store.ledger_dir / "ledger.sqlite3") as ledger:
        ledger.execute("UPDATE metadata SET value='unrelated' WHERE key='identity'")
    with pytest.raises(RuntimeError, match="identity mismatch"):
        store.erase("alice", case["id"], [source["id"]], "ERASE")


def test_corrupt_source_cannot_be_committed_as_a_finished_reply(tmp_path):
    from contracts.relaydesk import Recall
    from relaydesk_api.recall import RecallEngine

    store, case, _, job = queued(tmp_path)
    hits = RecallEngine(store).search("alice", case["id"], Recall(question=job["question"]))["hits"]
    assert hits
    claimed = store.claim()
    with store.connect() as db:
        db.execute(
            "UPDATE sources SET body='CORRUPTED' WHERE id=?", (hits[0]["evidence"]["source_id"],)
        )
    with pytest.raises(ValueError, match="integrity"):
        store.finish(
            claimed,
            {"summary": "Controlled", "status": "partial", "recall": {"hits": hits}},
            store.case("alice", case["id"])["revision"],
            "test",
        )
