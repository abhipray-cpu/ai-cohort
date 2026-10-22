import pytest
from contracts.releasefence import Event
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from releasefence_api.connector import Router
from releasefence_api.crypto import public_key
from releasefence_api.sdk import Runtime, Spool


def test_spool_is_durable_bounded_idempotent_retrying_and_dead_letters(tmp_path):
    now = [1000]
    path = tmp_path / "spool.db"
    spool = Spool(path, capacity=2, now=lambda: now[0])
    event = Event(
        id="one", task="task", session="session", release="a" * 64, kind="accepted", at=1000
    )
    spool.enqueue(event)
    spool.enqueue(event)
    with pytest.raises(ValueError):
        spool.enqueue(event.model_copy(update={"task": "other"}))
    spool.enqueue(event.model_copy(update={"id": "two"}))
    with pytest.raises(ValueError):
        spool.enqueue(event.model_copy(update={"id": "three"}))
    spool = Spool(path, capacity=2, now=lambda: now[0])

    def timeout(*a, **k):
        raise TimeoutError("secret")

    for _ in range(5):
        spool.flush(timeout)
        now[0] += 1000
    assert spool.status() == {"dead_letter": 2}
    assert spool.replay() == 2
    seen = []

    def accepted(path, body):
        seen.extend(body["events"])
        return {"accepted": len(body["events"])}

    assert spool.flush(accepted) == 2
    assert len(seen) == 2 and spool.status() == {"delivered": 2}


def test_sdk_counts_independent_tasks_emits_usage_and_exception_terminal(tmp_path):
    key = Ed25519PrivateKey.generate()
    router = Router(
        tmp_path / "router.db",
        "runtime",
        "support",
        "staging",
        public_key(key),
        key,
        {"a" * 64},
        "a" * 64,
        now=lambda: 1000,
    )
    spool = Spool(tmp_path / "spool.db", now=lambda: 1000)
    runtime = Runtime(router, spool, now=lambda: 1000)
    with runtime.task("one", "conversation") as task:
        assert task.release == "a" * 64
        task.usage("attempt", input_tokens=10, output_tokens=2, reported_cost="0.01")
    with pytest.raises(RuntimeError), runtime.task("two", "conversation"):
        raise RuntimeError("PRIVATE ERROR")
    payload = []
    spool.flush(lambda p, b: payload.extend(b["events"]) or {"accepted": len(b["events"])})
    assert len(payload) == 5 and "PRIVATE" not in str(payload)
    counters = router.attest("heartbeat")["body"]["counters"]
    assert counters == [{"release": "a" * 64, "accepted": 2, "terminal": 2}]


def test_signed_window_counters_exclude_traffic_after_fixed_cutoff(tmp_path):
    key = Ed25519PrivateKey.generate()
    now = [1000.5]
    router = Router(
        tmp_path / "r.db",
        "runtime",
        "support",
        "staging",
        public_key(key),
        key,
        {"a" * 64},
        "a" * 64,
        now=lambda: now[0],
    )
    router.begin_task("in-window", "s1")
    router.end_task("in-window")
    now[0] = 1331
    router.begin_task("after-window", "s2")
    router.end_task("after-window")
    proof = router.attest("heartbeat", window=(1000, 1300))["body"]
    assert proof["window_start"] == 1000 and proof["window_end"] == 1300
    assert proof["counters"][0]["accepted"] == 1


def test_late_spool_sender_cannot_overwrite_a_new_lease_success(tmp_path):
    now = [1000]
    spool = Spool(tmp_path / "spool.db", now=lambda: now[0])
    spool.enqueue(
        Event(id="one", task="task", session="session", release="a" * 64, kind="accepted", at=1000)
    )

    def expired_sender(*args):
        now[0] += 61
        assert spool.flush(lambda *a: {"accepted": 1}) == 1
        raise TimeoutError()

    spool.flush(expired_sender)
    assert spool.status() == {"delivered": 1}


def test_tool_fingerprints_are_keyed_stable_on_restart_and_private_per_customer(tmp_path):
    first = Spool(tmp_path / "first.db")
    value = first.fingerprint(["tool", {"private": "argument"}])
    assert value == Spool(tmp_path / "first.db").fingerprint(["tool", {"private": "argument"}])
    assert value != Spool(tmp_path / "second.db").fingerprint(["tool", {"private": "argument"}])
    assert first.path.stat().st_mode & 0o077 == 0
