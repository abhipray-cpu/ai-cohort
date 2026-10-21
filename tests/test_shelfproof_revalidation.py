import json

import pytest
from shelfproof_api.core import canonical
from shelfproof_api.store import Conflict
from shelfproof_api.workflow import Worker
from test_shelfproof_core import draft, evaluation
from test_shelfproof_workflow import Provider, job, setup  # noqa: F401


def old_snapshot(store, task):
    with store.db() as db:
        snapshot = json.loads(
            db.execute("SELECT body FROM snapshots WHERE task=?", (task,)).fetchone()[0]
        )
        snapshot["code_fingerprint"] = "prior-code"
        db.execute("UPDATE snapshots SET body=? WHERE task=?", (canonical(snapshot), task))


def test_fixed_code_successor_preserves_budget_source_original_and_history(setup):  # noqa: F811
    from scripts.revalidate_shelfproof_campaign import prepare_successors

    store, _, grant = setup
    task = job(setup, draft())
    Worker(store, Provider([evaluation()])).run_once()
    before = store.task("maker", task)
    old_snapshot(store, task)
    kwargs = {
        "expected_head": store.journal_head(),
        "expected_calls": 1,
        "evidence": "explicit rerun approval",
        "key": "round-one",
    }
    children = prepare_successors(store, "maker", [task], **kwargs)
    assert prepare_successors(store, "maker", [task], **kwargs) == children
    child = store.task("maker", children[0])
    assert child["calls"] == before["calls"] and child["claims"] == before["claims"]
    assert child["versions"][0]["draft"] == before["versions"][0]["draft"]
    assert child["grant_id"] == grant
    assert store.task("maker", task)["state"] == "stale"
    with store.db() as db:
        assert db.execute("SELECT calls FROM grants WHERE id=?", (grant,)).fetchone()[0] == 1


def test_revalidation_rejects_stale_spend_or_head_and_unmodified_code(setup):  # noqa: F811
    from scripts.revalidate_shelfproof_campaign import prepare_successors

    store, _, _ = setup
    task = job(setup)
    Worker(store, Provider([draft(), evaluation()])).run_once()
    kwargs = {
        "expected_head": store.journal_head(),
        "expected_calls": 2,
        "evidence": "approved",
        "key": "one",
    }
    with pytest.raises(Conflict):
        prepare_successors(store, "maker", [task], **kwargs)
    old_snapshot(store, task)
    with pytest.raises(Conflict):
        prepare_successors(store, "maker", [task], **{**kwargs, "expected_calls": 0})
    with pytest.raises(Conflict):
        prepare_successors(store, "maker", [task], **{**kwargs, "expected_head": "old"})
    assert store.task("maker", task)["state"] == "review_ready"
