"""Read-only cross-phase accounting; do not erase prior unknown liabilities."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from contracts.catalogbridge import Usage

from scripts.run_catalogbridge_real_models import fingerprint, snapshot_runtime


def reconcile(database, journal):
    with sqlite3.connect("file:" + str(database.resolve()) + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        identity = db.execute("SELECT value FROM meta WHERE key='identity'").fetchone()[0]
        rows = db.execute("SELECT * FROM attempts").fetchall()
    with sqlite3.connect("file:" + str(journal.resolve()) + "?mode=ro", uri=True) as db:
        entries = dict(db.execute("SELECT id,body FROM entries WHERE identity=?", (identity,)))
    expected = {
        r["id"]: json.dumps({"state": r["state"], "usage": r["usage"]}, sort_keys=True)
        for r in rows
    }
    assert expected == entries
    return {
        "attempts": len(rows),
        "unknown": sum(r["usage"] is None for r in rows),
        "tokens": sum(Usage.model_validate_json(r["usage"]).total for r in rows if r["usage"]),
        "journals_reconcile": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path("var/validation"))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("preserve prior evidence")
    root = args.root
    phases = {}
    reports = {}
    for name in ("catalogbridge-runtime-hardening-models-v1", "catalogbridge-compact-models-v1"):
        report_path = root / name / "report.json"
        report = json.loads(report_path.read_text())
        assert report["code_unchanged"]
        reports[name] = report
        phases[name] = {
            mode: reconcile(
                root / name / mode / "catalogbridge.sqlite3",
                root / name / f"{mode}-usage/liabilities.sqlite3",
            )
            for mode in report["modes"]
        }
    for name in (
        "catalogbridge-runtime-hardening-http-v1",
        "catalogbridge-compact-http-v1",
        "catalogbridge-final-safety-http-v1",
    ):
        report = json.loads((root / name / "report.json").read_text())
        assert report["code_unchanged"]
        reports[name] = report
        phases[name] = {
            "http": reconcile(
                root / name / "product/catalogbridge.sqlite3",
                root / name / "usage-journal/liabilities.sqlite3",
            )
        }
    name = "catalogbridge-instruction-cost-v1"
    reports[name] = json.loads((root / name / "report.json").read_text())
    phases[name] = {
        f"{style}-{route}": reconcile(
            root / name / f"{style}-{route}/catalogbridge.sqlite3",
            root / name / f"{style}-{route}-usage/liabilities.sqlite3",
        )
        for style in ("legacy", "compact")
        for route in ("economy", "strong")
    }
    current = fingerprint()
    assert current == reports["catalogbridge-final-safety-http-v1"]["frozen"]["code"]
    snapshot = args.output.with_suffix("")
    if snapshot.exists():
        raise ValueError("preserve existing source snapshot")
    snapshot_runtime(snapshot / "runtime-source", current)
    all_ledgers = [ledger for phase in phases.values() for ledger in phase.values()]
    compact = reports["catalogbridge-compact-models-v1"]["modes"]
    legacy_reference = json.loads(
        (root / "catalogbridge-fresh-replay-models-v1/report.json").read_text()
    )["modes"]
    fault = json.loads((root / "catalogbridge-runtime-faults-v3/report.json").read_text())
    assert fault["code"] == current
    for path, expected in fault["historical_database_and_journal_hashes_unchanged"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
    result = {
        "verdict": "runtime safety hardened; release remains blocked",
        "phase_ledgers": phases,
        "new_dispatches": sum(v["attempts"] for v in all_ledgers),
        "new_unknown_attempts": sum(v["unknown"] for v in all_ledgers),
        "new_reported_tokens": sum(v["tokens"] for v in all_ledgers),
        "historical_unknown_attempts_preserved": fault["historical_unknown_attempts_preserved"],
        "historical_reserved_liability_preserved": fault["historical_reserved_liability_preserved"],
        "fault_injection": {
            "real_model_calls": 0,
            "workspace_boundary_calls": fault["provider_boundary_calls_before_workspace_stop"],
            "later_batches_without_dispatch": fault["later_batches_manual_without_dispatch"],
            "campaign_boundary_calls": fault["campaign_boundary_calls_before_global_stop"],
        },
        "current_runtime": current,
        "source_snapshot": str(snapshot),
        "compact_vs_historical_same_case_legacy": {
            mode: {
                "token_reduction": 1 - compact[mode]["tokens"] / legacy_reference[mode]["tokens"],
                "not_causal_or_release_evidence": True,
            }
            for mode in compact
        },
        "compact_router_token_reduction_vs_compact_strong": 1
        - compact["router"]["tokens"] / compact["strong-only"]["tokens"],
        "qualification": json.loads(
            (root / "catalogbridge-exit-qualification-v2.json").read_text()
        ),
        "phase_report_sha256": {
            name: hashlib.sha256((root / name / "report.json").read_bytes()).hexdigest()
            for name in reports
        },
        "limits": [
            "No retrospective root cause established for original missing telemetry",
            "No verified effective identity or empirical confidence profile",
            "Historical replay is not independent quality or causal cost evidence",
            "No full 4500/600 live, browser, Windows/edge or buyer acceptance",
            "No actual bill or hard token enforcement",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ("qualification", "current_runtime", "phase_report_sha256")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
