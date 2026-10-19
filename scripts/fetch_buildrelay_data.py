"""Capture public evaluation artifacts with provenance; never execute/extract archives.

LogChunks: Brandt et al., DOI 10.5281/zenodo.3632351, CC BY 4.0 per API metadata.
GHALogs sample: D2KLab/gha-dataset (research source; review rights before redistribution).
Runtime data lives in gitignored var/, not in the distributable application.
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

import httpx

SOURCES = {
    "logchunks.zip": (
        "https://zenodo.org/records/3632351/files/LogChunks.zip?download=1",
        32000000,
        "aafa45079bdae44e340f4474ca5c4340",
    ),
    "gha-example-run.json": (
        "https://raw.githubusercontent.com/D2KLab/gha-dataset/master/examples/run.json",
        1000000,
        None,
    ),
    "gha-example-log.tar.gz": (
        "https://raw.githubusercontent.com/D2KLab/gha-dataset/master/examples/log.tar.gz",
        5000000,
        None,
    ),
}


def capture(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {
        "captured_at": time.time(),
        "artifacts": [],
        "scope": "public research logs, not original webhook traffic",
    }
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for name, (url, limit, expected) in SOURCES.items():
                value = bytearray()
                start = time.monotonic()
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    for chunk in response.iter_bytes():
                        value.extend(chunk)
                        if len(value) > limit or time.monotonic() - start > 120:
                            raise ValueError("source exceeded capture allowance")
                if expected and hashlib.md5(value, usedforsecurity=False).hexdigest() != expected:
                    raise ValueError("publisher checksum mismatch")
                (destination / name).write_bytes(value)
                manifest["artifacts"].append(
                    {
                        "file": name,
                        "url": url,
                        "bytes": len(value),
                        "sha256": hashlib.sha256(value).hexdigest(),
                    }
                )
    finally:
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = capture(args.output)
    print(json.dumps(result, indent=2))
