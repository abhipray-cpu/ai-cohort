import argparse
import json
from pathlib import Path

from buildrelay_api.corpus import audit_capture

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Audit captured public data without invoking AI")
    p.add_argument("--corpus", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = audit_capture(a.corpus)
    with Path(a.output).open("x") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["missing_log_references"] or result["empty_gold_chunks"] else 0)
