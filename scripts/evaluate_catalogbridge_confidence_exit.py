"""Evaluate, never activate, a frozen no-model exit rule on development data."""

import argparse
import hashlib
import json
import math
import re
import zipfile
from decimal import Decimal
from pathlib import Path

from catalogbridge_api.corpus import normalize_pair, safe_members
from contracts.catalogbridge import Product

from scripts.audit_catalogbridge_corpus import load_rows

RULE_VERSION = "single-title-capacity-same-unit-conflict-v1"


def capacity_conflict(left, right):
    pattern = r"\b(\d+(?:\.\d+)?)\s*(gb|tb)\b"
    a = {(Decimal(n), u) for n, u in re.findall(pattern, left.title.casefold())}
    b = {(Decimal(n), u) for n, u in re.findall(pattern, right.title.casefold())}
    if len(a) != 1 or len(b) != 1:
        return False
    (size_a, unit_a), (size_b, unit_b) = next(iter(a)), next(iter(b))
    return unit_a == unit_b and size_a != size_b


def lower_bound(correct, samples):
    if not samples:
        return 0.0
    z = 1.959963984540054
    p = correct / samples
    return (
        p
        + z * z / (2 * samples)
        - z * math.sqrt(p * (1 - p) / samples + z * z / (4 * samples * samples))
    ) / (1 + z * z / samples)


def evaluate(corpus, output):
    if output.exists():
        raise ValueError("preserve prior evidence")
    roles = {"train_large": {}, "valid_large": {}}
    sources = {}
    invalid = 0
    for hard in (20, 50, 80):
        path = corpus / f"{hard}pair.zip"
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        with zipfile.ZipFile(path) as archive:
            safe_members(archive)
            for role, records in roles.items():
                name = next(n for n in archive.namelist() if role in n)
                for row in load_rows(archive, name):
                    try:
                        pair = normalize_pair(row)
                    except ValueError:
                        invalid += 1
                        continue
                    left = Product(**pair["input"]["supplier"])
                    right = Product(**pair["input"]["master"])
                    key = "#".join(sorted((left.id, right.id)))
                    value = {
                        "id": key,
                        "offer_ids": [left.id, right.id],
                        "label": pair["gold"],
                        "selected": capacity_conflict(left, right),
                    }
                    if key in records and records[key]["label"] != value["label"]:
                        raise ValueError("conflicting development labels")
                    records.setdefault(key, value)
    training_ids = set(roles["train_large"])
    overlap = training_ids & set(roles["valid_large"])
    train_offers = {i for r in roles["train_large"].values() for i in r["offer_ids"]}
    excluded_validation = 0
    report = {}
    for role, values in roles.items():
        rows = []
        used = set(train_offers)
        for row in sorted(
            values.values(), key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest()
        ):
            if role == "valid_large":
                if set(row["offer_ids"]) & used:
                    excluded_validation += 1
                    continue
                used.update(row["offer_ids"])
            rows.append(row)
        selected = [r for r in rows if r["selected"]]
        correct = sum(r["label"] == 0 for r in selected)
        bound = lower_bound(correct, len(selected))
        report[role] = {
            "unique_pairs": len(rows),
            "selected": len(selected),
            "benchmark_correct": correct,
            "benchmark_disagreements": len(selected) - correct,
            "precision_point": correct / len(selected) if selected else None,
            "wilson_95_lower_bound": bound,
            "meets_500_and_99_percent_lower_bound": len(selected) >= 500 and bound >= 0.99,
            "disagreement_ids": [r["id"] for r in selected if r["label"] == 1],
        }
    valid_offers = {i for r in roles["valid_large"].values() for i in r["offer_ids"]}
    result = {
        "rule": RULE_VERSION,
        "frozen_qualification": {"minimum_accepted": 500, "minimum_precision_lower_bound": 0.99},
        "roles": report,
        "source_sha256": sources,
        "overlapping_pairs_excluded_from_qualification": len(overlap),
        "train_validation_offer_overlap": len(train_offers & valid_offers),
        "qualification_selection": "SHA256 order; exclude training offers and repeated offers within qualification",
        "validation_pairs_excluded_for_offer_reuse": excluded_validation,
        "qualification_training_or_internal_offer_overlap": 0,
        "cluster_independence_verified": False,
        "invalid_presentations_excluded": invalid,
        "test_gold_read": False,
        "runtime_policy_changed": False,
        "production_qualified": False,
        "verdict": "No automatic activation; independent adjudication and release checks remain required",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.corpus, args.output)
