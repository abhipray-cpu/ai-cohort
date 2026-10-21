"""Take a stopped-driver evidence snapshot without overwriting its original report."""

import argparse
import json
from pathlib import Path

from shelfproof_api.core import canonical, digest
from shelfproof_api.runtime import runtime_lock
from shelfproof_api.store import Conflict, Store
from shelfproof_api.validation import summarize


def finalize(run_directory, data_root, actor):
    directory = Path(run_directory)
    original_bytes = (directory / "report.json").read_bytes()
    original = json.loads(original_bytes)
    store = Store(data_root)
    tasks = [p["task"] for p in original["products"]]
    with runtime_lock(store.root) as acquired:
        if not acquired:
            raise Conflict(
                "stop and isolate the participating worker before final evidence snapshot"
            )
        measured = summarize(store, actor, tasks, original["mode"])
        fingerprints = {store.task(actor, task)["snapshot"]["code_fingerprint"] for task in tasks}
        result = {
            **original,
            **measured,
            "code_fingerprint": next(iter(fingerprints)) if len(fingerprints) == 1 else None,
            "evaluated_code_fingerprints": sorted(fingerprints),
            "source_report_sha256": digest(original_bytes),
            "historical_report_preserved": True,
            "snapshot_after_driver_shutdown": True,
            "grant_or_liability_changed": False,
        }
        with (directory / "report-final.json").open("x", encoding="utf-8") as file:
            file.write(canonical(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--actor", required=True)
    args = parser.parse_args()
    result = finalize(args.run, args.data_root, args.actor)
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in {"products", "cohorts", "approval"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
