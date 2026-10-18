import json
import sqlite3
import time

import pytest
from catalogbridge_api.ingest import parse_feed
from catalogbridge_api.store import Store
from catalogbridge_api.worker import run_once
from contracts.catalogbridge import Product, Review, Usage
from test_catalogbridge_core import setup_batch
from test_catalogbridge_worker import FakeModels


def test_active_reservation_blocks_a_second_dispatch_even_if_budget_remains(tmp_path):
    store, b = setup_batch(tmp_path, 30000)
    task = store.tasks("w", b["id"])[0]
    store.reserve(b["id"], task["id"], "economy", 100)
    with pytest.raises(ValueError, match="in.flight"):
        store.reserve(b["id"], task["id"], "strong", 100)


def test_restore_to_before_spending_is_detected(tmp_path):
    store, b = setup_batch(tmp_path, 30000)
    backup = tmp_path / "before.sqlite3"
    with store.connect() as db, sqlite3.connect(backup) as dest:
        db.backup(dest)
    task = store.tasks("w", b["id"])[0]
    a = store.reserve(b["id"], task["id"], "economy", 100)
    store.settle(a, Usage(input_tokens=50, output_tokens=10))
    restored = Store(tmp_path / "restore", journal_dir=store.journal_dir)
    with sqlite3.connect(backup) as source, restored.connect() as dest:
        source.backup(dest)
    restored = Store(tmp_path / "restore", journal_dir=store.journal_dir)
    assert not restored.analytics("w", b["id"])["journal_consistent"]
    with pytest.raises(ValueError, match="journal"):
        restored.reserve(b["id"], task["id"], "strong", 100)


def test_cancel_fences_worker_publication_but_retains_usage(tmp_path):
    store, b = setup_batch(tmp_path, 30000)
    store.start("w", b["id"])
    job = store.claim()
    a = store.reserve(b["id"], job["id"], "economy", 100)
    store.cancel("w", b["id"])
    store.settle(a, Usage(input_tokens=50, output_tokens=10))
    with pytest.raises(ValueError, match="lease"):
        store.checkpoint(job, {"reason": "late"})
    assert store.analytics("w", b["id"])["tokens"] == 60


def test_expired_worker_moves_to_partial_and_keeps_first_row(tmp_path):
    store, b = setup_batch(tmp_path, 30000)
    store.start("w", b["id"])
    job = store.claim()
    with store.write() as db:
        db.execute("UPDATE tasks SET deadline=? WHERE id=?", (time.time() - 1, job["id"]))
    assert store.claim() is None
    assert store.batch("w", b["id"])["state"] == "partial"
    assert store.tasks("w", b["id"])[0]["state"] == "failed"


def test_source_tamper_blocks_export_not_just_inference(tmp_path):
    store, b = setup_batch(tmp_path)
    with store.write() as db:
        db.execute(
            "UPDATE feeds SET body=? WHERE id=?",
            (json.dumps([Product(id="m", title="other").model_dump()]), b["spec"]["master_id"]),
        )
    with pytest.raises(ValueError, match="integrity"):
        store.export("w", b["id"])


def test_attempt_overrun_is_not_clipped(tmp_path):
    store, b = setup_batch(tmp_path, 1000)
    task = store.tasks("w", b["id"])[0]
    a = store.reserve(b["id"], task["id"], "economy", 600)
    store.settle(a, Usage(input_tokens=1000, output_tokens=100))
    assert store.analytics("w", b["id"])["tokens"] == 1100
    assert store.analytics("w", b["id"])["remaining_tokens"] == 0
    assert any('"overrun": true' in e["body"] for e in store.audit("w", b["id"]))


def test_explicit_failures_do_not_drop_earlier_row_results(tmp_path):
    store = Store(tmp_path)
    m = store.import_feed("w", "master", [Product(id="m", title="Memory 8GB")])
    s = store.import_feed(
        "w",
        "supplier",
        [Product(id="s1", title="Memory 8GB"), Product(id="s2", title="Memory 8GB")],
    )
    from contracts.catalogbridge import BatchSpec

    b = store.create_batch("w", BatchSpec(master_id=m["id"], supplier_id=s["id"], egress=True))
    store.start("w", b["id"])
    run_once(store, FakeModels(["same_product", "same_product"]))
    run_once(store, FakeModels(["timeout"]))
    tasks = store.tasks("w", b["id"])
    assert tasks[0]["result"]["proposal"]["outcome"] == "same_product"
    assert tasks[1]["state"] == "failed"
    assert store.batch("w", b["id"])["state"] == "partial"


@pytest.mark.parametrize(
    "payload",
    [b"id,title\nx,a\nx,b", b"[]", b"{}", b'[{"id":"a","title":"x","cluster_id":1}]', b"\xff"],
)
def test_bad_imports(payload):
    with pytest.raises(ValueError):
        parse_feed(payload, "csv" if payload.startswith(b"id,") else "json")


def test_review_with_another_master_id_is_rejected(tmp_path):
    store, b = setup_batch(tmp_path)
    store.start("w", b["id"])
    # Manual-only egress set for this fixture.
    with store.write() as db:
        spec = b["spec"] | {"egress": False}
        db.execute("UPDATE batches SET spec=? WHERE id=?", (json.dumps(spec), b["id"]))
    run_once(store)
    t = store.tasks("w", b["id"])[0]
    with pytest.raises(ValueError, match="candidate"):
        store.review(
            "w",
            t["id"],
            "reviewer",
            Review(
                expected_revision=t["revision"],
                action="correct",
                candidate_id="foreign",
                reason="fixture",
            ),
        )
