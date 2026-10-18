"""Bounded real-input router/baseline campaign; no synthetic identity/calibration."""

import argparse
import hashlib
import json
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from catalogbridge_api.corpus import score_pairs
from catalogbridge_api.local_router import PairRouter
from catalogbridge_api.matching import validate_proposal
from catalogbridge_api.model_boundary import InstalledModels
from catalogbridge_api.runtime import DispatchNotStarted, diagnostics
from catalogbridge_api.store import Store
from catalogbridge_api.worker import run_once
from contracts.catalogbridge import BatchSpec, Product, Proposal


def fingerprint():
    root = Path(__file__).resolve().parents[1]
    files = (
        list((root / "apps/catalogbridge-api").rglob("*.py"))
        + list((root / "apps/catalogbridge-api").rglob("*.txt"))
        + list((root / "packages/agent-core").rglob("*.py"))
        + [root / "packages/contracts/src/contracts/catalogbridge.py"]
    )
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def snapshot_runtime(destination, hashes):
    """Archive only the whitelisted source/asset files, never credentials or data."""
    root = Path(__file__).resolve().parents[1]
    for relative, expected in hashes.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("unsafe source snapshot path")
        payload = (root / path).read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError("runtime changed before snapshot")
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)


def campaign(
    inputs,
    gold,
    output,
    call_cap,
    modes=None,
    provider=None,
    instruction_profile="legacy",
    local_profile=None,
):
    mode_names = modes or ["router", "economy-only", "strong-only"]
    pair_router = PairRouter(json.loads(local_profile.read_bytes())) if local_profile else None
    if output.exists():
        raise ValueError("new output required")
    rows = [json.loads(line) for line in inputs.read_text().splitlines() if line.strip()]
    labels = {
        r["id"]: r["label"]
        for r in (json.loads(line) for line in gold.read_text().splitlines() if line.strip())
    }
    if len({r["id"] for r in rows}) != len(rows) or any(
        set(r) != {"id", "supplier", "master"} or r["id"] not in labels for r in rows
    ):
        raise ValueError("duplicate input, missing gold or leaked evaluator fields")
    output.mkdir(parents=True)
    frozen = {
        "started_at": datetime.now(UTC).isoformat(),
        "code": fingerprint(),
        "input_sha256": hashlib.sha256(inputs.read_bytes()).hexdigest(),
        "gold_sha256": hashlib.sha256(gold.read_bytes()).hexdigest(),
        "cases": len(rows),
        "actual_call_cap": call_cap,
        "requested_models": ["gpt-6-luna", "gpt-6.1-sol"],
        "calibration": "none; no effective identity fabricated",
        "input_type": "real publisher records",
        "provider_kind": "installed_cli" if provider is None else "injected_test_boundary",
        "instruction_profile": instruction_profile,
        "local_router_sha256": pair_router.fingerprint if pair_router else None,
        "cache_policy": "disabled for all modes",
    }
    (output / "frozen.json").write_text(json.dumps(frozen, indent=2))
    snapshot_runtime(output / "runtime-source", frozen["code"])
    if pair_router:
        (output / "local-router-profile.json").write_bytes(local_profile.read_bytes())
    lock = threading.Lock()
    calls = 0
    observations = []
    runtime_stop = {"open": False, "reason": None}

    def trip(reason):
        with lock:
            runtime_stop.update(open=True, reason=reason)

    class Meter:
        def preflight(self, supplier, gallery):
            with lock:
                if runtime_stop["open"]:
                    raise DispatchNotStarted()
            if provider is None:
                InstalledModels(instruction_profile=instruction_profile).preflight(
                    supplier, gallery
                )
            else:
                InstalledModels.prepare(supplier, gallery, instruction_profile)

        def generate_pair(self, *args, **kwargs):
            nonlocal calls
            with lock:
                if runtime_stop["open"] or calls >= call_cap:
                    raise DispatchNotStarted()
                calls += 1
            try:
                result = (
                    provider or InstalledModels(instruction_profile=instruction_profile)
                ).generate_pair(*args, **kwargs)
            except Exception as exc:
                trip(getattr(exc, "diagnostics", diagnostics(exception=exc))["category"])
                raise
            if result.exit_code or not result.audited or result.usage is None:
                reason = result.diagnostics.get("category", "runtime_failure")
                if not result.exit_code:
                    reason = "audit_unverified" if not result.audited else "usage_unknown"
                trip(reason)
            return result

    meter = Meter()

    def run_mode(mode):
        store = Store(output / mode)
        local = []
        for index, item in enumerate(rows):
            with lock:
                remaining = call_cap - calls
                stopped = runtime_stop["open"]
            if stopped or remaining < (2 if mode == "router" else 1):
                break
            supplier, master = (
                Product.model_validate(item["supplier"]),
                Product.model_validate(item["master"]),
            )
            m = store.import_feed("evaluation", "master", [master])
            s = store.import_feed("evaluation", "supplier", [supplier])
            spec = BatchSpec(
                master_id=m["id"],
                supplier_id=s["id"],
                egress=True,
                instruction_profile=instruction_profile,
                routing_policy="local_review_v1"
                if pair_router and mode == "router"
                else "llm_only",
                local_router_sha256=pair_router.fingerprint
                if pair_router and mode == "router"
                else None,
            )
            b = store.create_batch("evaluation", spec)
            store.start("evaluation", b["id"])
            if mode == "router":
                run_once(store, meter, local_router=pair_router)
            else:
                job = store.claim()
                selected = spec.economy_model if mode == "economy-only" else spec.strong_model
                route = "economy" if mode == "economy-only" else "strong"
                attempt = None
                result = {"candidate_id": None, "reason": "unprocessed", "attempts": []}
                state = "needs_review"
                try:
                    meter.preflight(supplier, [master])
                    attempt = store.reserve(
                        b["id"], job["id"], route, 12000, expected_lease=job["lease"]
                    )
                    result["attempts"].append(attempt)
                    generated = meter.generate_pair(supplier, [master], selected, 90)
                    store.settle(attempt, generated.usage, runtime_evidence=generated.diagnostics)
                    result.update(
                        {
                            "requested_model": selected,
                            "effective_model": generated.effective_model,
                            "elapsed_ms": generated.elapsed_ms,
                            "audited": generated.audited,
                            "raw_text": generated.text,
                            "runtime_diagnostics": generated.diagnostics,
                        }
                    )
                    if generated.exit_code or not generated.audited or generated.usage is None:
                        evidence = generated.diagnostics or {"category": "runtime_failure"}
                        store.open_runtime_circuit("evaluation", b["id"], evidence)
                        with store.write() as db:
                            store.event(
                                db,
                                b["id"],
                                "provider_failure",
                                {"attempt": attempt, "diagnostics": evidence},
                            )
                        raise ValueError("provider_runtime_failure")
                    proposal = Proposal.model_validate_json(generated.text)
                    validate_proposal(proposal, supplier, [master])
                    result.update(
                        {
                            "proposal": proposal.model_dump(),
                            "candidate_id": proposal.candidate_id,
                            "reason": "baseline proposal only; never an automatic accepted link",
                        }
                    )
                except (ValueError, RuntimeError, OSError) as exc:
                    settled = False
                    if attempt:
                        with store.connect() as db:
                            settled = (
                                db.execute(
                                    "SELECT state FROM attempts WHERE id=?", (attempt,)
                                ).fetchone()[0]
                                == "settled"
                            )
                    if attempt and not settled:
                        store.settle(
                            attempt,
                            getattr(exc, "usage", None),
                            runtime_evidence=getattr(
                                exc, "diagnostics", diagnostics(exception=exc)
                            ),
                        )
                    if attempt and not isinstance(exc, DispatchNotStarted) and not settled:
                        evidence = getattr(exc, "diagnostics", diagnostics(exception=exc))
                        store.open_runtime_circuit("evaluation", b["id"], evidence)
                    result["reason"] = type(exc).__name__
                    if hasattr(exc, "diagnostics"):
                        result["runtime_diagnostics"] = exc.diagnostics
                    state = "failed"
                store.checkpoint(job, result, state)
            task = store.tasks("evaluation", b["id"])[0]
            metrics = store.analytics("evaluation", b["id"])
            observation = {
                "id": item["id"],
                "mode": mode,
                "batch_id": b["id"],
                "state": task["state"],
                "prediction": {"same_product": 1, "different_product": 0}.get(
                    task["result"].get("proposal", {}).get("outcome")
                ),
                "result": task["result"],
                "metrics": metrics,
            }
            with (output / (mode + ".jsonl")).open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(observation) + "\n")
            local.append(observation)
            with lock:
                print(
                    json.dumps(
                        {
                            "mode": mode,
                            "completed": len(local),
                            "actual_calls": calls,
                            "last_state": task["state"],
                            "last_tokens": metrics["tokens"],
                        }
                    ),
                    flush=True,
                )
        return local

    with ThreadPoolExecutor(max_workers=3) as pool:
        for group in pool.map(run_mode, mode_names):
            observations.extend(group)
    all_ids = [r["id"] for r in rows]
    shared = set.intersection(
        *[{r["id"] for r in observations if r["mode"] == mode} for mode in mode_names]
    )
    summaries = {}
    for mode in mode_names:
        group = [r for r in observations if r["mode"] == mode]
        mapping = {r["id"]: r for r in group}
        summaries[mode] = {
            "completed": len(group),
            "agreement_full_denominator": score_pairs(
                [labels[i] for i in all_ids],
                [mapping.get(i, {}).get("prediction") for i in all_ids],
            ),
            "paired_agreement": score_pairs(
                [labels[i] for i in sorted(shared)],
                [mapping[i]["prediction"] for i in sorted(shared)],
            )
            if shared
            else None,
            "tokens": sum(r["metrics"]["tokens"] for r in group),
            "attempts": sum(r["metrics"]["attempts"] for r in group),
            "unknown_attempts": sum(r["metrics"]["unknown_attempts"] for r in group),
            "states": dict(Counter(r["state"] for r in group)),
            "journal_mismatches": sum(not r["metrics"]["journal_consistent"] for r in group),
            "automatic_acceptances": sum(r["state"] == "recommended_match" for r in group),
            "local_draft_exits": sum(r["result"].get("exit_stage") == "local_pair" for r in group),
        }
    report = {
        "finished_at": datetime.now(UTC).isoformat(),
        "frozen": frozen,
        "code_unchanged": frozen["code"] == fingerprint(),
        "actual_calls": calls,
        "dispatched_invocations": calls,
        "runtime_stop": runtime_stop,
        "comparison_eligible": not runtime_stop["open"]
        and all(
            s["completed"] == len(rows) and s["unknown_attempts"] == 0 for s in summaries.values()
        ),
        "paired_rows": len(shared) if len(mode_names) > 1 else 0,
        "shared_completed_rows": len(shared),
        "modes": summaries,
        "verdict": "blocked",
        "limits": [
            "Bounded diagnostic, not the documented 4500/600 live campaign",
            "Publisher benchmark agreement is not independent truth",
            "Effective model identity absent",
            "No qualified real calibration; early exit not validated",
            "No actual billing/savings claims",
        ],
    }
    if "router" in summaries and "strong-only" in summaries:
        router = summaries["router"]
        strong = summaries["strong-only"]
        saving = 1 - router["tokens"] / strong["tokens"] if strong["tokens"] else None
        quality = (
            router["agreement_full_denominator"]["accuracy_all_rows"]
            - strong["agreement_full_denominator"]["accuracy_all_rows"]
        )
        report["benchmark_tradeoff"] = {
            "token_reduction": saving,
            "accuracy_difference": quality,
            "meets_point_targets_on_this_cohort": bool(
                report["comparison_eligible"]
                and report["code_unchanged"]
                and saving is not None
                and saving >= 0.2
                and quality >= -0.01
            ),
            "original_600_pair_and_independent_quality_gate_complete": False,
            "automatic_acceptance_qualified": False,
        }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--call-cap", type=int, default=180)
    parser.add_argument("--modes", nargs="+", choices=["router", "economy-only", "strong-only"])
    parser.add_argument(
        "--instruction-profile", choices=["legacy", "compact_classifier_v1"], default="legacy"
    )
    parser.add_argument("--local-profile", type=Path)
    args = parser.parse_args()
    if not 1 <= args.call_cap <= 10000:
        parser.error("explicit bounded call cap required")
    campaign(
        args.inputs,
        args.gold,
        args.output,
        args.call_cap,
        args.modes,
        instruction_profile=args.instruction_profile,
        local_profile=args.local_profile,
    )
