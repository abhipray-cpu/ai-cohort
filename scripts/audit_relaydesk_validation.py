"""Aggregate distinct real evidence and separate replicas, injected checks and live AI."""

import argparse
import importlib.metadata
import json
import platform
import sys
from collections import Counter
from pathlib import Path

from contracts.relaydesk import ImportBatch
from relaydesk_api.common import digest, file_hash, now
from relaydesk_api.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--evaluation", default="relaydesk-aggressive-evaluation-v1")
    parser.add_argument("--long-evaluation", default="relaydesk-aggressive-long-evaluation-v1")
    parser.add_argument("--continuity", default="relaydesk-aggressive-continuity-v1")
    parser.add_argument("--scale", default="relaydesk-aggressive-scale-v1")
    parser.add_argument("--recovery", default="relaydesk-aggressive-recovery-v1")
    parser.add_argument("--http", default="relaydesk-aggressive-http-v1.json")
    parser.add_argument("--freeze", help="Pre-run product-code hash manifest")
    parser.add_argument("--additional-corpus", action="append", default=[])
    parser.add_argument("--additional-evaluation", action="append", default=[])
    args = parser.parse_args()
    dest = Path(args.output)
    if dest.exists():
        raise ValueError("Do not overwrite prior evidence")
    base = Path("var/validation")
    report = {
        "created_at": now(),
        "corpora": [],
        "runs": [],
        "live_jobs": [],
        "known_injected_failures": [],
        "host": {
            "platform": platform.platform(),
            "python": sys.version,
            "runtime_versions": {
                k: importlib.metadata.version(k)
                for k in ["numpy", "onnxruntime", "tokenizers", "pydantic", "fastapi"]
            },
        },
        "product_code_sha256": {
            str(p): file_hash(p)
            for root in [Path("apps/relaydesk-api/src"), Path("apps/relaydesk-web/src")]
            for p in sorted(root.rglob("*"))
            if p.is_file() and p.suffix in [".py", ".ts", ".tsx", ".css"]
        },
    }
    report["product_code_sha256"]["packages/contracts/src/contracts/relaydesk.py"] = file_hash(
        Path("packages/contracts/src/contracts/relaydesk.py")
    )
    bodies = Counter()
    identities = set()
    threads = set()
    repos = set()
    humans = 0
    bots = 0
    quality = []
    selected = {}
    for name in [
        "relaydesk-aggressive-corpus-v1",
        "relaydesk-aggressive-long-v1",
        *args.additional_corpus,
    ]:
        root = base / name
        r = json.loads((root / "report.json").read_text())
        report["corpora"].append(
            {"path": str(root), "sha256": file_hash(root / "report.json"), "totals": r["totals"]}
        )
        for row in r["threads"]:
            key = (row["repository"], row["issue"])
            batch = ImportBatch.model_validate_json((root / "batches" / row["batch"]).read_text())
            rank = (bool(row["complete"]), row["human_messages"])
            if key not in selected or rank >= selected[key][0]:
                selected[key] = (rank, row, batch, str(root))
    report["deduplication_policy"] = (
        "One capture per repository/issue: prefer complete, then more non-bot records, then later supplied corpus. Source keys counted once. Original variants retained, never summed as new threads."
    )
    for key, (_, row, batch, origin) in selected.items():
        threads.add(key)
        repos.add(row["repository"])
        for message in batch.messages:
            if message.source_key in identities:
                continue
            identities.add(message.source_key)
            if message.bot:
                bots += 1
            else:
                humans += 1
                bodies[digest(message.body)] += 1
        quality.append(
            {
                "repository": row["repository"],
                "issue": row["issue"],
                "human_messages": row["human_messages"],
                "complete": row["complete"],
                "gaps": row["gaps"],
                "selected_capture": origin,
                "body_characters": sum(len(m.body) for m in batch.messages if not m.bot),
                "authors": len({m.author for m in batch.messages if not m.bot}),
            }
        )
    report["distinct_data"] = {
        "threads": len(threads),
        "repositories": len(repos),
        "messages": len(identities),
        "human_messages": humans,
        "bot_messages": bots,
        "unique_nonbot_body_hashes": len(bodies),
        "repeated_nonbot_bodies": sum(v - 1 for v in bodies.values()),
        "complete_threads": sum(q["complete"] for q in quality),
        "partial_threads": sum(not q["complete"] for q in quality),
        "threads_with_at_least_20_nonbot_messages": sum(q["human_messages"] >= 20 for q in quality),
        "zero_nonbot_threads": sum(q["human_messages"] == 0 for q in quality),
        "over_100_nonbot_threads": sum(q["human_messages"] > 100 for q in quality),
    }
    report["thread_quality"] = quality
    for name in [args.evaluation, args.long_evaluation, *args.additional_evaluation]:
        root = base / name
        r = json.loads((root / "report.json").read_text())
        report["runs"].append(
            {
                "path": str(root),
                "sha256": file_hash(root / "report.json"),
                "summary": r.get("summary"),
                "finished_at": r.get("finished_at"),
            }
        )
        store = Store(root / "store", ledger_dir=root / "ledger")
        for job in r["live_jobs"]:
            out = store.output("analyst", job["output_id"]) if job.get("output_id") else None
            payload = out["payload"] if out else {}
            hits = payload.get("recall", {}).get("hits", [])
            self_hits = [
                h["id"]
                for h in hits
                if store.source("analyst", h["evidence"]["source_id"])["source_key"].startswith(
                    "turn:"
                )
            ]
            report["live_jobs"].append(
                {
                    **{
                        k: job[k]
                        for k in [
                            "repository",
                            "issue",
                            "status",
                            "ai_succeeded",
                            "calls",
                            "reason",
                            "seconds",
                        ]
                    },
                    "run": name,
                    "self_turn_hits": len(self_hits),
                    "selected_hits": len(hits),
                    "answer_state": payload.get("answer_state"),
                    "quoted_claims": len(payload.get("claims", [])),
                    "output_id": job.get("output_id"),
                    "validation_failures": [
                        e["detail"] for e in job["events"] if e["kind"] == "validation_failed"
                    ],
                }
            )
        report["known_injected_failures"].extend(r.get("summary", {}).get("failed_checks", []))
    continuity_path = base / args.continuity / "report.json"
    if continuity_path.exists():
        continuity = json.loads(continuity_path.read_text())
        report["continuity"] = continuity
        for job in continuity["jobs"]:
            report["live_jobs"].append(
                {
                    k: job.get(k)
                    for k in [
                        "kind",
                        "status",
                        "ai_succeeded",
                        "reason",
                        "calls",
                        "marker_in_answer",
                        "marker_in_proposed_questions",
                        "answer_state",
                        "quoted_claims",
                    ]
                }
            )
    for key, name in [
        ("relaydesk-aggressive-http-v1.json", args.http),
        ("relaydesk-aggressive-scale-v1/report.json", args.scale + "/report.json"),
        ("relaydesk-aggressive-recovery-v1/report.json", args.recovery + "/report.json"),
    ]:
        p = base / name
        if p.exists():
            report[key] = json.loads(p.read_text())
            report.setdefault("auxiliary_evidence", []).append(
                {"path": str(p), "sha256": file_hash(p)}
            )
    if args.freeze:
        frozen = json.loads(Path(args.freeze).read_text())
        report["code_freeze"] = {
            "path": args.freeze,
            "sha256": file_hash(Path(args.freeze)),
            "started_at": frozen["created_at"],
            "unchanged": frozen["product_code_sha256"] == report["product_code_sha256"],
        }
        if not report["code_freeze"]["unchanged"]:
            raise ValueError("Product code changed during final validation")
    report["summary"] = {
        "data": report["distinct_data"],
        "live_jobs": len(report["live_jobs"]),
        "ai_succeeded": sum(j["ai_succeeded"] for j in report["live_jobs"]),
        "ai_unavailable_or_rejected": sum(not j["ai_succeeded"] for j in report["live_jobs"]),
        "independent_gold": "NOT PERFORMED",
        "browser": "UNAVAILABLE",
        "windows": "UNRUN",
        "release_verdict": "FAIL / NOT PRODUCTION READY",
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
