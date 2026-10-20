"""Record an already obtained explicit payload/destination approval in a new subset."""

import argparse
import json

from casecouncil_api.evaluation import approve_development_subset

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--approval-reference", required=True)
    p.add_argument("--limit", type=int, default=6)
    p.add_argument("--max-calls", type=int, default=132)
    args = p.parse_args()
    print(
        json.dumps(
            approve_development_subset(
                args.corpus, args.output, args.limit, args.max_calls, args.approval_reference
            ),
            indent=2,
        )
    )
