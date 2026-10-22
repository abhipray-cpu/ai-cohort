import pytest
from contracts.releasefence import Command
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from releasefence_api.connector import Router
from releasefence_api.crypto import public_key, signed, verify


def command(**kw):
    return Command(
        id="one",
        enrollment="enrolled",
        application="support",
        environment="staging",
        rollout="roll",
        epoch=1,
        expected_revision=0,
        expires=200,
        action="canary",
        stable="a" * 64,
        candidate="b" * 64,
        weight=25,
        seed="seed",
        authority="approval",
        **kw,
    )


def test_signed_router_is_fenced_scoped_sticky_and_restart_durable(tmp_path):
    server = Ed25519PrivateKey.generate()
    runtime = Ed25519PrivateKey.generate()
    r = Router(
        tmp_path / "runtime.db",
        "enrolled",
        "support",
        "staging",
        public_key(server),
        runtime,
        {"a" * 64, "b" * 64},
        "a" * 64,
        now=lambda: 100,
    )
    request = signed(command(), server)
    first = r.apply(request)
    assert r.apply(request) == first
    chosen = r.open_session("session")
    newer = command().model_copy(
        update={"id": "two", "epoch": 2, "expected_revision": 1, "action": "rollback", "weight": 0}
    )
    r.apply(signed(newer, server))
    assert r.open_session("session") == chosen
    assert r.open_session("fresh") == "a" * 64
    again = Router(
        tmp_path / "runtime.db",
        "enrolled",
        "support",
        "staging",
        public_key(server),
        runtime,
        {"a" * 64, "b" * 64},
        "a" * 64,
        now=lambda: 100,
    )
    assert again.state()["revision"] == 2
    proof = again.attest(newer.id)
    assert verify(proof, public_key(runtime))["probe_release"] == "a" * 64
    for bad in [
        newer.model_copy(update={"id": "replay", "epoch": 1}),
        newer.model_copy(update={"id": "expired", "expires": 99}),
        newer.model_copy(update={"id": "other", "enrollment": "other"}),
    ]:
        with pytest.raises(ValueError):
            again.apply(signed(bad, server))


def test_router_rejects_tampered_payload_and_unknown_bundles(tmp_path):
    key = Ed25519PrivateKey.generate()
    r = Router(
        tmp_path / "r.db",
        "enrolled",
        "support",
        "staging",
        public_key(key),
        key,
        {"a" * 64},
        "a" * 64,
        now=lambda: 100,
    )
    request = signed(command(), key)
    with pytest.raises(ValueError):
        r.apply(request)
    request["body"]["weight"] = 100
    with pytest.raises(ValueError):
        r.apply(request)


def test_url_policy_rejects_private_dns_credentials_and_redirect_targets():
    from releasefence_api.network import resolve_destination

    with pytest.raises(ValueError):
        resolve_destination("http://127.0.0.1/hook")
    with pytest.raises(ValueError):
        resolve_destination("https://u:p@example.com/hook")
    with pytest.raises(ValueError):
        resolve_destination("https://x.test/hook", resolver=lambda *a: [("127.0.0.1", 443)])
    assert resolve_destination("http://127.0.0.1/hook", lab_loopback=True)[1] == "127.0.0.1"


def test_closed_candidate_session_cannot_resume_bad_bundle_after_verified_drain(tmp_path):
    from releasefence_api.core import assignment

    key = Ed25519PrivateKey.generate()
    router = Router(
        tmp_path / "r.db",
        "enrolled",
        "support",
        "staging",
        public_key(key),
        key,
        {"a" * 64, "b" * 64},
        "a" * 64,
        now=lambda: 100,
    )
    router.apply(signed(command(), key))
    session = next(
        "s" + str(i)
        for i in range(1000)
        if assignment("enrolled:support:staging", "s" + str(i), "seed", 25) == "candidate"
    )
    assert router.open_session(session) == "b" * 64
    router.finish_session(session)
    rollback = command().model_copy(
        update={
            "id": "rollback",
            "epoch": 2,
            "expected_revision": 1,
            "weight": 0,
            "action": "rollback",
        }
    )
    router.apply(signed(rollback, key))
    with pytest.raises(ValueError):
        router.open_session(session)
    assert router.open_session("fresh-after-rollback") == "a" * 64
    new_canary = command().model_copy(
        update={"id": "new-canary", "epoch": 3, "expected_revision": 2}
    )
    router.apply(signed(new_canary, key))
    router.finish_session(session)  # Duplicate completion must not undo retirement.
    with pytest.raises(ValueError):
        router.open_session(session)
