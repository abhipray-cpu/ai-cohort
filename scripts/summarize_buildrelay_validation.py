"""Re-score frozen outputs without new model calls; publish failures and provenance."""

import argparse
import hashlib
import json
import sqlite3
import zipfile
from collections import Counter
from pathlib import Path

from buildrelay_api.evaluation import normalized, overlap


def summarize(
    capture, prepared, live, native, faults, output, regression=None, github_capture=None
):
    output.mkdir(parents=True, exist_ok=False)
    inventory = json.loads((prepared / "manifest.json").read_text())
    progress = json.loads((live / "progress.json").read_text())
    live_by_id = {r["id"]: r for r in progress}
    records = []
    with zipfile.ZipFile(capture / "logchunks.zip") as archive:
        for record in inventory["records"]:
            case = prepared / record["id"]
            gold = (case / "gold.txt").read_text()
            raw = archive.read("LogChunks/logs/" + record["context"]["original_log_path"]).decode(
                "utf-8", errors="replace"
            )
            evidence = json.loads((case / "evidence.json").read_text())
            anchor = next(
                (normalized(line) for line in gold.splitlines() if len(normalized(line)) >= 12), ""
            )
            row = {
                "id": record["id"],
                "repository": record["context"]["repository"],
                "anchor_in_full": bool(anchor and anchor in normalized(raw)),
                "anchor_in_selected": bool(anchor and anchor in normalized(evidence["text"])),
            }
            if record["id"] in live_by_id:
                row["gold_overlap_v2"] = overlap(live_by_id[record["id"]]["triage"], gold)
            records.append(row)
    scorable = [r for r in records if r["anchor_in_full"]]
    retained = sum(r["anchor_in_selected"] for r in scorable)
    overlap_count = sum(r.get("gold_overlap_v2", False) for r in records)
    native_report = json.loads((native / "report.json").read_text())
    receipts = [r for result in progress for r in result.get("receipts", [])]
    receipts += [
        r for result in native_report["workflow_results"] for r in result.get("receipts", [])
    ]
    usage = [r["usage"] for r in receipts if isinstance(r.get("usage"), dict)]
    import xml.etree.ElementTree as ET

    cases = list(ET.parse(faults).iter("testcase"))
    failed = [
        {"name": c.attrib["name"], "message": c.find("failure").attrib.get("message", "")}
        for c in cases
        if c.find("failure") is not None
    ]
    result = {
        "full_product_accepted": False,
        "selector_manifest": {
            "scorable": inventory["scorable_anchors"],
            "retained": inventory["retained_anchors"],
            "fraction": inventory["gold_anchor_retention"],
        },
        "selector_rescore": {
            "logs": len(records),
            "scorable": len(scorable),
            "retained": retained,
            "fraction": retained / len(scorable),
            "gate_90_percent_passed": retained / len(scorable) >= 0.9,
        },
        "semantic": {
            "selected": len(json.loads((live / "selection.json").read_text())["ids"]),
            "completed": len(progress),
            "statuses": dict(Counter(r["status"] for r in progress)),
            "saved_gold_overlap": sum(
                r.get("lexical_gold_citation_overlap", False) for r in progress
            ),
            "rescored_gold_overlap": overlap_count,
            "rescored_gold_overlap_fraction": overlap_count / len(progress),
            "lexical_gate_90_percent_passed": overlap_count / len(progress) >= 0.9,
            "scoring_method": "Normalize visible SGR fragments symmetrically. Aggregation reuses this campaign's saved outputs; no additional AI calls during aggregation. This is lexical overlap, not causal accuracy.",
            "independent_causal_accuracy": "not_measured",
            "sample_repositories": len({r["context"]["repository"] for r in progress}),
            "sample_languages": len({r["context"]["language"] for r in progress}),
        },
        "native_e2e": {k: v for k, v in native_report.items() if k != "workflow_results"},
        "faults": {
            "cases": len(cases),
            "passed": sum(len(c) == 0 for c in cases),
            "failures": failed,
            "scope": "Real child-process crashes and real broker redelivery on recorded data; controlled proposer/effect stand-in, one-second test leases/ack waits. Broker power loss/restart not tested.",
        },
        "runtime": {
            "calls": len(receipts),
            "all_tools_audited": all(r.get("tools_audited") for r in receipts),
            "usage_receipts": len(usage),
            "unknown_usage_receipts": len(receipts) - len(usage),
            "input_tokens": sum(r.get("input_tokens", 0) for r in usage),
            "cached_input_tokens_subset": sum(r.get("cached_input_tokens", 0) for r in usage),
            "output_tokens": sum(r.get("output_tokens", 0) for r in usage),
        },
        "not_executed": [
            "browser interactions: Browser skill returned no available browser",
            "actual Windows host/reboot/Cloudflare deployment",
            "live GitHub issue writes: no authorized owned test repository supplied",
            "independent causal/next-step review",
        ],
    }
    result["semantic"]["sample_unique_gold_chunks"] = inventory["sample_unique_gold_chunks"]
    if regression:
        regression_cases = list(ET.parse(regression).iter("testcase"))
        result["regression"] = {
            "cases": len(regression_cases),
            "passed": sum(len(c) == 0 for c in regression_cases),
            "failed": [c.attrib["name"] for c in regression_cases if c.find("failure") is not None],
            "skipped": sum(c.find("skipped") is not None for c in regression_cases),
        }
    if github_capture:
        gha = json.loads((github_capture / "manifest.json").read_text())
        expected = [
            json.loads((github_capture / r["id"] / "event.json").read_text())
            for r in gha["records"]
        ]
        with sqlite3.connect(
            f"file:{(native / 'service/buildrelay.sqlite3').resolve().as_posix()}?mode=ro", uri=True
        ) as db:
            actual = [json.loads(row[0]) for row in db.execute("SELECT payload FROM events")]
            counters = dict(
                db.execute(
                    "SELECT action,count(*) FROM audit WHERE action IN ('event_accepted','duplicate_ignored','queue_rejected') GROUP BY action"
                )
            )
            origin = dict(
                db.execute(
                    "SELECT actor,count(*) FROM audit WHERE action='event_accepted' GROUP BY actor"
                )
            )
        canonical = lambda rows: sorted(json.dumps(r, sort_keys=True) for r in rows)
        result["native_e2e"]["all_event_payloads_match_frozen_capture"] = canonical(
            actual
        ) == canonical(expected)
        result["native_e2e"]["ingress_audit_counts"] = counters
        result["native_e2e"]["initial_event_origin_counts"] = origin
    (output / "rescore-records.json").write_text(json.dumps(records, indent=2) + "\n")
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    root = Path(__file__).resolve().parents[1]
    files = [
        *sorted((root / "apps/buildrelay-api/src/buildrelay_api").glob("*.py")),
        *sorted((root / "scripts").glob("*buildrelay*.py")),
    ]
    (output / "current-code-hashes.json").write_text(
        json.dumps(
            {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            indent=2,
        )
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("capture", "prepared", "live", "native", "faults", "output"):
        p.add_argument("--" + name, required=True, type=Path)
    p.add_argument("--regression", type=Path)
    p.add_argument("--github-capture", type=Path)
    a = p.parse_args()
    summarize(
        a.capture, a.prepared, a.live, a.native, a.faults, a.output, a.regression, a.github_capture
    )
