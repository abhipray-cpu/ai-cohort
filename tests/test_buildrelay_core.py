"""Day 8 behavioral contracts, written before the corresponding implementation."""

import concurrent.futures

import pytest
from buildrelay_api.store import Store
from contracts.buildrelay import RunEvent


def event(**changes):
    return RunEvent.model_validate(
        dict(
            repository_id=123,
            repository="acme/shop",
            run_id=77,
            attempt=1,
            conclusion="failure",
            workflow="CI",
            branch="main",
            sha="a" * 40,
            source_url="https://github.com/acme/shop/actions/runs/77",
            **changes,
        )
    )


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path)
    s.create_client("client", "Shop client")
    s.create_repo(
        "repo",
        "client",
        "acme/shop",
        123,
        "BUILDRELAY_SHOP_SECRET",
        "BUILDRELAY_SHOP_TOKEN",
        "Engineering",
        False,
    )
    return s


def test_cross_transport_deduplication_survives_restart(store):
    first = store.accept("repo", event(), "webhook", "delivery-one")
    second = Store(store.root).accept("repo", event(), "queue", "different-delivery")
    assert first == second
    assert len(store.events()) == 1


def test_repository_binding(store):
    e = event().model_copy(update={"repository_id": 999})
    with pytest.raises(ValueError, match="repository"):
        store.accept("repo", e, "queue", "bad")


def test_concurrent_claim_and_expired_lease_fencing(store):
    store.accept("repo", event(), "webhook", "a")
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        claimed = list(pool.map(lambda _: store.claim(now=100, lease=10), range(4)))
    job = next(j for j in claimed if j)
    assert sum(j is not None for j in claimed) == 1
    newer = store.claim(now=111, lease=10)
    assert newer["id"] == job["id"]
    with pytest.raises(ValueError, match="lease"):
        store.checkpoint(job, "evidence", {"text": "old"}, now=112)
    store.checkpoint(newer, "evidence", {"text": "fresh"}, now=112)


def test_retry_exhaustion_and_replay_preserve_identity(store):
    ident = store.accept("repo", event(), "webhook", "a")
    for now in (100, 200, 400):
        job = store.claim(now=now)
        store.fail(job, "upstream_unavailable", transient=True, now=now, max_attempts=3)
    assert store.events()[0]["state"] == "dead"
    store.replay(ident, "operator", now=500)
    assert store.events()[0]["id"] == ident
    assert store.events()[0]["state"] == "pending"
    assert any(a["action"] == "dead_letter_replayed" for a in store.audit())


def test_success_without_incident_does_not_create_one(store):
    success = event().model_copy(update={"conclusion": "success"})
    store.accept("repo", success, "webhook", "success")
    j = store.claim(now=100)
    store.finish(j, None, now=101)
    assert store.incidents() == []


def test_long_work_can_renew_but_expired_worker_cannot(store):
    store.accept("repo", event(), "queue", "one")
    job = store.claim(now=100, lease=10)
    store.renew(job, now=109, lease=20)
    assert store.claim(now=112) is None
    with pytest.raises(ValueError, match="lease"):
        store.renew(job, now=130, lease=20)


def test_contract_forbids_unknown_fields_and_invalid_urls():
    with pytest.raises(ValueError):
        event().model_copy().model_validate({**event().model_dump(), "shell": "run me"})
    with pytest.raises(ValueError):
        event().model_copy().model_validate(
            {**event().model_dump(), "source_url": "http://evil.test"}
        )
