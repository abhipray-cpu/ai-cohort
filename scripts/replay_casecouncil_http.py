"""Actual loopback API + installed-Codex worker replay of authorized local evidence.

Operator-only, explicitly isolated research launcher; no normal-service IE flag.
No automated review performed here is independent human/domain acceptance.
"""

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
from casecouncil_api.campaign import summarize_replay
from casecouncil_api.consensus import digest
from casecouncil_api.evaluation import audit_corpus, load_manifest

ROOT = Path(__file__).resolve().parents[1]


def child(args):
    from casecouncil_api.store import Store

    if args.role == "api":
        import uvicorn
        from casecouncil_api.api import create_app

        uvicorn.run(
            create_app(
                args.data_dir,
                username="replay-maker",
                password=os.environ["CASECOUNCIL_REPLAY_PASSWORD"],
                evaluation_only=True,
            ),
            host="127.0.0.1",
            port=args.port,
            log_level="warning",
            access_log=False,
        )
    else:
        from casecouncil_api.controller import Controller
        from casecouncil_api.runtime import provider_from_env

        store = Store(args.data_dir, evaluation_only=True)
        controller = Controller(store, provider_from_env())
        while True:
            if not controller.once():
                time.sleep(0.2)


def replay(args):
    if not args.live or not 1 <= args.limit <= 50 or args.max_calls < 22:
        raise ValueError("explicit --live, limit 1..50 and bounded call allowance required")
    inventory = audit_corpus(args.corpus)
    if inventory["near_duplicate_warnings"]:
        raise ValueError("split duplicate review required")
    root, manifest = load_manifest(args.corpus)
    if not manifest["permission"]["egress"]:
        raise ValueError(
            "explicit approval of real-payload/model destination required before live replay"
        )
    selected = sorted(
        [r for r in manifest["cases"] if r["split"] == args.split], key=lambda r: digest(r["id"])
    )[: args.limit]
    if not selected:
        raise ValueError("empty split")
    approval = manifest.get("egress_approval")
    if approval and (
        args.max_calls > approval["max_calls"]
        or any(r["id"] not in approval["ids"] for r in selected)
    ):
        raise ValueError("campaign exceeds explicit approved IDs or cumulative allowance")
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "selection.json").write_text(
        json.dumps(
            {
                "ids": [r["id"] for r in selected],
                "manifest_hash": inventory["manifest_hash"],
                "max_calls": args.max_calls,
                "split": args.split,
            },
            indent=2,
        )
    )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    password = secrets.token_urlsafe(32)
    env = {**os.environ, "CASECOUNCIL_REPLAY_PASSWORD": password}
    logs = [(output / (role + ".log")).open("w") for role in ("api", "worker")]
    processes = []
    results = []
    calls = 0
    try:
        base = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--data-dir",
            str(output / "service"),
            "--port",
            str(port),
        ]
        processes.append(
            subprocess.Popen(
                base + ["--role", "api"], cwd=ROOT, env=env, stdout=logs[0], stderr=logs[0]
            )
        )
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
            for _ in range(100):
                try:
                    if client.get("/health/live").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("API failed to start")

            def request(method, path, **kwargs):
                response = client.request(
                    method, path, headers={"Idempotency-Key": uuid.uuid4().hex}, **kwargs
                )
                if not response.is_success:
                    raise RuntimeError(f"HTTP {response.status_code}: {path}")
                return response.json()

            login = request(
                "POST", "/api/session", json={"username": "replay-maker", "password": password}
            )
            client.headers["X-CSRF-Token"] = login["csrf"]
            w = request(
                "POST", "/api/workspaces", json={"name": "Irish retrospective research only"}
            )["id"]
            request(
                "PUT",
                f"/api/workspaces/{w}/policy",
                json={
                    "revision": 1,
                    "policy": {
                        "name": "Irish retrospective replay v1",
                        "instructions": "Irish evidence replay only, NOT UK law or prospective validation. Use attributed party statements only. Full policy/file gaps prevent qualified conclusions. No external law, web or published-outcome inference.",
                        "required_documents": ["complaint"],
                        "egress_enabled": True,
                    },
                },
            )
            rid = request("POST", f"/api/workspaces/{w}/rights", json=manifest["permission"])["id"]
            request(
                "POST", "/api/users", json={"username": "replay-reviewer", "password": password}
            )
            request(
                "PUT",
                f"/api/workspaces/{w}/members",
                json={"username": "replay-reviewer", "role": "reviewer"},
            )
            processes.append(
                subprocess.Popen(
                    base + ["--role", "worker"], cwd=ROOT, env=env, stdout=logs[1], stderr=logs[1]
                )
            )
            for record in selected:
                if args.max_calls - calls < 22:
                    break
                c = request(
                    "POST", "/api/cases", json={"workspace": w, "context": record["context"]}
                )["id"]
                for n, doc in enumerate(record["documents"]):
                    path = root / doc["path"]
                    request(
                        "POST",
                        f"/api/cases/{c}/sources",
                        data={"revision": n + 1, "kind": doc["kind"], "rights_id": rid},
                        files={"file": (path.name, path.read_bytes(), "text/plain")},
                    )
                preview = request("GET", f"/api/cases/{c}/egress-preview")
                started = time.monotonic()
                start_key = uuid.uuid4().hex
                first = client.post(
                    f"/api/cases/{c}/runs",
                    json={"binding": preview["binding"]},
                    headers={"Idempotency-Key": start_key},
                )
                first.raise_for_status()
                job = first.json()["id"]
                repeated = client.post(
                    f"/api/cases/{c}/runs",
                    json={"binding": preview["binding"]},
                    headers={"Idempotency-Key": start_key},
                )
                assert repeated.status_code == 202 and repeated.json()["id"] == job
                while time.monotonic() - started < 1900:
                    run = request("GET", f"/api/runs/{job}")
                    if run["state"] not in {"queued", "running"}:
                        break
                    time.sleep(0.5)
                else:
                    raise RuntimeError("campaign run wall limit")
                calls += run["calls"]
                packet = run["packet"] or {}
                export = request("GET", f"/api/runs/{job}/export")
                html_export = client.get(f"/api/runs/{job}/export?format=html")
                assert (
                    html_export.status_code == 200
                    and "attachment" in html_export.headers["content-disposition"]
                )
                rejected_review = client.post(
                    f"/api/runs/{job}/reviews",
                    json={
                        "packet_hash": run["packet_hash"],
                        "reason": "Automated negative permission check, not domain approval",
                        "response": "Not an actual reviewed response",
                        "resolutions": {},
                        "overrides": {},
                    },
                    headers={"Idempotency-Key": uuid.uuid4().hex},
                )
                assert rejected_review.status_code == 403
                with httpx.Client(base_url=f"http://127.0.0.1:{port}") as anonymous:
                    assert anonymous.get(f"/api/runs/{job}").status_code == 401
                receipts = [a["receipt"] for a in run["attempts"]]
                stages = list(run["checkpoints"])
                consensus = packet.get("consensus") or {}
                result = {
                    "id": record["id"],
                    "case": c,
                    "job": job,
                    "state": run["state"],
                    "calls": run["calls"],
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "stages": stages,
                    "proposers": sorted(packet.get("proposals", {})),
                    "critic_available": packet.get("critique") is not None,
                    "ballots": sorted(packet.get("ballots", {})),
                    "synthesis_available": packet.get("synthesis") is not None,
                    "consensus": consensus,
                    "unavailable": packet.get("unavailable", []),
                    "packet_hash": run["packet_hash"],
                    "review_requirements": packet.get("review_requirements", []),
                    "draft_approved": export["approved"],
                    "http_checks": {
                        "idempotent_start": True,
                        "maker_review_denied": True,
                        "anonymous_packet_denied": True,
                        "html_export": True,
                    },
                    "usage_known": sum(bool(r and r.get("usage")) for r in receipts),
                    "all_tools_audited": all(r and r.get("tools_audited") for r in receipts),
                    "input_tokens": sum(
                        (r or {}).get("usage", {}).get("input_tokens", 0)
                        for r in receipts
                        if (r or {}).get("usage")
                    ),
                    "output_tokens": sum(
                        (r or {}).get("usage", {}).get("output_tokens", 0)
                        for r in receipts
                        if (r or {}).get("usage")
                    ),
                }
                # Evaluator-only outcome opened AFTER completed inference.
                result["historical_outcome"] = json.loads((root / record["gold_path"]).read_text())[
                    "issues"
                ]
                (output / (record["id"] + ".packet.json")).write_text(json.dumps(packet, indent=2))
                results.append(result)
                (output / "progress.json").write_text(json.dumps(results, indent=2))
                print(
                    json.dumps(
                        {
                            "terminal_packets": len(results),
                            "id": record["id"],
                            "state": run["state"],
                            "calls": run["calls"],
                            "unavailable": result["unavailable"],
                        }
                    ),
                    flush=True,
                )
                if request("GET", f"/api/workspaces/{w}")["hold"]:
                    break
            report = {
                "scope": "actual Irish FSPO motor-insurance party-summary data through real HTTP API and installed-Codex worker",
                "inventory": inventory,
                "selected": len(selected),
                "completed": len(results),
                "calls": calls,
                "results": results,
                "pending_ids": [
                    r["id"] for r in selected if r["id"] not in {r["id"] for r in results}
                ],
                "actual_data_replay_executed": bool(results),
                "uk_domain_validated": False,
                "independent_semantic_accuracy": "not_measured",
                "full_product_accepted": False,
                **summarize_replay([r["id"] for r in selected], results),
            }
            # Compatibility field only: terminal packets include degraded results.
            report["completed_definition"] = "terminal packets, NOT full protocol passes"
            (output / "report.json").write_text(json.dumps(report, indent=2))
            print(
                json.dumps(
                    {k: v for k, v in report.items() if k not in {"results", "inventory"}}, indent=2
                ),
                flush=True,
            )
            return report
    finally:
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for log in logs:
            log.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--role", choices=("api", "worker"))
    p.add_argument("--data-dir")
    p.add_argument("--port", type=int)
    p.add_argument("--corpus")
    p.add_argument("--output")
    p.add_argument("--live", action="store_true")
    p.add_argument("--limit", type=int, default=6)
    p.add_argument("--max-calls", type=int, default=132)
    p.add_argument("--split", choices=("development", "calibration", "test"), default="development")
    args = p.parse_args()
    if args.role:
        child(args)
    else:
        report = replay(args)
        raise SystemExit(0 if report["protocol_campaign_passed"] else 1)
