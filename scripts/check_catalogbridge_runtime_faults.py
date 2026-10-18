"""Real source records with explicit injected runtime failure; never a quality pass."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from catalogbridge_api.model_boundary import ModelResult
from catalogbridge_api.store import Store
from catalogbridge_api.worker import run_once
from contracts.catalogbridge import BatchSpec, Product

from scripts.run_catalogbridge_real_models import campaign, fingerprint


class BrokenBoundary:
    calls = 0

    def generate_pair(self, *_):
        self.calls += 1
        return ModelResult("", None, None, False, 1, 1, {"category": "network", "exit_code": 1})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cohort", type=Path, required=True)
    p.add_argument("--historical", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("preserve evidence")
    args.output.mkdir(parents=True)
    pairs = list(map(json.loads, (args.cohort / "inputs.jsonl").read_text().splitlines()))
    historical_hashes = {}
    unknown = held = 0
    for mode in ("router", "economy-only", "strong-only"):
        database = args.historical / mode / "catalogbridge.sqlite3"
        journal = args.historical / f"{mode}-usage/liabilities.sqlite3"
        for path in (database, journal):
            historical_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        with sqlite3.connect("file:" + str(database.resolve()) + "?mode=ro", uri=True) as db:
            count, reserve = db.execute(
                "SELECT count(*), coalesce(sum(reserved),0) FROM attempts WHERE state='usage_unknown'"
            ).fetchone()
            unknown += count
            held += reserve
    store = Store(args.output / "product")
    provider = BrokenBoundary()
    manual = 0
    for index, row in enumerate(pairs):
        if index == 1:
            store = Store(args.output / "product")
        master = store.import_feed("fault-test", "master", [Product(**row["master"])])
        supplier = store.import_feed("fault-test", "supplier", [Product(**row["supplier"])])
        b = store.create_batch(
            "fault-test", BatchSpec(master_id=master["id"], supplier_id=supplier["id"], egress=True)
        )
        store.start("fault-test", b["id"])
        run_once(store, provider)
        task = store.tasks("fault-test", b["id"])[0]
        manual += task["state"] == "needs_review"
        if index:
            assert store.analytics("fault-test", b["id"])["attempts"] == 0
    assert provider.calls == 1 and manual == len(pairs) - 1
    try:
        store.acknowledge_runtime("fault-test", "owner", "Investigated provider failure")
        raise AssertionError("unknown liability was bypassed")
    except ValueError as exc:
        assert "unknown" in str(exc)
    campaign_provider = BrokenBoundary()
    campaign(
        args.cohort / "inputs.jsonl",
        args.cohort / "gold.jsonl",
        args.output / "campaign",
        12,
        provider=campaign_provider,
    )
    campaign_report = json.loads((args.output / "campaign/report.json").read_text())
    assert campaign_report["runtime_stop"]["open"] and campaign_provider.calls <= 3
    assert all(
        hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
        for path, expected in historical_hashes.items()
    )
    report = {
        "scope": "Real source inputs, explicit injected provider outage; NOT real inference or semantic quality",
        "real_model_calls": 0,
        "real_input_pairs": len(pairs),
        "provider_boundary_calls_before_workspace_stop": provider.calls,
        "later_batches_manual_without_dispatch": manual,
        "restart_preserves_circuit": True,
        "unknown_liability_acknowledgement_refused": True,
        "campaign_boundary_calls_before_global_stop": campaign_provider.calls,
        "historical_unknown_attempts_preserved": unknown,
        "historical_reserved_liability_preserved": held,
        "historical_database_and_journal_hashes_unchanged": historical_hashes,
        "code": fingerprint(),
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
