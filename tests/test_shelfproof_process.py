"""Real child and opt-in loopback tests. All provider data is authored, not USDA."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from shelfproof_api.runtime import CodexProvider
from shelfproof_api.store import Store
from test_shelfproof_workflow import job, setup  # noqa: F401


@pytest.mark.parametrize("stage", ["draft:0", "judge:0", "reflect:1", "draft:1", "judge:1"])
def test_actual_worker_child_crash_reuses_completed_checkpoint(setup, stage):  # noqa: F811
    store, _, _ = setup
    task = job(setup)
    child = Path(__file__).with_name("support_shelfproof_process.py")
    result = subprocess.run(
        [sys.executable, str(child), "--root", str(store.root), "--fault", stage],
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 23, result.stderr.decode()[-400:]
    with store.db() as db:
        db.execute("UPDATE tasks SET lease_until=0 WHERE id=?", (task,))
    store.isolate_orphans("maker", "actual child terminated with code 23", store.journal_head())
    store.resume("maker", task, store.task("maker", task)["selected_hash"], f"resume:{stage}")
    result = subprocess.run(
        [sys.executable, str(child), "--root", str(store.root)],
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()[-400:]
    saved = store.task("maker", task)
    assert saved["state"] == "review_ready" and saved["calls"] == 5


def test_actual_child_reservation_crash_leaves_global_unknown_hold(setup):  # noqa: F811
    store, _, _ = setup
    task = job(setup)
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("support_shelfproof_process.py")),
            "--root",
            str(store.root),
            "--fault",
            "reservation",
        ],
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 24
    with store.db() as db:
        db.execute("UPDATE tasks SET lease_until=0 WHERE id=?", (task,))
    store.isolate_orphans("maker", "actual child terminated with code 24", store.journal_head())
    assert store.liability_hold() and store.task("maker", task)["calls"] == 1


def test_actual_child_timeout_is_killed_and_usage_remains_unknown():
    provider = CodexProvider(timeout_seconds=0.15)
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        provider._run([sys.executable, "-c", "import time;time.sleep(30)"], "")
    assert time.monotonic() - started < 5
    assert provider._exit_code is None


def test_actual_child_stream_overflow_is_bounded():
    provider = CodexProvider()
    with pytest.raises(RuntimeError, match="stream"):
        provider._run([sys.executable, "-c", "print('x'*2000000)"], "")
    assert len(provider._events.encode()) <= 1048576


def test_actual_child_cancellation_is_not_a_completed_turn():
    provider = CodexProvider()
    provider.cancel_check = lambda: True
    with pytest.raises(RuntimeError):
        provider._run([sys.executable, "-c", "import time;time.sleep(30)"], "")
    assert provider._exit_code is None


def test_actual_http_process_auth_assets_and_no_boot_inference(tmp_path):
    if os.environ.get("SHELFPROOF_PROCESS_TEST") != "1":
        pytest.skip("enable loopback process acceptance with SHELFPROOF_PROCESS_TEST=1")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "SHELFPROOF_DATA_DIR": str(tmp_path),
        "SHELFPROOF_USERNAME": "owner",
        "SHELFPROOF_PASSWORD": "owned-test-password-123",
        "SHELFPROOF_ORIGIN": origin,
        "SHELFPROOF_CODEX_COMMAND": "does-not-exist-no-boot-model",
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "shelfproof_api.api:app_from_env",
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
        with httpx.Client(base_url=origin, timeout=5) as client:
            for _ in range(100):
                try:
                    if client.get("/health/live").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.05)
            assert client.get("/health/live").status_code == 200
            assert client.get("/health/ready").status_code == 503
            login = client.post(
                "/api/session", json={"username": "owner", "password": "owned-test-password-123"}
            )
            assert login.status_code == 200
            assert client.get("/api/me").json()["actor"] == "owner"
            client.headers.update({"Origin": origin, "X-CSRF-Token": login.json()["csrf"]})
            workspace = client.post("/api/workspaces", json={"name": "Owned HTTP test"})
            assert workspace.status_code == 200
            index = client.get("/")
            assert index.status_code == 200 and "ShelfProof" in index.text
            assert "default-src 'self'" in index.headers["content-security-policy"]
            assert not (tmp_path / "usage.jsonl").exists()
            Store(tmp_path).heartbeat()
            assert client.get("/health/ready").status_code == 200
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_runtime_artifact_path_does_not_point_into_another_product():
    from shelfproof_api import api

    assert (Path(api.__file__).resolve().parents[3] / "shelfproof-web/dist/index.html").is_file()
