"""Frozen real-input pair campaign. --live consumes installed Codex usage."""

import argparse
import hashlib
import json
from pathlib import Path

from catalogbridge_api.corpus import score_pairs
from catalogbridge_api.store import Store
from catalogbridge_api.worker import run_once
from contracts.catalogbridge import BatchSpec, Product


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-pairs", type=int, required=True)
    parser.add_argument("--max-calls", type=int, default=20)
    parser.add_argument("--economy-model", default="gpt-6-luna")
    parser.add_argument("--strong-model", default="gpt-6.1-sol")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.output.exists() or not 1 <= args.max_pairs <= 50000 or not 1 <= args.max_calls <= 10000:
        parser.error("new output and bounded positive limits required")
    inputs = [json.loads(line) for line in args.inputs.read_text().splitlines() if line.strip()][
        : args.max_pairs
    ]
    labels = {
        r["id"]: r["label"]
        for r in (json.loads(line) for line in args.gold.read_text().splitlines() if line.strip())
    }
    if (
        not inputs
        or len({r["id"] for r in inputs}) != len(inputs)
        or any(r["id"] not in labels for r in inputs)
    ):
        parser.error("missing/duplicate evaluation rows")
    args.output.mkdir(parents=True)
    store = Store(args.output / "product")
    observations = []
    calls = 0
    for item in inputs:
        if set(item) != {"id", "supplier", "master"}:
            raise ValueError("unexpected runtime fields; gold leakage refused")
        supplier = Product.model_validate(item["supplier"])
        master = Product.model_validate(item["master"])
        m = store.import_feed("evaluation", "master", [master])
        s = store.import_feed("evaluation", "supplier", [supplier])
        live = args.live and calls + 2 <= args.max_calls
        b = store.create_batch(
            "evaluation",
            BatchSpec(
                master_id=m["id"],
                supplier_id=s["id"],
                egress=live,
                economy_model=args.economy_model,
                strong_model=args.strong_model,
            ),
        )
        store.start("evaluation", b["id"])
        run_once(store)
        t = store.tasks("evaluation", b["id"])[0]
        metrics = store.analytics("evaluation", b["id"])
        calls += metrics["attempts"]
        proposal = t["result"].get("proposal", {})
        prediction = {"same_product": 1, "different_product": 0}.get(proposal.get("outcome"))
        observations.append(
            {
                "id": item["id"],
                "batch_id": b["id"],
                "live_authorized": live,
                "state": t["state"],
                "prediction": prediction,
                "result": t["result"],
                "analytics": metrics,
            }
        )
        (args.output / "observations.jsonl").open("a", encoding="utf-8").write(
            json.dumps(observations[-1]) + "\n"
        )
        if metrics["unknown_attempts"]:
            break
    by_id = {r["id"]: r for r in observations}
    predictions = [by_id.get(r["id"], {}).get("prediction") for r in inputs]
    report = {
        "input_sha256": hashlib.sha256(args.inputs.read_bytes()).hexdigest(),
        "gold_sha256": hashlib.sha256(args.gold.read_bytes()).hexdigest(),
        "requested_rows": len(inputs),
        "processed_rows": len(observations),
        "live": args.live,
        "calls": calls,
        "raw_proposal_benchmark_agreement": score_pairs(
            [labels[r["id"]] for r in inputs], predictions
        ),
        "automatic_acceptances": sum(r["state"] == "recommended_match" for r in observations),
        "release_verdict": "blocked",
        "limitations": [
            "Not independently adjudicated",
            "Pairwise inputs do not validate candidate retrieval",
            "No qualified calibration installed",
            "Strict token enforcement unavailable",
            "Browser/Windows/buyer acceptance pending",
        ],
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
