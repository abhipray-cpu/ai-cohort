"""Assess the actual build against ALL release gates; missing evidence never passes.

Runs the existing tests with expected-failure masking disabled. Reuses hashed real
corpus evidence only when product-code hashes match; never fabricates independent
review, browser journeys, Windows deployment or customer-usefulness evidence.
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from relaydesk_api.common import file_hash, now

ROOT = Path(__file__).resolve().parents[1]


def verdict(gates):
    if any(g["status"] == "failed" for g in gates):
        return "rejected"
    if not gates or any(g["status"] != "passed" for g in gates):
        return "blocked"
    return "accepted"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit", default="var/validation/relaydesk-corrective-audit-v3.json")
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--check-source-quota", action="store_true")
    args = parser.parse_args()
    destination = Path(args.output)
    destination.mkdir(parents=True, exist_ok=False)
    audit_path = Path(args.audit)
    audit = json.loads(audit_path.read_text())
    report = {
        "started_at": now(),
        "host": platform.platform(),
        "scope": "all-gate acceptance assessment; NOT a claim every test was executable",
        "prior_audit": {"path": str(audit_path), "sha256": file_hash(audit_path)},
        "gates": [],
    }
    if args.check_source_quota:
        from relaydesk_api.ingest import GithubTransport

        try:
            resources = GithubTransport().request("https://api.github.com/rate_limit")["resources"]
            report["source_quota_observation"] = {
                "observed_at": now(),
                "core": resources["core"],
                "search": resources["search"],
            }
        except (OSError, ValueError, TimeoutError) as error:
            report["source_quota_observation"] = {
                "observed_at": now(),
                "unavailable": type(error).__name__,
            }

    def gate(identity, status, reason, evidence=None):
        report["gates"].append(
            {"id": identity, "status": status, "reason": reason, "evidence": evidence}
        )

    def checkpoint():
        (destination / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    mismatches = [
        name
        for name, sha in audit["product_code_sha256"].items()
        if not (ROOT / name).is_file() or file_hash(ROOT / name) != sha
    ]
    for evidence in [*audit.get("runs", []), *audit.get("auxiliary_evidence", [])]:
        path = Path(evidence["path"])
        if path.is_dir():
            path = path / "report.json"
        if not path.is_file() or file_hash(path) != evidence["sha256"]:
            mismatches.append(str(path))
    if freeze := audit.get("code_freeze"):
        path = Path(freeze["path"])
        if not path.is_file() or file_hash(path) != freeze["sha256"] or not freeze["unchanged"]:
            mismatches.append("pre_run_code_freeze")
    from relaydesk_api.embeddings import Encoder

    try:
        encoder = Encoder(ROOT / "var/models/relaydesk-minilm")
        expected_model = json.loads((Path(audit["runs"][0]["path"]) / "report.json").read_text())[
            "model"
        ]
        if encoder.fingerprint != expected_model:
            mismatches.append("semantic_model_namespace")
    except (OSError, ValueError, KeyError):
        mismatches.append("semantic_model_unavailable_or_invalid")
    gate(
        "G01-evidence-currentness",
        "failed" if mismatches else "passed",
        "Product code must match prior evidence; corrective revalidation is separate.",
        {"mismatched_paths": mismatches},
    )
    corrupt = []
    for corpus in audit["corpora"]:
        path = Path(corpus["path"]) / "report.json"
        if file_hash(path) != corpus["sha256"]:
            corrupt.append(str(path))
            continue
        captured = json.loads(path.read_text())
        for thread in captured["threads"]:
            batch = path.parent / "batches" / thread["batch"]
            if file_hash(batch) != thread["sha256"]:
                corrupt.append(str(batch))
        raw = path.parent / "raw"
        for row in json.loads((raw / "manifest.json").read_text()):
            if file_hash(raw / row["path"]) != row["sha256"]:
                corrupt.append(str(raw / row["path"]))
    gate(
        "G02-frozen-input-integrity",
        "failed" if corrupt else "passed",
        "Verify actual captured files, not just declared counts.",
        {"corrupt_paths": corrupt},
    )
    data = audit["distinct_data"]
    volume = (
        data["threads"] >= 200
        and data["repositories"] >= 20
        and data["human_messages"] >= 5000
        and data["over_100_nonbot_threads"] >= 10
    )
    gate(
        "G03-full-real-cohort",
        "failed" if not volume else "blocked",
        "Need 200 independently screened substantive threads, >=20 repositories, >=5000 non-bot messages, >=10 >100-message histories; body duplicate/partial screening still required.",
        data,
    )
    if args.run_tests:
        commands = [
            (
                "python",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests",
                    "--runxfail",
                    "-q",
                    f"--junitxml={destination.resolve() / 'tests.xml'}",
                ],
            ),
            (
                "frontend-state",
                ["npm.cmd" if os.name == "nt" else "npm", "--prefix", "apps/relaydesk-web", "test"],
            ),
            (
                "frontend-build",
                [
                    "npm.cmd" if os.name == "nt" else "npm",
                    "--prefix",
                    "apps/relaydesk-web",
                    "run",
                    "build",
                ],
            ),
        ]
        outcomes = {}
        for name, command in commands:
            with (destination / (name + ".log")).open("w", encoding="utf-8") as log:
                try:
                    result = subprocess.run(
                        command,
                        cwd=ROOT,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        timeout=240,
                        check=False,
                    )
                    outcomes[name] = result.returncode
                except (OSError, subprocess.TimeoutExpired):
                    outcomes[name] = None
            print(name, outcomes[name], flush=True)
            checkpoint()
        counts = {}
        if (destination / "tests.xml").exists():
            cases = ET.parse(destination / "tests.xml").getroot().findall(".//testcase")
            counts = {
                "total": len(cases),
                "failed": sum(
                    c.find("failure") is not None or c.find("error") is not None for c in cases
                ),
                "skipped": sum(c.find("skipped") is not None for c in cases),
            }
        gate(
            "G04-tests-without-masked-failures",
            "passed" if outcomes["python"] == 0 and counts.get("skipped", 1) == 0 else "failed",
            "Expected failures are executed as failures for acceptance; skipped tests cannot pass a full gate.",
            {
                "exit_code": outcomes["python"],
                "counts": counts,
                "log": "python.log",
                "junit": "tests.xml",
            },
        )
        gate(
            "G05-frontend-build-state",
            "passed" if outcomes["frontend-state"] == outcomes["frontend-build"] == 0 else "failed",
            "Build/state checks only; not browser acceptance.",
            outcomes,
        )
    else:
        gate(
            "G04-tests-without-masked-failures",
            "blocked",
            "Fresh acceptance tests were not run; use --run-tests.",
        )
        gate(
            "G05-frontend-build-state", "blocked", "Fresh frontend build/state tests were not run."
        )
    gate(
        "G06-independent-quality-and-heldout",
        "blocked",
        "No 300-question two-human-reviewer gold set, adjudication, required 150/60/90 repository split or blind quality/critical-fact/abstention results. Self-generated labels and extractive probes cannot substitute.",
    )
    live = audit["live_jobs"]
    live_fail = any(not j["ai_succeeded"] for j in live)
    gate(
        "G07-live-grounding-and-continuity",
        "blocked" if mismatches else "failed" if live_fail else "blocked",
        "AI-stage failures fail this gate; even all completions need independent natural-answer grounding review. Exact quotations establish provenance, not relevance or technical truth.",
        {
            "jobs": len(live),
            "ai_stage_completions": sum(j["ai_succeeded"] for j in live),
            "source": "prior frozen live observations, not new provider calls",
        },
    )
    issues = audit["known_injected_failures"]
    gate(
        "G08-privacy-integrity-currentness",
        "blocked"
        if mismatches
        else "failed"
        if issues
        else "passed"
        if audit.get("code_freeze", {}).get("unchanged")
        else "blocked",
        "Wrong-ledger restore, corrupted-source citation and stale source publication must pass corrected revalidation.",
        issues,
    )
    scale = audit["relaydesk-aggressive-scale-v1/report.json"]["measurements"]
    scale_ok = all(
        m["each_probe_under_provisional_500ms"]
        and m["compression_plus_schema_can_fit_48000_char_ceiling"]
        for m in scale
    )
    gate(
        "G09-capacity-and-context",
        "blocked" if mismatches else "passed" if scale_ok else "failed",
        "Bounded replica latency/context observations; replicas add no unique real-world data.",
        scale,
    )
    gate(
        "G10-browser-ui",
        "blocked",
        "No browser connection: cannot execute keyboard, responsive/accessibility or actual two-browser acceptance. HTTP/state tests are not substitutes.",
    )
    gate(
        "G11-windows-protected-edge-and-operations",
        "blocked",
        "Actual Windows service identity/reboot/Codex, protected Cloudflare, disk/ACL/process cleanup and five-product resource acceptance are unavailable on this macOS host.",
    )
    gate(
        "G12-handover-usefulness",
        "blocked",
        "No separately consenting customer paired tasks/reviewer-accepted required-fact/effort evidence; no external outreach is authorized.",
    )
    report["verdict"] = verdict(report["gates"])
    report["full_acceptance_completed"] = all(
        g["status"] in ["passed", "failed"] for g in report["gates"]
    )
    report["failed"] = [g["id"] for g in report["gates"] if g["status"] == "failed"]
    report["blocked"] = [g["id"] for g in report["gates"] if g["status"] == "blocked"]
    report["finished_at"] = now()
    checkpoint()
    print(
        json.dumps(
            {k: report[k] for k in ["verdict", "full_acceptance_completed", "failed", "blocked"]},
            indent=2,
        )
    )
    return 0 if report["verdict"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
