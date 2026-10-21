"""Evidence utilities. Controlled engineering, actual inference and quality stay separate."""

import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import httpx
from contracts.shelfproof import CorrectionPlan, Draft, FactPack, JudgeEvaluation, PlanItem, Rating

from .core import canonical, check_draft, code_fingerprint, digest, freeze_import
from .corpus import source_group
from .store import Store
from .workflow import Worker


def select_smoke_records(records, limit=6):
    if not 1 <= limit <= 6:
        raise ValueError("approved maximum six distinct development products")
    selected = []
    groups = set()
    owners = set()
    for record in records:
        owner = source_group(record["raw"])
        facts = FactPack.model_validate(record["facts"])
        literal = Draft(
            title=f"{facts.brand} {facts.name} {facts.net_quantity} {facts.net_unit}",
            description=facts.ingredients,
        )
        if check_draft(facts, literal):
            continue  # Positive smoke scope is frozen before any model outputs, not selected by scores.
        if (
            record["split"] == "development"
            and record["group"] not in groups
            and owner not in owners
        ):
            groups.add(record["group"])
            owners.add(owner)
            selected.append(record)
            if len(selected) == limit:
                return selected
    raise ValueError("insufficient distinct development groups; do not substitute holdout rows")


def acceptance_gates(report):
    actual = report.get("mode") == "actual_installed_codex"
    provider = (
        "pass"
        if report.get("actual_calls", 0) > 0
        and report.get("unknown_attempts") == 0
        and report.get("all_concepts_observed")
        and report.get("terminal") == report.get("rows")
        and report.get("rows", 0) > 0
        and report.get("states") == {"review_ready": report["rows"]}
        else "fail"
    )
    return {
        "actual_provider": provider if actual else "not_run",
        "independent_quality": "not_run",
        "browser": "not_run",
        "windows_tunnel": "not_run",
        "commercial": "not_run",
        "production_accepted": False,
        "note": "Judge scores and fixture volume are not independent quality evidence.",
    }


def load_corpus(path):
    root = Path(path)
    manifest = json.loads((root / "manifest.json").read_text())
    raw = (root / "records.jsonl").read_bytes()
    if digest(raw) != manifest["records_hash"]:
        raise ValueError("corpus manifest mismatch")
    records = [json.loads(line) for line in raw.decode().splitlines()]
    if len(records) != manifest["eligible_selected"] or not records:
        raise ValueError("corpus row count mismatch")
    for record in records:
        FactPack.model_validate(record["facts"])
        if digest(record["raw"]) != record["raw_hash"]:
            raise ValueError("raw source record hash mismatch")
    return manifest, records


def summarize(store, actor, task_ids, mode):
    tasks = [store.task(actor, task) for task in task_ids]
    attempts = [a for t in tasks for a in t["attempts"]]
    stages = {s["stage"].split(":")[0] for t in tasks for s in t["stages"]}
    terminal = sum(t["state"] not in {"queued", "running"} for t in tasks)
    report = {
        "schema": "shelfproof-validation-v1",
        "mode": mode,
        "code_fingerprint": code_fingerprint(),
        "rows": len(tasks),
        "terminal": terminal,
        "states": dict(Counter(t["state"] for t in tasks)),
        "actual_calls": len(attempts) if mode == "actual_installed_codex" else 0,
        "controlled_calls": len(attempts) if mode == "controlled_provider" else 0,
        "unknown_attempts": sum(a["status"] != "known" for a in attempts),
        "known_input_tokens_lower_bound": sum(
            (a["receipt"] or {}).get("input_tokens") or 0 for a in attempts
        ),
        "known_output_tokens_lower_bound": sum(
            (a["receipt"] or {}).get("output_tokens") or 0 for a in attempts
        ),
        "all_concepts_observed": stages >= {"draft", "judge", "reflect"}
        and any(t["metrics"] for t in tasks),
        "pending_ids": [t["id"] for t in tasks if t["state"] in {"queued", "running"}],
        "human_quality_labels": 0,
        "actual_customer_drafts": 0,
        "source_truth": "USDA snapshot only",
        "products": [
            {
                "task": t["id"],
                "product_id": t["facts"]["product_id"],
                "state": t["state"],
                "calls": t["calls"],
                "versions": len(t["versions"]),
                "plans": len(t["plans"]),
                "selected_hash": t["selected_hash"],
                "metrics": t["metrics"],
                "warnings": t["warnings"],
            }
            for t in tasks
        ],
    }
    report["gates"] = acceptance_gates(report)
    return report


