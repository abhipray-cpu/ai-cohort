"""Freeze unused WDC cases and new queries before observing model answers."""

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

from scripts.audit_catalogbridge_corpus import load_rows, normalized_offer


def order(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def select_pairs(rows, labels, excluded, per_stratum=10):
    selected, used = [], set(excluded)
    for hard in (20, 50, 80):
        for label in (0, 1):
            count = 0
            for row in sorted(rows, key=lambda r: order(r["id"])):
                gold = labels[row["id"]]
                ids = {row["supplier"]["id"], row["master"]["id"]}
                if gold["hard"] != hard or gold["label"] != label or ids & used:
                    continue
                selected.append(row)
                used.update(ids)
                count += 1
                if count == per_stratum:
                    break
            if count != per_stratum:
                raise ValueError("insufficient unused records for a complete frozen stratum")
    return selected


def prepare(root, output):
    if output.exists():
        raise ValueError("preserve prior evidence")
    original = root / "catalogbridge-real-audit-v1"
    source_paths = [
        original / "gallery.json",
        original / "queries.json",
        original / "retrieval-gold.json",
    ]
    gallery = json.loads(source_paths[0].read_text())
    old_queries = json.loads(source_paths[1].read_text())
    old_gold = json.loads(source_paths[2].read_text())
    old_ids = {r["id"] for r in old_queries} | {r["id"] for r in gallery}
    archive_path = root / "catalogbridge-real-corpus-v2/80multi.zip"
    source_paths.append(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        seen = load_rows(archive, next(n for n in names if "000un_gs" in n))
        unseen = load_rows(archive, next(n for n in names if "100un_gs" in n))
    gallery_clusters = set(old_gold["gallery"].values())
    fresh_seen = [
        r for r in seen if str(r["id"]) not in old_ids and r["cluster_id"] in gallery_clusters
    ]
    fresh_unseen = [
        r for r in unseen if str(r["id"]) not in old_ids and r["cluster_id"] not in gallery_clusters
    ]
    queries = (
        sorted(fresh_seen, key=lambda r: order(r["id"]))[:200]
        + sorted(fresh_unseen, key=lambda r: order(r["id"]))[:200]
    )
    if len(queries) != 400:
        raise ValueError("require exactly 200 fresh seen and 200 fresh unseen queries")
    excluded = old_ids | {str(r["id"]) for r in queries}
    for cohort in (original / "diagnostic", root / "catalogbridge-legacy-cohort-v1"):
        path = cohort / "inputs.jsonl"
        source_paths.append(path)
        for row in map(json.loads, path.read_text().splitlines()):
            excluded.update([row["supplier"]["id"], row["master"]["id"]])
    source = original / "live-target"
    source_paths.extend([source / "inputs.jsonl", source / "gold.jsonl"])
    rows = list(map(json.loads, (source / "inputs.jsonl").read_text().splitlines()))
    labels = {r["id"]: r for r in map(json.loads, (source / "gold.jsonl").read_text().splitlines())}
    pairs = select_pairs(rows, labels, excluded)
    output.mkdir(parents=True)
    (output / "pairs").mkdir()
    (output / "retrieval").mkdir()
    for name, values in [("inputs", pairs), ("gold", [labels[r["id"]] for r in pairs])]:
        (output / "pairs" / f"{name}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in values)
        )
    for name, data in [
        ("gallery", gallery),
        ("queries", [normalized_offer(r).model_dump() for r in queries]),
        (
            "retrieval-gold",
            {
                "gallery": old_gold["gallery"],
                "queries": {str(r["id"]): r["cluster_id"] for r in queries},
            },
        ),
    ]:
        (output / "retrieval" / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False))
    manifest = {
        "purpose": "Fresh publisher-benchmark validation; not independent customer adjudication",
        "selection": "SHA256-ordered unused offers, 10 pairs per hardness/label stratum; no reuse within pairs",
        "pair_cases": len(pairs),
        "strata": dict(
            Counter(f"{labels[r['id']]['hard']}:{labels[r['id']]['label']}" for r in pairs)
        ),
        "pair_offer_overlap_with_prior_records_or_new_queries": 0,
        "new_queries": len(queries),
        "new_query_id_overlap_with_prior_queries_or_gallery": 0,
        "gallery_records_reused": len(gallery),
        "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
        "limitations": [
            "Offer-disjoint is not cluster-disjoint or provider-pretraining-disjoint",
            "Same audited publisher corpus; no model fitting",
            "Benchmark labels are not independent truth",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("var/validation"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.root, args.output)
