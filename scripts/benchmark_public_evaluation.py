"""Run an isolated live Codex evaluation on a public TenderLens PDF case."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import time
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path

from agent_core.codex_local import LocalCodexProvider
from tenderlens_api.store import Store
from tenderlens_api.worker import run_once

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/tenderlens/manifests/public-evaluation-sources.json"
REPORT_DIR = ROOT / "var/tenderlens-evaluation"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=("montenegro", "serbia", "nepal"))
    parser.add_argument(
        "--only-source", action="append", help="Source ID to include (may be repeated)"
    )
    parser.add_argument(
        "--session", help="Persistent evaluation session name; reruns resume saved chunks"
    )
    args = parser.parse_args()
    sources = [
        source
        for source in json.loads(MANIFEST.read_text(encoding="utf-8"))["sources"]
        if source["case"] == args.case
        and (args.only_source is None or source["id"] in args.only_source)
    ]
    if not sources:
        raise SystemExit("No sources match the requested case/source")
    if args.session and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", args.session):
        raise SystemExit("Session must contain only letters, digits, hyphens or underscores")
    session_root = REPORT_DIR / "sessions" / args.session if args.session else None
    context = nullcontext(session_root) if session_root else tempfile.TemporaryDirectory(
        prefix=f"tenderlens-{args.case}-"
    )
    with context as temporary:
        store = Store(Path(temporary))
        fingerprint = {
            "case": args.case,
            "sources": [{"id": source["id"], "sha256": source["sha256"]} for source in sources],
        }
        prepared = []
        for source in sources:
            path = ROOT / source["local_path"]
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != source["sha256"]:
                raise SystemExit(f"Missing or changed source: {source['id']}")
            prepared.append((source, path, data))
        session_file = session_root / "session.json" if session_root else None
        if session_file and session_file.exists():
            session = json.loads(session_file.read_text(encoding="utf-8"))
            if session["fingerprint"] != fingerprint:
                raise SystemExit("Session source set changed; choose a new session name")
            run_id = session["run_id"]
            names = session["document_names"]
            run = store.run(run_id)
            if run is None:
                raise SystemExit("Session run is missing; choose a new session name")
            if run["status"] in ("failed", "partial"):
                store.requeue_run(run_id)
                print(f"Resuming {run_id}: {run['progress']}", flush=True)
            elif run["status"] == "running":
                raise SystemExit("Session is running; wait for its worker to finish")
        else:
            opportunity = store.create_opportunity(f"Public evaluation: {args.case}")
            names = {}
            for source, path, data in prepared:
                document = store.add_document(opportunity["id"], path.name, data)
                if document["page_count"] != source["pages"]:
                    raise SystemExit(f"Page count changed: {source['id']}")
                names[document["id"]] = source["id"]
                print(f"Loaded {source['id']}: {document['page_count']} pages", flush=True)
            run_id = store.create_run(opportunity["id"])["id"]
            if session_file:
                session_file.write_text(
                    json.dumps({
                        "fingerprint": fingerprint,
                        "run_id": run_id,
                        "document_names": names,
                    }, indent=2),
                    encoding="utf-8",
                )

        class CountingProvider:
            calls = 0

            def __init__(self):
                self.inner = LocalCodexProvider()

            def generate(self, *, prompt, schema):
                self.calls += 1
                print(f"Codex call {self.calls} started", flush=True)
                result = self.inner.generate(prompt=prompt, schema=schema)
                print(
                    f"Codex call {self.calls}: exit={result.exit_code} "
                    f"elapsed={result.elapsed_ms / 1000:.1f}s",
                    flush=True,
                )
                if result.exit_code:
                    print(f"Provider stderr tail: {result.stderr[-500:]}", flush=True)
                return result

        provider = CountingProvider()
        started = time.monotonic()
        if store.run(run_id)["status"] == "queued":
            run_once(store, provider)
        run = store.run(run_id)
        claims = run["brief"]["claims"] if run["brief"] else []
        report = {
            "case": args.case,
            "only_source": args.only_source,
            "run_date": datetime.now(UTC).isoformat(),
            "sources": [
                {"id": source["id"], "sha256": source["sha256"], "pages": source["pages"]}
                for source in sources
            ],
            "status": run["status"],
            "error": run["error"],
            "elapsed_seconds": round(time.monotonic() - started, 1),
            "codex_calls": provider.calls,
            "progress": run["progress"],
            "claim_count": len(claims),
            "events": run["events"],
            "open_questions": run["brief"]["open_questions"] if run["brief"] else [],
            "claims": [
                {
                    "kind": claim["kind"],
                    "value": claim["value"],
                    "status": claim["status"],
                    "citations": [
                        {
                            "source": names.get(citation["document_id"], "unknown"),
                            "page": citation["page"],
                            "quote": citation["quote"],
                        }
                        for citation in claim["citations"]
                    ],
                }
                for claim in claims
            ],
        }
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_name = args.session or (
            "-".join(args.only_source) if args.only_source else args.case
        )
        destination = REPORT_DIR / f"{report_name}.json"
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "report": str(destination),
                    "status": report["status"],
                    "error": report["error"],
                    "elapsed_seconds": report["elapsed_seconds"],
                    "codex_calls": report["codex_calls"],
                    "claim_count": report["claim_count"],
                    "validation_failures": len(report["events"]),
                },
                indent=2,
            ),
            flush=True,
        )
        if report["status"] != "draft":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
