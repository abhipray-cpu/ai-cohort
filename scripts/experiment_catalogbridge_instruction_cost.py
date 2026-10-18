"""Eight-call paired instruction-cost experiment; no automatic policy activation."""

import argparse
import hashlib
import json
from pathlib import Path

from catalogbridge_api.matching import validate_proposal
from catalogbridge_api.model_boundary import InstalledModels, MeteredCodex
from catalogbridge_api.store import Store
from contracts.catalogbridge import BatchSpec, Product, Proposal

from scripts.run_catalogbridge_real_models import fingerprint


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cohort", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("preserve prior evidence")
    labels = {
        r["id"]: r["label"]
        for r in map(json.loads, (args.cohort / "gold.jsonl").read_text().splitlines())
    }
    rows = list(map(json.loads, (args.cohort / "inputs.jsonl").read_text().splitlines()))
    selected = [
        min(
            [r for r in rows if labels[r["id"]] == label],
            key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest(),
        )
        for label in (0, 1)
    ]
    instructions = Path(__file__).with_name("catalogbridge_classifier_instructions.txt").resolve()
    args.output.mkdir(parents=True)
    frozen = {
        "code": fingerprint(),
        "cases": [r["id"] for r in selected],
        "call_cap": 8,
        "instructions_sha256": hashlib.sha256(instructions.read_bytes()).hexdigest(),
        "not_acceptance": "Two diagnostic cases, not calibrated quality or savings evidence",
    }
    (args.output / "frozen.json").write_text(json.dumps(frozen, indent=2))
    observations = []
    stopped = False
    for style in ("legacy", "compact"):
        for route, model in [("economy", "gpt-6-luna"), ("strong", "gpt-6.1-sol")]:
            store = Store(args.output / f"{style}-{route}")
            for row in selected:
                if stopped:
                    break
                supplier, master = Product(**row["supplier"]), Product(**row["master"])
                m = store.import_feed("experiment", "master", [master])
                s = store.import_feed("experiment", "supplier", [supplier])
                batch = store.create_batch(
                    "experiment", BatchSpec(master_id=m["id"], supplier_id=s["id"], egress=True)
                )
                store.start("experiment", batch["id"])
                task = store.claim()
                attempt = store.reserve(
                    batch["id"], task["id"], route, 12000, expected_lease=task["lease"]
                )
                adapter = MeteredCodex(model)
                if style == "compact":
                    adapter.config_overrides += (
                        "model_instructions_file=" + json.dumps(str(instructions)),
                    )
                prompt, schema = InstalledModels.prepare(supplier, [master])
                result = {
                    "id": row["id"],
                    "style": style,
                    "route": route,
                    "batch_id": batch["id"],
                    "requested_model": model,
                }
                try:
                    generated = adapter.generate_metered(prompt, schema)
                    store.settle(attempt, generated.usage)
                    result.update(
                        usage=generated.usage.model_dump() if generated.usage else None,
                        diagnostics=generated.diagnostics,
                        effective_model=generated.effective_model,
                    )
                    if generated.exit_code or not generated.audited or generated.usage is None:
                        stopped = True
                        raise ValueError("runtime_failure")
                    proposal = Proposal.model_validate_json(generated.text)
                    validate_proposal(proposal, supplier, [master])
                    result.update(
                        prediction={"same_product": 1, "different_product": 0}.get(
                            proposal.outcome
                        ),
                        proposal=proposal.model_dump(),
                    )
                except (ValueError, RuntimeError, OSError) as exc:
                    with store.connect() as db:
                        settled = (
                            db.execute(
                                "SELECT state FROM attempts WHERE id=?", (attempt,)
                            ).fetchone()[0]
                            == "settled"
                        )
                    if not settled:
                        store.settle(attempt, getattr(exc, "usage", None))
                        stopped = True
                    result["error_type"] = type(exc).__name__
                metrics = store.analytics("experiment", batch["id"])
                result.update(
                    metrics=metrics, benchmark_agrees=result.get("prediction") == labels[row["id"]]
                )
                store.checkpoint(task, result, "needs_review" if "proposal" in result else "failed")
                observations.append(result)
                (args.output / "observations.json").write_text(json.dumps(observations, indent=2))
                print(
                    json.dumps(
                        {
                            k: result[k]
                            for k in ("id", "style", "route", "usage", "benchmark_agrees")
                            if k in result
                        }
                    ),
                    flush=True,
                )
    report = {
        "frozen": frozen,
        "code_unchanged": fingerprint() == frozen["code"],
        "runtime_stopped": stopped,
        "dispatches": len(observations),
        "modes": {
            style: {
                route: {
                    "rows": len(
                        group := [
                            r for r in observations if r["style"] == style and r["route"] == route
                        ]
                    ),
                    "tokens": sum(r["metrics"]["tokens"] for r in group),
                    "benchmark_agreements": sum(r["benchmark_agrees"] for r in group),
                    "unknown_attempts": sum(r["metrics"]["unknown_attempts"] for r in group),
                }
                for route in ("economy", "strong")
            }
            for style in ("legacy", "compact")
        },
        "not_promoted": True,
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
