"""Actual project evidence validation, with opt-in installed Codex and live source calls."""

import argparse
import hashlib
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

from contracts.patchdesk import InputUpload, ProjectCreate, ProjectPolicy
from patchdesk_api.common import digest
from patchdesk_api.corpus import FrozenSources, load_capture
from patchdesk_api.reconcile import validate_references
from patchdesk_api.store import Store
from patchdesk_api.worker import run_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="var/patchdesk-corpus/20261015-expanded")
    parser.add_argument(
        "--live", action="store_true", help="Actual Codex; consumes authenticated usage"
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="Acquire fresh official source data rather than frozen replay",
    )
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--split", choices=("development", "calibration", "held_out"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repository", default="postmanlabs/newman")
    parser.add_argument("--session")
    args = parser.parse_args()
    payload = load_capture(args.corpus)
    session = Path(args.session or f"var/patchdesk-evaluation/{datetime.now(UTC):%Y%m%dT%H%M%S%f}")
    if session.exists():
        raise SystemExit("Use a new evaluation session")
    store = Store(session)
    store.add_user("evaluation", "evaluation-local-only-password", admin=True)
    root = Path(__file__).resolve().parents[1]
    paths = [
        *root.glob("apps/patchdesk-api/src/**/*.py"),
        root / "packages/contracts/src/contracts/patchdesk.py",
        Path(__file__).resolve(),
    ]
    report = {
        "kind": "actual-public-data functional validation",
        "corpus_hash": digest(payload),
        "live_codex": args.live,
        "live_sources": args.network,
        "platform": platform.platform(),
        "quality_gold": "not independently adjudicated",
        "code_hashes": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
        },
        "cases": [],
    }
    selected = (
        payload["projects"]
        if args.all
        else [next(p for p in payload["projects"] if p["repository"] == args.repository)]
    )
    if args.split:
        selected = [p for p in selected if p.get("split") == args.split]
    if args.limit is not None:
        selected = selected[: args.limit]
    if not selected:
        raise SystemExit("No matching real-data cases; refusing an empty validation pass")
    for captured in selected:
        project = store.create_project(
            "evaluation",
            ProjectCreate(name=captured["repository"], client="Public-data evaluation"),
        )
        artifact = store.import_input(
            "evaluation",
            project["id"],
            InputUpload(
                manifest=captured["manifest"],
                lockfile=captured["lockfile"],
                origin=captured["repository"],
                commit=captured["commit"],
            ),
        )
        names = sorted(
            {
                p["name"]
                for p in artifact["payload"]["inventory"]["packages"]
                if p["source_type"] != "private_or_unknown"
            }
        )
        store.update_policy(
            "evaluation",
            project["id"],
            ProjectPolicy(expected_revision=1, public_packages=names, model_egress=args.live),
        )
        run = store.enqueue(
            "evaluation",
            project["id"],
            "Prepare an evidence-backed maintenance plan. Preserve source gaps and conflicting advice; upgrades need separate compatibility verification.",
            "evaluation",
            {},
        )
        print(
            f"Starting {captured['repository']}@{captured['ref']} with {len(names)} approved public names",
            flush=True,
        )
        started = time.monotonic()
        run_once(store, sources=None if args.network else FrozenSources(payload))
        completed = store.run("evaluation", run["id"])
        result = completed["report"]["payload"]
        snapshots = {
            r["snapshot_id"]: store._object(r["snapshot_id"])["payload"]
            for r in completed["results"].values()
            if r.get("snapshot_id")
        }
        validate_references(result, snapshots)
        summary = {
            "repository": captured["repository"],
            "split": captured.get("split", "unassigned"),
            "ref": captured["ref"],
            "commit": captured["commit"],
            "run_id": run["id"],
            "status": completed["status"],
            "seconds": round(time.monotonic() - started, 2),
            "actions": completed["actions"],
            "model_calls": completed["model_calls"],
            "http_attempts": completed["http_attempts"],
            "findings": len(result["findings"]),
            "conflicts": len(result["conflicts"]),
            "candidates": len(result["candidates"]),
            "gaps": len(result["gaps"]),
            "structural_references_valid": True,
            "exact_reference_count": sum(
                len(item.get("evidence", []))
                for item in [*result["findings"], *result["candidates"]]
            ),
            "node_outcomes": {
                outcome: sum(v["outcome"] == outcome for v in completed["results"].values())
                for outcome in sorted({v["outcome"] for v in completed["results"].values()})
            },
            "stop_reason": completed["stop_reason"],
        }
        report["cases"].append(summary)
        (session / f"run-{run['id']}.json").write_text(
            json.dumps(completed, indent=2), encoding="utf-8"
        )
        (session / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(summary), flush=True)
    print(f"Evidence: {session / 'report.json'}")


if __name__ == "__main__":
    main()
