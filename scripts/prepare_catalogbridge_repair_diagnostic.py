"""Freeze targeted real-source regression cases; never feed gold to routing."""

import argparse
import hashlib
import json
from pathlib import Path


def prepare(cohort, baseline, output):
    if output.exists():
        raise ValueError("preserve previous evidence")
    rows = [json.loads(line) for line in (cohort / "inputs.jsonl").read_text().splitlines()]
    gold = [json.loads(line) for line in (cohort / "gold.jsonl").read_text().splitlines()]
    router = [json.loads(line) for line in (baseline / "router.jsonl").read_text().splitlines()]
    key = lambda value: hashlib.sha256(value.encode()).hexdigest()
    failures = sorted({r["id"] for r in router if r["prediction"] is None}, key=key)
    controls = sorted({r["id"] for r in rows} - set(failures), key=key)
    selected = set(failures[:12] + controls[:8])
    output.mkdir(parents=True)
    for name, records in [("inputs", rows), ("gold", gold)]:
        (output / f"{name}.jsonl").write_text(
            "".join(
                json.dumps(r, ensure_ascii=False) + "\n" for r in records if r["id"] in selected
            )
        )
    manifest = {
        "purpose": "Corrective regression, NOT independent held-out quality acceptance",
        "selection": "12 prior router abstentions and 8 non-abstention controls, SHA256 order",
        "selected_ids": sorted(selected),
        "source_hashes": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [cohort / "inputs.jsonl", cohort / "gold.jsonl", baseline / "router.jsonl"]
        },
        "cases": len(selected),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.cohort, args.baseline, args.output)
