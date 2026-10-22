import pytest
from contracts.releasefence import Event, Policy
from releasefence_api.core import assignment
from releasefence_api.engine import Engine
from test_releasefence_store import configured, rf, rf_admin  # noqa: F401


def started(rf):
    s, tenant, _ = rf
    stable, candidate, _key, enrolled = configured(rf)
    rollout = s.create_rollout(
        "owner",
        tenant,
        "support",
        "staging",
        stable,
        candidate,
        Policy(),
        [enrolled["id"]],
        2000,
        "roll",
    )
    s.approve(
        "reviewer", tenant, rollout, 0, ["canary", "rollback"], 2000, "approve", auto_rollback=True
    )
    commands = s.control("owner", tenant, rollout, "canary", 0, "start")
    auth = s.machine(enrolled["token"])
    router = s.test_router
    envelope = s.poll(auth)[0]
    router.apply(envelope)
    assert s.poll(auth)[0] == envelope  # Apply succeeded; acknowledgement was lost.
    router.apply(envelope)
    s.attest(auth, router.attest(commands[0]))
    return s, tenant, rollout, auth, router, stable, candidate


def test_verified_control_retains_the_signed_runtime_receipt_for_independent_audit(rf):
    from releasefence_api.crypto import verify

    s, tenant, _roll, auth, _router, _stable, _candidate = started(rf)
    command = s.list("owner", tenant, "command")[0]
    enrollment = next(
        r for r in s.list("owner", tenant, "enrollment") if r["id"] == auth["enrollment"]
    )
    assert verify(command["proof_envelope"], enrollment["public_key"]) == command["proof"]


def test_closed_oss_profile_decision_demands_mlflow_and_phoenix_not_legacy_vendor(rf):
    s, tenant, _ = rf
    stable, candidate, _, enrolled = configured(rf)
    roll = s.create_rollout(
        "owner",
        tenant,
        "support",
        "staging",
        stable,
        candidate,
        Policy(trace_profile="mlflow-phoenix-v1"),
        [enrolled["id"]],
        2000,
        "roll",
    )
    s.approve("reviewer", tenant, roll, 0, ["canary", "rollback"], 2000, "approval")
    command = s.control("owner", tenant, roll, "canary", 0, "start")[0]
    auth, router = s.machine(enrolled["token"]), s.test_router
    router.apply(s.poll(auth)[0])
    s.attest(auth, router.attest(command))
    s.now = lambda: 1331
    s.heartbeat(auth, router.attest("heartbeat", window=(1000, 1300)))
    result = s.analyze_rollout("owner", tenant, roll)
    assert result["decision"] == "inconclusive"
    assert "mlflow_trace_backend_unverified" in result["reasons"]
    assert "phoenix_trace_backend_unverified" in result["reasons"]
    assert not any("langsmith" in reason for reason in result["reasons"])


def test_real_router_rollback_is_not_verified_until_inflight_work_is_drained(rf):
    s, t, roll, auth, r, stable, candidate = started(rf)
    state = r.state()
    session = next(
        "s" + str(i)
        for i in range(1000)
        if assignment(f"{r.enrollment}:support:staging", "s" + str(i), state["seed"], 5)
        == "candidate"
    )
    assert r.open_session(session) == candidate
    row = next(x for x in s.list("owner", t, "rollout") if x["id"] == roll)
    command = s.control("owner", t, roll, "rollback", row["revision"], "rollback")[0]
    r.apply(s.poll(auth)[0])
    assert not s.attest(auth, r.attest(command))
    assert s.list("owner", t, "rollout")[0]["state"] == "verifying"
    assert r.open_session("fresh-after-rollback") == stable
    r.finish_session(session)
    assert s.attest(auth, r.attest(command))
    assert s.list("owner", t, "rollout")[0]["state"] == "rollback_verified"


