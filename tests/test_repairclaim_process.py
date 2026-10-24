"""Opt-in local process acceptance. Authored fixture data only; no live sources/models."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from repairclaim_api.parser import RestrictedParser
from repairclaim_api.store import Store
from test_repairclaim_workflow import make_pdf, register

pytestmark = pytest.mark.skipif(
    os.environ.get("REPAIRCLAIM_PROCESS_TESTS") != "1",
    reason="Opt-in isolated local process checks; not real-world data validation",
)
ROOT = Path(__file__).resolve().parents[1]


def test_production_restricted_parser_extracts_redacts_and_previews():
    parser = RestrictedParser()
    raw = make_pdf("Repair mileage: 90000 mi\nPRIVATE FIXTURE ADDRESS")
    parsed = parser.run("parse", raw, "fixture.pdf")
    assert parsed["proposals"][0]["value"] == "90000"
    clean = parser.run("sanitize", raw, "fixture.pdf", redactions=["PRIVATE FIXTURE ADDRESS"])
    assert parser.run("preview", clean, "fixture.pdf", page=1).startswith(b"\x89PNG")
    reparsed = parser.run("parse", clean, "fixture.pdf")
    assert "PRIVATE FIXTURE ADDRESS" not in str(reparsed)


def test_native_parser_sandbox_denies_other_private_files_and_network(tmp_path):
    if sys.platform != "darwin":
        pytest.skip("Native macOS sandbox check; container policy is separate")
    import tempfile

    sentinel = tmp_path / "private-sentinel.txt"
    sentinel.write_text("authored fixture, not a real secret")
    with tempfile.TemporaryDirectory(prefix="rc-policy-") as directory:
        command = RestrictedParser().command(directory)[:3]
        script = f"""import socket
try:
 open({str(sentinel)!r}).read()
 raise RuntimeError('file unexpectedly readable')
except PermissionError: pass
try:
 socket.create_connection(('127.0.0.1',9),timeout=1)
 raise RuntimeError('network unexpectedly allowed')
except PermissionError: pass
print('policy-denied')"""
        result = subprocess.run(
            [*command, sys.executable, "-I", "-c", script],
            capture_output=True,
            text=True,
            cwd=directory,
            timeout=5,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "policy-denied"


def test_actual_api_worker_and_static_web_roundtrip(tmp_path):
    store = Store(tmp_path / "state" / "repairclaim.sqlite3")
    store.provision_owner("fixture-owner", "fixture-process-password")
    register(store)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "REPAIRCLAIM_DATA_DIR": str(store.path.parent),
        "REPAIRCLAIM_PUBLIC_ORIGIN": origin,
        "REPAIRCLAIM_ENABLE_CODEX": "0",
        "REPAIRCLAIM_ENABLE_SOURCE_CHECKS": "0",
        "PYTHONPATH": str(ROOT / "apps" / "repairclaim-api" / "src")
        + os.pathsep
        + os.environ.get("PYTHONPATH", ""),
    }
    processes = []
    with (
        (tmp_path / "process.log").open("wb") as log,
        httpx.Client(base_url=origin, headers={"origin": origin}, timeout=10) as client,
    ):
        try:
            for arguments in [
                [
                    "-m",
                    "uvicorn",
                    "repairclaim_api.api:app_from_env",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--no-access-log",
                ],
                ["-m", "repairclaim_api.worker"],
            ]:
                processes.append(
                    subprocess.Popen(
                        [sys.executable, *arguments], env=env, cwd=ROOT, stdout=log, stderr=log
                    )
                )
            for _ in range(100):
                try:
                    if client.get("/health/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert all(p.poll() is None for p in processes), (
                    tmp_path / "process.log"
                ).read_text()
                time.sleep(0.1)
            assert client.get("/health/ready").status_code == 200
            assert "<title>RepairClaim" in client.get("/").text
            base = "/api/repairclaim/v1"
            login = client.post(
                base + "/sessions",
                json={"username": "fixture-owner", "password": "fixture-process-password"},
            ).json()
            client.headers["x-csrf-token"] = login["csrf_token"]
            vehicle = client.post(
                base + "/vehicles",
                json={
                    "make": "Honda",
                    "model": "Fixture",
                    "model_year": 2018,
                    "jurisdiction": "US",
                },
            ).json()
            case = client.post(
                base + "/cases",
                json={"vehicle_id": vehicle["id"], "title": "Authored fixture case"},
            ).json()
            doc = client.post(
                base
                + f"/cases/{case['id']}/documents?filename=fixture.pdf&kind=invoice&revision=1",
                content=make_pdf("Repair mileage: 90000 mi"),
                headers={"content-type": "application/octet-stream"},
            ).json()
            for _ in range(100):
                result = client.get(base + f"/documents/{doc['id']}").json()
                if result["status"] != "queued":
                    break
                time.sleep(0.1)
            assert result["status"] == "ready", result
            assert client.get(base + f"/documents/{doc['id']}/preview").content.startswith(
                b"\x89PNG"
            )
            assert (
                client.post(
                    base + f"/documents/{doc['id']}/confirm",
                    json={"selected": [0], "expected_revision": 2},
                ).status_code
                == 200
            )
            job = client.post(
                base + f"/cases/{case['id']}/investigations",
                json={"key": "synthetic", "expected_revision": 3},
            ).json()
            for _ in range(100):
                result = client.get(base + f"/jobs/{job['id']}").json()
                if result["status"] not in {"queued", "running"}:
                    break
                time.sleep(0.1)
            assert result["result"]["search"]["search_status"] == "complete"
            assert result["result"]["search"]["state"] == "potentially_applicable"
            assert result["attempts"] == []
            packet = client.post(
                base + f"/cases/{case['id']}/packets",
                json={
                    "job_id": job["id"],
                    "recipient": "Authored fixture dealer",
                    "key": "fixture-packet",
                    "attachments": [
                        {"document_id": doc["id"], "mode": "sanitized", "redactions": []}
                    ],
                },
            ).json()
            assert client.post(base + f"/packets/{packet['id']}/render", json={}).status_code == 202
            for _ in range(100):
                rendered = client.get(base + f"/packets/{packet['id']}").json()
                if rendered["status"] == "rendered":
                    break
                time.sleep(0.1)
            assert rendered["status"] == "rendered", rendered
            assert client.get(base + f"/packets/{packet['id']}/preview").content.startswith(
                b"\x89PNG"
            )
            assert (
                client.post(base + f"/packets/{packet['id']}/download", json={}).status_code == 409
            )
            assert (
                client.post(
                    base + f"/packets/{packet['id']}/approve",
                    json={"fingerprint": rendered["fingerprint"]},
                ).status_code
                == 200
            )
            assert client.post(
                base + f"/packets/{packet['id']}/download", json={}
            ).content.startswith(b"PK")
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
