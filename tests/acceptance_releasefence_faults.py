"""Explicit source-bound mechanical campaign; not auto-collected or live inference.

Run this file explicitly. Every episode has independent database/router state and
a different real USDA record. Clocks, faults and connector probes are controlled;
this is not 150 natural customer incidents or 150 live-model failures.
"""

import json
import os

import pytest
from contracts.releasefence import Event, Policy, Span, Usage
from pydantic import ValidationError
from releasefence_api.backends import trace_gate
from releasefence_api.connector import Router
from releasefence_api.core import analyze, assignment, detect, digest, metrics
from releasefence_api.errors import Conflict, Forbidden
from releasefence_api.sdk import Spool
from releasefence_api.telemetry import normalize_otlp, otlp
from releasefence_api.validation import load_corpus, source_checks
from test_releasefence_core import samples
from test_releasefence_pipeline import started
from test_releasefence_store import configured, rf, rf_admin  # noqa: F401

FAMILIES = (
    "repeated_action",
    "bounded_polling",
    "iteration_cap",
    "provider_deadline",
    "schema_exhaustion",
    "missing_terminal",
    "human_wait",
    "clock_skew",
    "duplicate_delivery",
    "conflicting_id",
    "late_event",
    "sampled_trace_hold",
    "collector_overflow",
    "exporter_outage",
    "unknown_cost",
    "cached_token_overlap",
    "price_revision",
    "cohort_imbalance",
    "low_traffic",
    "healthy_canary",
    "regressed_canary",
    "stale_approval",
    "replayed_command",
    "lost_ack_after_apply",
    "offline_runtime",
    "partial_rollback",
    "incompatible_stable",
    "runtime_restart",
    "cross_tenant",
    "redaction",
)


@pytest.fixture(scope="session")
def actual_corpus():
    path = os.environ.get("RELEASEFENCE_ACCEPTANCE_CORPUS")
    if not path:
        pytest.fail("explicit real corpus required; no synthetic fallback")
    rows, receipt = load_corpus(path)
    assert len(rows) >= 1000
    return rows, receipt


