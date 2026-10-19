"""One explicit installed-Codex smoke call on a labelled fixture, not real-data acceptance."""

import argparse
import json
import os
from pathlib import Path

from buildrelay_api.worker import provider_from_env
from buildrelay_api.workflow import validate_triage
from contracts.buildrelay import Triage
from dev_stack import environment


def smoke(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    os.environ.update(environment())
    text = "Test checkout\nAssertionError: expected 2, got 3"
    report = {
        "kind": "controlled_fixture_runtime_smoke",
        "real_data_acceptance": False,
        "calls": 1,
        "tools_audited": False,
        "status": "started",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    try:
        provider = provider_from_env()
        result = provider.generate(
            prompt="Return schema JSON triage for this CONTROLLED TEST FIXTURE. No tools. Cite exact line 2. Keep diagnosis a hypothesis, not a verified fix.\n1: Test checkout\n2: AssertionError: expected 2, got 3",
            schema=Triage.model_json_schema(),
        )
        report.update(
            exit_code=result.exit_code,
            elapsed_ms=result.elapsed_ms,
            tools_audited=result.tools_audited,
        )
        if result.exit_code:
            report["status"] = (
                "quota_blocked"
                if any(s in result.stderr.lower() for s in ("quota", "usage limit", "rate limit"))
                else "provider_exit"
            )
        else:
            report["triage"] = validate_triage(json.loads(result.text), text)
            report["status"] = "passed" if result.tools_audited else "unaudited"
    except (ValueError, RuntimeError, OSError) as exc:
        report["status"] = type(exc).__name__
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "triage"}, indent=2))
    return report["status"] == "passed"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--live", action="store_true")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    if not args.live:
        p.error("explicit --live required; consumes authenticated Codex usage")
    raise SystemExit(0 if smoke(args.output) else 1)