def test_loop_incident_dedup_notifications_retry_and_preauthorized_rollback(rf):
    s, t, _roll, auth, _r, _stable, candidate = started(rf)
    s.destination(
        "owner",
        t,
        "http://127.0.0.1:9999/hook",
        "owned-webhook-secret-123456",
        "destination",
        lab_loopback=True,
    )
    events = [
        Event(
            id="accepted", task="bad", session="bad", release=candidate, kind="accepted", at=1000
        ),
        Event(
            id="cap",
            task="bad",
            session="bad",
            release=candidate,
            kind="terminal",
            at=1000,
            outcome="failure",
            model_calls=0,
            duration_ms=10,
            stop_reason="iteration_exhausted",
        ),
    ]
    s.ingest(auth, events)
    calls = []

    def transport(*args, **kw):
        calls.append(kw)
        if len(calls) == 1:
            raise TimeoutError("private receiver error")
        return 202, b"ok"

    engine = Engine(s, transport=transport, lab_loopback=True)
    engine.scan(t)
    engine.scan(t)
    assert len(s.list("owner", t, "incident")) == 1
    assert engine.deliver(t)
    assert s.list("owner", t, "notification")[0]["state"] == "retry"
    s.now = lambda: 1006
    assert engine.deliver(t)
    assert s.list("owner", t, "notification")[0]["state"] == "delivered"
    assert len(s.list("owner", t, "command")) == 2
    assert s.list("owner", t, "rollout")[0]["state"] == "verifying"


def test_low_volume_window_closes_inconclusive_and_cannot_be_peeked_again(rf):
    s, t, roll, auth, r, _stable, _candidate = started(rf)
    assert s.analyze_rollout("owner", t, roll)["reasons"] == ["window_not_closed"]
    from contracts.releasefence import Span

    s.backend(
        "owner",
        t,
        "phoenix",
        "http://127.0.0.1:9999/v1/traces",
        "http://127.0.0.1:9999",
        "private",
        "project",
        "backend",
        lab_loopback=True,
    )
    s.ingest_spans(
        auth,
        [
            Span(
                trace_id="1" * 32,
                span_id="2" * 16,
                name="agent",
                release=_stable,
                started_ns=1001 * 10**9,
                ended_ns=1002 * 10**9,
            )
        ],
    )
    s.now = lambda: 1331
    s.heartbeat(auth, r.attest("heartbeat"))
    result = s.analyze_rollout("owner", t, roll)
    assert result["decision"] == "inconclusive"
    assert "phoenix_trace_export_incomplete" in result["reasons"]
    assert s.analyze_rollout("owner", t, roll)["id"] == result["id"]


def test_expired_lost_command_requires_fresh_reconciliation_and_new_independent_approval(rf):
    from releasefence_api.errors import Conflict, Forbidden

    s, t, _ = rf
    stable, candidate, _, enrolled = configured(rf)
    roll = s.create_rollout(
        "owner",
        t,
        "support",
        "staging",
        stable,
        candidate,
        Policy(),
        [enrolled["id"]],
        1100,
        "roll",
    )
    s.approve("reviewer", t, roll, 0, ["canary", "rollback"], 1100, "approval")
    s.control("owner", t, roll, "canary", 0, "start")
    auth = s.machine(enrolled["token"])
    router = s.test_router
    router.apply(s.poll(auth)[0])  # Crash/lost ACK after applying candidate routing.
    s.now = lambda: 1161
    with pytest.raises(Conflict):
        s.recover("owner", t, roll, 2000)
    s.heartbeat(auth, router.attest("heartbeat"))
    s.recover("owner", t, roll, 2000)
    row = s.list("owner", t, "rollout")[0]
    with pytest.raises(Forbidden):
        s.control("owner", t, roll, "rollback", row["revision"], "without-new-approval")
    s.approve("reviewer", t, roll, row["revision"], ["rollback"], 2000, "recovery-approval")
    old_proof = router.attest(s.list("owner", t, "command")[0]["id"])
    cmd = s.control("owner", t, roll, "rollback", row["revision"], "recovery")
    router.apply(next(e for e in s.poll(auth) if e["body"]["id"] == cmd[0]))
    assert s.attest(auth, router.attest(cmd[0]))
    with pytest.raises(Conflict):
        s.attest(auth, old_proof)
    assert s.list("owner", t, "rollout")[0]["state"] == "rollback_verified"


def test_demoting_approver_invalidates_unexecuted_authority(rf):
    from releasefence_api.errors import Forbidden

    s, t, roll, _auth, _r, _, _ = started(rf)
    s.member("owner", t, "reviewer", "observer")
    row = s.list("owner", t, "rollout")[0]
    with pytest.raises(Forbidden):
        s.control("owner", t, roll, "rollback", row["revision"], "no-longer-authorized")


