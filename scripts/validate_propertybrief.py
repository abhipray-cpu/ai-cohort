"""Validate captured real records, optionally running the installed Codex planner."""

import argparse
import hashlib
import json
import platform
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from contracts.propertybrief import PropertyInput
from propertybrief_api.corpus import FrozenSources, load_corpus
from propertybrief_api.evidence import validate_draft
from propertybrief_api.sources import REQUIRED
from propertybrief_api.store import Store
from propertybrief_api.worker import run_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="var/propertybrief-corpus/20261014-final")
    parser.add_argument(
        "--live", action="store_true", help="Consumes authenticated Codex service usage"
    )
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--session")
    args = parser.parse_args()
    manifest, cases = load_corpus(args.corpus)
    selected = (
        cases
        if args.all
        else [
            case
            for case in cases
            if case["identity"]["building_id"] in (args.case_ids or ["375411"])
        ]
    )
    if not selected:
        raise SystemExit("No matching captured cases")
    session = Path(
        args.session or f"var/propertybrief-evaluation/{datetime.now(UTC):%Y%m%dT%H%M%S%f}"
    )
    if session.exists():
        raise SystemExit("Use a new validation session directory")
    store = Store(session)
    report = {
        "kind": "actual-data functional validation",
        "live_codex": args.live,
        "corpus": str(Path(args.corpus).resolve()),
        "source_created_at": manifest["created_at"],
        "platform": platform.platform(),
        "cases": [],
        "quality_gold": "not yet adjudicated",
        "commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip(),
    }
    root = Path(__file__).resolve().parents[1]
    files = [
        *root.glob("apps/propertybrief-api/src/**/*.py"),
        *root.glob("packages/agent-core/src/**/*.py"),
        root / "packages/contracts/src/contracts/propertybrief.py",
        Path(__file__).resolve(),
    ]
    report["code_hashes"] = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files
    }
    for payload in selected:
        identity = payload["identity"]
        count = sum(value["count"] for value in payload["observations"].values())
        result = {
            "building_id": identity["building_id"],
            "captured_records": count,
            "all_source_hashes_valid": True,
            "acquisition_coverage": {
                key: value["completeness"] for key, value in payload["observations"].items()
            },
        }
        if args.live:
            borough = {
                "1": "Manhattan",
                "2": "Bronx",
                "3": "Brooklyn",
                "4": "Queens",
                "5": "Staten Island",
            }[identity["bbl"][0]]
            item = store.create_case(
                PropertyInput(address=identity["address"], borough=borough), "evaluation"
            )
            store.save_candidates(item["id"], [identity])
            store.confirm_identity(item["id"], identity["id"], 1, "evaluation")
            run = store.enqueue(
                item["id"],
                "Investigate the captured records and prepare evidence-based questions for seller, inspector and attorney. Check all required sources, adapt to contradictions, and qualify missing evidence.",
                "actual-data",
                "evaluation",
            )
            started = time.monotonic()
            print(
                f"Starting actual Codex investigation: building {identity['building_id']}",
                flush=True,
            )
            run_once(store, sources=FrozenSources(payload))
            completed = store.run(run["id"])
            from contracts.propertybrief import ReportDraft

            draft = ReportDraft.model_validate(completed["report"]["payload"]["draft"])
            validate_draft(draft, completed["observations"], completed["identity"])
            result.update(
                status=completed["status"],
                run_id=run["id"],
                actions=completed["actions"],
                model_calls=completed["model_calls"],
                seconds=round(time.monotonic() - started, 2),
                finding_count=len(draft.findings),
                citation_count=sum(len(f.evidence) for f in draft.findings),
                structural_citations_valid=True,
                critique=completed["report"]["payload"]["critique"],
                checked_sources=list(completed["observations"]),
                all_sources_attempted=set(REQUIRED).issubset(completed["observations"]),
                stop_reason=completed["stop_reason"],
            )
            (session / f"run-{run['id']}.json").write_text(
                json.dumps(completed, indent=2), encoding="utf-8"
            )
            print(
                f"Finished {identity['building_id']}: {completed['status']}; {completed['actions']} actions; {completed['model_calls']} calls",
                flush=True,
            )
        report["cases"].append(result)
        (session / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Evidence saved at {session / 'report.json'}")


if __name__ == "__main__":
    main()
