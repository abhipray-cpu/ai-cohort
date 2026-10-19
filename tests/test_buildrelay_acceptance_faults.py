"""Actual child-process crashes and broker redelivery; proposer/effects are explicit stand-ins."""

import asyncio
import importlib.util
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest
from buildrelay_api.queue import consume_message
from buildrelay_api.store import Store
from buildrelay_api.workflow import Failure, Workflow
from contracts.buildrelay import RunEvent

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "buildrelay_fault_worker", ROOT / "scripts/buildrelay_fault_worker.py"
)
SUPPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUPPORT)


@pytest.fixture
def real_case(tmp_path):
    capture = ROOT / os.environ.get(
        "BUILDRELAY_GITHUB_CAPTURE", "var/validation/buildrelay-github-2026-10-18-v1"
    )
    if not (capture / "manifest.json").is_file():
        pytest.skip("requires verified real GitHub capture")
    manifest = json.loads((capture / "manifest.json").read_text())
    record = next(r for r in manifest["records"] if r["status"] == "evidence_captured")
    path = capture / record["id"]
    event = RunEvent.model_validate_json((path / "event.json").read_text())
    evidence = json.loads((path / "evidence.json").read_text())
    s = Store(tmp_path)
    s.create_client("client", "Real captured repository")
    s.create_repo(
        "repo",
        "client",
        event.repository,
        event.repository_id,
        "BUILDRELAY_FAULT_SECRET",
        "BUILDRELAY_FAULT_TOKEN",
        "Test operator",
        True,
    )
    return s, event, evidence, path / "evidence.json"


@pytest.mark.parametrize(
    "fault,exit_code", [("evidence", 24), ("triage", 24), ("external_accepted", 25)]
)
def test_real_process_crash_preserves_checkpoints_and_external_identity(
    real_case, fault, exit_code
):
    store, event, evidence, evidence_path = real_case
    store.accept("repo", event, "webhook", "original-source-event")
    child = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "scripts/buildrelay_fault_worker.py"),
            "--root",
            str(store.root),
            "--evidence",
            str(evidence_path),
            "--fault",
            fault,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        assert child.wait(timeout=10) == exit_code
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
    assert store.events()[0]["state"] == "processing"
    time.sleep(1.2)  # child deliberately used a one-second lease; no clock mocking
    source = SUPPORT.RecordedSourceAndEffectStandIn(evidence, store.root)
    provider = SUPPORT.ControlledProposer(evidence, store.root / "proposer-count.txt")
    assert Workflow(store, source, provider).once()
    assert store.events()[0]["state"] == "done"
    assert (store.root / "proposer-count.txt").read_text() == "1"
    assert len(store.incidents()) == 1
    with sqlite3.connect(source.path) as db:
        assert db.execute("SELECT count(*) FROM issues").fetchone()[0] == 1


def test_commit_before_ack_crash_real_broker_redelivers_without_duplicate(real_case, monkeypatch):
    binary = os.environ.get("BUILDRELAY_NATS_BINARY") or shutil.which("nats-server")
    if not binary:
        pytest.skip("requires actual NATS binary")
    store, event, _, _ = real_case
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"nats://fault-password@127.0.0.1:{port}"
    monkeypatch.setenv("BUILDRELAY_FAULT_NATS_URL", url)
    broker = subprocess.Popen(
        [
            binary,
            "-js",
            "-a",
            "127.0.0.1",
            "-p",
            str(port),
            "--auth",
            "fault-password",
            "-sd",
            str(store.root / "broker"),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    async def exercise():
        import nats
        from nats.js.api import StorageType, StreamConfig

        nc = None
        for _ in range(50):
            try:
                nc = await nats.connect(url, connect_timeout=0.3, max_reconnect_attempts=0)
                break
            except (OSError, nats.errors.Error):
                await asyncio.sleep(0.1)
        assert nc is not None
        try:
            js = nc.jetstream()
            await js.add_stream(
                config=StreamConfig(
                    name="FAULTS", subjects=["fault.runs"], storage=StorageType.FILE
                )
            )
            payload = {
                "schema_version": 1,
                "repo_id": "repo",
                "delivery_id": "same-real-event",
                "event": event.model_dump(),
            }
            await js.publish("fault.runs", json.dumps(payload).encode())
            child = await asyncio.to_thread(
                subprocess.Popen,
                [
                    sys.executable,
                    str(ROOT / "scripts/buildrelay_fault_worker.py"),
                    "--root",
                    str(store.root),
                    "--fault",
                    "queue_commit_before_ack",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                assert await asyncio.to_thread(child.wait, timeout=10) == 23
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
            assert len(store.events()) == 1
            await asyncio.sleep(1.2)
            sub = await js.pull_subscribe("fault.runs", durable="fault-inbox", stream="FAULTS")
            msg = (await sub.fetch(1, timeout=5))[0]
            assert msg.metadata.num_delivered >= 2
            await consume_message(store, msg)
            assert len(store.events()) == 1
            info = await js.consumer_info("FAULTS", "fault-inbox")
            assert info.num_ack_pending == 0
        finally:
            await nc.close()

    try:
        asyncio.run(exercise())
    finally:
        broker.terminate()
        broker.wait(timeout=5)


def test_dead_letter_replay_after_four_transient_failures_preserves_real_event(real_case):
    store, event, evidence, _ = real_case
    ident = store.accept("repo", event, "webhook", "source")
    source = SUPPORT.RecordedSourceAndEffectStandIn(evidence, store.root)
    original = source.evidence
    source.evidence = lambda *_: (_ for _ in ()).throw(Failure("upstream_503", transient=True))
    provider = SUPPORT.ControlledProposer(evidence, store.root / "proposer-count.txt")
    w = Workflow(store, source, provider)
    for _ in range(4):
        assert w.once()
        with store.write() as db:
            db.execute(
                "UPDATE events SET due=0"
            )  # accelerate schedule only; retry calculation separately tested
    assert store.events()[0]["state"] == "dead"
    assert not (store.root / "proposer-count.txt").exists()
    store.replay(ident, "fault-test-operator", reason="Injected temporary outage removed")
    source.evidence = original
    w.once()
    assert store.events()[0]["state"] == "done"
    assert RunEvent.model_validate_json(store.events()[0]["payload"]) == event
    assert (store.root / "proposer-count.txt").read_text() == "1"


def test_expired_worker_network_failure_does_not_crash_supervising_loop(real_case):
    store, event, evidence, _ = real_case
    store.accept("repo", event, "webhook", "source")
    source = SUPPORT.RecordedSourceAndEffectStandIn(evidence, store.root)

    def unavailable_after_sleep(*_):
        with store.write() as db:
            db.execute("UPDATE events SET lease_until=0 WHERE state='processing'")
        raise Failure("network_after_host_sleep", transient=True)

    source.evidence = unavailable_after_sleep
    provider = SUPPORT.ControlledProposer(evidence, store.root / "proposer-count.txt")
    assert Workflow(store, source, provider).once()
    assert (
        store.events()[0]["state"] == "processing"
    )  # expired job remains reclaimable, not written by stale token
