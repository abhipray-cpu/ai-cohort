"""Evaluate frozen real logs through production selector/triage; no fabricated GitHub events."""

import argparse
import concurrent.futures
import hashlib
import json
import threading
import time
from collections import Counter
from pathlib import Path

from buildrelay_api.evaluation import overlap, prepare_logchunks
from buildrelay_api.worker import provider_from_env
from buildrelay_api.workflow import triage_evidence


class Recorder:
    """Record calls/usage without persisting stdout, signed URLs or credential-bearing stderr."""

    def __init__(self, directory):
        self.directory = Path(directory)
        self.provider = provider_from_env()
        self.calls, self.receipts = 0, []

    def generate(self, *, prompt, schema):
        self.calls += 1
        receipt = {
            "call": self.calls,
            "status": "started",
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt_chars": len(prompt),
            "usage": None,
        }
        path = self.directory / f"call-{self.calls}.json"
        path.write_text(json.dumps(receipt))
        original = self.provider._run

        def collect(args, body):
            result = original(args, body)
            for line in result.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get("type") == "turn.completed":
                    receipt["usage"] = event.get("usage")
            return result

        self.provider._run = collect
        try:
            result = self.provider.generate(prompt=prompt, schema=schema)
            receipt.update(
                status="returned",
                exit_code=result.exit_code,
                elapsed_ms=result.elapsed_ms,
                tools_audited=result.tools_audited,
                quota=any(
                    s in result.stderr.lower() for s in ("quota", "usage limit", "rate limit")
                ),
            )
            return result
        except (RuntimeError, ValueError, OSError) as exc:
            receipt.update(status=type(exc).__name__)
            raise
        finally:
            self.provider._run = original
            path.write_text(json.dumps(receipt, indent=2) + "\n")
            self.receipts.append(receipt)


def campaign(prepared, output, limit=80, workers=2):
    prepared, output = Path(prepared), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((prepared / "manifest.json").read_text())
    selected = manifest["sample_ids"][:limit]
    (output / "selection.json").write_text(
        json.dumps(
            {
                "ids": selected,
                "workers": workers,
                "selection": "one source-path-hash-selected case per repository; gold excluded from prompts",
                "limits": {"cases": limit, "attempts_per_case": 2},
                "gates": {
                    "nonfallback_fraction": 0.95,
                    "lexical_gold_citation_overlap_fraction": 0.90,
                    "exact_citation_validity": 1.0,
                    "tools_audited": True,
                },
                "limitations": "Gold quote overlap is not independent causal diagnosis/next-step correctness.",
            },
            indent=2,
        )
    )
    results = []
    stop = threading.Event()

    def analyze(ident):
        case = output / ident
        case.mkdir()
        source = prepared / ident
        if not (source / "evidence.json").exists():
            return {"id": ident, "status": "selector_failure", "calls": 0}
        context = json.loads((source / "context.json").read_text())
        evidence = json.loads((source / "evidence.json").read_text())
        gold = (source / "gold.txt").read_text()
        recorder = Recorder(case)
        audit = []
        triage = triage_evidence(
            recorder,
            context,
            evidence,
            lambda action, detail: audit.append({"action": action, **detail}),
        )
        report = {
            "id": ident,
            "context": context,
            "triage": triage,
            "audit": audit,
            "calls": recorder.calls,
            "receipts": recorder.receipts,
            "truncated": evidence["truncated"],
            "status": "fallback"
            if triage.get("fallback_reason")
            else "schema_and_exact_quotes_valid",
            "lexical_gold_citation_overlap": overlap(triage, gold),
            "gold_in_prompt": False,
            "independent_semantic_review": "not_performed",
        }
        (case / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        if any(
            r.get("exit_code", 0) != 0 or r.get("status") != "returned" for r in recorder.receipts
        ):
            stop.set()
        return report

    started = time.monotonic()
    pending_ids = iter(selected)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(analyze, ident): ident
            for ident in [next(pending_ids, None) for _ in range(workers)]
            if ident
        }
        while futures:
            completed, _ = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in completed:
                ident = futures.pop(future)
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001 -- preserve benchmark failure, never turn it into pass
                    result = {
                        "id": ident,
                        "status": "harness_error",
                        "error_class": type(exc).__name__,
                    }
                    stop.set()
                results.append(result)
                (output / "progress.json").write_text(json.dumps(results, indent=2))
                print(
                    json.dumps(
                        {
                            k: result.get(k)
                            for k in ("id", "status", "calls", "lexical_gold_citation_overlap")
                        }
                    ),
                    flush=True,
                )
                next_id = next(pending_ids, None) if not stop.is_set() else None
                if next_id:
                    futures[pool.submit(analyze, next_id)] = next_id
    valid = [r for r in results if r["status"] == "schema_and_exact_quotes_valid"]
    summary = {
        "selected": len(selected),
        "completed": len(results),
        "stopped_on_runtime_error": stop.is_set(),
        "statuses": dict(Counter(r["status"] for r in results)),
        "calls": sum(r.get("calls", 0) for r in results),
        "valid_nonfallback": len(valid),
        "gold_overlap_count": sum(r.get("lexical_gold_citation_overlap", False) for r in results),
        "elapsed_seconds": time.monotonic() - started,
        "independent_causal_review": "not_performed",
        "full_product_accepted": False,
        "pending_ids": [i for i in selected if i not in {r["id"] for r in results}],
    }
    (output / "report.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("prepare", "live"))
    p.add_argument("--corpus", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--limit", type=int, default=80, choices=range(1, 81))
    p.add_argument("--workers", type=int, default=2, choices=(1, 2))
    a = p.parse_args()
    if a.action == "prepare":
        result = prepare_logchunks(a.corpus, a.output)
        print(
            json.dumps(
                {k: v for k, v in result.items() if k not in {"records", "sample_ids"}}, indent=2
            )
        )
    else:
        campaign(a.corpus, a.output, a.limit, a.workers)
