"""Freeze a small hardest-stratum replay, not additional independent examples."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cohort", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("preserve existing evidence")
    source = args.cohort / "pairs"
    gold = list(map(json.loads, (source / "gold.jsonl").read_text().splitlines()))
    selected = []
    for label in (0, 1):
        eligible = [r for r in gold if r["hard"] == 80 and r["label"] == label]
        eligible.sort(key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())
        if len(eligible) < 6:
            raise ValueError("need six cases per label")
        selected.extend(eligible[:6])
    ids = {r["id"] for r in selected}
    rows = [
        r
        for r in map(json.loads, (source / "inputs.jsonl").read_text().splitlines())
        if r["id"] in ids
    ]
    args.output.mkdir(parents=True)
    for name, records in [("inputs", rows), ("gold", selected)]:
        (args.output / f"{name}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
        )
    manifest = {
        "purpose": "Availability recheck after failed inference; NOT new independent examples",
        "pairs": 12,
        "hardness": 80,
        "labels": {"0": 6, "1": 6},
        "selection": "SHA256 order per label before replay answers",
        "source_hashes": {
            str(f): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in [source / "inputs.jsonl", source / "gold.jsonl"]
        },
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
