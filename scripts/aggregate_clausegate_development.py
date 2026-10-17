"""Combine disjoint same-build real-development cohorts; never average F1 scores."""

import argparse
import json
from pathlib import Path

from clausegate_api.common import byte_hash, now


def merge_pairs(groups):
    values = [p for group in groups for p in group]
    if len({(p["source_id"], p["hypothesis"]) for p in values}) != len(values):
        raise ValueError("Duplicate document/hypothesis predictions cannot be pooled")
    return values


def pool_evidence(groups):
    counts = {key: 0 for key in ["intersection", "predicted", "gold"]}
    for group in groups:
        if any(type(group[k]) is not int or group[k] < 0 for k in counts) or group[
            "intersection"
        ] > min(group["predicted"], group["gold"]):
            raise ValueError("Invalid evidence counts")
        for key in counts:
            counts[key] += group[key]
    i, p, g = counts["intersection"], counts["predicted"], counts["gold"]
    return {
        "counts": counts,
        "precision": i / p if p else 0,
        "recall": i / g if g else 0,
        "f1": 2 * i / (p + g) if p + g else 0,
    }


def main():
    from score_clausegate import classification
    from validate_clausegate import product_hashes

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", action="append", required=True)
    parser.add_argument("--corpus", default="var/validation/clausegate-corpus-v2")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output, corpus = Path(args.output), Path(args.corpus)
    if output.exists():
        raise ValueError("New output required")
    manifest = json.loads((corpus / "manifest.json").read_text())
    normalized = corpus / "evaluator-only.json"
    if byte_hash(normalized.read_bytes()) != manifest["normalized_sha256"]:
        raise ValueError("Corpus hash mismatch")
    rows = {r["id"]: r for r in json.loads(normalized.read_text()) if r["split"] == "dev"}
    scores, reports, sources = [], [], []
    frozen = product_hashes()
    for value in args.score:
        path = Path(value)
        report_path = path.parent / "report.json"
        score, report = json.loads(path.read_text()), json.loads(report_path.read_text())
        if (
            score["evidence_sha256"] != byte_hash(report_path.read_bytes())
            or not report.get("finished_at")
            or not report["product_code_unchanged"]
            or report["product_code_sha256"] != frozen
            or report["corpus_manifest"]["normalized_sha256"] != manifest["normalized_sha256"]
        ):
            raise ValueError("Frozen compatible campaign evidence required")
        if any(j["split"] != "dev" for j in report["live_jobs"]):
            raise ValueError("Only development campaigns can be combined here")
        if score["documents"] != len(report["live_jobs"]):
            raise ValueError("Scored document denominator mismatch")
        scores.append(score)
        reports.append(report)
        sources.append(
            {
                "score": str(path),
                "score_sha256": byte_hash(path.read_bytes()),
                "report_sha256": byte_hash(report_path.read_bytes()),
            }
        )
    scorers = {s["evidence_token_micro"]["scorer_sha256"] for s in scores}
    if len(scorers) != 1:
        raise ValueError("Exact same pinned scorer required")
    pairs = merge_pairs([s["pairs"] for s in scores])
    expected = {(r["id"], k) for r in rows.values() for k in r["gold"]}
    if {(p["source_id"], p["hypothesis"]) for p in pairs} != expected or any(
        p["gold"] != rows[p["source_id"]]["gold"][p["hypothesis"]]["choice"] for p in pairs
    ):
        raise ValueError("Complete official development coverage with unchanged gold required")
    baseline = []
    for score in scores:
        for gold, predictions in score["training_only_per_hypothesis_majority_baseline"][
            "confusion"
        ].items():
            for predicted, count in predictions.items():
                baseline.extend([(gold, None if predicted == "null" else predicted)] * count)
    retained = [
        (p["gold"], p["predicted"])
        for p in pairs
        if p["assessment"] == "supported" and p["predicted"] is not None
    ]
    jobs = [j for r in reports for j in r["live_jobs"]]
    result = {
        "created_at": now(),
        "classification": "Complete official development diagnostic, NOT held-out/independent/qualified legal acceptance; policies and reviewer decisions are fixtures",
        "sources": sources,
        "product_code_sha256": frozen,
        "normalized_sha256": manifest["normalized_sha256"],
        "documents": len(rows),
        "unique_text_hashes": len({r["document"]["text_hash"] for r in rows.values()}),
        "all_development_ids_covered": True,
        "completed_stages": sum(j["job"]["status"] == "completed" for j in jobs),
        "partial_stages": sum(j["job"]["status"] == "partial" for j in jobs),
        "reserved_calls": sum(j["job"]["calls"] for j in jobs),
        "semantic": classification([(p["gold"], p["predicted"]) for p in pairs]),
        "majority_baseline": classification(baseline),
        "supported_subset": classification(retained),
        "supported_coverage": len(retained) / len(pairs),
        "per_hypothesis": {
            k: classification([(p["gold"], p["predicted"]) for p in pairs if p["hypothesis"] == k])
            for k in next(iter(rows.values()))["hypotheses"]
        },
        "evidence_character_micro": pool_evidence(
            [s["evidence_character_micro"]["counts"] for s in scores]
        ),
        "evidence_token_micro": {
            **pool_evidence([s["evidence_token_micro"]["counts"] for s in scores]),
            "scorer_sha256": next(iter(scorers)),
            "method": scores[0]["evidence_token_micro"]["method"],
        },
        "pairs": pairs,
    }
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"pairs", "product_code_sha256", "per_hypothesis"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
