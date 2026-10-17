"""Test-first synthetic fixtures; actual encoder/data acceptance is separate."""

import pytest
from contracts.relaydesk import ImportBatch, SourceMessage
from relaydesk_api.context import build_buffer, compress
from relaydesk_api.store import Store


def setup(tmp_path):
    store = Store(tmp_path / "live", ledger_dir=tmp_path / "ledger")
    store.add_user("alice", "alice-long-password", admin=True)
    store.add_user("bob", "bob-long-password")
    account = store.create_account("alice", "Example")
    case = store.create_case("alice", account["id"], "Database escalation")
    return store, case


def batch(text="Rollback was attempted but the server still failed to start."):
    return ImportBatch(
        messages=[
            SourceMessage(
                source_key="comment:1",
                author="reporter",
                body=text,
                created_at="2025-01-01T12:00:00Z",
                updated_at="2025-01-01T12:00:00Z",
            )
        ]
    )


def test_import_is_scoped_durable_and_idempotent(tmp_path):
    store, case = setup(tmp_path)
    result = store.import_messages("alice", case["id"], batch())
    assert result["inserted"] == 1
    assert store.import_messages("alice", case["id"], batch())["inserted"] == 0
    with pytest.raises(PermissionError):
        store.case("bob", case["id"])
    restored = Store(store.root, ledger_dir=tmp_path / "ledger")
    assert len(restored.memories("alice", case["id"])) == 1
    assert restored.memories("alice", case["id"])[0]["kind"] == "episode"


def test_revision_conflict_revocation_and_sync(tmp_path):
    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    store.membership("alice", case["id"], "bob", ["investigator"])
    before = store.changes("bob", case["id"], 0)
    memory = store.memories("alice", case["id"])[0]
    store.correct(
        "alice",
        memory["id"],
        1,
        "Rollback did not fix this version.",
        "outcome",
        "reported",
        "Correction",
    )
    with pytest.raises(ValueError):
        store.correct("alice", memory["id"], 1, "stale", "outcome", "reported", "stale")
    assert store.changes("bob", case["id"], before["cursor"])["events"]
    store.membership("alice", case["id"], "bob", [])
    assert store.cases("bob") == []
    with pytest.raises(PermissionError):
        store.changes("bob", case["id"], 0)


def test_erasure_clears_dependencies_and_external_ledger(tmp_path):
    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    source = store.sources("alice", case["id"])[0]
    store.erase("alice", case["id"], [source["id"]], "ERASE")
    assert store.memories("alice", case["id"]) == []
    assert store.source("alice", source["id"])["body"] == "[erased]"
    assert store.ledger_entries()


def test_buffer_and_compression_keep_denominators():
    rows = [
        {
            "id": str(i),
            "body": "message " + str(i) + " " * 100,
            "kind": "episode",
            "state": "reported",
            "source_id": str(i),
        }
        for i in range(30)
    ]
    buffer = build_buffer(rows, 500)
    assert len(buffer["messages"]) < 30 and buffer["omitted"] > 0
    summary = compress(rows, 500)
    assert summary["coverage"]["total"] == 30
    assert summary["coverage"]["omitted"] > 0
    assert summary["status"] == "partial"


def test_erasure_includes_correction_source_and_survives_old_snapshot(tmp_path):
    import sqlite3

    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    original = store.sources("alice", case["id"])[0]
    memory = store.memories("alice", case["id"])[0]
    store.correct(
        "alice", memory["id"], 1, "Sensitive corrected content", "outcome", "reported", "review"
    )
    snapshot = tmp_path / "old.sqlite3"
    with store.connect() as db, sqlite3.connect(snapshot) as dest:
        db.backup(dest)
    store.erase("alice", case["id"], [original["id"]], "ERASE")
    assert all(s["body"] == "[erased]" for s in store.sources("alice", case["id"]))
    with sqlite3.connect(snapshot) as old, store.connect() as dest:
        old.backup(dest)
    restored = Store(store.root, ledger_dir=tmp_path / "ledger")
    assert all(s["body"] == "[erased]" for s in restored.sources("alice", case["id"]))
    assert restored.memories("alice", case["id"]) == []


def test_restarting_after_erasure_does_not_destroy_new_clean_drafts(tmp_path):
    from relaydesk_api.worker import run_once

    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    source = store.sources("alice", case["id"])[0]
    store.erase("alice", case["id"], [source["id"]], "ERASE")
    value = batch("New unrelated evidence remains available")
    value.messages[0].source_key = "new-clean-source"
    store.import_messages("alice", case["id"], value)
    conv = store.conversation("alice", case["id"])
    job = store.enqueue(
        "alice", conv["id"], conv["session"]["id"], "What new evidence exists?", "new-clean"
    )
    run_once(store, encoder=None)
    assert store.job("alice", job["id"])["output"]["payload"]
    restarted = Store(store.root, ledger_dir=store.ledger_dir)
    assert restarted.job("alice", job["id"])["output"]["payload"]
