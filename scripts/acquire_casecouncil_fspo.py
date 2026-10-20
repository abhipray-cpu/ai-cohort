"""Acquire a bounded Irish motor-insurance research cohort under published FSPO reuse conditions."""

import argparse
import json

from casecouncil_api.fspo import acquire, reprepare

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--accept-reuse-conditions", action="store_true", required=True)
    p.add_argument(
        "--reprepare-from",
        help="Offline preparation of already acquired originals into a new directory",
    )
    args = p.parse_args()
    print(
        json.dumps(
            reprepare(args.reprepare_from, args.output)
            if args.reprepare_from
            else acquire(args.output),
            indent=2,
        )
    )
