"""Reconcile fresh benchmark evidence, abstentions and per-stratum quality."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from catalogbridge_api.corpus import score_pairs
from catalogbridge_api.store import Store
from contracts.catalogbridge import Usage

from scripts.run_catalogbridge_real_models import fingerprint


def detail(rows, labels):
    gold = [labels[r["id"]]["label"] for r in rows]
    predicted = [r["prediction"] for r in rows]
    return {
        **score_pairs(gold, predicted),
        "binary_wrong_links": sum(g == 0 and p == 1 for g, p in zip(gold, predicted, strict=True)),
        "binary_wrong_nonmatches": sum(
            g == 1 and p == 0 for g, p in zip(gold, predicted, strict=True)
        ),
        "abstained_positive": sum(
            g == 1 and p is None for g, p in zip(gold, predicted, strict=True)
        ),
        "abstained_negative": sum(
            g == 0 and p is None for g, p in zip(gold, predicted, strict=True)
        ),
    }


def ledger(store, rows, workspace):
    tokens = known = unknown = overruns = 0
    routes, events = Counter(), Counter()
    for row in rows:
        bid = row["batch_id"]
        metrics = store.analytics(workspace, bid)
        assert metrics["journal_consistent"]
        with store.connect() as db:
            attempts = db.execute("SELECT * FROM attempts WHERE batch_id=?", (bid,)).fetchall()
            audit = db.execute(
                "SELECT * FROM events WHERE batch_id=? ORDER BY seq", (bid,)
            ).fetchall()
        subtotal = 0
        for attempt in attempts:
            routes[attempt["route"]] += 1
            if attempt["usage"] is None:
                unknown += 1
                continue
            usage = Usage.model_validate_json(attempt["usage"])
            known += 1
            tokens += usage.total
            subtotal += usage.total
            overruns += usage.total > attempt["reserved"]
            reserve = next(
                e["seq"]
                for e in audit
                if e["kind"] == "reserved" and json.loads(e["body"])["attempt"] == attempt["id"]
            )
            settle = next(
                e["seq"]
                for e in audit
                if e["kind"] == "settled" and json.loads(e["body"])["attempt"] == attempt["id"]
            )
            assert reserve < settle
        assert subtotal == metrics["tokens"] == row["metrics"]["tokens"]
        assert len(attempts) == metrics["attempts"]
        events.update(e["kind"] for e in audit)
    return {
        "known_usage_calls": known,
        "unsettled_or_unknown_attempts": unknown,
        "measured_tokens": tokens,
        "routes": dict(routes),
        "reservation_overruns": overruns,
        "validation_failure_events": events["validation_failure"],
        "partial_retention_events": events["partial_proposal_retained"],
        "calibrated_early_exit_events": events["early_exit"],
        "journals_reconcile": True,
    }


def summarize(cohort, models, http, guards, output, replay=None, probe=None):
    if output.exists():
        raise ValueError("preserve prior evidence")
    model_report = json.loads((models / "report.json").read_text())
    http_report = json.loads((http / "report.json").read_text())
    gold = {
        r["id"]: r for r in map(json.loads, (cohort / "pairs/gold.jsonl").read_text().splitlines())
    }
    manifest = json.loads((cohort / "manifest.json").read_text())
    prior_ids = set()
    prior_retrieval_ids = set()
    for name, expected in manifest["source_sha256"].items():
        path = Path(name)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        if path.name in {"gallery.json", "queries.json"}:
            ids = {r["id"] for r in json.loads(path.read_text())}
            prior_ids.update(ids)
            prior_retrieval_ids.update(ids)
        elif name.endswith(("diagnostic/inputs.jsonl", "legacy-cohort-v1/inputs.jsonl")):
            for row in map(json.loads, path.read_text().splitlines()):
                prior_ids.update(row[side]["id"] for side in ("supplier", "master"))
    fresh_queries = json.loads((cohort / "retrieval/queries.json").read_text())
    query_ids = {r["id"] for r in fresh_queries}
    pairs = list(map(json.loads, (cohort / "pairs/inputs.jsonl").read_text().splitlines()))
    pair_ids = [row[side]["id"] for row in pairs for side in ("supplier", "master")]
    assert len(query_ids) == len(fresh_queries) == 400
    assert len(set(pair_ids)) == len(pair_ids) == 120
    assert not query_ids & prior_retrieval_ids
    assert not set(pair_ids) & (prior_ids | query_ids)
    modes = {}
    for mode in model_report["modes"]:
        rows = list(map(json.loads, (models / f"{mode}.jsonl").read_text().splitlines()))
        assert set(gold) == {r["id"] for r in rows}
        modes[mode] = {
            "quality": detail(rows, gold),
            "by_hardness": {
                str(h): detail([r for r in rows if gold[r["id"]]["hard"] == h], gold)
                for h in (20, 50, 80)
            },
            "accounting": ledger(Store(models / mode), rows, "evaluation"),
            "states": dict(Counter(r["state"] for r in rows)),
            "automatic_acceptances": sum(r["state"] == "recommended_match" for r in rows),
            "identity_unverified_rows": sum(not r["result"].get("effective_model") for r in rows),
        }
    live = json.loads((http / "live-results.json").read_text())
    live_accounting = ledger(Store(http / "product", http / "usage-journal"), live, "default")
    router, strong = modes["router"], modes["strong-only"]
    comparable = not any(m["accounting"]["unsettled_or_unknown_attempts"] for m in modes.values())
    reduction = (
        1 - router["accounting"]["measured_tokens"] / strong["accounting"]["measured_tokens"]
    )
    agreement_delta = (
        router["quality"]["accuracy_all_rows"] - strong["quality"]["accuracy_all_rows"]
    )
    coverage_delta = router["quality"]["coverage"] - strong["quality"]["coverage"]
    frozen = json.loads((http / "frozen.json").read_text())
    code = fingerprint()
    assert code == frozen["code"] == model_report["frozen"]["code"]
    result = {
        "verdict": "release blocked; fresh benchmark checks executed",
        "cohort": manifest,
        "freshness_checks": {
            "source_hashes_verified": True,
            "new_unique_query_ids": len(query_ids),
            "new_unique_pair_offer_ids": len(pair_ids),
            "pair_offer_overlap_with_prior_records_or_new_queries": 0,
            "query_overlap_with_prior_queries_or_gallery": 0,
            "query_overlap_with_prior_pair_diagnostics": len(query_ids & prior_ids),
        },
        "modes": modes,
        "http": http_report,
        "http_live_accounting": live_accounting,
        "guards": json.loads((guards / "report.json").read_text()),
        "known_usage_calls_total": sum(m["accounting"]["known_usage_calls"] for m in modes.values())
        + live_accounting["known_usage_calls"],
        "measured_tokens_total": sum(m["accounting"]["measured_tokens"] for m in modes.values())
        + live_accounting["measured_tokens"],
        "unknown_attempts_total": sum(
            m["accounting"]["unsettled_or_unknown_attempts"] for m in modes.values()
        )
        + live_accounting["unsettled_or_unknown_attempts"],
        "exploratory_paired_comparison": {
            "comparison_eligible": comparable,
            "ineligible_reason": None
            if comparable
            else "Unequal runtime failures and unknown usage; recorded subtotals are not comparable full costs",
            "token_reduction_vs_strong": reduction if comparable else None,
            "partial_recorded_token_ratio_not_savings": reduction,
            "agreement_all_rows_delta": agreement_delta,
            "coverage_delta": coverage_delta,
            "meets_20_percent_token_target": reduction >= 0.2 if comparable else None,
            "meets_1pp_agreement_proxy": agreement_delta >= -0.01 if comparable else None,
            "meets_5pp_coverage_proxy": coverage_delta >= -0.05 if comparable else None,
            "not_final_acceptance": "60 paired benchmark cases, no qualified confidence or independent adjudication",
        },
        "same_unchanged_runtime": True,
        "code": code,
        "report_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [models / "report.json", http / "report.json", guards / "report.json"]
        },
        "actual_charge": None,
        "limits": [
            "No independent human adjudication",
            "No qualified calibration or effective identity",
            "Advisory reserves, not hard token limits",
            "No browser/Windows/edge or buyer acceptance",
            "Not the full 4500/600 live campaign",
            "Offer-disjoint does not establish cluster or provider-pretraining independence",
        ],
    }
    if replay:
        report = json.loads((replay / "report.json").read_text())
        assert report["frozen"]["code"] == code
        replay_modes = {}
        for mode in report["modes"]:
            rows = list(map(json.loads, (replay / f"{mode}.jsonl").read_text().splitlines()))
            assert len(rows) == 12 and all(gold[r["id"]]["hard"] == 80 for r in rows)
            accounting = ledger(Store(replay / mode), rows, "evaluation")
            replay_modes[mode] = {"quality": detail(rows, gold), "accounting": accounting}
            result["known_usage_calls_total"] += accounting["known_usage_calls"]
            result["measured_tokens_total"] += accounting["measured_tokens"]
            result["unknown_attempts_total"] += accounting["unsettled_or_unknown_attempts"]
        clean = not any(
            m["accounting"]["unsettled_or_unknown_attempts"] for m in replay_modes.values()
        )
        replay_reduction = (
            1
            - replay_modes["router"]["accounting"]["measured_tokens"]
            / replay_modes["strong-only"]["accounting"]["measured_tokens"]
        )
        result["availability_replay"] = {
            "not_new_independent_cases": True,
            "paired_rows": report["paired_rows"],
            "modes": replay_modes,
            "usage_complete": clean,
            "token_reduction_vs_strong": replay_reduction if clean else None,
            "meets_20_percent_token_target": replay_reduction >= 0.2 if clean else None,
            "not_final_acceptance": True,
        }
        result["report_sha256"][str(replay / "report.json")] = hashlib.sha256(
            (replay / "report.json").read_bytes()
        ).hexdigest()
    if probe:
        observations = json.loads(probe.read_text())
        result["runtime_probes"] = observations
        for observation in observations["observations"]:
            if observation.get("usage"):
                result["known_usage_calls_total"] += 1
                result["measured_tokens_total"] += Usage.model_validate(observation["usage"]).total
            else:
                result["unknown_attempts_total"] += 1
        result["report_sha256"][str(probe)] = hashlib.sha256(probe.read_bytes()).hexdigest()
    output.write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("code", "http", "cohort")}, indent=2
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cohort", "models", "http", "guards", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--probe", type=Path)
    summarize(**vars(parser.parse_args()))
