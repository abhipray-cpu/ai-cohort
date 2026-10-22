import json

import pytest
from contracts.releasefence import Span
from releasefence_api.backends import Backend, correlation
from releasefence_api.telemetry import otlp
from test_releasefence_store import configured, rf, rf_admin  # noqa: F401


def test_backend_configuration_encrypted_export_retry_readback_and_scope(rf):
    s, t, other = rf
    stable, _, _, enrolled = configured(rf)
    id = s.backend(
        "owner",
        t,
        "phoenix",
        "http://127.0.0.1:4318/v1/traces",
        "http://127.0.0.1:6006",
        "super-private-key",
        "project",
        "backend",
        lab_loopback=True,
    )
    assert "super-private-key" not in str(s.list("owner", t, "backend"))
    auth = s.machine(enrolled["token"])
    span = Span(
        trace_id="1" * 32, span_id="2" * 16, name="agent", release=stable, started_ns=1, ended_ns=2
    )
    s.ingest_spans(auth, [span])
    calls = []

    def transport(url, **kw):
        calls.append(url)
        if kw["method"] == "GET":
            return 200, json.dumps(
                {
                    "data": [
                        {
                            "context": {"trace_id": span.trace_id, "span_id": span.span_id},
                            "parent_id": None,
                            "attributes": {"releasefence.release": stable},
                        }
                    ]
                }
            ).encode()
        return 202, b"{}"

    result = s.export_backend(t, id, transport=transport)
    assert result["verified"] and len(calls) == 2
    assert s.list("owner", t, "backend")[0]["status"] == "verified"
    assert not s.list("owner", other, "backend")
    assert s.export_backend(t, id, transport=transport) is None


def test_vendor_readback_requires_identity_parent_release_not_http_success():
    root = Span(
        trace_id="1" * 32,
        span_id="2" * 16,
        name="agent",
        release="a" * 64,
        started_ns=1,
        ended_ns=2,
    )
    child = root.model_copy(update={"span_id": "3" * 16, "parent_span_id": root.span_id})
    calls = []

    def transport(url, **kw):
        calls.append((url, kw))
        if kw.get("method") == "GET":
            span = child if correlation(child)["id"] in url else root
            ids = correlation(span)
            return 200, json.dumps(
                {
                    "id": ids["id"],
                    "parent_run_id": ids["parent"],
                    "extra": {
                        "metadata": {
                            "releasefence.release": span.release,
                            "releasefence.trace_id": span.trace_id,
                            "releasefence.span_id": span.span_id,
                        }
                    },
                }
            ).encode()
        return 200, b"{}"

    backend = Backend(
        "langsmith",
        "https://owned.example/otel/v1/traces",
        "https://owned.example",
        "secret",
        "project",
        transport=transport,
    )
    backend.export([root, child])
    assert backend.verify([root, child])["verified"]
    attrs = otlp([child])["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"]
    assert any(a["key"] == "langsmith.span.parent_id" for a in attrs)
    backend.transport = lambda *a, **k: (200, b"{}")
    assert not backend.verify([root])["verified"]


def test_phoenix_readback_and_no_raw_backend_errors():
    span = Span(
        trace_id="1" * 32,
        span_id="2" * 16,
        name="agent",
        release="a" * 64,
        started_ns=1,
        ended_ns=2,
    )
    payload = {
        "data": [
            {
                "context": {"trace_id": span.trace_id, "span_id": span.span_id},
                "parent_id": None,
                "attributes": {"releasefence.release": span.release},
            }
        ]
    }
    b = Backend(
        "phoenix",
        "https://owned.example/v1/traces",
        "https://owned.example",
        "secret",
        "project",
        transport=lambda *a, **k: (200, json.dumps(payload).encode()),
    )
    assert b.verify([span])["verified"]
    payload["data"][0]["attributes"]["releasefence.release"] = "b" * 64
    assert not b.verify([span])["verified"]
    with pytest.raises(ValueError):
        Backend("unknown", "https://a", "https://a", "secret", "project")


