"""Explicit real browser/API/PG campaign. Source-bound fixture traffic, no inference."""

import base64
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from contracts.releasefence import Event
from releasefence_api.validation import load_corpus
from test_releasefence_store import configured, rf, rf_admin  # noqa: F401


def test_real_browser_operator_workflow_tenants_accessibility_and_mobile(rf, tmp_path):  # noqa: F811
    s, first, second = rf
    s.now = time.time
    stable, candidate, _, enrolled = configured(rf)
    rows, _ = load_corpus(os.environ["RELEASEFENCE_ACCEPTANCE_CORPUS"])
    for i, row in enumerate(rows[:10]):
        assert row["facts"]["source_ref"]
        s.ingest(
            s.machine(enrolled["token"]),
            [
                Event(
                    id=f"a{i}",
                    task=f"t{i}",
                    session=f"s{i}",
                    release=stable,
                    kind="accepted",
                    at=time.time(),
                ),
                Event(
                    id=f"e{i}",
                    task=f"t{i}",
                    session=f"s{i}",
                    release=stable,
                    kind="terminal",
                    at=time.time(),
                    outcome="success",
                    duration_ms=10 + i,
                    model_calls=1,
                ),
            ],
        )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    root = Path(os.environ["RELEASEFENCE_BROWSER_OUTPUT"]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    fixture = root / "fixture.json"
    fixture.write_text(
        json.dumps(
            {
                "first": first,
                "second": second,
                "stable": stable,
                "candidate": candidate,
                "enrollment": enrolled["id"],
                "passwords": {"owner": "owned-password-123", "reviewer": "review-password-123"},
            }
        )
    )
    fixture.chmod(0o600)
    env = {
        **os.environ,
        "RELEASEFENCE_DATABASE_URL": s.dsn,
        "RELEASEFENCE_SCHEMA": s.schema,
        "RELEASEFENCE_ENCRYPTION_KEY": s.test_encryption_key.decode(),
        "RELEASEFENCE_SIGNING_KEY": base64.b64encode(s.key.private_bytes_raw()).decode(),
        "RELEASEFENCE_ORIGIN": url,
        "RELEASEFENCE_USERNAME": "owner",
        "RELEASEFENCE_PASSWORD": "owned-password-123",
        "RELEASEFENCE_LAB_LOOPBACK": "1",
        "RELEASEFENCE_BROWSER_URL": url,
        "RELEASEFENCE_BROWSER_FIXTURE": str(fixture),
        "RELEASEFENCE_BROWSER_OUTPUT": str(root / "artifacts"),
        "RELEASEFENCE_BROWSER_JUNIT": str(root / "browser.xml"),
    }
    with (root / "api.log").open("wb") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "releasefence_api.api:app_from_env",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                try:
                    if httpx.get(url + "/health/live").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            result = subprocess.run(
                ["npm", "exec", "--", "playwright", "test"],
                cwd="apps/releasefence-web",
                env=env,
                timeout=360,
                check=False,
            )
            assert result.returncode == 0, f"Browser acceptance failed; see {root}"
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
