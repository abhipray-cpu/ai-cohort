"""Score retained live proposals against evaluator-only labels; never feed gold to AI."""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from clausegate_api.common import byte_hash, now
from clausegate_api.store import Store

LABELS = ["Entailment", "Contradiction", "NotMentioned"]


def merged(intervals):
    result = []
    for left, right in sorted(intervals):
        if result and left <= result[-1][1]:
            result[-1] = (result[-1][0], max(right, result[-1][1]))
        else:
            result.append((left, right))
    return result


def span_counts(predicted, gold):
    p, g = merged(predicted), merged(gold)
    overlap = sum(max(0, min(b, d) - max(a, c)) for a, b in p for c, d in g)
    return overlap, sum(b - a for a, b in p), sum(b - a for a, b in g)


def token_counts(text, predicted, gold):
    tokens = [(m.start(), m.end()) for m in re.finditer(r"\w+|[^\w\s]", text)]

    def covered(ranges):
        return {i for i, (a, b) in enumerate(tokens) if any(a < d and b > c for c, d in ranges)}

    p, g = covered(predicted), covered(gold)
    return len(p & g), len(p), len(g)


def majorities(rows):
    counts = defaultdict(Counter)
    for row in rows:
        if row["split"] == "train":
            for key, value in row["gold"].items():
                counts[key][value["choice"]] += 1
    return {key: max(LABELS, key=lambda label: count[label]) for key, count in counts.items()}


def classification(pairs):
    result = {}
    for label in LABELS:
        tp = sum(g == label and p == label for g, p in pairs)
        fp = sum(g != label and p == label for g, p in pairs)
        fn = sum(g == label and p != label for g, p in pairs)
        precision, recall = tp / (tp + fp) if tp + fp else 0, tp / (tp + fn) if tp + fn else 0
        result[label] = {
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
            "support": sum(g == label for g, _ in pairs),
        }
    return {
        "pairs": len(pairs),
        "correct": sum(g == p for g, p in pairs),
        "missing": sum(p is None for _, p in pairs),
        "per_class": result,
        "macro_f1": sum(x["f1"] for x in result.values()) / 3,
        "confusion": {
            g: {p: sum(a == g and b == p for a, b in pairs) for p in LABELS + [None]}
            for g in LABELS
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    dest, root, corpus = Path(args.output), Path(args.evidence), Path(args.corpus)
    if dest.exists():
        raise ValueError("New scoring artifact required")
    manifest = json.loads((corpus / "manifest.json").read_text())
    raw = corpus / "evaluator-only.json"
    if byte_hash(raw.read_bytes()) != manifest["normalized_sha256"]:
        raise ValueError("Corpus hash mismatch")
    rows = {r["id"]: r for r in json.loads(raw.read_text())}
    report = json.loads((root / "report.json").read_text())
    store = Store(root / "store", ledger_dir=root / "authority")
    pairs, retained, details, baseline_pairs = [], [], [], []
    baseline = majorities(rows.values())
    intersection, predicted_size, gold_size = 0, 0, 0
    token_intersection, token_predicted_size, token_gold_size = 0, 0, 0
    for job in report["live_jobs"]:
        row = rows[job["source_id"]]
        c = store.case("requester", job["case_id"])
        lookup = {f["check_id"]: f for f in c["findings"]}
        for key, expected in row["gold"].items():
            f = lookup.get(key)
            # Provider/coverage failure is not a correct guessed NotMentioned.
            predicted = (
                f["label"]
                if f
                and job["job"]["status"] == "completed"
                and f["assessment"] not in {"unavailable", "incomplete"}
                else None
            )
            pairs.append((expected["choice"], predicted))
            baseline_pairs.append((expected["choice"], baseline[key]))
            if f and f["assessment"] == "supported" and predicted:
                retained.append((expected["choice"], predicted))
            actual_spans = (
                [(e["start"], e["end"]) for e in f.get("evidence", [])] if f and predicted else []
            )
            expected_spans = [row["gold_spans"][i] for i in expected["spans"]]
            i, p, g = span_counts(actual_spans, expected_spans)
            intersection += i
            predicted_size += p
            gold_size += g
            ti, tp, tg = token_counts(row["document"]["text"], actual_spans, expected_spans)
            token_intersection += ti
            token_predicted_size += tp
            token_gold_size += tg
            details.append(
                {
                    "source_id": row["id"],
                    "hypothesis": key,
                    "gold": expected["choice"],
                    "predicted": predicted,
                    "assessment": f["assessment"] if f else "missing",
                    "source_characters": len(row["document"]["text"]),
                }
            )
    precision = intersection / predicted_size if predicted_size else 0
    recall = intersection / gold_size if gold_size else 0
    token_precision = token_intersection / token_predicted_size if token_predicted_size else 0
    token_recall = token_intersection / token_gold_size if token_gold_size else 0
    result = {
        "created_at": now(),
        "evidence_sha256": byte_hash((root / "report.json").read_bytes()),
        "classification": "Development diagnostic from retained original model proposals; not blind held-out, qualified legal review or customer approval truth",
        "documents": len(report["live_jobs"]),
        "semantic": classification(pairs),
        "training_only_per_hypothesis_majority_baseline": classification(baseline_pairs),
        "per_hypothesis": {
            key: classification(
                [(x["gold"], x["predicted"]) for x in details if x["hypothesis"] == key]
            )
            for key in baseline
        },
        "heuristic_retained": classification(retained),
        "heuristic_coverage": len(retained) / len(pairs) if pairs else 0,
        "evidence_character_micro": {
            "counts": {
                "intersection": intersection,
                "predicted": predicted_size,
                "gold": gold_size,
            },
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
            "limitation": "Character-overlap metric, NOT the proposed token/span benchmark or proof of semantic support",
        },
        "evidence_token_micro": {
            "counts": {
                "intersection": token_intersection,
                "predicted": token_predicted_size,
                "gold": token_gold_size,
            },
            "precision": token_precision,
            "recall": token_recall,
            "f1": 2 * token_precision * token_recall / (token_precision + token_recall)
            if token_precision + token_recall
            else 0,
            "method": "Unicode regex \\w+|[^\\w\\s], each document token counted once per hypothesis if its character interval overlaps any cited/gold interval; punctuation retained; NOT the official ContractNLI scorer or semantic sufficiency proof",
            "scorer_sha256": byte_hash(Path(__file__).read_bytes()),
        },
        "pairs": details,
    }
    dest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"pairs", "per_hypothesis"}}, indent=2
        )
    )


if __name__ == "__main__":
    main()
