"""Actual loopback API + independent worker acceptance on artificial feed fixtures."""

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--live", action="store_true", help="Real installed-model fixture call; consumes usage"
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("preserve previous evidence; output already exists")
    checks = []
    with tempfile.TemporaryDirectory(prefix="catalogbridge-http-") as temporary:
        root = Path(temporary)
        password = secrets.token_urlsafe(24)
        env = os.environ.copy() | {
            "CATALOGBRIDGE_DATA_DIR": str(root / "product"),
            "CATALOGBRIDGE_USERNAME": "owner",
            "CATALOGBRIDGE_PASSWORD": password,
        }
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        processes = []
        logs = (root / "process.log").open("w")
        try:
            for command in (
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "catalogbridge_api.api:app_from_env",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                [sys.executable, "-m", "catalogbridge_api.worker"],
            ):
                processes.append(subprocess.Popen(command, env=env, stdout=logs, stderr=logs))
            with httpx.Client(base_url=base, timeout=5) as client:
                deadline = time.monotonic() + 15
                while True:
                    try:
                        if client.get("/health/ready").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    if time.monotonic() > deadline:
                        raise RuntimeError("API did not start; inspect startup configuration")
                    time.sleep(0.1)
                assert client.get("/api/batches").status_code == 401
                checks.append("unauthenticated denial")
                login = client.post(
                    "/api/session", json={"username": "owner", "password": password}
                )
                login.raise_for_status()
                client.headers["X-CSRF-Token"] = login.json()["csrf"]
                feed_ids = []
                for kind, body in [
                    ("master", "id,title,brand\nm,Crucial 8GB SODIMM,Crucial\n"),
                    ("supplier", "id,title,brand\ns,Crucial 8GB SODIMM,Crucial\n"),
                ]:
                    response = client.post("/api/feeds", params={"kind": kind}, content=body)
                    response.raise_for_status()
                    feed_ids.append(response.json()["id"])
                checks.append("actual CSV imports")
                b = client.post(
                    "/api/batches",
                    json={
                        "master_id": feed_ids[0],
                        "supplier_id": feed_ids[1],
                        "egress": args.live,
                    },
                )
                b.raise_for_status()
                batch_id = b.json()["id"]
                client.post(f"/api/batches/{batch_id}/start").raise_for_status()
                deadline = time.monotonic() + (110 if args.live else 10)
                while True:
                    rows = client.get(f"/api/batches/{batch_id}/tasks").json()
                    if rows[0]["state"] == "needs_review":
                        break
                    if time.monotonic() > deadline:
                        raise RuntimeError("independent worker did not checkpoint")
                    time.sleep(0.1)
                task = rows[0]
                checks.append("independent worker durable checkpoint")
                assert (
                    client.post(f"/api/batches/{batch_id}/exports").json()["manifest"]["included"]
                    == 0
                )
                checks.append("unreviewed export excluded")
                reviewed = client.post(
                    f"/api/tasks/{task['id']}/review",
                    json={
                        "expected_revision": task["revision"],
                        "action": "correct",
                        "candidate_id": "m",
                        "reason": "Checked both fixture source records",
                    },
                )
                reviewed.raise_for_status()
                assert (
                    client.post(
                        f"/api/tasks/{task['id']}/review",
                        json={
                            "expected_revision": task["revision"],
                            "action": "reject",
                            "reason": "stale fixture form",
                        },
                    ).status_code
                    == 409
                )
                checks.append("stale review rejected")
                out = client.post(f"/api/batches/{batch_id}/exports").json()
                assert out["manifest"]["included"] == 1 and "s,m,owner" in out["csv"]
                checks.append("reviewed mapping export")
                metrics = client.get(f"/api/batches/{batch_id}/analytics").json()
                assert metrics["estimated_microunits"] is None
                if args.live:
                    assert (
                        metrics["attempts"] >= 1
                        and metrics["tokens"] > 0
                        and metrics["unknown_attempts"] == 0
                    )
                    checks.append("actual installed-model usage settled through independent worker")
                else:
                    assert metrics["attempts"] == 0
                    checks.append("manual-only usage and unknown cost are honest")
                audit = client.get(f"/api/batches/{batch_id}/audit").json()
                assert {"review", "export", "checkpoint"} <= {e["kind"] for e in audit}
                checks.append("workflow audit lineage")
                assert client.get("/").status_code == 200
                checks.append("built frontend served over actual HTTP (not browser QA)")
        finally:
            for process in reversed(processes):
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            logs.close()
    report = {
        "data": "artificial fixtures; not real-world semantic validation",
        "checks": checks,
        "passed": len(checks),
        "actual_processes": 2,
        "browser_acceptance": False,
        "production_accepted": False,
        "live_model_calls": metrics["attempts"],
        "measured_tokens": metrics["tokens"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
