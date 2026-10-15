"""Resume a failed actual-data validation run with a new bounded budget grant."""

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from contracts.propertybrief import ReportDraft
from propertybrief_api.corpus import FrozenSources, load_corpus
from propertybrief_api.evidence import validate_draft
from propertybrief_api.store import Store
from propertybrief_api.worker import run_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session")
    parser.add_argument("--corpus", default="var/propertybrief-corpus/20261014-final")
    parser.add_argument("--case", action="append", dest="ids", default=[])
    args = parser.parse_args()
    _, payloads = load_corpus(args.corpus)
    mapping = {payload["identity"]["building_id"]: payload for payload in payloads}
    store = Store(args.session)
    with store.connect() as db:
        if db.execute("SELECT 1 FROM runs WHERE status IN ('running','queued')").fetchone():
            raise SystemExit("Wait for the existing session worker to finish before recovery")
        runs = [
            dict(row)
            for row in db.execute(
                "SELECT * FROM runs WHERE status='partial' AND grant=1 ORDER BY created_at"
            )
        ]
    report = {
        "kind": "actual-data recovery validation",
        "cases": [],
        "source_session": str(Path(args.session).resolve()),
        "code_hashes": {},
    }
    root = Path(__file__).resolve().parents[1]
    for path in [
        *root.glob("apps/propertybrief-api/src/**/*.py"),
        *root.glob("packages/agent-core/src/**/*.py"),
        root / "packages/contracts/src/contracts/propertybrief.py",
    ]:
        report["code_hashes"][str(path.relative_to(root))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    output = Path(args.session) / f"recovery-{datetime.now(UTC):%Y%m%dT%H%M%S%f}.json"
    for run in runs:
        identity = json.loads(run["identity_json"])
        bid = identity["building_id"]
        if args.ids and bid not in args.ids:
            continue
        payload = mapping[bid]
        before = store.run(run["id"])
        print(
            f"Resuming real investigation {bid} from {len(before['observations'])} checkpoints",
            flush=True,
        )
        store.resume(run["id"], f"recovery-{time.time_ns()}")
        run_once(store, sources=FrozenSources(payload))
        after = store.run(run["id"])
        draft = ReportDraft.model_validate(after["report"]["payload"]["draft"])
        validate_draft(draft, after["observations"], after["identity"])
        report["cases"].append(
            {
                "building_id": bid,
                "run_id": run["id"],
                "status": after["status"],
                "actions": after["actions"],
                "model_calls": after["model_calls"],
                "new_actions": after["actions"] - before["actions"],
                "new_model_calls": after["model_calls"] - before["model_calls"],
                "findings": len(draft.findings),
                "citations": sum(len(f.evidence) for f in draft.findings),
                "critique": after["report"]["payload"]["critique"],
                "stop_reason": after["stop_reason"],
                "coverage": after["report"]["payload"]["coverage"],
                "structural_citations_valid": True,
            }
        )
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(
            f"Recovery {bid}: {after['status']}; critique {after['report']['payload']['critique']['outcome']}",
            flush=True,
        )
    if not report["cases"]:
        raise SystemExit("No matching recoverable runs")
    print(f"Recovery evidence: {output}")


if __name__ == "__main__":
    main()
