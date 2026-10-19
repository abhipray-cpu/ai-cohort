"""Real TCP API + worker smoke; opt-in because loopback ports may be restricted."""

import os
import secrets
import socket
import subprocess
import sys
import time

import httpx
import pytest


def test_real_http_api_worker_and_built_assets(tmp_path):
    if os.environ.get("BUILDRELAY_PROCESS_TEST") != "1":
        pytest.skip("set BUILDRELAY_PROCESS_TEST=1 for actual loopback process smoke")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    password = secrets.token_urlsafe(24)
    env = dict(
        os.environ,
        BUILDRELAY_DATA_DIR=str(tmp_path),
        BUILDRELAY_USERNAME="owner",
        BUILDRELAY_PASSWORD=password,
        BUILDRELAY_NATS_URL="",
        BUILDRELAY_SECURE_COOKIES="false",
    )
    processes = []
    try:
        for cmd in (
            [
                sys.executable,
                "-m",
                "uvicorn",
                "buildrelay_api.api:app_from_env",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            [sys.executable, "-m", "buildrelay_api.worker"],
        ):
            processes.append(
                subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            )
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=3) as c:
            for _ in range(80):
                assert all(p.poll() is None for p in processes), "service exited during startup"
                try:
                    if c.get("/health/ready").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            else:
                pytest.fail("service failed readiness")
            html = c.get("/")
            assert html.status_code == 200 and "BuildRelay" in html.text
            assert "script-src 'self'" in html.headers["content-security-policy"]
            assert c.get("/api/overview").status_code == 401
            login = c.post("/api/session", json={"username": "owner", "password": password})
            assert login.status_code == 200
            assert c.get("/api/overview").json()["events"] == []
    finally:
        for p in reversed(processes):
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=10)
