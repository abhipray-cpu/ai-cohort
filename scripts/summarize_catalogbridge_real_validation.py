"""Reconcile actual validation ledgers and keep reference pricing separate from bills."""

import argparse
import json
import random
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from catalogbridge_api.store import Store
from contracts.catalogbridge import Usage

RATES = {"gpt-6-luna": (2500000, 250000, 12500000), "gpt-6.1-sol": (50000000, 2500000, 250000000)}


def reconcile(root, mode):
    store = Store(root / mode)
    rows = [json.loads(line) for line in (root / (mode + ".jsonl")).read_text().splitlines()]
    tokens = 0
    attempts = 0
    reference = 0
    routes = Counter()
    overruns = 0
    for row in rows:
        with store.connect() as db:
            batch = db.execute("SELECT spec FROM batches WHERE id=?", (row["batch_id"],)).fetchone()
            spec = json.loads(batch[0])
            ledger = db.execute(
                "SELECT * FROM attempts WHERE batch_id=?", (row["batch_id"],)
            ).fetchall()
            events = db.execute(
                "SELECT * FROM events WHERE batch_id=? ORDER BY seq", (row["batch_id"],)
            ).fetchall()
        total = 0
        for attempt in ledger:
            usage = Usage.model_validate_json(attempt["usage"])
            total += usage.total
            tokens += usage.total
            attempts += 1
            reserve = next(
                e["seq"]
                for e in events
                if e["kind"] == "reserved" and json.loads(e["body"])["attempt"] == attempt["id"]
            )
            settle = next(
                e["seq"]
                for e in events
                if e["kind"] == "settled" and json.loads(e["body"])["attempt"] == attempt["id"]
            )
            assert reserve < settle
            model = spec["strong_model"] if attempt["route"] == "strong" else spec["economy_model"]
            routes[model] += 1
            rate = RATES[model]
            reference += (
                (usage.input_tokens - usage.cached_input_tokens) * rate[0]
                + usage.cached_input_tokens * rate[1]
                + usage.output_tokens * rate[2]
            )
            overruns += usage.total > attempt["reserved"]
        assert total == row["metrics"]["tokens"] and len(ledger) == row["metrics"]["attempts"]
        assert store.analytics("evaluation", row["batch_id"])["journal_consistent"]
    correct = sum(r["prediction"] is not None for r in rows)
    return {
        "rows": len(rows),
        "attempts": attempts,
        "tokens": tokens,
        "requested_model_calls": dict(routes),
        "reservation_overruns": overruns,
        "ledger_reconciles": True,
        "reference_credits": str(Decimal(reference) / Decimal(10**12)),
        "reference_credits_per_input_row": str(Decimal(reference) / Decimal(10**12) / len(rows)),
        "actual_charge": None,
        "nonabstained_proposals": correct,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("models", "http", "stress", "legacy", "audit", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("preserve prior report")
    models = json.loads((args.models / "report.json").read_text())
    http = json.loads((args.http / "report.json").read_text())
    stress = json.loads((args.stress / "report.json").read_text())
    legacy = json.loads((args.legacy / "report.json").read_text())
    audit = json.loads((args.audit / "audit.json").read_text())
    ledgers = {m: reconcile(args.models, m) for m in models["modes"]}
    for mode, ledger in ledgers.items():
        score = models["modes"][mode]["agreement_full_denominator"]
        ledger["reference_credits_per_benchmark_correct_decision"] = (
            str(Decimal(ledger["reference_credits"]) / score["correct"])
            if score["correct"]
            else None
        )
    legacy_ledger = reconcile(args.legacy, "economy-only")
    # Product-cluster bootstrap for retrieval, not a false 800-independent-entities claim.
    truth = json.loads((args.audit / "retrieval-gold.json").read_text())
    tasks = json.loads((args.http / "tasks-before-review.json").read_text())
    gallery_clusters = set(truth["gallery"].values())
    groups = defaultdict(list)
    for task in tasks:
        cluster = truth["queries"][task["source"]["id"]]
        if cluster not in gallery_clusters:
            continue
        groups[cluster].append(
            any(truth["gallery"][r["id"]] == cluster for r in task["result"].get("candidates", []))
        )
    values = list(groups.values())
    rng = random.Random(42)
    samples = []
    for _ in range(2000):
        sampled = [values[rng.randrange(len(values))] for _ in values]
        samples.append(sum(sum(v) for v in sampled) / sum(len(v) for v in sampled))
    samples.sort()
    r = models["modes"]["router"]
    s = models["modes"]["strong-only"]
    ra = r["agreement_full_denominator"]
    sa = s["agreement_full_denominator"]
    reduction = 1 - r["tokens"] / s["tokens"]
    report = {
        "corpus": {
            "pair_presentations": sum(v["rows"] for v in audit["files"].values()),
            "multi_presentations": audit["multi_presentations"],
            "unique_multi_offer_ids": audit["unique_multi_offer_ids"],
            "test_pair_presentations": audit["pair_test_presentations"],
            "unique_test_pairs": audit["unique_test_pairs"],
            "unsupported_pair_presentations": len(audit["invalid"]),
            "unsupported_multi_presentations": len(audit["multi_invalid_presentations"]),
            "legacy_combined_raw_pairs": audit["legacy"]["legacy-all.json.gz"]["rows"],
        },
        "model_campaign": models,
        "ledgers": ledgers,
        "legacy_model_campaign": legacy,
        "legacy_ledger": legacy_ledger,
        "http": http,
        "stress": stress,
        "actual_model_attempts_total": models["actual_calls"]
        + http["live_attempts"]
        + legacy["actual_calls"],
        "measured_tokens_total": sum(v["tokens"] for v in ledgers.values())
        + http["live_measured_tokens"]
        + legacy_ledger["tokens"],
        "retrieval_cluster_bootstrap": {
            "positive_clusters": len(values),
            "resamples": 2000,
            "seed": 42,
            "interval_95_percent": [samples[50], samples[1949]],
        },
        "exploratory_paired_comparison": {
            "token_reduction_vs_strong_only": reduction,
            "agreement_all_rows_delta": ra["accuracy_all_rows"] - sa["accuracy_all_rows"],
            "binary_proposal_coverage_delta": ra["coverage"] - sa["coverage"],
            "meets_20_percent_token_target": reduction >= 0.2,
            "meets_1pp_agreement_proxy_target": ra["accuracy_all_rows"] - sa["accuracy_all_rows"]
            >= -0.01,
            "meets_5pp_coverage_proxy_target": ra["coverage"] - sa["coverage"] >= -0.05,
            "not_final_gate": "Only 60 pairs; benchmark agreement not adjudicated truth; automatic acceptance zero",
        },
        "reference_pricing": {
            "source": "https://learn.chatgpt.com/docs/pricing#token-rates",
            "inspected_date": "2026-10-17",
            "basis": "Post-hoc hypothetical Standard credit-rate scenario keyed to requested model, NOT a bill or quota estimate",
            "microunits_per_million": RATES,
            "actual_charge": None,
        },
        "legacy_scope_note": "Single economy-only profile, not paired; the historical v1 generic paired_rows field is a one-mode intersection, not a model comparison.",
        "release_verdict": "blocked",
        "not_completed": [
            "4500 unique live router pairs",
            "600 paired baseline cases",
            "1200 independently adjudicated cases",
            "calibrated confidence early exit with verified effective identities",
            "browser and actual Windows/Cloudflare acceptance",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in ("model_campaign", "legacy_model_campaign", "http", "stress")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
