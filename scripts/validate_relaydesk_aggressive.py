"""Real-corpus diagnostics, controlled fault injection and load probes, NOT independent gold.

Only fresh isolated stores are modified. Failures are retained and exit status is
nonzero when engineering invariants fail. Extractive probes are explicitly not
natural-language correctness/entailment scores.
"""

import argparse
import json
import re
import secrets
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from agent_core.provider import ProviderTimeoutError, StructuredGeneration
from contracts.relaydesk import ImportBatch, Policy, Recall
from relaydesk_api.backup import backup, restore
from relaydesk_api.common import file_hash, now
from relaydesk_api.context import compress
from relaydesk_api.embeddings import Encoder
from relaydesk_api.recall import RecallEngine, index_case
from relaydesk_api.store import Store
from relaydesk_api.worker import run_once


class FakeProvider:
    """Explicitly injected deterministic provider; never counted as live AI evidence."""

    def __init__(self, values, callback=None):
        self.values, self.callback = iter(values), callback

    def generate(self, **kwargs):
        value = next(self.values)
        if self.callback:
            self.callback(kwargs)
        if isinstance(value, Exception):
            raise value
        return StructuredGeneration(
            text=value if isinstance(value, str) else json.dumps(value),
            exit_code=0,
            elapsed_ms=1,
            tools_audited=True,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--live-jobs", type=int, default=0)
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    corpus = Path(args.corpus)
    frozen = json.loads((corpus / "report.json").read_text())
    store = Store(root / "store", ledger_dir=root / "ledger")
    for actor in ["analyst", "reviewer", "outsider"]:
        store.add_user(actor, secrets.token_urlsafe(24), admin=actor == "analyst")
    account = store.create_account("analyst", "Frozen public issue evaluation")
    encoder = Encoder("var/models/relaydesk-minilm")
    report = {
        "started_at": now(),
        "classification": "engineering diagnostics and labelled injected failures; not independent gold",
        "corpus_sha256": file_hash(corpus / "report.json"),
        "model": encoder.fingerprint,
        "checks": [],
        "cases": [],
        "queries": [],
        "live_jobs": [],
        "latency_ms": [],
        "frozen_selection": frozen["selection"],
    }

    def checkpoint():
        (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    def check(name, condition, detail=None):
        report["checks"].append({"name": name, "passed": bool(condition), "detail": detail})
        if not condition:
            print("FAIL:", name, flush=True)

    def exercise(name, operation):
        try:
            operation()
        except Exception as error:  # noqa: BLE001 — validation runner retains and continues independent checks
            check(name, False, {"category": type(error).__name__, "reason": str(error)[:250]})

    cases = []
    for row in frozen["threads"]:
        path = corpus / "batches" / row["batch"]
        if file_hash(path) != row["sha256"]:
            raise ValueError("Frozen batch hash mismatch")
        batch = ImportBatch.model_validate_json(path.read_text())
        case = store.create_case("analyst", account["id"], f"{row['repository']}#{row['issue']}")
        cid = case["id"]
        cases.append((case, row, batch))
        imported = store.import_messages("analyst", cid, batch)
        check(
            "import non-bot count matches",
            imported["inserted"] == sum(not m.bot for m in batch.messages),
            cid,
        )
        check(
            "replay deduplicates",
            store.import_messages("analyst", cid, batch)["inserted"] == 0,
            cid,
        )
        started = time.perf_counter()
        indexed = index_case(store, "analyst", cid, encoder)
        memories = store.memories("analyst", cid)
        check("all imported episodes indexed", indexed["saved"] == len(memories), cid)
        check(
            "restart retains sources and vector namespace",
            len(Store(store.root, ledger_dir=store.ledger_dir).memories("analyst", cid))
            == len(memories),
            cid,
        )
        summary = compress(memories, 6000)
        selected = [m for group in summary["groups"].values() for m in group]
        check(
            "compression full denominator",
            summary["coverage"]["total"] == len(memories)
            and summary["coverage"]["selected"] + summary["coverage"]["omitted"] == len(memories),
            cid,
        )
        check(
            "compression does not rewrite selected memory text",
            all(
                s["body"] == next(m["body"] for m in memories if m["id"] == s["id"])
                for s in selected
            ),
            cid,
        )
        check(
            "compression omission is explicit",
            not summary["coverage"]["omitted"] or summary["status"] == "partial",
            cid,
        )
        report["cases"].append(
            {
                **row,
                "case_id": cid,
                "index_seconds": time.perf_counter() - started,
                "compression": {
                    "coverage": summary["coverage"],
                    "serialized_characters": len(json.dumps(summary)),
                    "raw_characters": sum(len(m["body"]) for m in memories),
                },
            }
        )

        # Six extractive probes distributed across the history, including older-than-buffer records.
        positions = sorted({int((len(memories) - 1) * p / 5) for p in range(6)}) if memories else []
        questions = [
            ("natural_diagnostic", q, None)
            for q in [
                "What workarounds were attempted and what outcome was reported?",
                "Which software versions and environment constraints were reported?",
                "Which questions or next steps remain unresolved?",
                "What changed between earlier and later reports?",
            ]
        ]
        for position in positions:
            target = memories[position]
            words = re.findall(r"\S+", target["body"])
            if len(words) < 8:
                continue
            start = max(0, len(words) // 3 - 6)
            phrase = " ".join(words[start : start + 12])
            questions.append(
                ("extractive_source_probe", "Locate the report containing: " + phrase, target["id"])
            )
        for classification, question, target in questions:
            started = time.perf_counter()
            result = RecallEngine(store, encoder).search(
                "analyst", cid, Recall(question=question, limit=10)
            )
            elapsed = (time.perf_counter() - started) * 1000
            report["latency_ms"].append(elapsed)
            valid = True
            for hit in result["hits"]:
                source = store.source("analyst", hit["evidence"]["source_id"])
                valid = (
                    valid
                    and source["case_id"] == cid
                    and source["body"][hit["evidence"]["start"] : hit["evidence"]["end"]]
                    == hit["evidence"]["quote"]
                )
            check(
                "authorized exact recall spans",
                valid,
                {"case_id": cid, "classification": classification},
            )
            lexical = RecallEngine(store).search(
                "analyst", cid, Recall(question=question, limit=10)
            )
            # Vector-only reference ranking over the identical authorized candidate set.
            query = encoder.query(question)
            ranked = []
            with store.connect() as db:
                for m in memories:
                    vectors = db.execute(
                        "SELECT value FROM vectors WHERE memory_id=? AND revision=? AND model=?",
                        (m["id"], m["revision"], encoder.fingerprint),
                    ).fetchall()
                    if vectors:
                        ranked.append(
                            (
                                max(
                                    float(np.dot(query, np.frombuffer(v[0], dtype=np.float32)))
                                    for v in vectors
                                ),
                                m["id"],
                            )
                        )
            vector_ids = [mid for _, mid in sorted(ranked, reverse=True)[:10]]
            report["queries"].append(
                {
                    "case_id": cid,
                    "classification": classification,
                    "question": question,
                    "required_memory_id": target,
                    "hybrid_ids": [h["id"] for h in result["hits"]],
                    "lexical_ids": [h["id"] for h in lexical["hits"]],
                    "vector_only_ids": vector_ids,
                    "latency_ms": elapsed,
                }
            )
        for percentile in [0, 25, 50, 75]:
            if not memories:
                continue
            cutoff = memories[int((len(memories) - 1) * percentile / 100)]["available_at"]
            result = RecallEngine(store, encoder).search(
                "analyst",
                cid,
                Recall(question="failure workaround environment", as_of=cutoff, limit=30),
            )
            check(
                "historical recall contains no later source",
                all(
                    h["available_at"] <= cutoff
                    and store.source("analyst", h["evidence"]["source_id"])["updated_at"] <= cutoff
                    for h in result["hits"]
                ),
                {"case_id": cid, "cutoff": cutoff},
            )
        try:
            RecallEngine(store, encoder).search("outsider", cid, Recall(question="failure"))
        except PermissionError:
            check("outsider recall denied", True, cid)
        else:
            check("outsider recall denied", False, cid)
        checkpoint()
        print("Evaluated", row["repository"], row["issue"], len(memories), "messages", flush=True)

    # Controlled fault suite reuses real source payloads; every mutation is labelled.
    _first_case, _first_row, first_batch = cases[0]

    def fixture(name, egress=True):
        case = store.create_case("analyst", account["id"], "INJECTED " + name)
        store.import_messages("analyst", case["id"], first_batch)
        store.policy(
            "analyst",
            case["id"],
            Policy(
                expected_revision=store.case("analyst", case["id"])["revision"], model_egress=egress
            ),
        )
        conv = store.conversation("analyst", case["id"])
        job = store.enqueue(
            "analyst",
            conv["id"],
            conv["session"]["id"],
            "Which failures and unresolved actions were reported?",
            "injected",
        )
        return case, conv, job

    def malformed():
        case, _, job = fixture("malformed JSON repair")
        run_once(store, encoder=encoder, provider=FakeProvider(["{bad", "{still bad"]))
        result = store.job("analyst", job["id"])
        events = store.changes("analyst", case["id"])["events"]
        check(
            "invalid JSON repair bounded and audited",
            result["model_calls"] == 2
            and result["status"] == "partial"
            and sum(e["kind"] == "validation_failed" for e in events) == 2,
        )

    exercise("malformed provider test executes", malformed)

    def late_timeout():
        case, _, job = fixture("late timeout")
        src = store.sources("analyst", case["id"])[0]
        quote = src["body"][: min(1000, len(src["body"]))]
        proposal = {
            "proposals": [
                {
                    "source_id": src["id"],
                    "quote": quote,
                    "text": "A participant reports the quoted issue; independent verification pending.",
                    "kind": "open_question",
                }
            ]
        }
        run_once(
            store,
            encoder=encoder,
            provider=FakeProvider([proposal, ProviderTimeoutError("injected late timeout")]),
        )
        result = store.job("analyst", job["id"])
        check(
            "late timeout preserves proposal and sources",
            result["status"] == "partial"
            and len(store.memories("analyst", case["id"]))
            > sum(not m.bot for m in first_batch.messages)
            and any(
                e["kind"] == "provider_timeout"
                for e in store.changes("analyst", case["id"])["events"]
            ),
        )

    exercise("late timeout test executes", late_timeout)

    def race():
        case, _, job = fixture("erasure during generation")
        src = store.sources("analyst", case["id"])[0]

        def erase(_):
            store.erase("analyst", case["id"], [src["id"]], "ERASE")

        run_once(store, encoder=encoder, provider=FakeProvider([{"proposals": []}], erase))
        result = store.job("analyst", job["id"])
        check(
            "erasure during generation prevents publication",
            result["status"] == "cancelled"
            and not result["output_id"]
            and store.source("analyst", src["id"])["erased"],
        )

    exercise("erasure race test executes", race)

    def index_race():
        case = store.create_case("analyst", account["id"], "INJECTED source edit during index")
        subset = ImportBatch(messages=[m for m in first_batch.messages if not m.bot][:1])
        store.import_messages("analyst", case["id"], subset)
        before = store.memories("analyst", case["id"])[0]
        calls = 0

        def change():
            nonlocal calls
            calls += 1
            if calls == 2:
                edited = subset.model_copy(deep=True)
                edited.messages[0].body += "\nINJECTED source correction"
                edited.messages[0].updated_at = now()
                store.import_messages("analyst", case["id"], edited)

        index_case(store, "analyst", case["id"], encoder, change)
        with store.connect() as db:
            stale = db.execute(
                "SELECT count(*) FROM vectors WHERE memory_id=?", (before["id"],)
            ).fetchone()[0]
        check(
            "source edit fences late old-source vector publication",
            stale == 0,
            {"stale_vectors": stale, "case_id": case["id"]},
        )

    exercise("index race test executes", index_race)

    def concurrency():
        case, conv, job = fixture("concurrent edits and idempotency", False)
        store.cancel("analyst", job["id"])
        memory = store.memories("analyst", case["id"])[0]

        def edit(i):
            try:
                store.correct(
                    "analyst",
                    memory["id"],
                    1,
                    "Controlled concurrent correction " + str(i),
                    "outcome",
                    "proposed",
                    "injected concurrency",
                )
                return "committed"
            except ValueError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(edit, range(16)))
        check(
            "sixteen simultaneous edits have one winner",
            results.count("committed") == 1 and results.count("conflict") == 15,
        )

        def enqueue(_):
            return store.enqueue(
                "analyst", conv["id"], conv["session"]["id"], "Same durable question", "same-key"
            )["id"]

        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(enqueue, range(16)))
        check("sixteen concurrent retries create one job", len(set(ids)) == 1)
        store.cancel("analyst", ids[0])

    exercise("concurrency test executes", concurrency)

    def source_corruption():
        case, _, job = fixture("corrupted source body", False)
        store.cancel("analyst", job["id"])
        memory = store.memories("analyst", case["id"])[0]
        index_case(store, "analyst", case["id"], encoder)
        with store.connect() as db:
            db.execute(
                "UPDATE sources SET body='INJECTED corrupted bytes' WHERE id=?",
                (memory["source_id"],),
            )
        try:
            result = RecallEngine(store, encoder).search(
                "analyst", case["id"], Recall(question=memory["body"][:300], limit=30)
            )
            corrupt = any(h["evidence"]["source_id"] == memory["source_id"] for h in result["hits"])
            check(
                "source-body integrity corruption rejected before citation",
                not corrupt,
                {"case_id": case["id"]},
            )
        except (ValueError, PermissionError):
            check("source-body integrity corruption rejected before citation", True)
        finally:
            # Restore only this injected fixture so an independent whole-store
            # backup drill is not contaminated by deliberately corrupted bytes.
            with store.connect() as db:
                db.execute(
                    "UPDATE sources SET body=? WHERE id=?",
                    (memory["source_body"], memory["source_id"]),
                )

    exercise("source corruption test executes", source_corruption)

    def restore_drill():
        case, _, job = fixture("backup erasure and epoch", False)
        store.cancel("analyst", job["id"])
        src = store.sources("analyst", case["id"])[0]
        snapshot = root / "snapshot"
        backup(store, snapshot)
        old_epoch = store.setting("epoch")
        store.erase("analyst", case["id"], [src["id"]], "ERASE")
        restored_path = root / "restored"
        restore(snapshot, restored_path, ledger_dir=store.ledger_dir)
        restored = Store(restored_path, ledger_dir=store.ledger_dir)
        check(
            "old backup cannot resurrect erased source",
            restored.source("analyst", src["id"])["erased"]
            and restored.setting("epoch") != old_epoch,
        )
        # Wrong-but-existing ledger is distinct from a missing file.
        unrelated = Store(root / "unrelated", ledger_dir=root / "unrelated-ledger")
        try:
            restore(snapshot, root / "wrong-ledger-restore", ledger_dir=unrelated.ledger_dir)
        except (ValueError, RuntimeError):
            check("unrelated erasure ledger rejected", True)
        else:
            check(
                "unrelated erasure ledger rejected",
                False,
                {"restored_path": str(root / "wrong-ledger-restore")},
            )

    exercise("backup restore drill executes", restore_drill)

    # Freeze the live subset by corpus size before running providers; no cherry-pick retry.
    chosen = sorted(
        cases,
        key=lambda item: (-item[2].messages.__len__(), item[1]["repository"], item[1]["issue"]),
    )[: args.live_jobs]
    report["live_selection"] = [
        {"repository": r["repository"], "issue": r["issue"]} for _, r, _ in chosen
    ]
    checkpoint()
    for case, row, batch in chosen:
        cid = case["id"]
        store.policy(
            "analyst",
            cid,
            Policy(expected_revision=store.case("analyst", cid)["revision"], model_egress=True),
        )
        conv = store.conversation("analyst", cid)
        job = store.enqueue(
            "analyst",
            conv["id"],
            conv["session"]["id"],
            "Prepare a source-grounded handover. Distinguish reported environment, proposed vs performed attempts, failed vs successful outcomes, conflicting reports, and unresolved questions. Do not certify a fix.",
            "live",
        )
        started = time.perf_counter()
        run_once(store, encoder=encoder)
        result = store.job("analyst", job["id"])
        payload = result.get("output", {}).get("payload", {})
        report["live_jobs"].append(
            {
                "repository": row["repository"],
                "issue": row["issue"],
                "job_id": job["id"],
                "status": result["status"],
                "ai_succeeded": payload.get("ai_succeeded", False),
                "answer_state": payload.get("answer_state"),
                "quoted_claims": len(payload.get("claims", [])),
                "calls": result["model_calls"],
                "reason": result["reason"],
                "seconds": time.perf_counter() - started,
                "output_id": result.get("output_id"),
                "coverage": payload.get("recall", {}).get("coverage"),
                "compression": payload.get("compression", {}).get("coverage"),
                "events": store.changes("analyst", cid)["events"],
            }
        )
        checkpoint()
        print(
            "Live outcome",
            row["repository"],
            row["issue"],
            result["status"],
            payload.get("ai_succeeded", False),
            flush=True,
        )
    probes = [q for q in report["queries"] if q["required_memory_id"]]
    durations = sorted(report["latency_ms"])
    report["summary"] = {
        "threads": len(cases),
        "human_messages": sum(r["human_messages"] for _, r, _ in cases),
        "repositories": len({r["repository"] for _, r, _ in cases}),
        "checks": len(report["checks"]),
        "failed_checks": [c for c in report["checks"] if not c["passed"]],
        "queries": len(report["queries"]),
        "extractive_probes": len(probes),
        "extractive_hit_at_10": {
            key: sum(q["required_memory_id"] in q[key] for q in probes)
            for key in ["hybrid_ids", "lexical_ids", "vector_only_ids"]
        },
        "recall_p50_ms": statistics.median(durations) if durations else None,
        "recall_p95_ms": durations[int(0.95 * (len(durations) - 1))] if durations else None,
        "live_ai_successes": sum(j["ai_succeeded"] for j in report["live_jobs"]),
        "live_jobs": len(report["live_jobs"]),
        "full_release_cohort_met": False,
        "independent_gold_evaluation": "NOT PERFORMED",
    }
    report["finished_at"] = now()
    checkpoint()
    print(json.dumps(report["summary"], indent=2))
    return 1 if report["summary"]["failed_checks"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