def test_phoenix_export_targets_the_same_project_as_readback():
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

    requests = []

    def transport(url, **kwargs):
        requests.append(kwargs)
        return 200, b"{}"

    backend = Backend(
        "phoenix",
        "http://127.0.0.1:6006/v1/traces",
        "http://127.0.0.1:6006",
        "lab",
        "isolated-project",
        transport=transport,
        lab_loopback=True,
    )
    backend.export(
        [
            Span(
                trace_id="1" * 32,
                span_id="2" * 16,
                name="agent",
                release="a" * 64,
                started_ns=1,
                ended_ns=2,
            )
        ]
    )
    assert requests[0]["headers"]["x-project-name"] == "isolated-project"
    assert requests[0]["headers"]["Content-Type"] == "application/x-protobuf"
    wire = ExportTraceServiceRequest.FromString(requests[0]["body"])
    span = wire.resource_spans[0].scope_spans[0].spans[0]
    assert span.trace_id.hex() == "1" * 32 and span.span_id.hex() == "2" * 16


def test_phoenix_readback_uses_documented_repeated_trace_id_wire_filter():
    from urllib.parse import parse_qs, urlsplit

    span = Span(
        trace_id="1" * 32,
        span_id="2" * 16,
        name="agent",
        release="a" * 64,
        started_ns=1,
        ended_ns=2,
    )

    def transport(url, **kwargs):
        query = parse_qs(urlsplit(url).query)
        # The Python client argument is trace_ids, but the REST wire name is trace_id.
        assert query.get("trace_id") == [span.trace_id]
        assert "trace_ids" not in query
        return 200, json.dumps(
            {
                "data": [
                    {
                        "context": {"trace_id": span.trace_id, "span_id": span.span_id},
                        "parent_id": None,
                        "attributes": {"releasefence.release": span.release},
                    }
                ]
            }
        ).encode()

    backend = Backend(
        "phoenix",
        "https://owned.example/v1/traces",
        "https://owned.example",
        "secret",
        "project",
        transport=transport,
    )
    assert backend.verify([span])["verified"]


