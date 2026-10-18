import time

import pytest
from test_catalogbridge_core import setup_batch


def test_expired_lease_cannot_dispatch_another_paid_attempt(tmp_path):
    store, b = setup_batch(tmp_path, 30000)
    store.start("w", b["id"])
    job = store.claim()
    with store.write() as db:
        db.execute("UPDATE tasks SET deadline=? WHERE id=?", (time.time() - 1, job["id"]))
    with pytest.raises(ValueError, match="lease"):
        store.reserve(b["id"], job["id"], "economy", 100, expected_lease=job["lease"])


def test_queue_capacity_is_bounded(tmp_path):
    store, b = setup_batch(tmp_path)
    from contracts.catalogbridge import BatchSpec

    spec = BatchSpec.model_validate(b["spec"])
    store.start("w", b["id"])
    for _ in range(19):
        created = store.create_batch("w", spec)
        store.start("w", created["id"])
    extra = store.create_batch("w", spec)
    with pytest.raises(ValueError, match="queue"):
        store.start("w", extra["id"])