class ControlledProvider:
    """Literal source copier and fixed rubric, for engineering load ONLY. Never LLM evidence."""

    last_receipt = None

    def generate(self, *, prompt, schema):
        context = json.loads(prompt)
        facts = context["facts"]
        if context["role"] == "independent listing evaluator":
            value = 2 if context["checks"] else 4
            output = JudgeEvaluation(
                ratings={
                    name: Rating(
                        value=value,
                        rationale="Controlled engineering fixture, not semantic judgment",
                    )
                    for name in ("fidelity", "coverage", "channel", "clarity", "brand")
                },
                findings=[],
            )
        elif context["role"] == "correction planner":
            output = CorrectionPlan(
                items=[
                    PlanItem(
                        finding_id=key,
                        operation="request_source",
                        rationale="Controlled provider cannot assert a semantic repair",
                        refs=[],
                    )
                    for key, finding in context["findings"].items()
                    if finding["severity"] != "minor"
                ]
            )
        else:
            output = Draft(
                title=f"{facts['brand']} {facts['name']} {facts['net_quantity']} {facts['net_unit']}",
                description=facts["ingredients"],
            )
        self.last_receipt = {"audited": True, "input_tokens": 0, "output_tokens": 0}
        return output.model_dump_json()


def software_validation(corpus, output):
    manifest, records = load_corpus(corpus)
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    store = Store(root / "service")
    store.create_user("engineering", "owned-fixture-password-123")
    workspace = store.create_workspace("engineering", "USDA source-backed ENGINEERING ONLY")
    grant = store.authorize(
        "engineering",
        workspace,
        basis="Controlled local provider, no real inference or network egress",
        expires=store.now() + 86400,
        max_calls=16000,
        egress=True,
    )
    raw = canonical([row["facts"] for row in records]).encode()
    mapping = {key: key for key in FactPack.model_fields}
    source = store.save_import("engineering", workspace, raw, freeze_import(raw, "json", mapping))
    tasks = []
    for start in range(0, len(records), 100):
        batch = store.create_batch(
            "engineering",
            workspace,
            source,
            list(range(start, min(start + 100, len(records)))),
            grant,
            f"batch:{start}",
        )
        tasks.extend(
            store.start_batch(
                "engineering", batch, store.batch_preview("engineering", batch)["binding"]
            )
        )
    worker = Worker(store, ControlledProvider())
    while worker.run_once():
        pass
    report = summarize(store, "engineering", tasks, "controlled_provider")
    report["source_manifest_hash"] = digest(manifest)
    report["heuristic_groups"] = len({r["group"] for r in records})
    (root / "report.json").write_text(canonical(report))
    return report


def _register_smoke_approval(approval_ref, root, manifest, selected):
    if not 1 <= len(approval_ref) <= 2000:
        raise ValueError("explicit user approval reference required")
    authority = Path(__file__).resolve().parents[4] / "var/validation/shelfproof-authority"
    authority.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(authority / "campaigns.sqlite3") as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS approvals(ref TEXT PRIMARY KEY,root TEXT NOT NULL,body TEXT NOT NULL)"
        )
        payload = {
            "reference": approval_ref,
            "maximum_calls": 96,
            "maximum_products": 6,
            "source_manifest_hash": digest(manifest),
            "product_ids": [r["facts"]["product_id"] for r in selected],
            "destination": "installed-codex-configured-service",
            "code_fingerprint": code_fingerprint(),
            "root": str(root.resolve()),
        }
        # Reusing the approval cannot silently create another clean store/grant after a fault.
        db.execute(
            "INSERT INTO approvals VALUES(?,?,?)",
            (digest(approval_ref.encode()), str(root.resolve()), canonical(payload)),
        )
        return payload


