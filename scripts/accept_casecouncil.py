"""Collect reproducible engineering evidence, separately from product acceptance."""

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def accept(output, runtime_smoke=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = {}
    commands = {
        "frontend_tests": ["npm", "--prefix", "apps/casecouncil-web", "test"],
        "frontend_build": ["npm", "--prefix", "apps/casecouncil-web", "run", "build"],
        "python_tests": [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *[str(p) for p in sorted((ROOT / "tests").glob("test_casecouncil*.py"))],
            f"--junitxml={output / 'tests.xml'}",
        ],
    }
    for name, command in commands.items():
        try:
            run = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=240,
                check=False,
                env=os.environ,
            )
            (output / f"{name}.log").write_text(run.stdout + run.stderr)
            results[name] = {
                "status": "passed" if run.returncode == 0 else "failed",
                "exit_code": run.returncode,
            }
        except subprocess.TimeoutExpired:
            results[name] = {"status": "timed_out"}
    xml = output / "tests.xml"
    if xml.exists():
        cases = list(ET.parse(xml).iter("testcase"))
        skipped = sum(c.find("skipped") is not None for c in cases)
        results["python_tests"].update(cases=len(cases), skipped=skipped)
        if skipped:
            results["python_tests"]["status"] = "incomplete"
    if runtime_smoke:
        report = json.loads(Path(runtime_smoke).read_text())
        passed = (
            report.get("state") == "draft_ready"
            and not report.get("unavailable")
            and report.get("all_tools_audited") is True
            and report.get("known_receipts") == report.get("calls", 0) > 0
        )
        results["actual_runtime_fixture"] = {
            "status": "passed" if passed else "not_passed",
            "scope": "owned fictional fixture, not real-world accuracy",
            "report": str(Path(runtime_smoke).resolve()),
        }
    result = {
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "results": results,
        "engineering_checks_passed": all(r["status"] == "passed" for r in results.values()),
        "real_data_validated": False,
        "full_product_accepted": False,
        "remaining_acceptance": [
            "source permission/reviewed legal basis or authorized partner case files",
            "eligible real corpus, held-out independent domain labels and baseline comparison",
            "interactive browser/accessibility acceptance",
            "actual old-Windows-host isolation, restart, load and restore qualification",
            "Cloudflare Access, TLS, source privacy and security review",
            "customer pilot and measured commercial benefit",
        ],
    }
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--runtime-smoke")
    parser.add_argument(
        "--engineering-only",
        action="store_true",
        help="Exit zero for complete engineering checks, not release acceptance",
    )
    args = parser.parse_args()
    result = accept(args.output, args.runtime_smoke)
    raise SystemExit(0 if args.engineering_only and result["engineering_checks_passed"] else 1)
