"""Explicit public-source validation tools. Never invokes a model or claims consumer acceptance."""

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from repairclaim_api.errors import DomainError
from repairclaim_api.parser import RestrictedParser
from repairclaim_api.sources import SourceFetcher, validate_source_url


def validate_plan(plan):
    if not isinstance(plan, list) or not 1 <= len(plan) <= 120:
        raise ValueError("Plan must contain 1..120 official PDF references")
    ids, urls = set(), set()
    for item in plan:
        if not isinstance(item, dict) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", item.get("id", "")
        ):
            raise ValueError("Invalid source identifier")
        try:
            parsed = validate_source_url(item.get("url"))
        except DomainError as error:
            raise ValueError("Official URL required") from error
        if not parsed.path.lower().endswith(".pdf") or item["id"] in ids or item["url"] in urls:
            raise ValueError("Unique official PDF references required")
        ids.add(item["id"])
        urls.add(item["url"])
    return plan


def summary(records):
    accepted = [r for r in records if r["status"] == "parsed"]
    return {
        "attempted": len(records),
        "parsed": len(accepted),
        "failed": sum(r["status"] == "failed" for r in records),
        "distinct_documents": len({r["sha256"] for r in accepted}),
        "pages": sum(r.get("pages", 0) for r in accepted),
        "consumer_e2e": False,
        "actual_provider_calls": 0,
        "browser_e2e": False,
        "independent_labels": False,
        "quality_gate_passed": False,
    }


def acquire(plan, out, *, fetcher=None, parser=None):
    plan = validate_plan(plan)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    (out / "raw").mkdir(mode=0o700)
    (out / "parsed").mkdir(mode=0o700)
    fetcher = fetcher or SourceFetcher(max_bytes=20 * 1024 * 1024)
    parser = parser or RestrictedParser()
    frozen = json.dumps(plan, sort_keys=True).encode()
    (out / "plan.json").write_bytes(frozen)
    records = []
    accounted = 0
    quota = 250 * 1024 * 1024
    for item in plan:
        record = {
            **item,
            "acquired_at": datetime.now(UTC).isoformat(),
            "status": "failed",
            "attempts": [],
            "rights": "Official archive; copyrighted publisher material. Internal validation only; redistribution not cleared.",
        }
        for _ in range(3):
            if accounted + 20 * 1024 * 1024 > quota:
                record["error"] = "conservative_acquisition_budget_exhausted"
                break
            try:
                result = fetcher.fetch(item["url"])
                accounted += len(result["body"])
                record["attempts"].append({"status": "fetched", "http_status": 200})
                record.update(
                    {
                        "sha256": result["sha256"],
                        "bytes": len(result["body"]),
                        "final_url": result["url"],
                    }
                )
                (out / "raw" / f"{item['id']}.pdf").write_bytes(result["body"])
                try:
                    parsed = parser.run("parse", result["body"], item["id"] + ".pdf")
                    (out / "parsed" / f"{item['id']}.json").write_text(
                        json.dumps(parsed, ensure_ascii=True), encoding="utf8"
                    )
                    record.update(
                        {
                            "status": "parsed",
                            "pages": parsed["page_count"],
                            "needs_ocr": parsed["needs_ocr"],
                        }
                    )
                except DomainError as error:
                    record["error"] = error.code
                break
            except DomainError as error:
                # Failed transfers have unknown byte counts; reserve the full per-request cap.
                accounted += 20 * 1024 * 1024
                record["attempts"].append(
                    {"status": "failed", "error": error.code, "http_status": None}
                )
                record["error"] = error.code
        records.append(record)
        report = {
            **summary(records),
            "plan_count": len(plan),
            "plan_sha256": hashlib.sha256(frozen).hexdigest(),
            "accounted_bytes_including_failed_transfer_reserves": accounted,
            "records": records,
        }
        (out / "acquisition.json").write_text(json.dumps(report, indent=2), encoding="utf8")
        print(
            json.dumps({key: record.get(key) for key in ("id", "status", "pages", "error")}),
            flush=True,
        )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["acquire"])
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="New dedicated evidence directory; existing paths are refused",
    )
    args = parser.parse_args()
    report = acquire(json.loads(args.plan.read_text()), args.out)
    print(json.dumps({k: v for k, v in report.items() if k != "records"}, indent=2))
    return 0 if not report["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
