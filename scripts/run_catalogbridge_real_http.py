"""Real WDC feeds through actual API/worker, retrieval, review/export and bounded live rows."""

import argparse
import csv
import io
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx
from run_catalogbridge_real_models import fingerprint, snapshot_runtime


def run(cohort, output, live_rows, stress=False, instruction_profile="legacy", repeat_drafts=False):
    if output.exists():
        raise ValueError("preserve previous evidence")
    output.mkdir(parents=True)
    gallery = json.loads((cohort / "gallery.json").read_text())
    queries = json.loads((cohort / "queries.json").read_text())
    gold = json.loads((cohort / "retrieval-gold.json").read_text())
    gallery_by_cluster = defaultdict(list)
    for row in gallery:
        gallery_by_cluster[gold["gallery"][row["id"]]].append(row["id"])
    source_hashes = {
        p.name: __import__("hashlib").sha256(p.read_bytes()).hexdigest()
        for p in cohort.glob("*.json")
    }
    frozen = {
        "started_at": datetime.now(UTC).isoformat(),
        "code": fingerprint(),
        "inputs": source_hashes,
        "queries": len(queries),
        "gallery": len(gallery),
        "maximum_live_rows": live_rows,
        "instruction_profile": instruction_profile,
        "repeat_drafts": repeat_drafts,
        "review_oracle": "automated benchmark-derived workflow fixtures, NOT actual human review",
    }
    (output / "frozen.json").write_text(json.dumps(frozen, indent=2))
    snapshot_runtime(output / "runtime-source", frozen["code"])
    password = secrets.token_urlsafe(24)
    env = os.environ.copy() | {
        "CATALOGBRIDGE_DATA_DIR": str((output / "product").resolve()),
        "CATALOGBRIDGE_USAGE_JOURNAL_DIR": str((output / "usage-journal").resolve()),
        "CATALOGBRIDGE_USERNAME": "operator",
        "CATALOGBRIDGE_PASSWORD": password,
    }
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    processes = []
    log = (output / "process.log").open("w")
    checks = []
    live_results = []
    stress_report = None
    repeat_results = []

    def spawn(role):
        command = (
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
            ]
            if role == "api"
            else [sys.executable, "-m", "catalogbridge_api.worker"]
        )
        child = subprocess.Popen(command, env=env, stdout=log, stderr=log)
        processes.append(child)
        return child

    def wait_batch(client, batch_id, seconds):
        deadline = time.monotonic() + seconds
        last = -1
        while True:
            b = client.get("/api/batches/" + batch_id)
            b.raise_for_status()
            metrics = client.get("/api/batches/" + batch_id + "/analytics").json()
            pending = sum(metrics["states"].get(s, 0) for s in ("queued", "running"))
            completed = metrics["rows"] - pending
            if completed // 100 != last:
                print(
                    json.dumps(
                        {
                            "batch": batch_id,
                            "completed": completed,
                            "pending": pending,
                            "state": b.json()["state"],
                        }
                    ),
                    flush=True,
                )
                last = completed // 100
            if pending == 0 or b.json()["state"] == "partial":
                return b.json(), metrics
            if time.monotonic() > deadline:
                raise TimeoutError("actual worker batch did not finish within recorded deadline")
            time.sleep(0.5)

    def fetch_tasks(client, batch_id):
        rows = []
        for offset in range(0, 25000, 100):
            response = client.get(
                f"/api/batches/{batch_id}/tasks", params={"offset": offset, "limit": 100}
            )
            response.raise_for_status()
            page = response.json()
            rows.extend(page)
            if len(page) < 100:
                break
        return rows

    try:
        spawn("api")
        worker = spawn("worker")
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=40) as client:
            deadline = time.monotonic() + 20
            while True:
                try:
                    if client.get("/health/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                if time.monotonic() > deadline:
                    raise TimeoutError("startup")
                time.sleep(0.1)
            assert client.get("/api/batches").status_code == 401
            checks.append("unauthenticated denied")
            response = client.post(
                "/api/session", json={"username": "operator", "password": password}
            )
            response.raise_for_status()
            client.headers["X-CSRF-Token"] = response.json()["csrf"]

            def upload(kind, rows):
                response = client.post(
                    "/api/feeds", params={"kind": kind, "format": "json"}, content=json.dumps(rows)
                )
                response.raise_for_status()
                assert response.json()["rows"] == len(rows)
                return response.json()["id"]

            master = upload("master", gallery)
            supplier = upload("supplier", queries)
            checks.append("all real gallery/query rows imported without hidden gold fields")
            b = client.post(
                "/api/batches",
                json={
                    "master_id": master,
                    "supplier_id": supplier,
                    "egress": False,
                    "instruction_profile": instruction_profile,
                },
            )
            b.raise_for_status()
            bid = b.json()["id"]
            client.post(f"/api/batches/{bid}/start").raise_for_status()
            final, metrics = wait_batch(client, bid, 1200)
            tasks = fetch_tasks(client, bid)
            assert len(tasks) == len(queries) and final["state"] == "review_ready"
            assert metrics["attempts"] == 0
            checks.append(
                "actual independent worker completes all real query retrieval/manual checkpoints"
            )
            (output / "tasks-before-review.json").write_text(json.dumps(tasks))
            hits, positives, negatives = 0, 0, 0
            misses = []
            for task in tasks:
                truth = gold["queries"][task["source"]["id"]]
                positive = truth in gallery_by_cluster
                if positive:
                    positives += 1
                    found = any(
                        gold["gallery"][r["id"]] == truth
                        for r in task["result"].get("candidates", [])
                    )
                    hits += found
                    if not found:
                        misses.append(task["source"]["id"])
                else:
                    negatives += 1
            retrieval = {
                "positive_queries": positives,
                "no_match_queries": negatives,
                "hits_at_10": hits,
                "recall_at_10": hits / positives if positives else None,
                "missed_query_ids": misses,
                "passed_95_percent_target": bool(positives and hits / positives >= 0.95),
            }
            # Restart at durable review checkpoint, not a mocked in-flight crash.
            worker.terminate()
            worker.wait(timeout=10)
            worker = spawn("worker")
            assert fetch_tasks(client, bid) == tasks
            checks.append("actual worker restart preserves complete review checkpoints")
            assert client.post(f"/api/batches/{bid}/exports").json()["manifest"]["included"] == 0
            checks.append("unreviewed natural-data export empty")
            reviewer_password = secrets.token_urlsafe(24)
            client.post(
                "/api/users",
                json={"username": "reviewer", "password": reviewer_password, "role": "reviewer"},
            ).raise_for_status()
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=40) as reviewer:
                response = reviewer.post(
                    "/api/session", json={"username": "reviewer", "password": reviewer_password}
                )
                response.raise_for_status()
                reviewer.headers["X-CSRF-Token"] = response.json()["csrf"]
                reviewed = accepted = rejected = stale_checks = 0
                for task in tasks:
                    truth = gold["queries"][task["source"]["id"]]
                    positive = truth in gallery_by_cluster
                    if positive and accepted >= 200 or not positive and rejected >= 200:
                        continue
                    action = "correct" if positive else "reject"
                    target = gallery_by_cluster[truth][0] if positive else None
                    payload = {
                        "expected_revision": task["revision"],
                        "action": action,
                        "candidate_id": target,
                        "reason": "Automated benchmark-derived workflow fixture, not independent human review",
                    }
                    response = reviewer.post(f"/api/tasks/{task['id']}/review", json=payload)
                    response.raise_for_status()
                    if reviewed % 10 == 0:
                        assert (
                            reviewer.post(
                                f"/api/tasks/{task['id']}/review", json=payload
                            ).status_code
                            == 409
                        )
                        stale_checks += 1
                    reviewed += 1
                    accepted += positive
                    rejected += not positive
                forbidden = reviewer.post(
                    f"/api/batches/{bid}/budget-increases", json={"tokens": 1}
                )
                assert forbidden.status_code == 403
                checks.append("reviewer cannot increase budget")
            exported = client.post(f"/api/batches/{bid}/exports").json()
            mappings = list(csv.DictReader(io.StringIO(exported["csv"])))
            assert len(mappings) == accepted and exported["manifest"]["total"] == len(queries)
            for row in mappings:
                assert gold["queries"][row["supplier_id"]] == gold["gallery"][row["master_id"]]
            checks.append("reviewed mappings and same-snapshot coverage match fixture oracle")
            (output / "export.json").write_text(json.dumps(exported))
            if stress:
                current = fetch_tasks(client, bid)[0]
                target = gallery_by_cluster[gold["queries"][current["source"]["id"]]][0]

                def writer():
                    for revision in range(current["revision"], current["revision"] + 100):
                        response = client.post(
                            f"/api/tasks/{current['id']}/review",
                            json={
                                "expected_revision": revision,
                                "action": "correct",
                                "candidate_id": target,
                                "reason": "Concurrent real-source workflow fixture, not a human judgment",
                            },
                        )
                        response.raise_for_status()
                    return 100

                def reader(index):
                    for _ in range(50):
                        response = client.get(f"/api/batches/{bid}/analytics")
                        response.raise_for_status()
                        summary = response.json()
                        assert (
                            summary["rows"] == len(queries)
                            and summary["attempts"] == 0
                            and summary["journal_consistent"]
                        )
                        response = client.get(f"/api/batches/{bid}/audit")
                        response.raise_for_status()
                    return 50

                with ThreadPoolExecutor(max_workers=7) as pool:
                    writes = pool.submit(writer)
                    reads = sum(pool.map(reader, range(6)))
                    updates = writes.result()
                from catalogbridge_api.auth import add_user
                from catalogbridge_api.backup import backup, restore
                from catalogbridge_api.store import Store

                active_store = Store(output / "product", output / "usage-journal")
                other_password = secrets.token_urlsafe(24)
                add_user(active_store, "other-workspace", other_password, "other-space", "owner")
                with httpx.Client(base_url=f"http://127.0.0.1:{port}") as other:
                    response = other.post(
                        "/api/session",
                        json={"username": "other-workspace", "password": other_password},
                    )
                    response.raise_for_status()
                    denied = 0
                    for path in [
                        f"/api/batches/{bid}",
                        f"/api/batches/{bid}/tasks",
                        f"/api/batches/{bid}/analytics",
                        f"/api/batches/{bid}/audit",
                        f"/api/feeds/{master}",
                    ]:
                        assert other.get(path).status_code == 404
                        denied += 1
                backup(active_store, output / "snapshot")
                restored = restore(
                    output / "snapshot", output / "restored", output / "usage-journal"
                )
                restored_store = Store(restored, output / "usage-journal")
                assert restored_store.export("default", bid)[1]["included"] == 0
                blocked = False
                try:
                    restored_store.reserve(bid, current["id"], "economy", 100)
                except ValueError as exc:
                    blocked = "quarantine" in str(exc)
                assert blocked
                stress_report = {
                    "actual_concurrent_summary_reads": reads,
                    "actual_concurrent_audit_reads": reads,
                    "actual_review_updates": updates,
                    "cross_workspace_denials": denied,
                    "real_data_backup_restore_quarantined": True,
                    "restored_reviews_invalidated": True,
                    "restore_model_dispatch_blocked": True,
                }
                checks.append(
                    "actual concurrent reads/writes, cross-workspace denial and quarantined backup/restore"
                )
            for query in sorted(queries, key=lambda r: r["id"])[:live_rows]:
                sid = upload("supplier", [query])
                response = client.post(
                    "/api/batches",
                    json={
                        "master_id": master,
                        "supplier_id": sid,
                        "egress": True,
                        "call_budget": 2,
                        "instruction_profile": instruction_profile,
                        "reuse_validated_drafts": repeat_drafts,
                    },
                )
                response.raise_for_status()
                live_bid = response.json()["id"]
                client.post(f"/api/batches/{live_bid}/start").raise_for_status()
                state, usage = wait_batch(client, live_bid, 240)
                result = {
                    "source_id": query["id"],
                    "batch_id": live_bid,
                    "state": state["state"],
                    "metrics": usage,
                    "tasks": fetch_tasks(client, live_bid),
                }
                live_results.append(result)
                (output / "live-results.json").write_text(json.dumps(live_results, indent=2))
            if repeat_drafts:
                worker.terminate()
                worker.wait(timeout=10)
                worker = spawn("worker")
                for original in live_results:
                    prior = original["tasks"][0]
                    repeat_spec = client.get(f"/api/batches/{original['batch_id']}").json()["spec"]
                    # A cache miss may not unexpectedly spend a second model call.
                    repeat_spec.update(token_budget=1, row_token_budget=1)
                    response = client.post("/api/batches", json=repeat_spec)
                    response.raise_for_status()
                    repeated_id = response.json()["id"]
                    client.post(f"/api/batches/{repeated_id}/start").raise_for_status()
                    _, usage = wait_batch(client, repeated_id, 30)
                    repeated = fetch_tasks(client, repeated_id)[0]
                    proposal = prior["result"].get("proposal")
                    eligible = bool(
                        proposal
                        and proposal["outcome"] != "insufficient_evidence"
                        and not prior["result"].get("degraded")
                    )
                    hit = "cached_from" in repeated["result"]
                    assert hit == eligible and usage["attempts"] == usage["tokens"] == 0
                    if hit:
                        assert repeated["state"] == "needs_review"
                        assert repeated["result"]["proposal"] == proposal
                        assert not repeated["result"]["calibrated"]
                    repeat_results.append(
                        {
                            "source_id": original["source_id"],
                            "eligible": eligible,
                            "cache_hit": hit,
                            "metrics": usage,
                            "task": repeated,
                        }
                    )
                (output / "repeat-results.json").write_text(json.dumps(repeat_results, indent=2))
                checks.append(
                    "opt-in exact-context draft replay after worker restart; zero new dispatches and no acceptance promotion"
                )
            report = {
                "finished_at": datetime.now(UTC).isoformat(),
                "frozen": frozen,
                "checks": checks,
                "query_rows": len(tasks),
                "retrieval": retrieval,
                "fixture_reviews": reviewed,
                "fixture_accepted": accepted,
                "fixture_rejected": rejected,
                "stale_form_checks": stale_checks,
                "actual_human_reviews": 0,
                "live_rows": len(live_results),
                "live_attempts": sum(r["metrics"]["attempts"] for r in live_results),
                "repeat_drafts": {
                    "rows": len(repeat_results),
                    "hits": sum(r["cache_hit"] for r in repeat_results),
                    "new_attempts": sum(r["metrics"]["attempts"] for r in repeat_results),
                    "fresh_row_routing_gate_claimed": False,
                },
                "live_measured_tokens": sum(r["metrics"]["tokens"] for r in live_results),
                "live_unknown_attempts": sum(
                    r["metrics"]["unknown_attempts"] for r in live_results
                ),
                "live_states": dict(Counter(t["state"] for r in live_results for t in r["tasks"])),
                "code_unchanged": frozen["code"] == fingerprint(),
                "stress": stress_report,
                "verdict": "blocked",
                "limits": [
                    "Not a browser journey",
                    "Review actions are benchmark-derived fixtures",
                    "Only explicitly counted rows invoke real models",
                    "No effective identity/calibration or strict tokens",
                ],
            }
            (output / "report.json").write_text(json.dumps(report, indent=2))
            print(
                json.dumps({k: v for k, v in report.items() if k != "frozen"}, indent=2), flush=True
            )
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live-rows", type=int, default=10)
    parser.add_argument("--stress", action="store_true")
    parser.add_argument("--repeat-drafts", action="store_true")
    parser.add_argument(
        "--instruction-profile", choices=["legacy", "compact_classifier_v1"], default="legacy"
    )
    args = parser.parse_args()
    if not 0 <= args.live_rows <= 10:
        parser.error("bounded at ten live rows in this diagnostic")
    run(
        args.cohort,
        args.output,
        args.live_rows,
        args.stress,
        args.instruction_profile,
        args.repeat_drafts,
    )
