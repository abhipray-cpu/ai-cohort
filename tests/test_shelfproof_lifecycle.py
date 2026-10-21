# ruff: noqa: F811
import json

import pytest
from shelfproof_api.core import freeze_import
from shelfproof_api.store import Conflict, Forbidden
from shelfproof_api.workflow import Worker
from test_shelfproof_core import draft, evaluation, facts
from test_shelfproof_workflow import Provider, job, setup  # noqa: F401


def frozen(setup):
    store, workspace, _ = setup
    raw = json.dumps([facts().model_dump(mode="json")]).encode()
    mapping = {k: k for k in type(facts()).model_fields}
    return store.save_import("maker", workspace, raw, freeze_import(raw, "json", mapping))


def test_batch_preview_freezes_exact_context_and_start_is_idempotent(setup):
    store, workspace, grant = setup
    batch = store.create_batch("maker", workspace, frozen(setup), [0], grant, "batch-key")
    assert store.claim() is None
    preview = store.batch_preview("maker", batch)
    assert preview["maximum_calls"] == 16
    assert preview["facts"][0]["product_id"] == "000123"
    assert preview["destination"] == "installed-codex-configured-service"
    first = store.start_batch("maker", batch, preview["binding"])
    assert store.start_batch("maker", batch, preview["binding"]) == first
    Worker(store, Provider([draft(), evaluation()])).run_once()
    result = store.batch("maker", batch)
    assert result["counts"] == {"review_ready": 1}
    assert result["calls"] == 2
    assert result["known_input_tokens"] == 20
    with pytest.raises(Conflict):
        store.start_batch("maker", batch, "changed-context")


def test_policy_activation_stales_old_batch_and_cannot_weaken_hard_gates(setup):
    store, workspace, grant = setup
    batch = store.create_batch("maker", workspace, frozen(setup), [0], grant, "batch")
    preview = store.batch_preview("maker", batch)
    with pytest.raises(ValueError):
        store.activate_policy("maker", workspace, {"required_score": 10}, "bad-policy")
    store.activate_policy("maker", workspace, {"brief": "Neutral factual copy."}, "policy")
    with pytest.raises(Conflict):
        store.start_batch("maker", batch, preview["binding"])


def test_batch_preview_is_invalidated_when_code_binding_changes(setup, monkeypatch):
    store, workspace, grant = setup
    batch = store.create_batch("maker", workspace, frozen(setup), [0], grant, "code-binding")
    preview = store.batch_preview("maker", batch)
    monkeypatch.setattr("shelfproof_api.lifecycle.code_fingerprint", lambda: "new-code")
    with pytest.raises(Conflict):
        store.start_batch("maker", batch, preview["binding"])


def test_last_workspace_owner_cannot_be_removed_by_role_change(setup):
    store, workspace, _ = setup
    with pytest.raises(Conflict):
        store.add_member("maker", workspace, "maker", "viewer")


def test_batch_cancel_fences_every_queued_and_running_row(setup):
    store, workspace, grant = setup
    batch = store.create_batch("maker", workspace, frozen(setup), [0], grant, "batch")
    store.start_batch("maker", batch, store.batch_preview("maker", batch)["binding"])
    lease = store.claim()
    store.cancel_batch("maker", batch)
    assert store.task("maker", lease["id"])["state"] == "cancelled"
    with pytest.raises(Conflict):
        store.select(lease["id"], lease["lease"], "x")


def test_human_edit_is_new_task_and_has_no_inherited_approval(setup):
    store, workspace, grant = setup
    task = job(setup)
    Worker(store, Provider([draft(), evaluation()])).run_once()
    selected = store.task("maker", task)["selected_hash"]
    store.review("checker", task, selected, "accept", "Checked")
    edited = store.edit("maker", task, selected, draft(), grant, "edit-key")
    assert edited != task
    assert store.task("maker", edited)["state"] == "queued"
    assert store.export("maker", workspace)["approved_count"] == 0
    assert store.task("maker", task)["state"] == "stale"


def test_dependency_aware_erasure_removes_source_and_derived_content(setup):
    store, workspace, grant = setup
    source = frozen(setup)
    batch = store.create_batch("maker", workspace, source, [0], grant, "batch")
    task = store.start_batch("maker", batch, store.batch_preview("maker", batch)["binding"])[0]
    Worker(store, Provider([draft(), evaluation()])).run_once()
    preview = store.erasure_preview("maker", source)
    assert preview["tasks"] == [task]
    store.erase_import("maker", source, preview["binding"], "erase-key")
    store.erase_import("maker", source, preview["binding"], "erase-key")
    with pytest.raises(Forbidden):
        store.task("maker", task)
    with store.db() as db:
        assert db.execute("SELECT count(*) FROM imports WHERE id=?", (source,)).fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM artifacts WHERE task=?", (task,)).fetchone()[0] == 0
    assert store.export("maker", workspace)["approved_count"] == 0


def test_review_csv_neutralizes_formula_and_preserves_gtin_as_text(setup):
    store, workspace, _ = setup
    task = job(setup, draft(title="=CMD()"))
    csv = store.review_csv("maker", workspace)
    assert "UNAPPROVED" in csv and "'=CMD()" in csv and "'000123" in csv
    assert task in csv


def test_human_edit_cannot_reset_row_invocation_allowance(setup):
    store, _, grant = setup
    task = job(setup, draft())
    with store.db() as db:
        db.execute("UPDATE tasks SET calls=16 WHERE id=?", (task,))
    with pytest.raises(Conflict):
        store.edit(
            "maker", task, store.task("maker", task)["selected_hash"], draft(), grant, "no-reset"
        )


def test_erasure_during_provider_call_fences_result_without_crashing_worker(setup):
    store, workspace, grant = setup
    source = frozen(setup)
    batch = store.create_batch("maker", workspace, source, [0], grant, "erase-race")
    task = store.start_batch("maker", batch, store.batch_preview("maker", batch)["binding"])[0]

    class ErasingProvider(Provider):
        def generate(self, **kwargs):
            preview = store.erasure_preview("maker", source)
            store.erase_import("maker", source, preview["binding"], "erase-during-call")
            return super().generate(**kwargs)

    assert Worker(store, ErasingProvider([draft()])).run_once()
    with pytest.raises(Forbidden):
        store.task("maker", task)
