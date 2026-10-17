"""Deterministic lexical duplicate screening; never supplies labels to the product."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from clausegate_api.common import byte_hash, now


def shingles(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {
        hashlib.sha256(" ".join(words[i : i + 5]).encode()).digest()[:16]
        for i in range(max(0, len(words) - 4))
    }


def similarity(left, right):
    overlap = len(left & right)
    total = len(left) + len(right) - overlap
    return overlap / total if total else float(left == right)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    root, output = Path(args.corpus), Path(args.output)
    if output.exists():
        raise ValueError("New evidence path required")
    raw = root / "evaluator-only.json"
    manifest = json.loads((root / "manifest.json").read_text())
    if byte_hash(raw.read_bytes()) != manifest["normalized_sha256"]:
        raise ValueError("Corpus integrity mismatch")
    rows = json.loads(raw.read_text())
    sets = [shingles(r["document"]["text"]) for r in rows]
    pairs = []
    for i, left in enumerate(sets):
        for j in range(i + 1, len(sets)):
            right = sets[j]
            if min(len(left), len(right)) < 0.7 * max(len(left), len(right)):
                continue
            score = similarity(left, right)
            if score >= 0.7:
                pairs.append(
                    {
                        "ids": [rows[i]["id"], rows[j]["id"]],
                        "splits": [rows[i]["split"], rows[j]["split"]],
                        "jaccard": score,
                    }
                )
    result = {
        "created_at": now(),
        "normalized_sha256": byte_hash(raw.read_bytes()),
        "method": "Lowercase ASCII-alphanumeric tokens, unique contiguous five-token shingles, SHA256 truncated to 128 bits, exact Jaccard >= 0.70; deterministic lexical screening, not semantic/template independence certification",
        "records": len(rows),
        "candidate_pairs": len(rows) * (len(rows) - 1) // 2,
        "near_duplicate_pairs": pairs,
        "cross_split_pairs": sum(x["splits"][0] != x["splits"][1] for x in pairs),
        "label_distribution": {
            split: dict(
                Counter(
                    g["choice"] for r in rows if r["split"] == split for g in r["gold"].values()
                )
            )
            for split in ["train", "dev", "test"]
        },
        "limitation": "No labels used in similarity or model input; high-overlap pairs flagged, not removed or silently reassigned. No held-out model evaluation performed.",
    }
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"near_duplicate_pairs", "label_distribution"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
