"""Check existing measured evidence; never downloads data, calls models or fabricates labels."""

import argparse
import json
from pathlib import Path

from shelfproof_api.validation import acceptance_gates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = json.loads(Path(args.evidence).read_text())
    gates = acceptance_gates(report)
    destination = Path(args.output)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "gates.json").write_text(json.dumps(gates, indent=2))
    print(json.dumps(gates, indent=2))
    raise SystemExit(0 if gates["production_accepted"] else 2)


if __name__ == "__main__":
    main()
