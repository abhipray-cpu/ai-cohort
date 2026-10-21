"""Acquire a bounded, versioned public USDA source inventory. Does not invoke Codex."""

import argparse
import json

from shelfproof_api.corpus import acquire, regroup_inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target", type=int, default=1000)
    parser.add_argument(
        "--regroup-from",
        help="Create a new owner-grouped split revision from a frozen inventory, without modifying the original",
    )
    parser.add_argument(
        "--expected-archive-sha256",
        help="Resume a verified completed download without replacing/redownloading it",
    )
    parser.add_argument(
        "--reviewed-dictionary-hash",
        help="After reviewing the bundled dictionary, curate the existing frozen archive without downloading again",
    )
    args = parser.parse_args()
    if args.regroup_from:
        print(json.dumps(regroup_inventory(args.regroup_from, args.output), indent=2))
        return
    print(
        json.dumps(
            acquire(
                args.output,
                target=args.target,
                reviewed_dictionary_hash=args.reviewed_dictionary_hash,
                expected_archive_sha256=args.expected_archive_sha256,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
