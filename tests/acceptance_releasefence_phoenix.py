"""Actual Phoenix process outage/recovery; explicit opt-in, never a fake vendor."""

import os
import secrets
import socket
import subprocess
import time

import httpx
from contracts.releasefence import Event, Span
from releasefence_api.backends import Backend
from test_releasefence_store import configured, rf, rf_admin  # noqa: F401


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def eventually(fn, timeout=40):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        try:
            result = fn()
            if result:
                return result
        except (httpx.HTTPError, OSError):
            pass
        time.sleep(0.2)
    raise AssertionError("actual Phoenix observation deadline exceeded")


def test_actual_phoenix_outage_retry_restart_parent_readback_and_no_double_count(rf, tmp_path):  # noqa: F811
    python = os.environ["RELEASEFENCE_PHOENIX_PYTHON"]
    s, tenant, _ = rf
    s.now = time.time
    stable, _, _, enrolled = configured(rf)
    auth = s.machine(enrolled["token"])
    url = f"http://127.0.0.1:{free_port()}"
    project = "actual-outage-" + secrets.token_hex(4)
    backend_id = s.backend(
        "owner",
        tenant,
        "phoenix",
        url + "/v1/traces",
        url,
        "isolated-lab",
        project,
        "backend",
        lab_loopback=True,
    )
    task = {"task": "one", "session": "one", "release": stable, "at": time.time()}
    s.ingest(
        auth,
        [
            Event(id="accepted", kind="accepted", **task),
            Event(
                id="terminal",
                kind="terminal",
                outcome="success",
                model_calls=0,
                duration_ms=10,
                **task,
            ),
        ],
    )
    baseline = s.metric_view("owner", tenant, "support", "staging")[stable]
    env = {
        k: v
        for k, v in os.environ.items()
        if k in {"PATH", "HOME", "TMPDIR", "SYSTEMROOT", "WINDIR"}
    }
    env.update(
        PHOENIX_HOST="127.0.0.1",
        PHOENIX_PORT=url.rsplit(":", 1)[1],
        PHOENIX_GRPC_PORT=str(free_port()),
        PHOENIX_WORKING_DIR=str(tmp_path / "phoenix"),
        PHOENIX_TELEMETRY_ENABLED="false",
        PHOENIX_DISABLE_AGENT_ASSISTANT="true",
        PHOENIX_ENABLE_MCP_SERVER="false",
        PHOENIX_ALLOW_EXTERNAL_RESOURCES="false",
    )
    processes = []

    def launch(log):
        p = subprocess.Popen(
            [python, "-m", "phoenix.server.main", "serve"], env=env, stdout=log, stderr=log
        )
        processes.append(p)
        eventually(lambda: httpx.get(url + "/healthz", timeout=2).status_code == 200)
        return p

    now = time.time_ns()
    trace_id, root_id = secrets.token_hex(16), secrets.token_hex(8)
    first = Span(
        trace_id=trace_id,
        span_id=root_id,
        name="agent",
        release=stable,
        started_ns=now - 1000000,
        ended_ns=now,
    )
    child = first.model_copy(
        update={"span_id": secrets.token_hex(8), "parent_span_id": root_id, "kind": "tool"}
    )
    later = first.model_copy(
        update={"trace_id": secrets.token_hex(16), "span_id": secrets.token_hex(8)}
    )

    def exported():
        result = s.export_backend(tenant, backend_id)
        return result if result and result["verified"] else None

    with (tmp_path / "phoenix.log").open("wb") as log:
        try:
            process = launch(log)
            s.ingest_spans(auth, [first, child])
            eventually(exported)
            process.terminate()
            process.wait(timeout=15)
            s.ingest_spans(auth, [later])
            assert not s.export_backend(tenant, backend_id)["verified"]
            assert s.list("owner", tenant, "backend")[0]["status"] == "degraded"
            assert any(r["state"] == "retry" for r in s.list("owner", tenant, "trace_export"))
            launch(log)
            eventually(exported)
            assert all(r["state"] == "verified" for r in s.list("owner", tenant, "trace_export"))
            real = Backend(
                "phoenix", url + "/v1/traces", url, "isolated-lab", project, lab_loopback=True
            )
            assert real.verify([first, child, later])["verified"]
            response = httpx.get(url + f"/v1/projects/{project}/spans", timeout=5)
            response.raise_for_status()
            assert len(response.json()["data"]) == 3
            current = s.metric_view("owner", tenant, "support", "staging")[stable]
            assert {k: v for k, v in current.items() if k != "as_of"} == {
                k: v for k, v in baseline.items() if k != "as_of"
            }
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
