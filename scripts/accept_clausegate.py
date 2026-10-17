"""Assess evidence without turning unavailable release gates into passes."""

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def verdict(gates):
    if "failed" in gates.values():
        return "rejected"
    return "accepted" if gates and all(s == "passed" for s in gates.values()) else "blocked"


def live_gate(jobs):
    return (
        "passed"
        if len({j["source_id"] for j in jobs}) >= 30
        and all(j["job"]["status"] == "completed" for j in jobs)
        else "blocked"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument(
        "--read-race-evidence",
        help="Retained concurrent-read/write stress result; missing evidence blocks this gate",
    )
    parser.add_argument("--corpus", default="var/validation/clausegate-corpus-v2")
    args = parser.parse_args()
    from validate_clausegate import product_hashes

    destination = Path(args.output)
    destination.mkdir(parents=True, exist_ok=False)
    path = Path(args.evidence)
    r = json.loads(path.read_text())
    gates = {
        "frozen_engineering_evidence": "passed"
        if r["product_code_unchanged"]
        and r["product_code_sha256"] == product_hashes()
        and not r["summary"]["failed_checks"]
        else "failed",
        "full_corpus_integrity": "passed"
        if r["data"]["records"] == 607 and r["data"]["labelled_pairs"] == 10319
        else "failed",
        "workflow_fixtures": "passed" if len(r["workflows"]) >= 60 else "failed",
        "live_30_document_workflows": live_gate(r["live_jobs"]),
        "unmasked_regression_and_ui_build": "blocked",
        "heldout_semantic_and_qualified_review": "blocked",
        "actual_two_person_browser": "blocked",
        "windows_protected_edge_and_resources": "blocked",
        "customer_usefulness": "blocked",
        "concurrent_read_write_consistency": "blocked",
    }
    read_race = None
    if args.read_race_evidence:
        read_path = Path(args.read_race_evidence)
        read_result = json.loads(read_path.read_text())
        gates["concurrent_read_write_consistency"] = (
            "passed"
            if read_result.get("passed") is True
            and read_result.get("final_audit", {}).get("valid") is True
            else "failed"
        )
        from clausegate_api.common import byte_hash

        read_race = {
            "path": str(read_path),
            "sha256": byte_hash(read_path.read_bytes()),
            "result": read_result,
        }
    outcomes = {}
    if args.run_tests:
        npm = "npm.cmd" if os.name == "nt" else "npm"
        commands = {
            "python": [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--runxfail",
                f"--junitxml={destination.resolve() / 'tests.xml'}",
            ],
            "frontend-tests": [npm, "--prefix", "apps/clausegate-web", "test"],
            "frontend-build": [npm, "--prefix", "apps/clausegate-web", "run", "build"],
            "ruff": [sys.executable, "-m", "ruff", "check", "."],
        }
        for name, command in commands.items():
            with (destination / (name + ".log")).open("w", encoding="utf-8") as log:
                try:
                    outcomes[name] = subprocess.run(
                        command, stdout=log, stderr=subprocess.STDOUT, timeout=240, check=False
                    ).returncode
                except (OSError, subprocess.TimeoutExpired):
                    outcomes[name] = None
            print(name, outcomes[name], flush=True)
        skipped = True
        if (destination / "tests.xml").exists():
            skipped = any(
                c.find("skipped") is not None
                for c in ET.parse(destination / "tests.xml").getroot().findall(".//testcase")
            )
        gates["unmasked_regression_and_ui_build"] = (
            "passed" if all(v == 0 for v in outcomes.values()) and not skipped else "failed"
        )
    from clausegate_api.common import byte_hash, now

    corpus = Path(args.corpus)
    try:
        source_ok = (
            byte_hash((corpus / "contract-nli.zip").read_bytes()) == r["corpus_manifest"]["sha256"]
            and byte_hash((corpus / "evaluator-only.json").read_bytes())
            == r["corpus_manifest"]["normalized_sha256"]
        )
    except OSError:
        source_ok = False
    if not source_ok:
        gates["full_corpus_integrity"] = "failed"
    if r["product_code_sha256"] != product_hashes():
        gates["frozen_engineering_evidence"] = "failed"
    result = {
        "finished_at": now(),
        "evidence": str(path),
        "evidence_sha256": byte_hash(path.read_bytes()),
        "gates": gates,
        "commands": outcomes,
        "read_race_evidence": read_race,
        "verdict": verdict(gates),
        "full_acceptance_completed": all(s in {"passed", "failed"} for s in gates.values()),
    }
    (destination / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if all(s == "passed" for s in gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
