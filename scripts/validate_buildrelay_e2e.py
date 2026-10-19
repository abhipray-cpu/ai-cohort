"""Real HTTP + authenticated broker + installed-Codex replay of frozen actual GHA records.

Source records/logs are real; envelopes/redeliveries are reconstructed. No GitHub
issues are written. This is NOT an observed live GitHub webhook/Windows deployment.
"""

import argparse
import asyncio
import hashlib
import hmac
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path

import httpx
from buildrelay_api.queue import listen
from buildrelay_api.store import Store
from buildrelay_api.workflow import Failure, Workflow
from contracts.buildrelay import RunEvent
from validate_buildrelay_semantics import Recorder


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class RecordedSource:
    """Source port replay, verified byte-for-byte against the live-read capture manifest."""

    def __init__(self, capture, records):
        self.capture = capture
        self.records = {(r["repository"].lower(), r["run_id"], r["attempt"]): r for r in records}

    def evidence(self, repo, event):
        record = self.records[(event.repository.lower(), event.run_id, event.attempt)]
        if record["status"] == "source_failure":
            raise Failure(record["error"])
        return json.loads((self.capture / record["id"] / "evidence.json").read_text())


async def validate(capture, output, binary, duplicates=10000, http_duplicates=500):
    import nats
    from nats.js.api import StorageType, StreamConfig

    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((capture / "manifest.json").read_text())
    records = manifest["records"]
    events = {}
    for record in records:
        for name, artifact in record["artifacts"].items():
            if (
                hashlib.sha256((capture / record["id"] / name).read_bytes()).hexdigest()
                != artifact["sha256"]
            ):
                raise ValueError("source capture hash mismatch")
        events[record["id"]] = RunEvent.model_validate_json(
            (capture / record["id"] / "event.json").read_text()
        )
    (output / "scope.json").write_text(
        json.dumps(
            {
                "records": len(records),
                "queue_deliveries": duplicates,
                "http_redeliveries": http_duplicates,
                "source_mode": "verified replay of actual read-only GitHub capture",
                "ai_mode": "installed Codex",
                "external_issue_writes": False,
                "expected_source_unavailable_ids": [
                    r["id"] for r in records if r["status"] == "source_failure"
                ],
            },
            indent=2,
        )
    )
    root = output / "service"
    store = Store(root)
    password, hook_secret, broker_secret = [secrets.token_urlsafe(24) for _ in range(3)]
    for event in events.values():
        repo_id = str(event.repository_id)
        try:
            store.repo(repo_id)
        except KeyError:
            store.create_client(repo_id, event.repository)
            store.create_repo(
                repo_id,
                repo_id,
                event.repository,
                event.repository_id,
                "BUILDRELAY_E2E_SECRET",
                "BUILDRELAY_E2E_TOKEN",
                "Acceptance engineering",
                False,
            )
    store.beat("workflow", "validation harness")
    broker_port, api_port = free_port(), free_port()
    url = f"nats://{broker_secret}@127.0.0.1:{broker_port}"
    os.environ.update(
        BUILDRELAY_NATS_URL=url,
        BUILDRELAY_NATS_STREAM="BUILDRELAY",
        BUILDRELAY_NATS_SUBJECT="buildrelay.runs",
    )
    os.environ.pop("BUILDRELAY_NATS_CREDS", None)
    env = dict(
        os.environ,
        BUILDRELAY_DATA_DIR=str(root),
        BUILDRELAY_USERNAME="validation-owner",
        BUILDRELAY_PASSWORD=password,
        BUILDRELAY_E2E_SECRET=hook_secret,
        BUILDRELAY_SECURE_COOKIES="false",
    )
    stop = threading.Event()
    processes, logs = [], []
    client, nc, queue_task = None, None, None
    started = time.monotonic()
    results = {
        "real_records": len(records),
        "source_failures": [r["id"] for r in records if r["status"] == "source_failure"],
        "workflow_results": [],
        "full_product_accepted": False,
    }
    try:
        commands = [
            [
                binary,
                "-js",
                "-a",
                "127.0.0.1",
                "-p",
                str(broker_port),
                "--auth",
                broker_secret,
                "-sd",
                str(output / "broker"),
            ],
            [
                sys.executable,
                "-m",
                "uvicorn",
                "buildrelay_api.api:app_from_env",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
            ],
        ]
        for index, command in enumerate(commands):
            log = (output / f"process-{index}.log").open("wb")
            logs.append(log)
            processes.append(
                await asyncio.to_thread(
                    subprocess.Popen, command, env=env, stdout=log, stderr=subprocess.STDOUT
                )
            )
        for _ in range(60):
            try:
                nc = await nats.connect(url, connect_timeout=0.3, max_reconnect_attempts=0)
                break
            except (OSError, nats.errors.Error):
                await asyncio.sleep(0.1)
        if nc is None:
            raise RuntimeError("broker failed startup")
        js = nc.jetstream()
        await js.add_stream(
            config=StreamConfig(
                name="BUILDRELAY",
                subjects=["buildrelay.runs"],
                storage=StorageType.FILE,
                max_bytes=64000000,
            )
        )
        queue_task = asyncio.create_task(listen(store, stop))
        client = httpx.Client(base_url=f"http://127.0.0.1:{api_port}", timeout=30)
        for _ in range(100):
            try:
                if client.get("/health/ready").status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("API/queue failed readiness")
        auth = client.post(
            "/api/session", json={"username": "validation-owner", "password": password}
        )
        auth.raise_for_status()
        client.headers["X-CSRF-Token"] = auth.json()["csrf"]
        values = list(events.values())

        def hook(event, delivery):
            payload = {
                "action": "completed",
                "repository": {"id": event.repository_id, "full_name": event.repository},
                "workflow_run": {
                    "id": event.run_id,
                    "run_attempt": event.attempt,
                    "status": "completed",
                    "conclusion": event.conclusion,
                    "name": event.workflow,
                    "head_branch": event.branch,
                    "head_sha": event.sha,
                    "html_url": event.source_url,
                },
            }
            raw = json.dumps(payload).encode()
            signature = "sha256=" + hmac.new(hook_secret.encode(), raw, hashlib.sha256).hexdigest()
            response = client.post(
                f"/hooks/github/{event.repository_id}",
                content=raw,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Delivery": delivery,
                    "X-GitHub-Event": "workflow_run",
                },
            )
            if response.status_code != 202:
                raise RuntimeError(f"webhook rejection {response.status_code}")

        for i, event in enumerate(values):
            await asyncio.to_thread(hook, event, f"initial-{i}")
        for i in range(duplicates):
            event = values[i % len(values)]
            body = {
                "schema_version": 1,
                "repo_id": str(event.repository_id),
                "delivery_id": f"delivery-{i}",
                "event": event.model_dump(),
            }
            await js.publish("buildrelay.runs", json.dumps(body).encode())
        for i in range(25):
            await js.publish("buildrelay.runs", f"invalid-envelope-{i}".encode())
        for i in range(http_duplicates):
            await asyncio.to_thread(hook, values[i % len(values)], f"repeat-{i}")
        for _ in range(300):
            info = await js.consumer_info("BUILDRELAY", "buildrelay-inbox-v1")
            if info.num_pending == 0 and info.num_ack_pending == 0:
                break
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("queue failed to drain")
        results["transport"] = {
            "http_requests": len(values) + http_duplicates,
            "queue_envelopes": duplicates,
            "poison_envelopes": 25,
            "unique_events": len(store.events()),
            "pending_acks": info.num_ack_pending,
            "backlog": info.num_pending,
            "passed": len(store.events()) == len(records),
        }
        (output / "progress.json").write_text(json.dumps(results, indent=2))
        print(json.dumps({"transport": results["transport"]}), flush=True)

        source = RecordedSource(capture, records)
        for dispatch in range(len(records)):
            with store.connect() as db:
                row = db.execute(
                    "SELECT * FROM events WHERE state='pending' ORDER BY created LIMIT 1"
                ).fetchone()
            if not row:
                break
            case = output / "calls" / row["id"]
            case.mkdir(parents=True)
            provider = Recorder(case)
            workflow = Workflow(store, source, provider)
            await asyncio.to_thread(workflow.once)
            with store.connect() as db:
                saved = dict(db.execute("SELECT * FROM events WHERE id=?", (row["id"],)).fetchone())
            result = {
                "event_id": row["id"],
                "source_event": json.loads(row["payload"]),
                "state": saved["state"],
                "error": saved["error"],
                "calls": provider.calls,
                "receipts": provider.receipts,
                "checkpoint": json.loads(saved["checkpoint"]),
            }
            results["workflow_results"].append(result)
            (output / "progress.json").write_text(json.dumps(results, indent=2))
            print(
                json.dumps({k: result[k] for k in ("event_id", "state", "error", "calls")}),
                flush=True,
            )
            if any(
                r.get("exit_code", 0) != 0 or r.get("status") != "returned"
                for r in provider.receipts
            ):
                results["stopped_on_runtime_error"] = True
                break
        overview = client.get("/api/overview")
        overview.raise_for_status()
        snapshot = overview.json()
        exports = []
        for incident in snapshot["incidents"]:
            export = client.get(f"/api/incidents/{incident['id']}/export")
            exports.append(
                export.status_code == 200 and export.json()["client_update_approved"] is False
            )
        results["exports"] = {"count": len(exports), "all_draft_labelled": all(exports)}
        first, second = (
            values[0],
            next(e for e in values if e.repository_id != values[0].repository_id),
        )
        response = client.post(
            "/api/users",
            json={
                "username": "scoped-viewer",
                "password": password,
                "role": "viewer",
                "clients": [str(first.repository_id)],
            },
        )
        response.raise_for_status()
        with httpx.Client(base_url=client.base_url) as viewer:
            viewer.post(
                "/api/session", json={"username": "scoped-viewer", "password": password}
            ).raise_for_status()
            visible = viewer.get("/api/overview").json()
            denied = next(
                (i for i in snapshot["incidents"] if i["repo_id"] == str(second.repository_id)),
                None,
            )
            results["isolation"] = {
                "only_granted_repos": all(
                    r["client_id"] == str(first.repository_id) for r in visible["repos"]
                ),
                "other_incident_export_status": viewer.get(
                    f"/api/incidents/{denied['id']}/export"
                ).status_code
                if denied
                else None,
            }
        results["states"] = dict(Counter(e["state"] for e in store.events()))
        results["incidents"] = len(snapshot["incidents"])
        results["calls"] = sum(r["calls"] for r in results["workflow_results"])
        results["nonfallback_analyses"] = sum(
            "triage" in r["checkpoint"] and not r["checkpoint"]["triage"].get("fallback_reason")
            for r in results["workflow_results"]
        )
        results["scope"] = (
            "Actual TCP/JetStream/Codex, frozen real GHA source replay. Not native GitHub deliveries or live issue writes."
        )
    finally:
        results["elapsed_seconds"] = time.monotonic() - started
        (output / "report.json").write_text(json.dumps(results, indent=2) + "\n")
        stop.set()
        if queue_task:
            await asyncio.wait_for(queue_task, timeout=5)
        if nc:
            await nc.close()
        if client:
            client.close()
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
        for log in logs:
            log.close()
    print(
        json.dumps({k: v for k, v in results.items() if k != "workflow_results"}, indent=2),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--nats-binary", required=True)
    p.add_argument("--queue-deliveries", type=int, default=10000, choices=range(100, 10001))
    p.add_argument("--http-redeliveries", type=int, default=500, choices=range(1, 1001))
    p.add_argument("--live", action="store_true")
    a = p.parse_args()
    if not a.live:
        p.error("--live required; consumes installed Codex usage; never writes GitHub issues")
    asyncio.run(
        validate(
            Path(a.capture), Path(a.output), a.nats_binary, a.queue_deliveries, a.http_redeliveries
        )
    )
