"""Run retrieval or opt-in live Codex smoke cases; labels remain provisional."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from contracts.resolvedesk import CaseInput
from resolvedesk_api.store import Store
from resolvedesk_api.worker import run_once

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="var/resolvedesk-evaluation")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Invoke authenticated Codex CLI; may consume service usage",
    )
    parser.add_argument("--case", default="backup-mismatch-17")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "data/resolvedesk/manifests/smoke-cases.json").read_text())
    items = [c for c in manifest["cases"] if c["id"] == args.case]
    if not items:
        raise SystemExit("Unknown case ID")
    item = items[0]
    store = Store(args.data_dir)
    case = store.create_case(CaseInput.model_validate(item["input"]), "evaluation")
    report = {
        "case_id": item["id"],
        "label_status": manifest["label_status"],
        "origin": item["origin"],
        "captured_at": datetime.now(UTC).isoformat(),
        "index_revision": store.index_revision(),
        "retrieval": [
            {"id": p["id"], "url": p["url"], "version": p["version"]}
            for p in store.retrieve(
                case["question"], [case["server_version"]] if case["server_version"] else []
            )
        ],
    }
    if args.live:
        run = store.create_run(case["id"], "evaluation")
        run_once(store)
        report["run"] = store.run(run["id"])
    folder = ROOT / "var/resolvedesk-evaluation/reports"
    folder.mkdir(parents=True, exist_ok=True)
    name = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f") + "-" + item["id"] + ".json"
    (folder / name).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(folder / name),
                "retrieved_passages": len(report["retrieval"]),
                "status": report.get("run", {}).get("status", "retrieval_only"),
                "label_status": manifest["label_status"],
            },
            indent=2,
        )
    )
    if args.live and report["run"]["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
