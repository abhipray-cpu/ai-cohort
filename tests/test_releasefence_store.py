import secrets

import pytest
from contracts.releasefence import Policy
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from psycopg.conninfo import make_conninfo
from releasefence_api.crypto import public_key
from releasefence_api.store import Conflict, Forbidden, Store
from test_releasefence_core import event, release


@pytest.fixture(scope="session")
def rf_admin(tmp_path_factory):
    import os

    if os.environ.get("RELEASEFENCE_TEST_ADMIN_DSN"):
        yield os.environ["RELEASEFENCE_TEST_ADMIN_DSN"]
        return
    import pgserver

    server = pgserver.get_server(
        tmp_path_factory.mktemp("rf-postgres") / "data", cleanup_mode="stop"
    )
    yield server.get_uri()
    server.cleanup()


@pytest.fixture
def rf(rf_admin, tmp_path):
    suffix = secrets.token_hex(6)
    schema = "rf_" + suffix
    role = "rf_app_" + suffix
    password = secrets.token_urlsafe(24)
    Store.install(rf_admin, schema, role, password)
    encryption_key = Fernet.generate_key()
    s = Store(
        make_conninfo(rf_admin, user=role, password=password),
        encryption_key,
        Ed25519PrivateKey.generate(),
        schema=schema,
        now=lambda: 1000,
    )
    s.runtime_dir = tmp_path
    s.test_encryption_key = encryption_key
    s.create_user("owner", "owned-password-123")
    s.create_user("reviewer", "review-password-123")
    a = s.create_org("owner", "First")
    b = s.create_org("owner", "Second")
    s.member("owner", a, "reviewer", "approver")
    return s, a, b


def configured(rf):
    s, tenant, _ = rf
    stable = s.release("owner", tenant, release())
    candidate = s.release("owner", tenant, release(index_digest="e" * 64))
    s.environment("owner", tenant, "support", "staging", stable)
    key = Ed25519PrivateKey.generate()
    enrolled = s.enroll("owner", tenant, "support", "staging", public_key(key), "controlled")
    from releasefence_api.connector import Router

    router = Router(
        s.runtime_dir / (enrolled["id"] + ".db"),
        enrolled["id"],
        "support",
        "staging",
        enrolled["server_public_key"],
        key,
        {stable, candidate},
        stable,
        now=lambda: s.now(),
        probe=lambda identity, nonce: (
            __import__("hashlib").sha256((identity + nonce).encode()).hexdigest()
        ),
    )
    s.test_router = router
    s.heartbeat(s.machine(enrolled["token"]), router.attest("heartbeat"))
    return stable, candidate, key, enrolled


def test_rls_scope_idempotency_membership_and_plaintext_password_absence(rf):
    s, a, b = rf
    r = s.release("owner", a, release())
    assert s.release("owner", a, release()) == r
    with s.db(b) as db:
        assert (
            db.execute("SELECT count(*) n FROM records WHERE kind='release'").fetchone()["n"] == 0
        )
    with s.db() as db:
        assert db.execute("SELECT count(*) n FROM records").fetchone()["n"] == 0
    with pytest.raises(Forbidden):
        s.list("reviewer", b, "release")
    with s.db() as db:
        assert "owned-password" not in str(db.execute("SELECT password FROM users").fetchall())
    token, csrf = s.login("owner", "owned-password-123")
    assert s.session(token)["actor"] == "owner" and csrf
    s.logout(token)
    with pytest.raises(Forbidden):
        s.session(token)


def test_metric_view_namespaces_customer_runtime_local_identifiers(rf):
    s, t, _ = rf
    stable, _, key, enrolled = configured(rf)
    other = s.enroll("owner", t, "support", "staging", public_key(key), "observe")
    for token in (enrolled["token"], other["token"]):
        s.ingest(
            s.machine(token),
            [
                event("accept", kind="accepted", release=stable),
                event(
                    "end",
                    kind="terminal",
                    release=stable,
                    outcome="success",
                    duration_ms=10,
                    model_calls=0,
                ),
            ],
        )
    assert s.metric_view("owner", t, "support", "staging")[stable]["accepted"] == 2


def test_capacity_rejects_new_evidence_but_still_acknowledges_duplicate_retries(rf, monkeypatch):
    import releasefence_api.store as module

    monkeypatch.setattr(module, "EVENT_CAPACITY", 2, raising=False)
    s, _t, _ = rf
    stable, _, _, enrolled = configured(rf)
    auth = s.machine(enrolled["token"])
    events = [
        event("accept", release=stable),
        event(
            "end", kind="terminal", release=stable, outcome="success", duration_ms=20, model_calls=0
        ),
    ]
    assert s.ingest(auth, events) == 2
    assert s.ingest(auth, events) == 0
    with pytest.raises(Conflict):
        s.ingest(auth, [event("overflow", kind="heartbeat", release=stable)])


def test_rollout_requires_scoped_control_and_independent_exact_approval(rf):
    s, a, _ = rf
    stable, candidate, _key, enrolled = configured(rf)
    roll = s.create_rollout(
        "owner",
        a,
        "support",
        "staging",
        stable,
        candidate,
        Policy(),
        [enrolled["id"]],
        1100,
        "roll",
    )
    assert (
        s.create_rollout(
            "owner",
            a,
            "support",
            "staging",
            stable,
            candidate,
            Policy(),
            [enrolled["id"]],
            1100,
            "roll",
        )
        == roll
    )
    with pytest.raises(Forbidden):
        s.approve("owner", a, roll, 0, ["canary", "rollback"], 1100, "approval")
    s.approve("reviewer", a, roll, 0, ["canary", "rollback"], 1100, "approval")
    command = s.control("owner", a, roll, "canary", 0, "start")
    assert command and s.list("owner", a, "command")
    with pytest.raises(Conflict):
        s.control("owner", a, roll, "canary", 0, "different")


def test_ingest_is_machine_scoped_deduped_and_conflicts_are_not_success(rf):
    s, a, b = rf
    _, _, _, enrolled = configured(rf)
    auth = s.machine(enrolled["token"])
    assert auth["tenant"] == a
    e = event().model_copy(update={"release": s.list("owner", a, "release")[0]["id"]})
    assert s.ingest(auth, [e]) == 1
    assert s.ingest(auth, [e]) == 0
    with pytest.raises(Conflict):
        s.ingest(auth, [e.model_copy(update={"sequence": 3})])
    assert len(s.list("owner", a, "event")) == 1 and not s.list("owner", b, "event")
