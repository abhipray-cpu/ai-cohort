# ruff: noqa: F811
import json

import pytest
from shelfproof_api.store import Conflict, Forbidden, Store
from shelfproof_api.workflow import Worker
from test_shelfproof_core import draft, evaluation
from test_shelfproof_workflow import Provider, job, setup  # noqa: F401


def test_backup_is_new_only_and_restore_revokes_sessions_and_quarantines(setup, tmp_path):
    store, _, _ = setup
    task = job(setup)
    token, _ = store.login("maker", "long-password-123")
    backup = tmp_path / "backup"
    store.backup(backup)
    with pytest.raises(FileExistsError):
        store.backup(backup)
    restored = Store.restore(backup, tmp_path / "restored", store.journal)
    with pytest.raises(Forbidden):
        restored.session(token)
    assert restored.task("maker", task)["state"] == "stale"
    assert restored.claim() is None
    assert not restored.health()["ready"]
    restored.release_quarantine(
        "maker", restored.journal_head(), "operator:verified restore", "release"
    )
    assert not restored.liability_hold()
    assert restored.task("maker", task)["state"] == "stale"


def test_orphan_reservation_is_not_forgiven_and_no_blind_resume(setup):
    store, _, _ = setup
    task = job(setup)
    lease = store.claim()["lease"]
    store.reserve(task, lease, "draft:0")
    with store.db() as db:
        db.execute("UPDATE tasks SET lease_until=0 WHERE id=?", (task,))
    store.isolate_orphans("maker", "operator:tree-termination:owned-fixture", store.journal_head())
    assert store.task("maker", task)["state"] == "manual_required"
    assert store.task("maker", task)["attempts"][0]["status"] == "unknown"
    with pytest.raises(Conflict):
        store.resume("maker", task, None, "resume")
    assert store.liability_hold()


def test_resume_completed_checkpoints_does_not_repeat_known_stage(setup):
    store, _, _ = setup
    task = job(setup)
    row = store.claim()
    lease = row["lease"]
    attempt = store.reserve(task, lease, "draft:0")
    store.settle(attempt, {"audited": True, "input_tokens": 10, "output_tokens": 5})
    store.checkpoint(
        task,
        lease,
        "stages",
        {"stage": "draft:0", "attempt": attempt, "output": draft().model_dump(mode="json")},
    )
    with store.db() as db:
        db.execute("UPDATE tasks SET lease_until=0 WHERE id=?", (task,))
    store.isolate_orphans("maker", "operator:tree-terminated", store.journal_head())
    store.resume("maker", task, None, "bounded-resume")
    provider = Provider([evaluation()])
    Worker(store, provider).run_once()
    result = store.task("maker", task)
    assert result["state"] == "review_ready" and result["calls"] == 2
    assert len(provider.prompts) == 1


def test_stale_journal_backup_and_corrupt_artifact_fail_closed(setup, tmp_path):
    store, _, _ = setup
    task = job(setup)
    Worker(store, Provider([draft(), evaluation()])).run_once()
    backup = tmp_path / "backup"
    store.backup(backup)
    manifest = json.loads((backup / "manifest.json").read_text())
    assert manifest["artifact_count"] >= 4
    with store.db() as db:
        db.execute("UPDATE artifacts SET body='{}' WHERE task=?", (task,))
    with pytest.raises(Conflict):
        store.verify_integrity()


def test_grant_amendment_preserves_spend_and_checks_current_head(setup):
    store, workspace, grant = setup
    job(setup)
    Worker(store, Provider([draft(), evaluation()])).run_once()
    with pytest.raises(Conflict):
        store.amend_grant(
            "maker", workspace, grant, 48, "stale-head", "approved expansion", "amend"
        )
    store.amend_grant(
        "maker", workspace, grant, 48, store.journal_head(), "approved expansion", "amend"
    )
    with store.db() as db:
        row = db.execute("SELECT * FROM grants WHERE id=?", (grant,)).fetchone()
        assert row["calls"] == 2 and row["max_calls"] == 48


def test_one_incident_preserves_unknown_and_requires_separate_resume(setup):
    store, _, _ = setup
    task = job(setup, draft())
    Worker(store, Provider([TimeoutError()])).run_once()
    old = store.task("maker", task)["attempts"][0]
    store.accept_incident(
        "maker",
        task,
        store.journal_head(),
        "Operator terminated tree; receipt irrecoverable",
        "operator:evidence:1",
        True,
        "incident-key",
    )
    assert store.liability_hold()  # Closure is not dispatch authority.
    store.resume("maker", task, store.task("maker", task)["selected_hash"], "resume-after-incident")
    Worker(store, Provider([evaluation()])).run_once()
    result = store.task("maker", task)
    assert result["state"] == "review_ready"
    assert result["attempts"][0] == old
    assert result["warnings"]
    with pytest.raises(Conflict):
        store.review("checker", task, result["selected_hash"], "accept", "checked")
    store.review(
        "checker",
        task,
        result["selected_hash"],
        "accept",
        "unknown history acknowledged",
        acknowledge_unknown=True,
    )
    # A second closure cannot be used as an automatic recovery loop.
    with pytest.raises(Conflict):
        store.accept_incident(
            "maker", task, store.journal_head(), "again", "evidence", True, "another-key"
        )


