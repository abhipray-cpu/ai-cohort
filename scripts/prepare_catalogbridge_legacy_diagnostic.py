"""Freeze a small independent legacy-gold smoke cohort; not full legacy evaluation."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from audit_catalogbridge_corpus import normalize_legacy_pair


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("preserve prior evidence")
    selected = []
    for category in ("computers", "cameras", "watches", "shoes"):
        rows = [
            json.loads(line)
            for line in gzip.decompress(
                (args.corpus / f"legacy-{category}.json.gz").read_bytes()
            ).splitlines()
        ]
        for label in ("0", "1"):
            eligible = []
            for row in rows:
                if row["label"] != label:
                    continue
                try:
                    pair = normalize_legacy_pair(row)
                except ValueError:
                    continue
                key = hashlib.sha256(json.dumps(pair["input"], sort_keys=True).encode()).hexdigest()
                eligible.append(
                    {"id": key, **pair["input"], "gold": pair["gold"], "category": category}
                )
            selected.extend(sorted(eligible, key=lambda r: r["id"])[:2])
    assert len(selected) == 16
    args.output.mkdir(parents=True)
    (args.output / "inputs.jsonl").write_text(
        "".join(
            json.dumps({k: r[k] for k in ("id", "supplier", "master")}) + "\n" for r in selected
        )
    )
    (args.output / "gold.jsonl").write_text(
        "".join(
            json.dumps({"id": r["id"], "label": r["gold"], "category": r["category"]}) + "\n"
            for r in selected
        )
    )
    print(
        json.dumps(
            {
                "real_legacy_pairs": len(selected),
                "labels": {"same": 8, "different": 8},
                "categories": 4,
            }
        )
    )


if __name__ == "__main__":
    main()
