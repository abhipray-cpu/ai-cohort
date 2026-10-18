"""Freeze 600 unseen-development-entity pairs and a balanced 60-pair live pilot."""

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

from catalogbridge_api.corpus import normalize_pair, safe_members

from scripts.audit_catalogbridge_corpus import load_rows


def freeze(corpus, validation_root, output):
    if output.exists():
        raise ValueError("preserve prior evidence")
    development = set()
    sources = {}
    prior_offers = set()
    invalid = 0
    for path in sorted(validation_root.glob("catalogbridge-*models-v*/*.jsonl")):
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        for line in path.read_text().splitlines():
            if line.strip():
                identity = json.loads(line).get("id", "")
                if "#" in identity:
                    prior_offers.update(identity.split("#"))
    for hard in (20, 50, 80):
        path = corpus / f"{hard}pair.zip"
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        with zipfile.ZipFile(path) as archive:
            safe_members(archive)
            for name in archive.namelist():
                if "train_large" in name or "valid_large" in name:
                    for row in load_rows(archive, name):
                        development.update(
                            str(row[f"cluster_id_{side}"]) for side in ("left", "right")
                        )
    strata = {}
    for hard in (20, 50, 80):
        with zipfile.ZipFile(corpus / f"{hard}pair.zip") as archive:
            member = next(n for n in archive.namelist() if "100un_gs" in n)
            for raw in load_rows(archive, member):
                groups = {str(raw[f"cluster_id_{side}"]) for side in ("left", "right")}
                offers = {str(raw[f"id_{side}"]) for side in ("left", "right")}
                if groups & development or offers & prior_offers:
                    continue
                try:
                    pair = normalize_pair(raw)
                except ValueError:
                    invalid += 1
                    continue
                row = {
                    "id": "#".join(sorted(offers)),
                    **pair["input"],
                    "label": pair["gold"],
                    "hard": hard,
                    "groups": sorted(groups),
                }
                strata.setdefault((hard, pair["gold"]), []).append(row)
    for values in strata.values():
        values.sort(
            key=lambda r: hashlib.sha256(
                ("local-router-comparison-v1:" + r["id"]).encode()
            ).hexdigest()
        )
    selected = []
    used = set()
    positions = Counter()
    for _ in range(100):
        for key in sorted(strata):
            values = strata[key]
            while positions[key] < len(values):
                row = values[positions[key]]
                positions[key] += 1
                offers = {row["supplier"]["id"], row["master"]["id"]}
                if offers & used:
                    continue
                selected.append(row)
                used.update(offers)
                break
            else:
                raise ValueError(f"insufficient fresh offers for full 600-pair cohort: {key}")
    if len(selected) != 600:
        raise ValueError("six complete strata required")
    output.mkdir(parents=True)
    for destination, rows in ((output, selected), (output / "pilot", selected[:60])):
        destination.mkdir(exist_ok=True)
        (destination / "inputs.jsonl").write_text(
            "".join(
                json.dumps({k: r[k] for k in ("id", "supplier", "master")}, ensure_ascii=False)
                + "\n"
                for r in rows
            )
        )
        (destination / "gold.jsonl").write_text(
            "".join(
                json.dumps({k: r[k] for k in ("id", "label", "hard", "groups")}) + "\n"
                for r in rows
            )
        )
    report = {
        "pairs": 600,
        "pilot_pairs": 60,
        "selection": "SHA256-ordered round-robin strata, no model scores or predictions",
        "strata": dict(Counter(f"{r['hard']}:{r['label']}" for r in selected)),
        "pilot_strata": dict(Counter(f"{r['hard']}:{r['label']}" for r in selected[:60])),
        "development_entity_group_overlap": 0,
        "internal_offer_overlap": 0,
        "prior_live_pair_offer_overlap": 0,
        "excluded_prior_offer_ids": len(prior_offers),
        "unique_entity_groups": len({g for r in selected for g in r["groups"]}),
        "invalid_candidate_presentations": invalid,
        "source_sha256": sources,
        "not_a_claim_of_unseen_to_pretraining_or_independent_customer_truth": True,
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "source_sha256"}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--validation-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    freeze(args.corpus, args.validation_root, args.output)
