"""Run local implementation gates; never equate these with full product acceptance."""

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from buildrelay_api.corpus import audit_capture

ROOT = Path(__file__).resolve().parents[1]


def accept(output, corpus=None, runtime_smoke=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = {}
    commands = {
        "frontend_tests": ["npm", "--prefix", "apps/buildrelay-web", "test"],
        "frontend_build": ["npm", "--prefix", "apps/buildrelay-web", "run", "build"],
        "python_tests": [
            sys.executable,
            "-m",
            "pytest",
            *[str(p) for p in sorted((ROOT / "tests").glob("test_buildrelay*.py"))],
            "-q",
            f"--junitxml={output / 'tests.xml'}",
        ],
    }
    for name, command in commands.items():
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=os.environ,
            timeout=180,
        )
        (output / f"{name}.log").write_text(result.stdout + result.stderr)
        results[name] = {
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
        }
    xml = output / "tests.xml"
    if xml.is_file():
        cases = list(ET.parse(xml).iter("testcase"))
        results["python_tests"]["cases"] = len(cases)
        results["python_tests"]["skipped"] = sum(c.find("skipped") is not None for c in cases)
        for gate, case in (
            ("actual_broker", "test_actual_broker_webhook_queue_and_workflow"),
            ("actual_http_processes", "test_real_http_api_worker_and_built_assets"),
        ):
            match = next((c for c in cases if c.attrib.get("name") == case), None)
            results[gate] = {
                "status": "passed" if match is not None and len(match) == 0 else "not_passed"
            }
    if corpus:
        results["data_inventory"] = audit_capture(corpus)
    if runtime_smoke:
        receipt = json.loads(Path(runtime_smoke).read_text())
        results["runtime_fixture_smoke"] = {
            "status": receipt.get("status"),
            "tools_audited": receipt.get("tools_audited"),
            "scope": "controlled fixture, not semantic accuracy",
        }
    report = {
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "results": results,
        "release_accepted": False,
        "remaining_acceptance": [
            "independent held-out real-failure semantic evaluation",
            "live GitHub credentials/permissions and opt-in issue lifecycle in an owned test repository",
            "browser interaction and accessibility review (browser unavailable in implementation session)",
            "actual old-Windows-host installation, restart and downtime recovery",
            "Cloudflare path-specific access and delivery validation",
            "load/retention/security review and recovery objectives",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--corpus")
    p.add_argument("--runtime-smoke")
    args = p.parse_args()
    accept(args.output, args.corpus, args.runtime_smoke)
    # This is intentionally a release gate, not a success-banner generator.
    raise SystemExit(1)