def test_connector_reconciles_already_applied_command_after_authority_expires(rf):
    from fastapi.testclient import TestClient
    from releasefence_api.api import create_app
    from releasefence_api.connector import Connector

    s, t, _ = rf
    stable, candidate, _, enrolled = configured(rf)
    roll = s.create_rollout(
        "owner",
        t,
        "support",
        "staging",
        stable,
        candidate,
        Policy(),
        [enrolled["id"]],
        1100,
        "roll",
    )
    s.approve("reviewer", t, roll, 0, ["canary"], 1100, "approve")
    s.control("owner", t, roll, "canary", 0, "start")
    auth = s.machine(enrolled["token"])
    router = s.test_router
    router.apply(s.poll(auth)[0])
    s.now = lambda: 1101
    with TestClient(
        create_app(s, origin="http://testserver", administrator="owner"),
        headers={"Authorization": "Bearer " + enrolled["token"]},
    ) as client:
        assert Connector(router, client, enrolled["id"]).tick() == 1
    assert s.list("owner", t, "rollout")[0]["state"] == "canary_running"


def test_incident_resolution_requires_ack_and_verified_mitigation(rf):
    from releasefence_api.errors import Conflict

    s, t, _roll, auth, router, _, candidate = started(rf)
    s.ingest(
        auth,
        [
            Event(
                id="accepted",
                task="bad",
                session="bad",
                release=candidate,
                kind="accepted",
                at=1000,
            ),
            Event(
                id="failure",
                task="bad",
                session="bad",
                release=candidate,
                kind="terminal",
                at=1000,
                model_calls=0,
                outcome="failure",
                duration_ms=10,
                stop_reason="iteration_exhausted",
            ),
        ],
    )
    Engine(s).scan(t)
    incident = s.list("owner", t, "incident")[0]["id"]
    with pytest.raises(Conflict):
        s.resolve("owner", t, incident, "Verified mitigation")
    s.acknowledge("owner", t, incident)
    with pytest.raises(Conflict):
        s.resolve("owner", t, incident, "Acknowledgement alone is not resolution")
    command = s.poll(auth)[0]
    router.apply(command)
    s.attest(auth, router.attest(command["body"]["id"]))
    s.resolve("owner", t, incident, "Verified stable release now serving")
    assert s.list("owner", t, "incident")[0]["state"] == "resolved"


def test_crashed_notification_leases_count_toward_dead_letter_limit(rf):
    s, t, _, auth, _, _, candidate = started(rf)
    s.destination(
        "owner",
        t,
        "http://127.0.0.1:9999/hook",
        "owned-webhook-secret-123456",
        "destination",
        lab_loopback=True,
    )
    s.ingest(
        auth,
        [
            Event(
                id="accepted",
                task="bad",
                session="bad",
                release=candidate,
                kind="accepted",
                at=1000,
            ),
            Event(
                id="failure",
                task="bad",
                session="bad",
                release=candidate,
                kind="terminal",
                at=1000,
                model_calls=0,
                outcome="failure",
                duration_ms=10,
                stop_reason="iteration_exhausted",
            ),
        ],
    )
    engine = Engine(
        s, transport=lambda *a, **k: (_ for _ in ()).throw(AssertionError("retry budget exceeded"))
    )
    engine.scan(t)
    with s.db(t) as db:
        row = s._rows(db, "notification")[0]
        row.update(
            state="sending",
            lease="crashed",
            lease_until=999,
            due=999,
            attempts=[
                {"at": 900 + i, "status": None, "disposition": "in_flight"} for i in range(5)
            ],
        )
        s._save(db, "notification", row)
    assert not engine.deliver(t)
    row = s.list("owner", t, "notification")[0]
    assert row["state"] == "dead_letter" and row["attempts"][-1]["disposition"] == "unknown"


def test_critical_failure_blocks_promotion_even_if_a_statistical_pass_exists(rf):
    from releasefence_api.errors import Conflict

    s, t, roll, auth, _, _, candidate = started(rf)
    s.ingest(
        auth,
        [
            Event(
                id="accepted",
                task="bad",
                session="bad",
                release=candidate,
                kind="accepted",
                at=1000,
            ),
            Event(
                id="failure",
                task="bad",
                session="bad",
                release=candidate,
                kind="terminal",
                at=1000,
                model_calls=0,
                outcome="failure",
                duration_ms=10,
                stop_reason="iteration_exhausted",
            ),
        ],
    )
    # Inject an analysis-pass state to test the independent dispatch safety boundary.
    with s.db(t) as db:
        row = s._get(db, "rollout", roll)
        row.update(state="promotion_pending", stage=25)
        s._save(db, "rollout", row)
    s.approve("reviewer", t, roll, row["revision"], ["promote"], 2000, "promotion")
    with pytest.raises(Conflict):
        s.control("owner", t, roll, "promote", row["revision"], "unsafe-promote")