def test_trace_dead_letters_are_durable_and_have_one_bounded_owner_replay(rf):
    from releasefence_api.errors import Conflict

    s, t, _ = rf
    stable, _, _, enrolled = configured(rf)
    id = s.backend(
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
        s.machine(enrolled["token"]),
        [
            Span(
                trace_id="1" * 32,
                span_id="2" * 16,
                name="agent",
                release=stable,
                started_ns=1,
                ended_ns=2,
            )
        ],
    )
    for i in range(5):
        s.now = lambda i=i: 1000 + i * 1000
        s.export_backend(t, id, transport=lambda *a, **k: (503, b"PRIVATE"))
    work = s.list("owner", t, "trace_export")[0]
    assert work["state"] == "dead_letter" and "PRIVATE" not in str(work)
    s.replay_trace("owner", t, work["id"])
    with pytest.raises(Conflict):
        s.replay_trace("owner", t, work["id"])
    s.set_connection("owner", t, "backend", id, False)
    assert (
        s.export_backend(t, id, transport=lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
        is None
    )


def test_canary_requires_fresh_both_backend_readback_for_both_release_arms():
    from releasefence_api.backends import trace_gate

    assert trace_gate([], "support:staging", "a" * 64, "b" * 64, 1000, 1300, 1331)
    records = [
        {
            "kind": kind,
            "enabled": True,
            "status": "verified",
            "verified_releases": {
                f"support:staging:{release}": {"at": 1300, "started_ns": 1100 * 10**9}
                for release in ("a" * 64, "b" * 64)
            },
        }
        for kind in ("langsmith", "phoenix")
    ]
    assert not trace_gate(records, "support:staging", "a" * 64, "b" * 64, 1000, 1300, 1331)
    assert trace_gate(
        records, "support:staging", "a" * 64, "b" * 64, 1000, 1300, 1331, backlog={"phoenix": 1}
    )
    assert trace_gate(records, "support:other", "a" * 64, "b" * 64, 1000, 1300, 1331)
    records[0]["status"] = "degraded"
    assert trace_gate(records, "support:staging", "a" * 64, "b" * 64, 1000, 1300, 1331)


def test_explicit_oss_profile_requires_mlflow_and_phoenix_without_waiving_legacy():
    from contracts.releasefence import Policy
    from releasefence_api.backends import trace_gate

    policy = Policy(trace_profile="mlflow-phoenix-v1")
    records = [
        {
            "kind": kind,
            "enabled": True,
            "status": "verified",
            "verified_releases": {
                f"support:staging:{r}": {"at": 1300, "started_ns": 1100 * 10**9}
                for r in ("a" * 64, "b" * 64)
            },
        }
        for kind in ("mlflow", "phoenix")
    ]
    assert not trace_gate(
        records,
        "support:staging",
        "a" * 64,
        "b" * 64,
        1000,
        1300,
        1331,
        profile=policy.trace_profile,
    )
    assert "langsmith_trace_backend_unverified" in trace_gate(
        records, "support:staging", "a" * 64, "b" * 64, 1000, 1300, 1331
    )
    assert "mlflow_trace_export_incomplete" in trace_gate(
        records,
        "support:staging",
        "a" * 64,
        "b" * 64,
        1000,
        1300,
        1331,
        profile=policy.trace_profile,
        backlog={"mlflow": 1},
    )
    with pytest.raises(ValueError):
        Policy(trace_profile="skip-vendor-checks")


def test_mlflow_configuration_is_encrypted_and_experiment_scoped(rf):
    import base64

    s, tenant, _ = rf
    configured(rf)
    id = s.backend(
        "owner",
        tenant,
        "mlflow",
        "http://127.0.0.1:5000/v1/traces",
        "http://127.0.0.1:5000",
        "scoped:private-password",
        "123",
        "mlflow",
        lab_loopback=True,
    )
    assert any(row["id"] == id for row in s.list("owner", tenant, "backend"))
    assert "private-password" not in str(s.list("owner", tenant, "backend"))
    backend = Backend(
        "mlflow",
        "http://127.0.0.1:5000/v1/traces",
        "http://127.0.0.1:5000",
        "scoped:private-password",
        "123",
        lab_loopback=True,
    )
    assert backend.headers["x-mlflow-experiment-id"] == "123"
    assert (
        backend.headers["Authorization"]
        == "Basic " + base64.b64encode(b"scoped:private-password").decode()
    )
    assert backend.headers["Content-Type"] == "application/x-protobuf"
    for key, project in [
        ("no-user-password", "123"),
        ("user:pass", "not-an-experiment"),
        ("user:", "123"),
    ]:
        with pytest.raises(ValueError):
            Backend(
                "mlflow",
                "http://127.0.0.1:5000/v1/traces",
                "http://127.0.0.1:5000",
                key,
                project,
                lab_loopback=True,
            )


def test_mlflow_readback_checks_proto_byte_ids_parent_release_and_experiment():
    import base64

    span = Span(
        trace_id="1" * 32,
        span_id="2" * 16,
        parent_span_id="3" * 16,
        name="llm",
        kind="llm",
        release="a" * 64,
        started_ns=1,
        ended_ns=2,
    )
    encode = lambda value: base64.b64encode(bytes.fromhex(value)).decode()
    item = {
        "trace_id": encode(span.trace_id),
        "span_id": encode(span.span_id),
        "parent_span_id": encode(span.parent_span_id),
        "attributes": [{"key": "releasefence.release", "value": {"string_value": span.release}}],
    }
    payload = {
        "trace": {
            "trace_info": {
                "trace_id": "tr-" + span.trace_id,
                "trace_location": {"mlflow_experiment": {"experiment_id": "123"}},
            },
            "spans": [item],
        }
    }
    calls = []

    def transport(url, **kwargs):
        calls.append(url)
        return 200, json.dumps(payload).encode()

    backend = Backend(
        "mlflow",
        "https://owned.example/v1/traces",
        "https://owned.example",
        "scoped:password",
        "123",
        transport=transport,
    )
    assert backend.verify([span])["verified"]
    assert "/api/3.0/mlflow/traces/get?trace_id=tr-" in calls[0]
    payload["trace"]["trace_info"]["trace_location"]["mlflow_experiment"]["experiment_id"] = "other"
    assert not backend.verify([span])["verified"]
    payload["trace"]["trace_info"]["trace_location"]["mlflow_experiment"]["experiment_id"] = "123"
    item["parent_span_id"] = encode("4" * 16)
    assert not backend.verify([span])["verified"]