@pytest.mark.parametrize("episode", range(5))
@pytest.mark.parametrize("family", FAMILIES)
def test_source_bound_mechanical_fault_episode(rf, tmp_path, actual_corpus, family, episode):  # noqa: F811
    rows, provenance = actual_corpus
    row = rows[FAMILIES.index(family) * 5 + episode]
    assert all(source_checks(row).values())
    identity = digest([row["facts"]["source_ref"], family, episode])[:24]
    (tmp_path / "case.json").write_text(
        json.dumps(
            {
                "source_ref": row["facts"]["source_ref"],
                "source_sha256": provenance["records_sha256"],
                "family": family,
                "episode": episode,
                "clock": "controlled",
                "model_calls": 0,
            }
        )
    )
    s, tenant, other = rf
    if family in FAMILIES[22:28]:
        s, tenant, roll, auth, router, stable, candidate = started(rf)
    else:
        stable, candidate, _, enrolled = configured(rf)
        auth = s.machine(enrolled["token"])

    def event(id="accepted", kind="accepted", **fields):
        return Event(
            id=identity + ":" + id,
            session=identity,
            task=identity,
            release=stable,
            kind=kind,
            at=1000,
            **fields,
        )

    accepted = event()
    terminal = event("terminal", "terminal", outcome="success", model_calls=0, duration_ms=10)
    if family in {"repeated_action", "bounded_polling"}:
        events = [accepted] + [
            event(
                str(i),
                "tool",
                tool_fingerprint=digest(row["facts"]),
                progress="unchanged",
                polling=family == "bounded_polling",
                sequence=i,
            )
            for i in range(3)
        ]
        findings = detect(events, Policy(), now=1001)
        assert bool(findings) == (family == "repeated_action")
        if findings:
            assert findings[0]["rule"] == "repeated_action"
    elif family in {"iteration_cap", "provider_deadline", "schema_exhaustion"}:
        reason = {
            "iteration_cap": "iteration_exhausted",
            "provider_deadline": "deadline",
            "schema_exhaustion": "schema_exhausted",
        }[family]
        terminal = terminal.model_copy(update={"outcome": "failure", "stop_reason": reason})
        s.ingest(auth, [accepted, terminal])
        from releasefence_api.engine import Engine

        Engine(s).scan(tenant)
        incident = s.list("owner", tenant, "incident")[0]
        assert incident["rule"] == reason and incident["severity"] == "critical"
        assert s.metric_view("owner", tenant, "support", "staging")[stable]["successful"] == 0
    elif family in {"missing_terminal", "human_wait"}:
        events = [accepted]
        if family == "human_wait":
            events.append(event("wait", "heartbeat", waiting_until=2000))
        findings = detect(events, Policy(), now=1500)
        assert bool(findings) == (family == "missing_terminal")
    elif family in {"clock_skew", "late_event"}:
        if family == "late_event":
            s.now = lambda: 700000
        bad = accepted.model_copy(update={"at": 1061 if family == "clock_skew" else 1})
        with pytest.raises(Conflict):
            s.ingest(auth, [bad])
        assert not s.list("owner", tenant, "event")
    elif family in {"duplicate_delivery", "conflicting_id"}:
        assert s.ingest(auth, [accepted, terminal]) == 2
        if family == "duplicate_delivery":
            assert s.ingest(auth, [accepted, terminal]) == 0
        else:
            with pytest.raises(Conflict):
                s.ingest(auth, [accepted.model_copy(update={"sequence": 99})])
        assert len(s.list("owner", tenant, "event")) == 2
    elif family == "sampled_trace_hold":
        assert trace_gate([], "support:staging", stable, candidate, 1000, 1300, 1331)
    elif family == "collector_overflow":
        spool = Spool(tmp_path / "bounded.sqlite3", capacity=1)
        spool.enqueue(accepted)
        with pytest.raises(ValueError, match="full"):
            spool.enqueue(terminal)
        assert spool.status() == {"pending": 1}
    elif family == "exporter_outage":
        backend = s.backend(
            "owner",
            tenant,
            "phoenix",
            "http://127.0.0.1:9/v1/traces",
            "http://127.0.0.1:9",
            "lab",
            "unavailable",
            "backend",
            lab_loopback=True,
        )
        s.ingest_spans(
            auth,
            [
                Span(
                    trace_id=digest(identity)[:32],
                    span_id=digest(identity)[:16],
                    release=stable,
                    name="agent",
                    started_ns=1,
                    ended_ns=2,
                )
            ],
        )
        result = s.export_backend(tenant, backend)
        assert not result["verified"]
        assert s.list("owner", tenant, "backend")[0]["status"] == "degraded"
    elif family == "unknown_cost":
        s.ingest(auth, [accepted, terminal.model_copy(update={"model_calls": 1})])
        measured = s.metric_view("owner", tenant, "support", "staging")[stable]
        assert measured["unknown_calls"] == 1 and measured["cost_per_success"] is None
    elif family == "cached_token_overlap":
        with pytest.raises(ValidationError):
            Usage(attempt=identity, input_tokens=episode + 1, cached_input_tokens=episode + 2)
        usage = event(
            "usage",
            "usage",
            usage=Usage(
                attempt=identity,
                input_tokens=10,
                cached_input_tokens=4,
                output_tokens=2,
                reported_cost="0.01",
            ),
        )
        result = metrics([accepted, usage, terminal.model_copy(update={"model_calls": 1})])
        assert result["input_tokens"] == 10 and result["uncached_input_tokens"] == 6
    elif family == "price_revision":
        with pytest.raises(ValidationError):
            Usage(attempt=identity, estimated_cost="0.01")
        assert (
            Usage(attempt=identity, estimated_cost="0.01", price_revision=identity).price_revision
            == identity
        )
    elif family in {"cohort_imbalance", "low_traffic", "healthy_canary", "regressed_canary"}:
        n = 5 if family == "low_traffic" else 1000
        a = samples(n, prefix="stable-" + identity)
        b = samples(
            5 if family == "cohort_imbalance" else n,
            prefix="candidate-" + identity,
            duration_ms=300 if family == "regressed_canary" else 100,
        )
        expected = (
            "pass"
            if family == "healthy_canary"
            else "fail"
            if family == "regressed_canary"
            else "inconclusive"
        )
        assert analyze(a, b, Policy())["decision"] == expected
    elif family == "stale_approval":
        roll = s.create_rollout(
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
        s.approve("reviewer", tenant, roll, 0, ["canary", "rollback"], 1100, "approval")
        command_id = s.control("owner", tenant, roll, "canary", 0, "start")[0]
        router = s.test_router
        router.apply(s.poll(auth)[0])
        assert s.attest(auth, router.attest(command_id))
        s.now = lambda: 1101
        revision = s.list("owner", tenant, "rollout")[0]["revision"]
        with pytest.raises(Forbidden):
            s.control("owner", tenant, roll, "rollback", revision, "expired")
    elif family == "replayed_command":
        with router.db() as db:
            saved = db.execute("SELECT result FROM commands").fetchone()[0]
        # Already applied envelopes are stored exactly; the command is not executed twice.
        assert json.loads(saved)["revision"] == router.state()["revision"] == 1
        envelope = s.list("owner", tenant, "command")[0]["envelope"]
        assert router.apply(envelope)["revision"] == 1
    elif family == "lost_ack_after_apply":
        assert s.list("owner", tenant, "rollout")[0]["state"] == "canary_running"
        assert router.state()["revision"] == 1  # started() retries the identical lost-ACK envelope.
    elif family in {"offline_runtime", "partial_rollback", "incompatible_stable"}:
        session = None
        if family == "partial_rollback":
            state = router.state()
            session = next(
                identity + str(i)
                for i in range(10000)
                if assignment(
                    f"{router.enrollment}:support:staging", identity + str(i), state["seed"], 5
                )
                == "candidate"
            )
            assert router.open_session(session) == candidate
        revision = s.list("owner", tenant, "rollout")[0]["revision"]
        command_id = s.control("owner", tenant, roll, "rollback", revision, "rollback")[0]
        envelope = s.poll(auth)[0]
        if family == "incompatible_stable":
            router.bundles.remove(stable)
            with pytest.raises(ValueError):
                router.apply(envelope)
        elif family == "partial_rollback":
            router.apply(envelope)
            assert not s.attest(auth, router.attest(command_id))
            assert router.open_session("fresh-" + identity) == stable
            router.finish_session(session)
            assert s.attest(auth, router.attest(command_id))
            return
        assert s.list("owner", tenant, "rollout")[0]["state"] == "verifying"
    elif family == "runtime_restart":
        state = router.state()
        restored = Router(
            router.path,
            router.enrollment,
            router.application,
            router.environment,
            router.server_public,
            router.private,
            router.bundles,
            stable,
            now=router.now,
            probe=router.probe,
        )
        assert restored.state() == state
        assert restored.open_session(identity) in {stable, candidate}
    elif family == "cross_tenant":
        s.ingest(auth, [accepted, terminal])
        with s.db(other) as db:
            assert (
                db.execute("SELECT count(*) n FROM records WHERE kind='event'").fetchone()["n"] == 0
            )
        with pytest.raises(Forbidden):
            s.list("reviewer", other, "event")
    elif family == "redaction":
        span = Span(
            trace_id=digest(identity)[:32],
            span_id=digest(identity)[:16],
            name=row["facts"]["brand"],
            release=stable,
            started_ns=1,
            ended_ns=2,
        )
        body = otlp([span])
        body["resourceSpans"][0]["resource"]["attributes"].append(
            {"key": "input.value", "value": {"stringValue": json.dumps(row["facts"])}}
        )
        normalized = normalize_otlp(body)
        assert "input.value" not in str(otlp(normalized))
        assert row["facts"]["source_ref"] not in str(otlp(normalized))
    else:
        pytest.fail("unimplemented acceptance family")
