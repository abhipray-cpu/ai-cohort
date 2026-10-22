"""Actual authenticated MLflow + Phoenix, with independent outage isolation."""

import os
import secrets
import time

import httpx
from contracts.releasefence import Span
from releasefence_api.backends import Backend
from releasefence_api.telemetry import protobuf_export

from scripts.releasefence_backend_lab import BackendLab, eventually


def test_actual_mlflow_phoenix_identity_auth_scope_and_each_backend_outage(tmp_path):
    with BackendLab(
        tmp_path / "backends",
        os.environ["RELEASEFENCE_MLFLOW_PYTHON"],
        os.environ["RELEASEFENCE_PHOENIX_PYTHON"],
    ) as lab:
        first, second = lab.provision("first"), lab.provision("second")
        now = time.time_ns()
        trace, root = secrets.token_hex(16), secrets.token_hex(8)
        spans = [
            Span(
                trace_id=trace,
                span_id=root,
                release="a" * 64,
                name="agent",
                started_ns=now - 10**6,
                ended_ns=now,
            ),
            Span(
                trace_id=trace,
                span_id=secrets.token_hex(8),
                parent_span_id=root,
                release="a" * 64,
                name="tool",
                kind="tool",
                started_ns=now - 10**5,
                ended_ns=now,
            ),
        ]
        mlflow = Backend(
            "mlflow",
            lab.urls["mlflow"] + "/v1/traces",
            lab.urls["mlflow"],
            first["secret"],
            first["project"],
            lab_loopback=True,
        )
        phoenix = Backend(
            "phoenix",
            lab.urls["phoenix"] + "/v1/traces",
            lab.urls["phoenix"],
            "lab",
            "first",
            lab_loopback=True,
        )
        for backend in [mlflow, phoenix]:
            backend.export(spans)
            eventually(lambda backend=backend: backend.verify(spans)["verified"])
        path = "/api/3.0/mlflow/traces/get?trace_id=tr-" + trace
        assert httpx.get(lab.urls["mlflow"] + path).status_code in {401, 403}
        assert httpx.post(
            lab.urls["mlflow"] + "/v1/traces",
            content=protobuf_export(spans),
            headers={
                "Content-Type": "application/x-protobuf",
                "x-mlflow-experiment-id": first["project"],
            },
        ).status_code in {401, 403}
        assert httpx.post(
            lab.urls["mlflow"] + "/v1/traces",
            content=protobuf_export(spans),
            headers={
                "Content-Type": "application/x-protobuf",
                "x-mlflow-experiment-id": first["project"],
            },
            auth=tuple(second["secret"].split(":", 1)),
        ).status_code in {403, 404}
        assert httpx.get(
            lab.urls["mlflow"] + path, auth=tuple(second["secret"].split(":", 1))
        ).status_code in {403, 404}
        for kind, broken, healthy in [("mlflow", mlflow, phoenix), ("phoenix", phoenix, mlflow)]:
            lab.stop(kind)
            assert not broken.verify(spans)["verified"]
            assert healthy.verify(spans)["verified"]
            lab.start(kind)
            eventually(lambda broken=broken: broken.verify(spans)["verified"])
