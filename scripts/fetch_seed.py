"""Fetch the public seed RFP into gitignored local benchmark storage."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/tenderlens/manifests/seed-sources.json"


def main():
    sources = json.loads(MANIFEST.read_text(encoding="utf-8"))["sources"]
    for source in sources:
        target = ROOT / source["local_path"]
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == source["sha256"]:
            print(f"Verified existing file: {target}")
            continue
        with urllib.request.urlopen(source["url"], timeout=60) as response:
            data = response.read(30_000_001)
        if len(data) > 30_000_000 or hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise SystemExit(f"Source size or checksum mismatch: {source['id']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        print(f"Fetched and verified: {target}")


if __name__ == "__main__":
    main()
