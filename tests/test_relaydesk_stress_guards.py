"""Controlled stress guards, separate from the frozen public-data evaluation."""

from datetime import UTC, datetime, timedelta

import pytest
from relaydesk_api.worker import run_once
from test_relaydesk_core import setup
from test_relaydesk_worker import Provider, queued


def test_queue_backpressure_does_not_commit_unaccepted_turns(tmp_path):
    store, case = setup(tmp_path)
    conv = store.conversation("alice", case["id"])
    for i in range(20):
        store.enqueue("alice", conv["id"], conv["session"]["id"], f"Question {i}", str(i))
    with pytest.raises(ValueError, match="queue full"):
        store.enqueue("alice", conv["id"], conv["session"]["id"], "Over capacity", "overflow")
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 20
        assert db.execute("SELECT count(*) FROM turns").fetchone()[0] == 20


def test_model_reservations_survive_reclaim_and_explicit_continuation(tmp_path):
    store, case, _, job = queued(tmp_path, True)
    claimed = store.claim()
    for _ in range(4):
        store.reserve(claimed["id"], claimed["lease"])
    with pytest.raises(ValueError, match="budget exhausted"):
        store.reserve(claimed["id"], claimed["lease"])
    with store.connect() as db:
        db.execute(
            "UPDATE jobs SET lease_until=? WHERE id=?",
            ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), job["id"]),
        )
    reclaimed = store.claim()
    assert reclaimed["model_calls"] == 4 and reclaimed["deadline"] == claimed["deadline"]
    with pytest.raises(ValueError, match="budget exhausted"):
        store.reserve(reclaimed["id"], reclaimed["lease"])
    store.finish(
        reclaimed,
        {"summary": "Controlled partial", "status": "partial"},
        store.case("alice", case["id"])["revision"],
        "injected",
    )
    continued = store.continue_job("alice", job["id"], "explicit-grant")
    assert (
        continued["grant"] == 2
        and continued["model_calls"] == 4
        and continued["deadline"] == claimed["deadline"]
    )
    repeated = store.continue_job("alice", job["id"], "explicit-grant")
    assert repeated["grant"] == 2
    final = store.claim()
    for _ in range(4):
        store.reserve(final["id"], final["lease"])
    with pytest.raises(ValueError, match="budget exhausted"):
        store.reserve(final["id"], final["lease"])


def test_expired_deadline_does_not_invoke_provider(tmp_path):
    store, _, _, job = queued(tmp_path, True)
    with store.connect() as db:
        db.execute(
            "UPDATE jobs SET deadline=? WHERE id=?",
            ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), job["id"]),
        )
    run_once(store, encoder=None, provider=Provider([]))
    result = store.job("alice", job["id"])
    assert result["status"] == "failed" and result["model_calls"] == 0 and not result["output_id"]


def test_login_throttle_and_session_logout(tmp_path):
    store, _ = setup(tmp_path)
    for _ in range(5):
        with pytest.raises(PermissionError):
            store.login("alice", "wrong")
    with pytest.raises(PermissionError, match="temporarily limited"):
        store.login("alice", "alice-long-password")
    token = store.login("bob", "bob-long-password")["token"]
    store.logout(token)
    with pytest.raises(PermissionError):
        store.authenticate(token)


def test_live_ledger_missing_fails_closed_on_restart(tmp_path):
    store, _ = setup(tmp_path)
    from relaydesk_api.store import Store

    with pytest.raises(RuntimeError, match="erasure ledger"):
        Store(store.root, ledger_dir=tmp_path / "missing-ledger")
