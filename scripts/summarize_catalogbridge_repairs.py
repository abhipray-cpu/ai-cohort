"""Compare targeted corrective evidence without calling it held-out acceptance."""

import argparse
import hashlib
import json
from pathlib import Path

from catalogbridge_api.corpus import score_pairs


def summarize(cohort, baseline, models, http, guards, output):
    if output.exists():
        raise ValueError("preserve previous evidence")
    labels = {
        r["id"]: r["label"]
        for r in map(json.loads, (cohort / "gold.jsonl").read_text().splitlines())
    }
    report = json.loads((models / "report.json").read_text())
    original = [
        r
        for r in map(json.loads, (baseline / "router.jsonl").read_text().splitlines())
        if r["id"] in labels
    ]
    original.sort(key=lambda r: r["id"])
    router = report["modes"]["router"]
    strong = report["modes"]["strong-only"]
    http_report = json.loads((http / "report.json").read_text())
    result = {
        "verdict": "corrective checks completed; release remains blocked",
        "cohort": json.loads((cohort / "manifest.json").read_text()),
        "prior_router_on_same_cases": {
            "agreement": score_pairs(
                [labels[r["id"]] for r in original], [r["prediction"] for r in original]
            ),
            "tokens": sum(r["metrics"]["tokens"] for r in original),
            "attempts": sum(r["metrics"]["attempts"] for r in original),
        },
        "fresh_modes": report["modes"],
        "fresh_paired_rows": report["paired_rows"],
        "router_token_reduction_vs_fresh_strong": 1 - router["tokens"] / strong["tokens"]
        if strong["tokens"]
        else None,
        "actual_calls": report["actual_calls"] + http_report["live_attempts"],
        "measured_tokens": sum(m["tokens"] for m in report["modes"].values())
        + http_report["live_measured_tokens"],
        "http": http_report,
        "guards": json.loads((guards / "report.json").read_text()),
        "code_unchanged": report["code_unchanged"] and http_report["code_unchanged"],
        "same_runtime_across_campaigns": report["frozen"]["code"]
        == json.loads((http / "frozen.json").read_text())["code"],
        "report_hashes": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [models / "report.json", http / "report.json", guards / "report.json"]
        },
        "limitations": [
            "Deliberately failure-enriched corrective cohort, not independent quality evidence",
            "Repeated real queries are not additional unique examples",
            "Model nondeterminism and cache/timing differences confound historical comparisons",
            "No actual bill, independent adjudication, calibrated early exit or effective identity attestation",
            "No browser, Windows/Cloudflare or buyer acceptance; hard-token mode unsupported",
        ],
    }
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cohort", "baseline", "models", "http", "guards", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    summarize(**vars(parser.parse_args()))
