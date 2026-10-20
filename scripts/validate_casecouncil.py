"""Audit authorized local packets or run a bounded installed-Codex evaluation; never fetch FOS."""

import argparse
import json
from pathlib import Path

from casecouncil_api.evaluation import audit_corpus, campaign
from casecouncil_api.runtime import provider_from_env

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--live", action="store_true")
    p.add_argument("--authorize-egress", action="store_true")
    p.add_argument("--rights-reviewed-reference", default="")
    p.add_argument(
        "--mode", choices=("debate", "single", "vote_only", "single_refine"), default="debate"
    )
    p.add_argument("--split", choices=("development", "calibration", "test"), default="development")
    p.add_argument("--limit", type=int, default=1)
    p.add_argument("--max-calls", type=int, default=22)
    args = p.parse_args()
    if args.live:
        if not args.authorize_egress or len(args.rights_reviewed_reference) < 20:
            p.error(
                "live inference requires explicit --authorize-egress and a reviewed rights reference"
            )
        report = campaign(
            args.corpus,
            args.output,
            provider_from_env(),
            args.mode,
            args.limit,
            args.max_calls,
            args.rights_reviewed_reference,
            args.split,
        )
    else:
        report = audit_corpus(args.corpus)
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=False)
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
