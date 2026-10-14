"""Opt-in real-corpus, real-Codex acceptance; isolated stores, explicit fault labels."""

import argparse
import hashlib
import json
import platform
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from contracts.resolvedesk import AnswerDraft, ChatCreate, ChatMessage
from resolvedesk_api.ingest import parse_document_details
from resolvedesk_api.network import PostgresSearch
from resolvedesk_api.store import Store
from resolvedesk_api.worker import PROMPT_VERSION, bounded, run_once, validate_draft

ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = ROOT / "data/resolvedesk/manifests/chat-acceptance.json"
SOURCE_PATH = ROOT / "data/resolvedesk/manifests/sources.json"


class SearchOutage:
    configured = True

    def search(self, query):
        raise RuntimeError("Deliberately injected search outage")


def corpus():
    result = []
    for source in json.loads(SOURCE_PATH.read_text())["sources"]:
        raw = (ROOT / source["local_path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError(f"Corpus checksum mismatch: {source['id']}")
        text, sections = parse_document_details(raw.decode("utf-8"))
        result.append((source, text, sections))
    return result


def seed(store, documents):
    for source, text, sections in documents:
        store.import_source(
            title=source["id"],
            url=source["url"],
            version=source["version"],
            text=text,
            sections=sections,
        )


def check_turn(store, run, expected):
    errors = []
    answer = run["answer"]
    if run["status"] == "failed" or not answer:
        return [run["error"] or "No answer"]
    draft, evidence = answer["draft"], answer["evidence"]
    try:
        validate_draft(AnswerDraft.model_validate(draft), evidence)
        search = store.checkpoint(run["id"], "search") or {"evidence": []}
        search_ids = {p["id"] for p in search["evidence"]}
        for passage in evidence:
            store.validate_passage(passage, run["index_revision"], search_ids)
    except ValueError as error:
        errors.append(str(error))
    expectation = expected["expect"]
    if expectation in ("answer", "search-answer"):
        if (
            run["status"] != "draft"
            or not draft["claims"]
            or draft["evidence_state"] != "supported"
        ):
            errors.append(
                f"Expected supported answer, got {run['status']}/{draft['evidence_state']}"
            )
        mapping = {p["id"]: p for p in evidence}
        cited = [
            (mapping[ref["passage_id"]], ref["quote"])
            for claim in draft["claims"]
            for ref in claim["citations"]
            if ref["passage_id"] in mapping
        ]
        if not any(p["url"].endswith(expected["required_page"]) for p, _ in cited):
            errors.append("Expected manual page not cited")
        if expected.get("required_version") and any(
            p["version"] != expected["required_version"] for p, _ in cited
        ):
            errors.append("Wrong citation version")
        if expected.get("allowed_versions") and any(
            p["version"] not in expected["allowed_versions"] for p, _ in cited
        ):
            errors.append("Citation version outside accepted client/server scope")
        if expected.get("required_quote") and not any(
            expected["required_quote"] in q for _, q in cited
        ):
            errors.append("Expected rule missing from citation quotes")
        if expectation == "search-answer":
            if not any(p["origin"] == "search" for p, _ in cited):
                errors.append("Search evidence not cited")
            if not any(
                e["stage"] == "fetch" and e["outcome"] == "succeeded" for e in run["events"]
            ):
                errors.append("No actual page fetched")
            if store.index_revision() != run["index_revision"]:
                errors.append("Search unexpectedly published evidence to index")
            if expected.get("search_after_generation"):
                stages = run["events"]
                first_search = next(
                    (
                        i
                        for i, e in enumerate(stages)
                        if e["stage"] == "search" and e["outcome"] == "started"
                    ),
                    len(stages),
                )
                if not any(
                    e["stage"] == "generation" and e["detail"].startswith("AnswerDraft;")
                    for e in stages[:first_search]
                ):
                    errors.append(
                        "Weak-local test did not generate/assess local evidence before fallback"
                    )
    else:
        if draft["evidence_state"] == "supported":
            errors.append("Unanswerable/ambiguous case falsely marked supported")
        if not draft["questions"] and not draft["limitations"]:
            errors.append("No visible uncertainty explanation")
        if expectation == "clarification" and run["status"] != "needs_clarification":
            errors.append("Ambiguous input did not request clarification")
        if draft["claims"]:
            errors.append("Negative control produced technical claims instead of abstaining")
    return errors


def evaluate(case, root, documents):
    store = Store(root / case["id"])
    if case["mode"] == "indexed":
        seed(store, documents)
    search = SearchOutage() if case["mode"] == "empty-search-outage" else PostgresSearch()
    chat = store.create_chat(
        ChatCreate(title=case["id"], **case.get("environment", {})), "acceptance"
    )
    result = {
        "id": case["id"],
        "origin": case["origin"],
        "mode": case["mode"],
        "turns": [],
        "errors": [],
    }
    previous = []
    for count, expected in enumerate(case["turns"]):
        value = ChatMessage(content=expected["message"], expected_turn_count=count)
        submitted = store.send_message(chat["id"], value, f"turn-{count}", "acceptance")
        duplicate = store.send_message(chat["id"], value, f"turn-{count}", "acceptance")
        assert duplicate["turns"][-1]["id"] == submitted["turns"][-1]["id"]
        started = time.monotonic()
        rid = submitted["turns"][-1]["run"]["id"]
        run_once(store, search=search)
        run = store.run(rid)
        errors = check_turn(store, run, expected)
        current = Store(store.root).chat(chat["id"])
        if [turn["run"]["answer"] for turn in current["turns"][:-1]] != previous:
            errors.append("Historical answers changed")
        previous = [turn["run"]["answer"] for turn in current["turns"]]
        turn = {
            "expected": expected,
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "resolution": store.checkpoint(rid, "chat_resolution"),
            "run": run,
            "errors": errors,
        }
        result["turns"].append(turn)
        result["errors"].extend(errors)
        print(
            json.dumps(
                {
                    "case": case["id"],
                    "turn": count + 1,
                    "status": run["status"],
                    "state": (run["answer"] or {}).get("draft", {}).get("evidence_state"),
                    "seconds": turn["elapsed_seconds"],
                    "errors": errors,
                }
            ),
            flush=True,
        )
    result["passed"] = not result["errors"]
    result["source_snapshots"] = store.sources()
    (root / f"{case['id']}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def retrieval_checks(root, documents):
    store = Store(root / "retrieval")
    seed(store, documents)
    queries = {
        "app-pgdump": "pg_dump newer than its own major version",
        "app-pgrestore": "pg_restore restore custom archive format",
        "app-pg-dumpall": "pg_dumpall global roles tablespaces",
        "pgupgrade": "pg_upgrade check compatibility",
        "libpq-connect": "sslmode verify-full host name",
        "client-authentication": "client authentication",
        "backup": "backup SQL dump file system continuous archiving",
        "upgrading": "upgrading major minor version",
    }
    results = []
    for source, _, _ in documents:
        topic = source["id"].split("-", 1)[1]
        evidence = bounded(store.retrieve(queries[topic], [source["version"]]))
        results.append(
            {
                "source": source["id"],
                "query": queries[topic],
                "expected_url": source["url"],
                "passed": any(p["url"] == source["url"] for p in evidence),
                "retrieved": [
                    {"id": p["id"], "url": p["url"], "version": p["version"]} for p in evidence
                ],
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="Required for real Codex and network execution"
    )
    parser.add_argument("--cases", nargs="+")
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    if not args.live:
        raise SystemExit("Use --live to explicitly run real Codex and official-source search")
    manifest = json.loads(CASE_PATH.read_text())
    cases = [c for c in manifest["cases"] if not args.cases or c["id"] in args.cases]
    if not cases or (args.cases and set(args.cases) - {c["id"] for c in cases}):
        raise SystemExit("Unknown case selection")
    documents = corpus()
    root = ROOT / "var/resolvedesk-acceptance" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    root.mkdir(parents=True)
    report = {
        "captured_at": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "prompt_version": PROMPT_VERSION,
        "label_status": manifest["label_status"],
        "case_manifest_sha256": hashlib.sha256(CASE_PATH.read_bytes()).hexdigest(),
        "source_manifest_sha256": hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(),
        "source_count": len(documents),
        "retrieval": retrieval_checks(root, documents),
        "cases": [],
    }
    destination = root / "report.json"
    print(
        json.dumps(
            {
                "report": str(destination),
                "retrieval_passes": sum(r["passed"] for r in report["retrieval"]),
                "retrieval_total": len(report["retrieval"]),
            }
        ),
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(evaluate, case, root, documents): case for case in cases}
        for future in as_completed(futures):
            try:
                report["cases"].append(future.result())
            except Exception as error:  # noqa: BLE001 - preserve every acceptance failure in report
                report["cases"].append(
                    {
                        "id": futures[future]["id"],
                        "passed": False,
                        "errors": [f"{type(error).__name__}: {error}"],
                    }
                )
            destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    report["passed"] = all(r["passed"] for r in report["retrieval"]) and all(
        c["passed"] for c in report["cases"]
    )
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(destination),
                "passed": report["passed"],
                "case_passes": sum(c["passed"] for c in report["cases"]),
                "case_total": len(cases),
            }
        ),
        flush=True,
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
