"""Run controlled engineering OR explicitly approved real installed-Codex smoke."""

import argparse
import json

from shelfproof_api.validation import actual_smoke, software_validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=("software", "actual-smoke"), default="software")
    parser.add_argument("--approval-reference")
    parser.add_argument("--products", type=int, default=6)
    args = parser.parse_args()
    if args.mode == "actual-smoke":
        if not args.approval_reference:
            parser.error("actual-smoke requires an explicit finite user approval reference")
        report = actual_smoke(
            args.corpus, args.output, args.approval_reference, products=args.products
        )
    else:
        report = software_validation(args.corpus, args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