def actual_smoke(corpus, output, approval_ref, *, products=6):
    manifest, records = load_corpus(corpus)
    selected = select_smoke_records(records, products)
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    approval = _register_smoke_approval(approval_ref, root, manifest, selected)
    (root / "approval.json").write_text(canonical(approval))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    password = secrets.token_urlsafe(24)
    env = {
        **os.environ,
        "SHELFPROOF_DATA_DIR": str(root / "service"),
        "SHELFPROOF_USERNAME": "validation-owner",
        "SHELFPROOF_PASSWORD": password,
        "SHELFPROOF_ORIGIN": origin,
    }
    api = subprocess.Popen(
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
    worker = None
    task_ids = []
    started = time.monotonic()
    report = None
    try:
        with httpx.Client(base_url=origin, timeout=20) as client:
            for _ in range(200):
                try:
                    if client.get("/health/live").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if api.poll() is not None:
                    raise RuntimeError("temporary API failed to start")
                time.sleep(0.05)

            def request(method, path, **kwargs):
                response = client.request(method, path, **kwargs)
                response.raise_for_status()
                return response.json()

            login = request(
                "POST", "/api/session", json={"username": "validation-owner", "password": password}
            )
            client.headers.update({"X-CSRF-Token": login["csrf"], "Origin": origin})
            workspace = request(
                "POST", "/api/workspaces", json={"name": "USDA actual development smoke"}
            )["id"]
            grant = request(
                "POST",
                f"/api/workspaces/{workspace}/rights",
                json={
                    "basis": approval_ref,
                    "expires": time.time() + 86400,
                    "max_calls": 96,
                    "egress": True,
                },
            )["id"]
            raw = canonical([r["facts"] for r in selected]).encode()
            request(
                "POST",
                f"/api/workspaces/{workspace}/imports/preview",
                files={"file": ("usda-facts.json", raw, "application/json")},
            )
            source = request(
                "POST",
                f"/api/workspaces/{workspace}/imports",
                data={"mapping": canonical({k: k for k in FactPack.model_fields})},
                files={"file": ("usda-facts.json", raw, "application/json")},
            )["id"]
            cohorts = []
            for i, record in enumerate(selected):
                facts = FactPack.model_validate(record["facts"])
                original = None
                if i >= products // 2:
                    wrong = "1" if facts.net_quantity != 1 else "2"
                    original = Draft(
                        title=f"{facts.brand} {facts.name} {wrong} {facts.net_unit}",
                        description=facts.ingredients,
                    ).model_dump(mode="json")
                task = request(
                    "POST",
                    f"/api/workspaces/{workspace}/tasks",
                    headers={"Idempotency-Key": f"smoke:{i}"},
                    json={"import_id": source, "row": i, "grant": grant, "original": original},
                )["id"]
                task_ids.append(task)
                cohorts.append(
                    {
                        "task": task,
                        "product_id": facts.product_id,
                        "group": record["group"],
                        "cohort": "authentic_source_injected_quantity_fault"
                        if original
                        else "authentic_source_generated_copy",
                        "injection_is_not_authentic_customer_error": bool(original),
                    }
                )
            (root / "cohorts.json").write_text(canonical(cohorts))
            worker = subprocess.Popen(
                [sys.executable, "-m", "shelfproof_api.worker"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            store = Store(root / "service")
            while time.monotonic() - started < 3 * 3600:
                current = [request("GET", f"/api/tasks/{task}") for task in task_ids]
                if store.liability_hold() or all(
                    t["state"] not in {"queued", "running"} for t in current
                ):
                    break
                if worker.poll() is not None:
                    break
                # Actual API responsiveness is checked during ongoing model work.
                if client.get("/health/live").status_code != 200:
                    raise RuntimeError("API liveness failed during inference")
                time.sleep(2)
            report = summarize(store, "validation-owner", task_ids, "actual_installed_codex")
            report.update(
                {
                    "source_manifest_hash": digest(manifest),
                    "approval": approval,
                    "elapsed_seconds": time.monotonic() - started,
                    "cohorts": cohorts,
                    "human_review_performed": False,
                    "automatic_approval_performed": False,
                }
            )
            (root / "UNAPPROVED-review.csv").write_text(
                store.review_csv("validation-owner", workspace)
            )
    finally:
        for process in (worker, api):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        if report is None:
            report = {
                "mode": "actual_installed_codex",
                "rows": products,
                "actual_calls": None,
                "result": "incomplete_harness_failure",
                "approval": approval,
                "task_ids": task_ids,
                "production_accepted": False,
            }
        (root / "report.json").write_text(canonical(report))
    return report
