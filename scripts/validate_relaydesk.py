"""Acquire immutable public issue evidence and exercise real CPU recall/local Codex.

This is engineering validation, NOT independent gold-set acceptance. Never overwrite captures.
"""

import argparse
import json
import secrets
import sys
from pathlib import Path

from agent_core.provider import ProviderTimeoutError
from contracts.relaydesk import Policy, Recall
from relaydesk_api.common import file_hash, now
from relaydesk_api.embeddings import Encoder
from relaydesk_api.ingest import GithubSources, GithubTransport
from relaydesk_api.recall import RecallEngine, index_case
from relaydesk_api.store import Store
from relaydesk_api.worker import run_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--live", action="store_true", help="Explicitly enable local Codex generation"
    )
    parser.add_argument(
        "--capture", help="Replay a previous raw capture directory without upstream requests"
    )
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    raw = root / "raw"
    raw.mkdir()
    transport = GithubTransport()
    captured = []

    def request(url):
        value = transport.request(url)
        path = raw / f"{len(captured):04}.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        captured.append(
            {"url": url, "path": path.name, "sha256": file_hash(path), "observed_at": now()}
        )
        (raw / "manifest.json").write_text(json.dumps(captured, indent=2), encoding="utf-8")
        return value

    if args.capture:
        previous = Path(args.capture)
        rows = json.loads((previous / "manifest.json").read_text())
        lookup = {r["url"]: r for r in rows}

        def request(url):
            row = lookup[url]
            path = previous / row["path"]
            if file_hash(path) != row["sha256"]:
                raise ValueError("Capture hash mismatch")
            return json.loads(path.read_text())

    store = Store(root / "store", ledger_dir=root / "ledger")
    store.add_user("validator", secrets.token_urlsafe(24), admin=True)
    store.add_user("outsider", secrets.token_urlsafe(24))
    account = store.create_account("validator", "Public upstream engineering validation")
    encoder = Encoder("var/models/relaydesk-minilm")
    report = {
        "started_at": now(),
        "scope": "Engineering validation; public issues are NOT customer cases or independent gold labels",
        "encoder": encoder.fingerprint,
        "threads": [],
        "errors": [],
    }
    seeds = [("elastic/elasticsearch", 90216), ("microsoft/vscode", 255749)]
    # Add bounded, comment-rich real issues from varied projects. Read-only public API.
    for repo in ["postgres/postgres", "redis/redis", "pallets/flask", "fastapi/fastapi"]:
        try:
            listing = request(
                f"https://api.github.com/repos/{repo}/issues?state=closed&per_page=30&sort=comments&direction=desc"
            )
            seeds.extend(
                (repo, i["number"])
                for i in [x for x in listing if "pull_request" not in x and x.get("body")][:3]
            )
        except (OSError, ValueError, TimeoutError, KeyError) as error:
            report["errors"].append(
                {"stage": "listing", "repository": repo, "category": type(error).__name__}
            )
    for repo, number in seeds:
        try:
            batch = GithubSources(request=request).fetch(repo, number)
            case = store.create_case("validator", account["id"], f"{repo}#{number}")
            imported = store.import_messages("validator", case["id"], batch)
            duplicate = store.import_messages("validator", case["id"], batch)
            assert duplicate["inserted"] == 0
            indexed = index_case(store, "validator", case["id"], encoder)
            question = (
                "Which failures, workarounds and unresolved investigation steps were reported?"
            )
            recalled = RecallEngine(store, encoder).search(
                "validator", case["id"], Recall(question=question)
            )
            for hit in recalled["hits"]:
                source = store.source("validator", hit["evidence"]["source_id"])
                assert (
                    hit["evidence"]["quote"]
                    == source["body"][hit["evidence"]["start"] : hit["evidence"]["end"]]
                )
            try:
                RecallEngine(store, encoder).search(
                    "outsider", case["id"], Recall(question=question)
                )
                raise AssertionError("Scope leak")
            except PermissionError:
                pass
            row = {
                "repository": repo,
                "issue": number,
                "case_id": case["id"],
                "messages": len(batch.messages),
                "human_messages": sum(not m.bot for m in batch.messages),
                "import": imported,
                "index": indexed,
                "recall_mode": recalled["mode"],
                "hits": len(recalled["hits"]),
                "source_complete": batch.complete,
                "gaps": batch.gaps,
                "checks": [
                    "idempotent replay",
                    "exact quoted spans",
                    "unauthorized recall rejected",
                    "real semantic vectors",
                ],
            }
            if args.live and len(report["threads"]) < 2:
                store.policy(
                    "validator",
                    case["id"],
                    Policy(
                        expected_revision=store.case("validator", case["id"])["revision"],
                        model_egress=True,
                    ),
                )
                conv = store.conversation("validator", case["id"])
                job = store.enqueue(
                    "validator", conv["id"], conv["session"]["id"], question, "live"
                )
                run_once(store, encoder=encoder)
                result = store.job("validator", job["id"])
                row["local_codex"] = {
                    "status": result["status"],
                    "calls": result["model_calls"],
                    "ai_succeeded": result.get("output", {})
                    .get("payload", {})
                    .get("ai_succeeded", False),
                    "reason": result["reason"],
                }
            report["threads"].append(row)
        except (
            OSError,
            ValueError,
            TimeoutError,
            KeyError,
            AssertionError,
            ProviderTimeoutError,
        ) as error:
            report["errors"].append(
                {
                    "stage": "thread",
                    "repository": repo,
                    "issue": number,
                    "category": type(error).__name__,
                    "reason": str(error)[:300],
                }
            )
        (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["finished_at"] = now()
    report["totals"] = {
        "threads": len(report["threads"]),
        "human_messages": sum(t["human_messages"] for t in report["threads"]),
        "errors": len(report["errors"]),
    }
    (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["threads"] else 1


if __name__ == "__main__":
    sys.exit(main())
