# ruff: noqa: F811
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from casecouncil_api.controller import Controller
from test_casecouncil_protocol import ControlledProvider
from test_casecouncil_store import CONTEXT, PASSWORD, seeded, start  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "stage",
    ["proposal:customer", "critic", "registry", "ballot:customer", "consensus", "synthesis"],
)
def test_real_child_crash_resumes_without_repeating_completed_model_work(seeded, stage):
    s, _w, c = seeded
    j = start(s, c)
    child = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tests/support_casecouncil_process.py"),
            "--root",
            str(s.root),
            "--fault",
            stage,
        ],
        capture_output=True,
        check=False,
        timeout=15,
    )
    assert child.returncode == 23, child.stderr.decode()[-500:]
    time.sleep(1.15)
    assert Controller(s, ControlledProvider()).once()
    saved = s.job("owner", j["id"])
    assert saved["state"] == "draft_ready" and saved["calls"] == 8
    assert len(saved["packet"]["ballots"]) == 3


def test_crash_after_reservation_keeps_unknown_liability_and_no_blind_replay(seeded):
    s, w, c = seeded
    j = start(s, c)
    child = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tests/support_casecouncil_process.py"),
            "--root",
            str(s.root),
            "--fault",
            "reservation",
        ],
        capture_output=True,
        check=False,
        timeout=15,
    )
    assert child.returncode == 24
    time.sleep(1.15)
    provider = ControlledProvider()
    Controller(s, provider).once()
    saved = s.job("owner", j["id"])
    assert saved["calls"] == 1 and not provider.prompts and saved["state"] == "manual_required"
    assert s.workspace("owner", w)["hold"]


def test_actual_http_service_auth_assets_and_owned_fixture_worker(tmp_path):
    if os.environ.get("CASECOUNCIL_PROCESS_TEST") != "1":
        pytest.skip("enable actual loopback process acceptance")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {
        **os.environ,
        "CASECOUNCIL_DATA_DIR": str(tmp_path),
        "CASECOUNCIL_USERNAME": "owner",
        "CASECOUNCIL_PASSWORD": PASSWORD,
    }
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "casecouncil_api.api:app_from_env",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as client:
            for _ in range(100):
                try:
                    if client.get("/health/live").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.05)
            r = client.post("/api/session", json={"username": "owner", "password": PASSWORD})
            assert r.status_code == 200
            client.headers.update(
                {"X-CSRF-Token": r.json()["csrf"], "Idempotency-Key": "http-fixture"}
            )
            w = client.post("/api/workspaces", json={"name": "HTTP authored fixture"}).json()["id"]
            from casecouncil_api.store import Store

            s = Store(tmp_path)
            s.set_policy(
                "owner",
                w,
                1,
                {
                    "name": "HTTP fixture policy",
                    "instructions": "No legal conclusions",
                    "required_documents": ["policy"],
                    "egress_enabled": True,
                },
            )
            rid = s.add_rights(
                "owner",
                w,
                {
                    "basis": "owned_test",
                    "reference": "Personally authored HTTP engineering fixture",
                    "expires": time.time() + 86400,
                    "egress": True,
                },
            )
            c = client.post("/api/cases", json={"workspace": w, "context": CONTEXT}).json()["id"]
            s.add_source(
                "owner",
                c,
                1,
                "policy.txt",
                b"Policy requires separate contractual and service consideration.",
                "policy",
                rid,
                "source",
            )
            preview = client.get(f"/api/cases/{c}/egress-preview").json()
            j = client.post(f"/api/cases/{c}/runs", json={"binding": preview["binding"]}).json()[
                "id"
            ]
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tests/support_casecouncil_process.py"),
                    "--root",
                    str(tmp_path),
                ],
                capture_output=True,
                check=False,
                timeout=15,
            )
            assert result.returncode == 0, result.stderr.decode()[-500:]
            assert client.get(f"/api/runs/{j}").json()["state"] == "draft_ready"
            assert client.get(f"/api/runs/{j}/export").json()["approved"] is False
            index = client.get("/")
            assert index.status_code == 200 and "CaseCouncil" in index.text
            assert "default-src 'self'" in index.headers["content-security-policy"]
            assert client.get("/api/me").status_code == 200
    finally:
        api.terminate()
        api.wait(timeout=10)
