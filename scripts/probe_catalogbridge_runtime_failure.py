"""At most two bounded diagnostic calls; classify CLI failures without exposing raw logs."""

import argparse
import json
from pathlib import Path

from catalogbridge_api.model_boundary import InstalledModels, MeteredCodex
from contracts.catalogbridge import Product


class Probe(MeteredCodex):
    def __init__(self, model):
        super().__init__(model, timeout=30)
        self.failure = {}

    def _execute(self, args, prompt):
        result = super()._execute(args, prompt)
        output = result.stdout + "\n" + result.stderr
        folded = output.casefold()
        patterns = {
            "usage_limit": ["usage limit", "usage_limit", "quota exceeded", "quota_exceeded"],
            "rate_limit": ["rate limit", "rate_limit", "too many requests"],
            "authentication": ["unauthorized", "authentication", "token expired", "401"],
            "network": ["connection refused", "connection reset", "network is unreachable", "dns"],
            "unsupported_model": ["model_not_found", "model is not supported", "does not exist"],
        }
        self.failure = {
            "exit_code": result.returncode,
            "stdout_bytes": len(result.stdout.encode()),
            "stderr_bytes": len(result.stderr.encode()),
            "matched_error_categories": [
                key for key, values in patterns.items() if any(v in folded for v in values)
            ],
            "event_types": [],
        }
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                self.failure["event_types"].append(event.get("type"))
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("preserve prior evidence")
    row = json.loads(args.inputs.read_text().splitlines()[0])
    prompt, schema = InstalledModels.prepare(Product(**row["supplier"]), [Product(**row["master"])])
    reports = []
    for model in ("gpt-6-luna", "gpt-6.1-sol"):
        probe = Probe(model)
        try:
            result = probe.generate_metered(prompt, schema)
            report = {
                "model_requested": model,
                "usage": result.usage.model_dump() if result.usage else None,
                "audited": result.audited,
                "effective_model": result.effective_model,
                **probe.failure,
            }
        except (ValueError, RuntimeError, OSError) as exc:
            report = {"model_requested": model, "error_type": type(exc).__name__, **probe.failure}
        reports.append(report)
    output = {
        "diagnostic_invocations": 2,
        "not_a_retry_of_existing_unknown_liability": True,
        "observations": reports,
    }
    args.output.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
