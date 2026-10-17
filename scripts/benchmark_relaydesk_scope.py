"""1k/5k/10k scope benchmark with LABELLED copies of real payloads.

Replicas test capacity only; they are never counted as additional real-world data,
independent queries, or accuracy evidence. Uses a new isolated store.
"""

import argparse
import json
import secrets
import time
from pathlib import Path

from contracts.relaydesk import ImportBatch, Recall
from relaydesk_api.common import file_hash, now
from relaydesk_api.context import compress
from relaydesk_api.embeddings import Encoder
from relaydesk_api.recall import RecallEngine, index_case
from relaydesk_api.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    corpus = Path(args.corpus)
    capture = json.loads((corpus / "report.json").read_text())
    messages = []
    for row in capture["threads"]:
        path = corpus / "batches" / row["batch"]
        if file_hash(path) != row["sha256"]:
            raise ValueError("Frozen batch integrity mismatch")
        batch = ImportBatch.model_validate_json(path.read_text())
        messages.extend(m for m in batch.messages if not m.bot)
    store = Store(root / "store", ledger_dir=root / "ledger")
    store.add_user("load-validator", secrets.token_urlsafe(24), admin=True)
    account = store.create_account("load-validator", "LABELLED artificial load scope")
    case = store.create_case(
        "load-validator", account["id"], "Real payload replicas; not a natural investigation"
    )
    encoder = Encoder("var/models/relaydesk-minilm")
    report = {
        "started_at": now(),
        "classification": "labelled repeated real payloads for capacity only; zero additional unique corpus messages",
        "unique_input_messages": len(messages),
        "model": encoder.fingerprint,
        "measurements": [],
    }
    previous = 0
    for size in [1000, 5000, 10000]:
        staged = []
        for i in range(previous, size):
            msg = messages[i % len(messages)].model_copy(deep=True)
            msg.source_key = f"load-copy:{i}:" + msg.source_key
            staged.append(msg)
            if len(staged) == 1000 or i == size - 1:
                store.import_messages(
                    "load-validator",
                    case["id"],
                    ImportBatch(
                        messages=staged,
                        origin="LABELLED scope load replicas",
                        complete=False,
                        gaps=["Not a natural thread; repeated source payloads"],
                    ),
                )
                staged = []
        started = time.perf_counter()
        index = index_case(store, "load-validator", case["id"], encoder)
        index_seconds = time.perf_counter() - started
        latencies = []
        for query in [
            "What workaround failed and which versions were affected?",
            "What remains unresolved and which actions were proposed?",
        ]:
            started = time.perf_counter()
            result = RecallEngine(store, encoder).search(
                "load-validator", case["id"], Recall(question=query)
            )
            latencies.append((time.perf_counter() - started) * 1000)
        summary = compress(store.memories("load-validator", case["id"]), 6000)
        with store.connect() as db:
            vectors = db.execute("SELECT count(*) FROM vectors").fetchone()[0]
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        measurement = {
            "memories": size,
            "vectors": vectors,
            "new_index_seconds": index_seconds,
            "index": index,
            "recall_ms": latencies,
            "coverage": result["coverage"],
            "summary_serialized_characters": len(json.dumps(summary)),
            "compression_coverage": summary["coverage"],
            "sqlite_bytes": store.path.stat().st_size,
            "sqlite_integrity": integrity,
            "each_probe_under_provisional_500ms": all(t <= 500 for t in latencies),
            "compression_plus_schema_can_fit_48000_char_ceiling": len(json.dumps(summary)) < 48000,
        }
        report["measurements"].append(measurement)
        (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(measurement), flush=True)
        previous = size
    report["finished_at"] = now()
    (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
