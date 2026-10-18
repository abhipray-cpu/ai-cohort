"""Full official split audit and frozen, label-separated real-data cohorts."""

import argparse
import gzip
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from catalogbridge_api.corpus import normalize_pair, safe_members, score_pairs
from catalogbridge_api.matching import conflicts, digest, words
from contracts.catalogbridge import Product


def load_rows(archive, member):
    raw = archive.read(member)
    if member.endswith(".gz"):
        raw = gzip.decompress(raw)
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def normalized_offer(row):
    return Product(
        id=str(row["id"]),
        title=str(row.get("title") or ""),
        brand=str(row.get("brand") or ""),
        description=str(row.get("description") or ""),
        price=str(row.get("price") or ""),
        currency=str(row.get("priceCurrency") or ""),
    )


def normalize_legacy_pair(row):
    label = row.get("label")
    if type(label) is str and label in ("0", "1"):
        row = {**row, "label": int(label)}
    return normalize_pair(row)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def audit(corpus, output):
    if output.exists():
        raise ValueError("preserve prior output")
    output.mkdir(parents=True)
    files, records, pair_labels, tests, primary = {}, {}, defaultdict(set), {}, {}
    invalid = []
    role_ids = defaultdict(set)
    primary_keys = {80: "100un_gs", 50: "050un_gs", 20: "000un_gs"}
    for hard in (20, 50, 80):
        with zipfile.ZipFile(corpus / f"{hard}pair.zip") as archive:
            for info in safe_members(archive):
                name = info.filename
                if not name.endswith(".gz"):
                    continue
                rows = load_rows(archive, name)
                role = "test" if "_gs." in name else "train" if "_train_" in name else "validation"
                gold, predictions = [], []
                normalized = []
                for index, row in enumerate(rows):
                    try:
                        pair = normalize_pair(row)
                        left = Product.model_validate(pair["input"]["supplier"])
                        right = Product.model_validate(pair["input"]["master"])
                    except ValueError as exc:
                        invalid.append(
                            {"member": name, "row": index, "error_type": type(exc).__name__}
                        )
                        gold.append(row.get("label"))
                        predictions.append(None)
                        continue
                    key = "#".join(sorted((left.id, right.id)))
                    pair_labels[key].add(pair["gold"])
                    for record in (left, right):
                        original = records.setdefault(record.id, record.model_dump())
                        if original != record.model_dump():
                            invalid.append(
                                {
                                    "member": name,
                                    "row": index,
                                    "reason": "offer ID content conflict",
                                }
                            )
                        role_ids[(hard, role)].add(record.id)
                    terms, other = words(left.title), words(right.title)
                    prediction = int(
                        not conflicts(left, right)
                        and len(terms & other) / max(1, len(terms | other)) >= 0.8
                    )
                    gold.append(pair["gold"])
                    predictions.append(prediction)
                    normalized.append(
                        {
                            "id": key,
                            **pair["input"],
                            "label": pair["gold"],
                            "source_member": name,
                            "hard": hard,
                            "hard_negative": bool(row.get("is_hard_negative")),
                        }
                    )
                files[f"{hard}pair.zip:{name}"] = {
                    "rows": len(rows),
                    "labels": dict(Counter(gold)),
                    "role": role,
                    "baseline": score_pairs(gold, predictions) if role == "test" else None,
                }
                if role == "test":
                    tests[f"{hard}:{name}"] = normalized
                    if primary_keys[hard] in name:
                        primary.update({r["id"]: r for r in normalized})
        print(
            json.dumps(
                {"audited_hardness": hard, "members": len(files), "unique_offer_ids": len(records)}
            ),
            flush=True,
        )
    legacy = {}
    for path in sorted(corpus.glob("legacy-*.json.gz")):
        rows = [
            json.loads(line)
            for line in gzip.decompress(path.read_bytes()).splitlines()
            if line.strip()
        ]
        ok, errors = [], []
        for index, row in enumerate(rows):
            try:
                ok.append(normalize_legacy_pair(row))
            except ValueError as exc:
                errors.append({"row": index, "error_type": type(exc).__name__})
        legacy[path.name] = {
            "rows": len(rows),
            "labels": dict(Counter(p["gold"] for p in ok)),
            "invalid": errors,
            "unique_pairs": len({digest(p["input"]) for p in ok}),
            "source_string_labels": sum(type(r.get("label")) is str for r in rows),
        }
    multi_files = {}
    multi_offers = {}
    multi_invalid = []
    per_variant_overlap = {}
    for hard in (20, 50, 80):
        with zipfile.ZipFile(corpus / f"{hard}multi.zip") as archive:
            train_ids = set()
            test_ids = {}
            for info in safe_members(archive):
                if not info.filename.endswith(".gz"):
                    continue
                rows = load_rows(archive, info.filename)
                for index, row in enumerate(rows):
                    multi_offers.setdefault(str(row["id"]), row)
                    try:
                        normalized_offer(row)
                    except ValueError as exc:
                        multi_invalid.append(
                            {
                                "member": info.filename,
                                "id": row["id"],
                                "row": index,
                                "error_type": type(exc).__name__,
                            }
                        )
                multi_files[f"{hard}multi.zip:{info.filename}"] = {"rows": len(rows)}
                if "train_large" in info.filename:
                    train_ids = {r["id"] for r in rows}
                if "_gs." in info.filename:
                    test_ids[info.filename] = {r["id"] for r in rows}
            per_variant_overlap[str(hard)] = {
                name: len(ids & train_ids) for name, ids in test_ids.items()
            }
    # Freeze full live target and balanced diagnostic before any model output is seen.
    ordered = sorted(primary.values(), key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())
    live = ordered[:4500]
    diagnostic = []
    for label in (0, 1):
        for hard in (20, 50, 80):
            diagnostic.extend(
                [r for r in ordered if r["label"] == label and r["hard"] == hard][:10]
            )
    for name, cohort in [("live-target", live), ("diagnostic", diagnostic)]:
        destination = output / name
        destination.mkdir()
        (destination / "inputs.jsonl").write_text(
            "".join(
                json.dumps({k: r[k] for k in ("id", "supplier", "master")}) + "\n" for r in cohort
            )
        )
        (destination / "gold.jsonl").write_text(
            "".join(
                json.dumps(
                    {
                        "id": r["id"],
                        "label": r["label"],
                        "source_member": r["source_member"],
                        "hard": r["hard"],
                    }
                )
                + "\n"
                for r in cohort
            )
        )
    # Independent query/gallery records: 800 seen-product queries, 200 withheld-entity queries.
    with zipfile.ZipFile(corpus / "80multi.zip") as archive:
        safe_members(archive)
        names = archive.namelist()
        seen = load_rows(archive, next(n for n in names if "000un_gs" in n))
        unseen = load_rows(archive, next(n for n in names if "100un_gs" in n))
        gallery = load_rows(archive, next(n for n in names if "train_large" in n))
    raw_gallery_count = len(gallery)
    retrieval_exclusions = []

    def eligible(values, role):
        accepted = []
        for row in values:
            try:
                normalized_offer(row)
                accepted.append(row)
            except ValueError as exc:
                retrieval_exclusions.append(
                    {"id": row["id"], "role": role, "error_type": type(exc).__name__}
                )
        return accepted

    gallery = eligible(gallery, "gallery")
    seen = eligible(seen, "seen_query")
    unseen = eligible(unseen, "unseen_query")
    gallery_clusters = {r["cluster_id"] for r in gallery}
    queries = (
        sorted(seen, key=lambda r: digest(r["id"]))[:800]
        + sorted(
            [r for r in unseen if r["cluster_id"] not in gallery_clusters],
            key=lambda r: digest(r["id"]),
        )[:200]
    )
    write_json(output / "gallery.json", [normalized_offer(r).model_dump() for r in gallery])
    write_json(output / "queries.json", [normalized_offer(r).model_dump() for r in queries])
    write_json(
        output / "retrieval-gold.json",
        {
            "gallery": {str(r["id"]): r["cluster_id"] for r in gallery},
            "queries": {str(r["id"]): r["cluster_id"] for r in queries},
        },
    )
    report = {
        "files": files,
        "pair_test_presentations": sum(r["rows"] for r in files.values() if r["role"] == "test"),
        "eligible_pair_test_presentations": sum(len(v) for v in tests.values()),
        "unique_test_pairs": len({r["id"] for v in tests.values() for r in v}),
        "unique_offer_ids_all_pair_splits": len(records),
        "conflicting_pair_labels": sum(len(v) > 1 for v in pair_labels.values()),
        "invalid": invalid,
        "legacy": legacy,
        "multi_files": multi_files,
        "multi_presentations": sum(r["rows"] for r in multi_files.values()),
        "unique_multi_offer_ids": len(multi_offers),
        "multi_invalid_presentations": multi_invalid,
        "per_variant_train_large_test_id_overlap": per_variant_overlap,
        "primary_union_pairs": len(primary),
        "live_target_pairs": len(live),
        "diagnostic_pairs": len(diagnostic),
        "gallery_records": len(gallery),
        "raw_gallery_records": raw_gallery_count,
        "retrieval_exclusions": retrieval_exclusions,
        "query_records": len(queries),
        "query_gallery_id_overlap": len({r["id"] for r in gallery} & {r["id"] for r in queries}),
        "within_hardness_role_overlap": {
            str(h): {
                f"{a}:{b}": len(role_ids[(h, a)] & role_ids[(h, b)])
                for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]
            }
            for h in (20, 50, 80)
        },
        "source_manifest_sha256": hashlib.sha256(
            (corpus / "manifest.json").read_bytes()
        ).hexdigest(),
        "baseline": "Fixed title Jaccard >= .8 plus product conflict checks; not calibrated on test labels",
        "quality_status": "Benchmark labels are not independent adjudication; noisy labels preserved",
    }
    hashes = {
        str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in output.rglob("*")
        if p.is_file()
    }
    report["frozen_artifact_hashes"] = hashes
    write_json(output / "audit.json", report)
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k
                not in (
                    "files",
                    "legacy",
                    "frozen_artifact_hashes",
                    "invalid",
                    "retrieval_exclusions",
                    "multi_files",
                    "multi_invalid_presentations",
                )
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.corpus, args.output)
