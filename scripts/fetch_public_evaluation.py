"""Fetch and checksum-verify public PDF cases listed in the evaluation manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/tenderlens/manifests/public-evaluation-sources.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("montenegro", "serbia", "nepal", "all"), default="all")
    args = parser.parse_args()
    sources = json.loads(MANIFEST.read_text(encoding="utf-8"))["sources"]
    for source in sources:
        if args.case not in ("all", source["case"]):
            continue
        path = ROOT / source["local_path"]
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]:
            print(f"verified {source['id']}: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(source["url"], timeout=60) as response:
            data = response.read(30_000_001)
        if len(data) > 30_000_000 or hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise SystemExit(f"download failed size/checksum verification: {source['id']}")
        path.write_bytes(data)
        print(f"downloaded and verified {source['id']}: {path}")


if __name__ == "__main__":
    main()
