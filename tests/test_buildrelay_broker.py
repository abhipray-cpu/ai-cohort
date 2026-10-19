"""Opt-in actual NATS process test. No GitHub writes or model calls."""

import asyncio
import hashlib
import hmac
import json
import os
import shutil
import socket
import subprocess
import threading

import pytest
from buildrelay_api.api import create_app
from buildrelay_api.queue import listen
from buildrelay_api.workflow import Workflow
from fastapi.testclient import TestClient
from test_buildrelay_transports import payload
from test_buildrelay_workflow import GitHub, Provider, run


def test_actual_broker_webhook_queue_and_workflow(tmp_path, monkeypatch):
    binary = os.environ.get("BUILDRELAY_NATS_BINARY") or shutil.which("nats-server")
    if not binary:
        pytest.skip("actual broker binary required; set BUILDRELAY_NATS_BINARY")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url = f"nats://test-broker-password@127.0.0.1:{port}"
    monkeypatch.setenv("BUILDRELAY_NATS_URL", url)
    monkeypatch.setenv("BUILDRELAY_SHOP_SECRET", "signed-test-secret")
    app = create_app(tmp_path / "app", username="owner", password="test-password-123")
    store = app.state.store
    store.create_client("client", "Shop")
    store.create_repo(
        "repo",
        "client",
        "acme/shop",
        123,
        "BUILDRELAY_SHOP_SECRET",
        "BUILDRELAY_SHOP_TOKEN",
        "QA",
        False,
    )
    client = TestClient(app)
    raw = json.dumps(payload()).encode()
    signature = "sha256=" + hmac.new(b"signed-test-secret", raw, hashlib.sha256).hexdigest()
    assert (
        client.post(
            "/hooks/github/repo",
            content=raw,
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Delivery": "http-first",
                "X-GitHub-Event": "workflow_run",
            },
        ).status_code
        == 202
    )
    stop = threading.Event()
    broker = subprocess.Popen(
        [
            binary,
            "-js",
            "-a",
            "127.0.0.1",
            "-p",
            str(port),
            "--auth",
            "test-broker-password",
            "-sd",
            str(tmp_path / "broker"),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    async def exercise():
        import nats
        from nats.js.api import StorageType, StreamConfig

        nc = None
        for _ in range(40):
            try:
                nc = await nats.connect(url, connect_timeout=0.3, max_reconnect_attempts=0)
                break
            except (OSError, nats.errors.Error):
                await asyncio.sleep(0.1)
        assert nc is not None, "broker did not start"
        js = nc.jetstream()
        await js.add_stream(
            config=StreamConfig(
                name="BUILDRELAY",
                subjects=["buildrelay.runs"],
                storage=StorageType.FILE,
                max_bytes=16000000,
            )
        )
        task = asyncio.create_task(listen(store, stop))
        try:
            for n in range(50):
                body = {
                    "schema_version": 1,
                    "repo_id": "repo",
                    "delivery_id": f"queue-{n}",
                    "event": run().model_dump(),
                }
                await js.publish("buildrelay.runs", json.dumps(body).encode())
            await js.publish("buildrelay.runs", b"invalid json")
            for _ in range(100):
                if any(a["action"] == "queue_rejected" for a in store.audit()):
                    break
                await asyncio.sleep(0.05)
            assert len(store.events()) == 1
            assert any(a["action"] == "queue_rejected" for a in store.audit())
            info = await js.consumer_info("BUILDRELAY", "buildrelay-inbox-v1")
            assert info.num_ack_pending == 0
            assert info.num_pending == 0
        finally:
            stop.set()
            await task
            await nc.close()

    try:
        asyncio.run(exercise())
        gh, provider = GitHub(), Provider()
        assert Workflow(store, gh, provider).once()
        assert store.events()[0]["state"] == "done"
        assert len(store.incidents()) == 1 and provider.calls == 1
    finally:
        broker.terminate()
        broker.wait(timeout=5)
