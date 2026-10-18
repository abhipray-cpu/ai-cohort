import json

from catalogbridge_api.store import Store
from catalogbridge_api.worker import run_once
from contracts.catalogbridge import BatchSpec, Product, Review
from test_catalogbridge_core import setup_batch
from test_catalogbridge_worker import FakeModels


def enable(store, batch):
    spec = BatchSpec.model_validate(batch["spec"] | {"reuse_validated_drafts": True})
    with store.write() as db:
        db.execute("UPDATE batches SET spec=? WHERE id=?", (spec.model_dump_json(), batch["id"]))
    return spec


def process(store, batch, provider):
    store.start("w", batch["id"])
    run_once(store, provider)
    return store.tasks("w", batch["id"])[0]


def test_opt_in_exact_repeat_reuses_draft_after_restart_without_acceptance(tmp_path):
    store, first = setup_batch(tmp_path, 30000)
    spec = enable(store, first)
    provider = FakeModels()
    original = process(store, first, provider)
    store = Store(tmp_path)
    second = store.create_batch("w", spec)
    reused = process(store, second, provider)
    assert len(provider.calls) == 1
    assert reused["state"] == "needs_review" and not reused["result"]["calibrated"]
    assert reused["result"]["proposal"] == original["result"]["proposal"]
    assert reused["result"]["cached_from"]["task_id"] == original["id"]
    assert reused["result"]["attempts"] == []
    assert store.analytics("w", second["id"])["tokens"] == 0
    assert any(e["kind"] == "draft_cache_hit" for e in store.audit("w", second["id"]))
    _, manifest = store.export("w", second["id"])
    assert manifest["included"] == 0  # a cached draft is not a reviewed link


def test_cache_is_disabled_by_default(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    assert not BatchSpec.model_validate(batch["spec"]).reuse_validated_drafts
    provider = FakeModels(["same_product", "same_product"])
    process(store, batch, provider)
    process(store, store.create_batch("w", BatchSpec.model_validate(batch["spec"])), provider)
    assert len(provider.calls) == 2


def test_any_source_or_master_change_invalidates_cached_context(tmp_path):
    store, first = setup_batch(tmp_path, 30000)
    spec = enable(store, first)
    provider = FakeModels(["same_product"] * 3)
    process(store, first, provider)
    changed = store.import_feed("w", "supplier", [Product(id="s", title="Memory 8GB", price="2")])
    altered = spec.model_copy(update={"supplier_id": changed["id"]})
    process(store, store.create_batch("w", altered), provider)
    master = store.import_feed("w", "master", [Product(id="m", title="Memory 8GB", price="3")])
    process(
        store,
        store.create_batch("w", spec.model_copy(update={"master_id": master["id"]})),
        provider,
    )
    assert len(provider.calls) == 3


def test_expired_entries_and_changed_profile_require_new_dispatch(tmp_path):
    store, first = setup_batch(tmp_path, 30000)
    spec = enable(store, first)
    provider = FakeModels(["same_product"] * 3)
    process(store, first, provider)
    with store.write() as db:
        db.execute("UPDATE draft_cache SET expires=0")
    process(store, store.create_batch("w", spec), provider)
    compact = spec.model_copy(update={"instruction_profile": "compact_classifier_v1"})
    process(store, store.create_batch("w", compact), provider)
    assert len(provider.calls) == 3


def test_reviewed_or_corrupted_source_draft_is_not_reused(tmp_path):
    store, first = setup_batch(tmp_path, 30000)
    spec = enable(store, first)
    provider = FakeModels(["same_product"] * 3)
    task = process(store, first, provider)
    store.review(
        "w",
        task["id"],
        "reviewer",
        Review(expected_revision=task["revision"], action="reject", reason="not same SKU"),
    )
    second = store.create_batch("w", spec)
    current = process(store, second, provider)
    with store.write() as db:
        result = current["result"]
        result["proposal"]["evidence"][0]["quote"] = "invented quote"
        db.execute("UPDATE tasks SET result=? WHERE id=?", (json.dumps(result), current["id"]))
    third = store.create_batch("w", spec)
    process(store, third, provider)
    assert len(provider.calls) == 3
    assert any(e["kind"] == "draft_cache_rejected" for e in store.audit("w", third["id"]))


def test_circuit_hold_and_egress_denial_do_not_use_cache_to_resume_work(tmp_path):
    store, first = setup_batch(tmp_path, 30000)
    spec = enable(store, first)
    provider = FakeModels()
    process(store, first, provider)
    store.open_runtime_circuit("w", first["id"], {"category": "network"})
    held = process(store, store.create_batch("w", spec), provider)
    assert "cached_from" not in held["result"] and len(provider.calls) == 1
    denied = process(
        store, store.create_batch("w", spec.model_copy(update={"egress": False})), provider
    )
    assert "cached_from" not in denied["result"]


def test_another_workspace_cannot_reuse_a_draft(tmp_path):
    store, first = setup_batch(tmp_path, 30000)
    spec = enable(store, first)
    provider = FakeModels(["same_product"] * 2)
    process(store, first, provider)
    master = store.import_feed("other", "master", [Product(id="m", title="Memory 8GB")])
    supplier = store.import_feed("other", "supplier", [Product(id="s", title="Memory 8GB")])
    other = store.create_batch(
        "other", spec.model_copy(update={"master_id": master["id"], "supplier_id": supplier["id"]})
    )
    store.start("other", other["id"])
    run_once(store, provider)
    assert len(provider.calls) == 2
    assert "cached_from" not in store.tasks("other", other["id"])[0]["result"]


def test_cache_hit_never_renews_original_expiry(tmp_path):
    store, first = setup_batch(tmp_path, 30000)
    spec = enable(store, first)
    provider = FakeModels()
    process(store, first, provider)
    with store.connect() as db:
        original = tuple(db.execute("SELECT task_id,created,expires FROM draft_cache").fetchone())
    process(store, store.create_batch("w", spec), provider)
    with store.connect() as db:
        assert (
            tuple(db.execute("SELECT task_id,created,expires FROM draft_cache").fetchone())
            == original
        )
    assert original[2] - original[1] == 86400


def test_uncertain_drafts_do_not_seed_cache(tmp_path):
    store, first = setup_batch(tmp_path, 30000)
    enable(store, first)
    provider = FakeModels(["insufficient_evidence"] * 2)
    task = process(store, first, provider)
    assert task["result"]["proposal"]["outcome"] == "insufficient_evidence"
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM draft_cache").fetchone()[0] == 0


def test_cancelled_worker_cannot_seed_a_cache_entry(tmp_path):
    import pytest

    store, first = setup_batch(tmp_path, 30000)
    enable(store, first)
    store.start("w", first["id"])
    task = store.claim()
    store.cancel("w", first["id"])
    with pytest.raises(ValueError, match="stale"):
        store.checkpoint(task, {}, draft_cache_key="not-authorized")
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM draft_cache").fetchone()[0] == 0
