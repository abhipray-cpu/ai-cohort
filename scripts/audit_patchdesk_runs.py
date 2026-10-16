"""Report capture-relative retrieval coverage; these are not adjudicated recall scores."""

import argparse
import json
from collections import Counter
from pathlib import Path

from patchdesk_api.corpus import load_capture


def audit(corpus, evaluation, destination):
    target = Path(destination)
    if target.exists():
        raise ValueError("Use a new run audit directory")
    target.mkdir(parents=True)
    capture = load_capture(corpus)
    lookups = {
        (r["package"], r["version"]): set(r["advisory_ids"]) for r in capture["lookup"]["records"]
    }
    cases = []
    totals = Counter()
    for file in sorted(Path(evaluation).glob("run-*.json")):
        run = json.loads(file.read_text())
        report = run["report"]["payload"]
        inventory = report["inventory"]
        expected = {
            (p["id"], a)
            for p in inventory["packages"]
            if p["source_type"] != "private_or_unknown"
            for a in lookups.get((p["name"], p["version"]), set())
        }
        presented = {
            (f["package_id"], a)
            for f in report["findings"]
            for a in [f["advisory_id"], *f["aliases"]]
        }
        retained = len(expected & presented)
        detailed_ids = {
            identity
            for result in run["results"].values()
            if result.get("capability") == "advisories.detail"
            for record in result.get("records", [])
            for identity in [record.get("id", record.get("ghsa_id"))]
        }
        missing_detail_pairs = sum(a not in detailed_ids for _, a in expected - presented)
        snapshots = {r["snapshot_id"]: r for r in run["results"].values() if r.get("snapshot_id")}
        reference_count = 0

        def walk(value, snapshots=snapshots):
            nonlocal reference_count
            if isinstance(value, dict):
                if {"snapshot_id", "path", "value"}.issubset(value):
                    current = snapshots[value["snapshot_id"]]
                    for part in value["path"]:
                        current = current[part]
                    if current != value["value"]:
                        raise ValueError("Invalid exact evidence reference")
                    reference_count += 1
                else:
                    for child in value.values():
                        walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk({k: report[k] for k in ("findings", "candidates", "conflicts")})
        candidate_ids = [c["id"] for c in report["candidates"]]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Duplicate candidate identity")
        events = run["events"]
        active = peak = 0
        for e in events:
            if e["stage"] == "node_start":
                active += 1
                peak = max(peak, active)
            elif e["stage"] == "node_end":
                active -= 1
        # Real run activity can finish a denied node without node_start; scheduler tests
        # assert actual in-flight bounds, so this value is an observed trace indicator.
        case = {
            "run_id": run["id"],
            "status": run["status"],
            "findings": len(report["findings"]),
            "source_expected_instance_advisory_pairs": len(expected),
            "presented_expected_pairs": retained,
            "capture_relative_coverage": round(retained / len(expected), 4) if expected else None,
            "missing_source_pairs": len(expected - presented),
            "missing_pairs_without_detail": missing_detail_pairs,
            "missing_pairs_with_detail": len(expected - presented) - missing_detail_pairs,
            "gaps": report["gaps"],
            "candidates": len(candidate_ids),
            "exact_references": reference_count,
            "peak_node_trace": peak,
            "actions": run["actions"],
            "model_calls": run["model_calls"],
            "http_attempts": run["http_attempts"],
        }
        cases.append(case)
        for field in (
            "findings",
            "source_expected_instance_advisory_pairs",
            "presented_expected_pairs",
            "missing_source_pairs",
            "missing_pairs_without_detail",
            "missing_pairs_with_detail",
            "candidates",
            "exact_references",
            "actions",
            "model_calls",
            "http_attempts",
        ):
            totals[field] += case[field]
    result = {
        "kind": "capture-relative coverage and evidence integrity, NOT human-adjudicated quality",
        "evaluation": evaluation,
        "cases": cases,
        "totals": dict(totals),
        "status_counts": dict(Counter(c["status"] for c in cases)),
        "limitations": [
            "Source query IDs can be withdrawn, aliased or disputed; not independent truth",
            "Snapshot totals repeat dependencies/advisories; distinct counts reported separately in corpus audit",
            "Uncaptured/unsupported identities are not included in source-relative denominator",
        ],
    }
    (target / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus")
    parser.add_argument("evaluation")
    parser.add_argument("destination")
    args = parser.parse_args()
    audit(args.corpus, args.evaluation, args.destination)
