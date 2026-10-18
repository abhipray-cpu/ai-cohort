"""Score a frozen local router on label-separated held-out pairs, without LLM calls."""

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from catalogbridge_api.local_router import PairRouter, lower_bound
from contracts.catalogbridge import Product


def evaluate(profile, inputs, gold, output):
    if output.exists():
        raise ValueError("preserve earlier evidence")
    router = PairRouter(json.loads(profile.read_bytes()))
    rows = [json.loads(line) for line in inputs.read_text().splitlines() if line.strip()]
    labels = {}
    hard = {}
    for line in gold.read_text().splitlines():
        row = json.loads(line)
        if row["id"] in labels or type(row["label"]) is not int or row["label"] not in (0, 1):
            raise ValueError("invalid evaluator gold")
        labels[row["id"]] = row["label"]
        hard[row["id"]] = row.get("hard")
    if len({r["id"] for r in rows}) != len(rows) or set(labels) != {r["id"] for r in rows}:
        raise ValueError("invalid evaluation denominator")
    results = []
    elapsed = []
    for row in rows:
        if set(row) != {"id", "supplier", "master"}:
            raise ValueError("evaluator field leaked into runtime input")
        start = time.monotonic()
        value = router.propose(Product(**row["supplier"]), [Product(**row["master"])])
        elapsed.append((time.monotonic() - start) * 1000)
        predicted = (
            {"same_product": 1, "different_product": 0}.get(value[0].outcome) if value else None
        )
        results.append(
            {
                "id": row["id"],
                "prediction": predicted,
                "label": labels[row["id"]],
                "hard": hard[row["id"]],
                "local_routing": value[1] if value else None,
            }
        )
    selected = [r for r in results if r["prediction"] is not None]
    correct = sum(r["prediction"] == r["label"] for r in selected)
    report = {
        "rows": len(rows),
        "local_draft_exits": len(selected),
        "coverage": len(selected) / len(rows),
        "benchmark_agreements": correct,
        "benchmark_disagreements": len(selected) - correct,
        "selected_precision": correct / len(selected) if selected else None,
        "naive_wilson_lower_bound_not_entity_independent": lower_bound(correct, len(selected)),
        "per_hardness": {
            str(h): {
                "rows": sum(r["hard"] == h for r in results),
                "exits": sum(r["hard"] == h for r in selected),
                "disagreements": sum(
                    r["hard"] == h and r["prediction"] != r["label"] for r in selected
                ),
            }
            for h in sorted(set(hard.values()), key=str)
        },
        "selected_labels": dict(Counter(r["label"] for r in selected)),
        "disagreement_ids": [r["id"] for r in selected if r["prediction"] != r["label"]],
        "latency_ms": {
            "p50": sorted(elapsed)[len(elapsed) // 2],
            "p95": sorted(elapsed)[int(len(elapsed) * 0.95)],
        },
        "profile_sha256": router.fingerprint,
        "source_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (profile, inputs, gold)
        },
        "real_model_calls": 0,
        "automatic_acceptance": False,
        "measured_token_savings_claim": False,
    }
    output.mkdir(parents=True)
    (output / "decisions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in results))
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ("profile", "inputs", "gold", "output"):
        p.add_argument("--" + flag, type=Path, required=True)
    args = p.parse_args()
    evaluate(args.profile, args.inputs, args.gold, args.output)