def test_explicit_unsafe_tool_receipt_is_never_incident_eligible(setup):
    store, _, _ = setup
    task = job(setup)
    lease = store.claim()["lease"]
    attempt = store.reserve(task, lease, "draft:0")
    store.settle(attempt, {"audited": False, "unsafe_tool_event": True})
    store.finish(task, lease, "manual_required", None)
    with pytest.raises(Conflict):
        store.accept_incident(
            "maker", task, store.journal_head(), "not safe", "evidence", True, "bad"
        )


def test_successor_edit_keeps_accepted_unknown_history_and_review_acknowledgement(setup):
    store, _, grant = setup
    task = job(setup, draft())
    Worker(store, Provider([TimeoutError()])).run_once()
    store.accept_incident(
        "maker", task, store.journal_head(), "approved", "isolated", True, "incident"
    )
    store.resume("maker", task, store.task("maker", task)["selected_hash"], "resume")
    Worker(store, Provider([evaluation()])).run_once()
    parent = store.task("maker", task)
    successor = store.edit("maker", task, parent["selected_hash"], draft(), grant, "successor")
    Worker(store, Provider([evaluation()])).run_once()
    child = store.task("maker", successor)
    assert child["warnings"] == parent["warnings"]
    assert child["calls"] == parent["calls"] + 1
    with pytest.raises(Conflict):
        store.review("checker", successor, child["selected_hash"], "accept", "checked")
    store.review(
        "checker",
        successor,
        child["selected_hash"],
        "accept",
        "checked history",
        acknowledge_unknown=True,
    )


def test_verified_supplement_is_append_only_and_not_a_refund(setup):
    store, _, _ = setup
    task = job(setup, draft())
    Worker(store, Provider([TimeoutError()])).run_once()
    attempt = store.task("maker", task)["attempts"][0]
    store.reconcile_receipt(
        "maker",
        attempt["id"],
        store.journal_head(),
        {"audited": True, "input_tokens": 10, "output_tokens": 5},
        "operator:independently-verified-attempt-receipt",
        "receipt-key",
    )
    assert store.task("maker", task)["attempts"][0] == attempt
    assert store.task("maker", task)["calls"] == 1
    assert store.liability_hold()  # explicit resume still required
    store.resume("maker", task, store.task("maker", task)["selected_hash"], "resume")
    assert not store.liability_hold()


def test_restoring_older_backup_does_not_resurrect_erased_source(setup, tmp_path):
    from test_shelfproof_lifecycle import frozen

    store, workspace, _ = setup
    source = frozen(setup)
    backup = tmp_path / "before-erasure"
    store.backup(backup)
    preview = store.erasure_preview("maker", source)
    store.erase_import("maker", source, preview["binding"], "erase")
    restored = Store.restore(backup, tmp_path / "restored-after-erasure", store.journal)
    with pytest.raises(Forbidden):
        restored.import_row("maker", workspace, source, 0)


def test_journal_fsync_failure_prevents_dispatch_and_holds_other_workspaces(setup, monkeypatch):
    import os

    store, _, _ = setup
    task = job(setup)
    lease = store.claim()["lease"]

    def fail(_descriptor):
        raise OSError("authored fsync fault")

    with monkeypatch.context() as fault:
        fault.setattr(os, "fsync", fail)
        with pytest.raises(OSError):
            store.reserve(task, lease, "draft:0")
    assert store.liability_hold()
    with store.db() as db:
        assert db.execute("SELECT calls FROM tasks WHERE id=?", (task,)).fetchone()[0] == 0
    assert store.claim() is None


def test_low_disk_blocks_reservation_without_spending_a_call(setup, monkeypatch):
    from types import SimpleNamespace

    store, _, _ = setup
    task = job(setup)
    lease = store.claim()["lease"]
    monkeypatch.setattr("shutil.disk_usage", lambda _: SimpleNamespace(free=0))
    with pytest.raises(Conflict):
        store.reserve(task, lease, "draft:0")
    assert store.task("maker", task)["calls"] == 0


def test_stage_retry_limit_survives_operator_resume(setup):
    store, _, _ = setup
    task = job(setup)
    lease = store.claim()["lease"]
    for _ in range(2):
        attempt = store.reserve(task, lease, "draft:0")
        store.settle(attempt, {"audited": True, "input_tokens": 10, "output_tokens": 5})
    store.finish(task, lease, "manual_required", None)
    store.resume("maker", task, None, "resume")
    renewed = store.claim()["lease"]
    with pytest.raises(Conflict):
        store.reserve(task, renewed, "draft:0")
