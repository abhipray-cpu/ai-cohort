"""Engineering acceptance over real local processes, not a real-source campaign."""

import base64
import hashlib
import hmac
import json
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
from fastapi.testclient import TestClient
from releasefence_api.client import Client
from releasefence_api.connector import Connector
from releasefence_api.core import assignment
from releasefence_api.gateway import HTTPBundles, create_gateway
from releasefence_api.sdk import Runtime, Spool
from test_releasefence_core import release
from test_releasefence_store import configured, rf, rf_admin  # noqa: F401


def eventually(fn, seconds=15):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            value = fn()
            if value:
                return value
        except (httpx.HTTPError, OSError):
            pass
        time.sleep(0.1)
    raise AssertionError("bounded process observation timed out")


def test_http_process_worker_sdk_alert_receiver_canary_rollback_and_restart(rf, tmp_path):
    s, t, _ = rf
    s.now = time.time
    stable, candidate, _, enrolled = configured(rf)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    received = []
    served = []
    secret = "owned-notification-secret-123456"

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = self.rfile.read(int(self.headers["Content-Length"]))
            if self.path.startswith(("/stable/", "/candidate/")):
                body = json.loads(payload)
                loaded = stable if self.path.startswith("/stable/") else candidate
                assert self.headers["Authorization"] == "Bearer owned-bundle-key"
                assert body["release"] == loaded
                response = (
                    {"nonce": body["nonce"], "release": loaded, "healthy": True}
                    if self.path.endswith("/probe")
                    else {
                        "release": loaded,
                        "output": "Served by loaded fixture bundle",
                        "outcome": "success",
                        "model_calls": 1,
                        "usage": [{"attempt": "fixture:" + body["id"], "reported_cost": "0.01"}],
                    }
                )
                if self.path.endswith("/tasks"):
                    served.append(loaded)
                raw = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            assert hmac.compare_digest(
                self.headers["X-ReleaseFence-Signature"],
                hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest(),
            )
            received.append((self.headers["Idempotency-Key"], json.loads(payload)))
            self.send_response(503 if len(received) == 1 else 202)
            self.end_headers()

        def log_message(self, *args):
            pass

    receiver = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    thread = threading.Thread(target=receiver.serve_forever, daemon=True)
    thread.start()
    bundles = HTTPBundles(
        {
            stable: {
                "manifest": release().model_dump(),
                "url": f"http://127.0.0.1:{receiver.server_port}/stable",
                "token": "owned-bundle-key",
            },
            candidate: {
                "manifest": release(index_digest="e" * 64).model_dump(),
                "url": f"http://127.0.0.1:{receiver.server_port}/candidate",
                "token": "owned-bundle-key",
            },
        },
        lab_loopback=True,
    )
    s.test_router.probe = bundles.probe
    s.destination(
        "owner",
        t,
        f"http://127.0.0.1:{receiver.server_port}/hook",
        secret,
        "destination",
        lab_loopback=True,
    )
    env = {
        **os.environ,
        "RELEASEFENCE_DATABASE_URL": s.dsn,
        "RELEASEFENCE_SCHEMA": s.schema,
        "RELEASEFENCE_ENCRYPTION_KEY": s.test_encryption_key.decode(),
        "RELEASEFENCE_SIGNING_KEY": base64.b64encode(s.key.private_bytes_raw()).decode(),
        "RELEASEFENCE_USERNAME": "owner",
        "RELEASEFENCE_PASSWORD": "owned-password-123",
        "RELEASEFENCE_ORIGIN": url,
        "RELEASEFENCE_LAB_LOOPBACK": "1",
    }
    processes = []

    def launch(module, args=()):
        p = subprocess.Popen(
            [sys.executable, "-m", module, *args],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(p)
        return p

    api_args = [
        "releasefence_api.api:app_from_env",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    try:
        api = launch("uvicorn", api_args)
        worker = launch("releasefence_api.worker")
        with (
            httpx.Client(base_url=url, timeout=3) as owner,
            httpx.Client(base_url=url, timeout=3) as reviewer,
        ):
            eventually(lambda: owner.get("/health/ready").status_code == 200)
            assert "ReleaseFence" in owner.get("/").text
            for client, user, password in (
                (owner, "owner", "owned-password-123"),
                (reviewer, "reviewer", "review-password-123"),
            ):
                response = client.post(
                    "/api/session", json={"username": user, "password": password}
                )
                response.raise_for_status()
                client.headers.update({"Origin": url, "X-CSRF-Token": response.json()["csrf"]})
            prefix = f"/api/orgs/{t}"
            response = owner.post(
                prefix + "/rollout",
                json={
                    "application": "support",
                    "environment": "staging",
                    "stable": stable,
                    "candidate": candidate,
                    "policy": {},
                    "enrollments": [enrolled["id"]],
                    "expires": time.time() + 1200,
                },
                headers={"Idempotency-Key": "rollout"},
            )
            response.raise_for_status()
            roll = response.json()["id"]
            response = reviewer.post(
                prefix + f"/rollout/{roll}/approve",
                json={
                    "expected_revision": 0,
                    "actions": ["canary", "rollback"],
                    "expires": time.time() + 1100,
                    "auto_rollback": True,
                },
                headers={"Idempotency-Key": "approve"},
            )
            response.raise_for_status()
            connector = Connector(
                s.test_router,
                Client(url, enrolled["token"], lab_loopback=True),
                enrolled["id"],
            )
            assert connector.tick() == 0  # Actual HTTP bundle inventory and fresh probe.
            owner.post(
                prefix + f"/rollout/{roll}/control",
                json={"expected_revision": 0, "action": "canary"},
                headers={"Idempotency-Key": "control"},
            ).raise_for_status()
            connector = Connector(
                s.test_router, Client(url, enrolled["token"], lab_loopback=True), enrolled["id"]
            )
            assert connector.tick() == 1
            routing = s.test_router.state()
            session = next(
                "s" + str(i)
                for i in range(10000)
                if assignment(f"{enrolled['id']}:support:staging", "s" + str(i), routing["seed"], 5)
                == "candidate"
            )
            spool = Spool(tmp_path / "spool.db")
            runtime = Runtime(s.test_router, spool)
            gateway = TestClient(create_gateway(s.test_router, spool, bundles, "owned-gateway-key"))
            reply = gateway.post(
                "/agent/v1/tasks",
                headers={"Authorization": "Bearer owned-gateway-key"},
                json={
                    "id": "served-candidate",
                    "session": session,
                    "input": "Deterministic engineering fixture",
                },
            )
            assert reply.status_code == 200 and reply.json()["release"] == candidate
            with runtime.task("bad-task", session) as task:
                task.usage("actual-attempt", input_tokens=10, output_tokens=2, reported_cost="0.01")
                task.outcome = "failure"
                task.stop_reason = "iteration_exhausted"
            assert spool.flush(connector.client.send) == 6
            eventually(lambda: len(owner.get(prefix + "/command").json()) == 2)
            assert connector.tick() == 1
            assert owner.get(prefix + "/rollout").json()[0]["state"] == "rollback_verified"
            reply = gateway.post(
                "/agent/v1/tasks",
                headers={"Authorization": "Bearer owned-gateway-key"},
                json={
                    "id": "served-stable",
                    "session": "new-after-rollback",
                    "input": "Deterministic engineering fixture",
                },
            )
            assert reply.status_code == 200 and reply.json()["release"] == stable
            assert served == [candidate, stable]
            gateway.close()
            eventually(
                lambda: any(
                    n["state"] == "retry" for n in owner.get(prefix + "/notification").json()
                )
            )
            worker.kill()
            worker.wait(timeout=10)
            launch("releasefence_api.worker")
            eventually(
                lambda: any(
                    n["state"] == "delivered" for n in owner.get(prefix + "/notification").json()
                )
            )
            assert len(received) == 2 and received[0][0] == received[1][0]
            metrics = owner.get(
                prefix + "/views/metrics?application=support&environment=staging"
            ).json()
            assert metrics[candidate]["known_cost"] == "0.02" and metrics[candidate]["failed"] == 1
            api.terminate()
            api.wait(timeout=10)
            launch("uvicorn", api_args)
            eventually(lambda: owner.get("/health/ready").status_code == 200)
            assert owner.get(prefix + "/rollout").json()[0]["state"] == "rollback_verified"
            assert connector.tick() == 0
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=5)
        receiver.shutdown()
        receiver.server_close()
        thread.join(timeout=3)
