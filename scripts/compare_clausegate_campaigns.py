"""Paired development diagnostics; do not confuse availability with semantic gains."""

import argparse
import json
from pathlib import Path

from clausegate_api.common import byte_hash, now


def paired_changes(before, after):
    left = {(r["source_id"], r["hypothesis"]): r for r in before}
    right = {(r["source_id"], r["hypothesis"]): r for r in after}
    if len(left) != len(before) or len(right) != len(after) or left.keys() != right.keys():
        raise ValueError("Same unique document/hypothesis cohort required")
    if any(left[k]["gold"] != right[k]["gold"] for k in left):
        raise ValueError("Gold annotations changed")
    pairs = [(left[k], right[k]) for k in left]
    correct = lambda r: r["predicted"] == r["gold"]
    return {
        "pairs": len(pairs),
        "corrected": sum(not correct(a) and correct(b) for a, b in pairs),
        "regressed": sum(correct(a) and not correct(b) for a, b in pairs),
        "both_correct": sum(correct(a) and correct(b) for a, b in pairs),
        "both_wrong": sum(not correct(a) and not correct(b) for a, b in pairs),
        "newly_available_pairs": sum(
            a["predicted"] is None and b["predicted"] is not None for a, b in pairs
        ),
        "newly_available_correct": sum(a["predicted"] is None and correct(b) for a, b in pairs),
        "previously_available_pairs": sum(a["predicted"] is not None for a, _ in pairs),
        "previously_available_old_correct": sum(
            a["predicted"] is not None and correct(a) for a, _ in pairs
        ),
        "previously_available_new_correct": sum(
            a["predicted"] is not None and correct(b) for a, b in pairs
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    before_path, after_path, output = Path(args.before), Path(args.after), Path(args.output)
    if output.exists():
        raise ValueError("New evidence output required")
    before, after = json.loads(before_path.read_text()), json.loads(after_path.read_text())
    if (
        before["evidence_token_micro"]["scorer_sha256"]
        != after["evidence_token_micro"]["scorer_sha256"]
    ):
        raise ValueError("Identical pinned scorer required")
    result = {
        "created_at": now(),
        "before_sha256": byte_hash(before_path.read_bytes()),
        "after_sha256": byte_hash(after_path.read_bytes()),
        "classification": "Same-cohort development rerun, not blind, independent, causal or deterministic evidence",
        "paired": paired_changes(before["pairs"], after["pairs"]),
        "before": {
            k: before[k] for k in ["semantic", "heuristic_retained", "evidence_token_micro"]
        },
        "after": {k: after[k] for k in ["semantic", "heuristic_retained", "evidence_token_micro"]},
    }
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["paired"], indent=2))


if __name__ == "__main__":
    main()
