"""Frozen real-corpus mechanics and explicitly labelled policy fixtures; optional live AI.

Gold is used only for mechanical fixtures/evaluation, never a model prompt. This
does not manufacture independent human approval history or customer evidence.
"""

import argparse
import json
import platform
import secrets
import time
from collections import Counter
from pathlib import Path

from clausegate_api.common import byte_hash, digest, now
from clausegate_api.intake import archive_members, pdf_document
from clausegate_api.store import Store
from clausegate_api.worker import run_once
from contracts.clausegate import DecisionInput, Finding, Playbook, Rule


def length_sample(rows, count):
    unique = {}
    for row in sorted(rows, key=lambda r: (len(r["document"]["text"]), str(r["id"]))):
        unique.setdefault(row["document"]["text_hash"], row)
    values = list(unique.values())
    count = min(count, len(values))
    if count <= 0:
        return []
    if count == 1:
        return [values[len(values) // 2]]
    return [values[round(i * (len(values) - 1) / (count - 1))] for i in range(count)]


def remaining_rows(rows, seen):
    hashes = {r["document"]["text_hash"] for r in rows if r["id"] in seen}
    return [r for r in rows if r["id"] not in seen and r["document"]["text_hash"] not in hashes]


def product_hashes():
    paths = [
        p
        for root in [Path("apps/clausegate-api/src"), Path("apps/clausegate-web/src")]
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix in {".py", ".ts", ".tsx", ".css"}
    ]
    paths.append(Path("packages/contracts/src/contracts/clausegate.py"))
    return {str(p): byte_hash(p.read_bytes()) for p in paths}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--workflow-cases", type=int, default=60)
    p.add_argument("--live-jobs", type=int, default=0)
    p.add_argument("--sample", choices=["shortest", "length-spread"], default="shortest")
    p.add_argument("--pdf-limit", type=int, default=30)
    p.add_argument(
        "--exclude-evidence",
        help="Completed same-code/same-corpus report whose model-input IDs and exact duplicate texts must not be rerun",
    )
    p.add_argument("--live-split", choices=["dev", "test"], default="dev")
    p.add_argument(
        "--allow-heldout",
        action="store_true",
        help="Explicitly authorize opening the sealed test evaluation; never tune on its failures",
    )
    args = p.parse_args()
    if (
        not 0 <= args.live_jobs <= 123
        or not 0 <= args.workflow_cases <= 607
        or not 0 <= args.pdf_limit <= 1000
    ):
        raise ValueError("Explicit bounded run allowances required")
    if args.live_split == "test" and not args.allow_heldout:
        raise ValueError("Held-out evaluation needs an explicit sealed-run grant")
    corpus, root = Path(args.corpus), Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((corpus / "manifest.json").read_text())
    raw = corpus / "contract-nli.zip"
    normalized = corpus / "evaluator-only.json"
    if (
        byte_hash(raw.read_bytes()) != manifest["sha256"]
        or byte_hash(normalized.read_bytes()) != manifest["normalized_sha256"]
    ):
        raise ValueError("Frozen corpus integrity mismatch")
    rows = json.loads(normalized.read_text())
    exclusion, seen = None, set()
    if args.exclude_evidence:
        previous_path = Path(args.exclude_evidence)
        previous = json.loads(previous_path.read_text())
        if (
            not previous.get("finished_at")
            or not previous.get("product_code_unchanged")
            or previous["product_code_sha256"] != product_hashes()
            or previous["corpus_manifest"]["normalized_sha256"] != manifest["normalized_sha256"]
        ):
            raise ValueError("Complement needs a completed same-code/same-corpus campaign")
        seen = {j["source_id"] for j in previous["live_jobs"]}
        exclusion = {
            "path": str(previous_path),
            "sha256": byte_hash(previous_path.read_bytes()),
            "excluded_ids": sorted(seen),
        }
    report = {
        "started_at": now(),
        "host": platform.platform(),
        "corpus_manifest": manifest,
        "product_code_sha256": product_hashes(),
        "checks": [],
        "workflows": [],
        "live_jobs": [],
        "pdf_intake": [],
        "complement_of": exclusion,
        "sampling": {
            "method": args.sample,
            "live_split": args.live_split,
            "gold_used_for_selection": False,
        },
        "classification": "Real documents; fixture policy/decisions are synthetic labelled mechanics. Live AI and semantic evaluation separate.",
    }

    def checkpoint():
        (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    def check(name, passed, detail=None):
        report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})

    ids, hashes, spans, pairs = set(), Counter(), 0, 0
    for row in rows:
        doc = row["document"]
        check(
            "source/span integrity",
            digest(doc["text"]) == doc["text_hash"]
            and all(doc["text"][s["start"] : s["end"]] == s["quote"] for s in doc["spans"]),
            {"id": row["id"], "split": row["split"]},
        )
        check(
            "gold separated and all checks labelled",
            "gold" not in doc and set(row["gold"]) == set(row["hypotheses"]),
            row["id"],
        )
        ids.add(row["id"])
        hashes[doc["text_hash"]] += 1
        spans += len(doc["spans"])
        pairs += len(row["gold"])
    by_split = {
        split: {r["document"]["text_hash"] for r in rows if r["split"] == split}
        for split in ["train", "dev", "test"]
    }
    report["data"] = {
        "records": len(rows),
        "unique_ids": len(ids),
        "unique_text_hashes": len(hashes),
        "duplicate_text_records": sum(v - 1 for v in hashes.values()),
        "source_spans": spans,
        "labelled_pairs": pairs,
        "cross_split_exact_overlap": {
            a + "/" + b: len(by_split[a] & by_split[b])
            for a, b in [("train", "dev"), ("train", "test"), ("dev", "test")]
        },
        "near_duplicate_screening": "NOT PERFORMED",
    }
    files = archive_members(raw.read_bytes(), quarantined=[])
    for name in [n for n in sorted(files) if n.lower().endswith(".pdf")][: args.pdf_limit]:
        try:
            doc = pdf_document(files[name], name.rsplit("/", 1)[-1][:160])
            report["pdf_intake"].append(
                {
                    "name": name,
                    "bytes_hash": doc["bytes_hash"],
                    "complete": doc["complete"],
                    "pages": len(doc["pages"]),
                    "characters": len(doc["text"]),
                    "gaps": doc["gaps"],
                }
            )
        except (ValueError, RuntimeError) as error:
            report["pdf_intake"].append(
                {"name": name, "complete": False, "rejected": type(error).__name__}
            )
    store = Store(root / "store", ledger_dir=root / "authority")
    store.add_user("requester", secrets.token_urlsafe(24), admin=True)
    store.add_user("reviewer", secrets.token_urlsafe(24))
    store.add_user("outsider", secrets.token_urlsafe(24))
    w = store.create_workspace("requester", "Public NDA validation · not real customer approvals")
    store.membership(
        "requester", w["id"], "reviewer", ["reviewer", "approver", "final_reviewer"], ["*"]
    )

    def prepare(row, name, action="require_exception", missing=False, full=False):
        c = store.create_case("requester", w["id"], name)
        selected = list(row["hypotheses"]) if full else [next(iter(row["hypotheses"]))]
        rules = [
            Rule(id=k, hypothesis=row["hypotheses"][k]["hypothesis"], action=action)
            for k in selected
        ]
        c = store.set_playbook(
            "requester",
            c["id"],
            c["revision"],
            Playbook(name="Explicit evaluation fixture, not legal advice", rules=rules),
        )
        if not missing:
            c = store.set_context(
                "requester",
                c["id"],
                c["revision"],
                "recipient",
                "Public benchmark workflow fixture",
            )
        c = store.import_document("requester", c["id"], c["revision"], row["document"])
        return c, selected

    def fixture_findings(row, selected):
        values = []
        for k in selected:
            gold = row["gold"][k]
            ranges = [row["gold_spans"][i] for i in gold["spans"]]
            evidence = [
                s["id"]
                for s in row["document"]["spans"]
                if any(s["start"] < right and s["end"] > left for left, right in ranges)
            ]
            values.append(
                Finding(
                    check_id=k,
                    label=gold["choice"],
                    assessment="supported",
                    evidence_ids=evidence[:30],
                    rationale="Gold-derived fixture for state-machine validation; not a natural model or real approver decision.",
                )
            )
        return values

    for index, row in enumerate(rows[: args.workflow_cases]):
        kind = ["clarification", "exception", "hard_block"][index % 3]
        c, selected = prepare(
            row,
            f"Fixture {kind} · real NDA {row['id']}",
            "block" if kind == "hard_block" else "require_exception",
            kind == "clarification",
        )
        c = store.submit_findings(
            "reviewer",
            c["id"],
            c["revision"],
            fixture_findings(row, selected),
            "Labelled mechanical fixture",
        )
        check("durable pause", c["state"] == "waiting_human", c["id"])
        store = Store(store.root, ledger_dir=store.ledger_dir)
        check(
            "waiting survives restart",
            store.case("requester", c["id"])["checkpoint"] == c["checkpoint"],
            c["id"],
        )
        if kind == "clarification":
            r = next(
                r for r in c["requests"] if r["kind"] == "clarification" and r["state"] == "pending"
            )
            store.decide(
                "requester",
                r["id"],
                DecisionInput(
                    expected_revision=r["revision"],
                    binding=r["binding"],
                    kind="clarify",
                    rationale="Fixture business facts supplied explicitly",
                    key="clarify",
                    side="recipient",
                    purpose="Public benchmark workflow fixture",
                ),
            )
            c = store.case("requester", c["id"])
            c = store.submit_findings(
                "reviewer",
                c["id"],
                c["revision"],
                fixture_findings(row, selected),
                "Fixture recheck after context clarification",
            )
        r = next(r for r in c["requests"] if r["state"] == "pending")
        value = DecisionInput(
            expected_revision=r["revision"],
            binding=r["binding"],
            kind="approve_exception",
            rationale="Explicit fixture decision, not legal advice",
            key="decision",
        )
        if kind == "hard_block":
            rejected = False
            try:
                store.decide("reviewer", r["id"], value)
            except ValueError:
                rejected = True
            check("non-waivable block", rejected, c["id"])
        else:
            d = store.decide("reviewer", r["id"], value)
            check(
                "idempotent decision",
                store.decide("reviewer", r["id"], value)["id"] == d["id"],
                c["id"],
            )
            run_once(store)
            c = store.case("requester", c["id"])
            check("validated continuation", c["state"] == "review_ready", c["id"])
            c = store.finalize(
                "reviewer",
                c["id"],
                c["revision"],
                c["packet"]["sha256"],
                "Fixture final review of exact packet",
                True,
            )
            check(
                "reviewed export",
                store.export("requester", c["id"])["reviewer"] == "reviewer",
                c["id"],
            )
            c = store.import_text(
                "requester",
                c["id"],
                c["revision"],
                "REVISED DOCUMENT\n" + row["document"]["text"],
                row["document"]["name"],
            )
            stale_rejected = False
            try:
                store.export("requester", c["id"])
            except ValueError:
                stale_rejected = True
            check("new revision invalidates export", stale_rejected, c["id"])
        check("audit reconstructs", store.verify_audit("requester", c["id"])["valid"], c["id"])
        denied = False
        try:
            store.case("outsider", c["id"])
        except PermissionError:
            denied = True
        check("outsider denied", denied, c["id"])
        report["workflows"].append(
            {
                "source_id": row["id"],
                "case_id": c["id"],
                "kind": kind,
                "classification": "gold-derived mechanical fixture, not human approval ground truth",
            }
        )
        checkpoint()
        if index % 10 == 0:
            print("Workflow", index + 1, kind, flush=True)
    # Default smoke sample is development-only. Test requires an explicit sealed-run flag.
    split_rows = remaining_rows([r for r in rows if r["split"] == args.live_split], seen)
    if args.live_jobs > len(split_rows):
        raise ValueError("Requested live count exceeds the distinct remaining cohort")
    candidates = (
        length_sample(split_rows, args.live_jobs)
        if args.sample == "length-spread"
        else sorted(split_rows, key=lambda r: len(r["document"]["text"]))[: args.live_jobs]
    )
    report["selected_live_ids"] = [r["id"] for r in candidates]
    checkpoint()
    for row in candidates:
        c, _ = prepare(
            row, f"Live provider · public NDA {row['id']}", action="require_review", full=True
        )
        c = store.set_egress("requester", c["id"], c["revision"], True)
        job = store.enqueue("requester", c["id"], c["revision"], "live")
        started = time.monotonic()
        run_once(store)
        c = store.case("requester", c["id"])
        current_job = next(j for j in store.jobs("requester", c["id"]) if j["id"] == job["id"])
        correct = sum(f["label"] == row["gold"][f["check_id"]]["choice"] for f in c["findings"])
        report["live_jobs"].append(
            {
                "source_id": row["id"],
                "case_id": c["id"],
                "split": args.live_split,
                "job": current_job,
                "state": c["state"],
                "findings": len(c["findings"]),
                "matching_labels": correct,
                "label_denominator": len(row["gold"]),
                "supported": sum(f["assessment"] == "supported" for f in c["findings"]),
                "seconds": time.monotonic() - started,
                "classification": "development diagnostic only; not held-out accuracy or qualified legal review",
            }
        )
        checkpoint()
        print(
            "Live NDA", row["id"], current_job["status"], correct, "/", len(row["gold"]), flush=True
        )
    report["product_code_unchanged"] = report["product_code_sha256"] == product_hashes()
    report["finished_at"] = now()
    report["summary"] = {
        "data": report["data"],
        "checks": len(report["checks"]),
        "failed_checks": [c for c in report["checks"] if not c["passed"]],
        "workflow_cases": len(report["workflows"]),
        "pdf_complete": sum(p["complete"] for p in report["pdf_intake"]),
        "pdf_attempted": len(report["pdf_intake"]),
        "live_jobs": len(report["live_jobs"]),
        "live_stage_complete": sum(j["job"]["status"] == "completed" for j in report["live_jobs"]),
        "independent_quality": "NOT PERFORMED",
        "browser": "UNAVAILABLE unless separately verified",
        "windows": "UNRUN",
        "release": "NOT ACCEPTED",
    }
    checkpoint()
    print(json.dumps(report["summary"], indent=2))
    return int(bool(report["summary"]["failed_checks"]) or not report["product_code_unchanged"])


if __name__ == "__main__":
    raise SystemExit(main())
