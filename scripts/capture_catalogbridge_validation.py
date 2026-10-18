"""Acquire the documented official WDC validation resources without extracting paths."""

import argparse
import hashlib
import json
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from catalogbridge_api.corpus import safe_members

BASE = "https://data.dws.informatik.uni-mannheim.de/largescaleproductcorpus/data/"
RESOURCES = {
    **{
        f"{hard}{kind}.zip": BASE + f"wdc-products/{hard}{kind}.zip"
        for hard in (20, 50, 80)
        for kind in ("pair", "multi")
    },
    **{
        f"legacy-{category}.json.gz": BASE + f"v2_nonnorm/goldstandards/{category}_gs.json.gz"
        for category in ("computers", "cameras", "watches", "shoes", "all")
    },
}


def capture(output, reuse_from=None):
    if output.exists():
        raise ValueError("new output required; preserve prior evidence")
    output.mkdir(parents=True)

    def fetch(item):
        name, url = item
        cached = Path(reuse_from) / name if reuse_from else None
        if cached and cached.is_file():
            data = cached.read_bytes()
            shutil.copyfile(cached, output / name)
        else:
            for attempt in range(5):
                try:
                    with urllib.request.urlopen(url, timeout=60) as response:
                        if not response.url.startswith(BASE):
                            raise ValueError("unapproved download redirect")
                        data = response.read(80 * 1024 * 1024 + 1)
                        if len(data) > 80 * 1024 * 1024:
                            raise ValueError("download exceeds limit")
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code != 429 or attempt == 4:
                        raise
                    delay = max(15 * (attempt + 1), int(exc.headers.get("Retry-After", "0")))
                    print(json.dumps({"rate_limited": name, "wait_seconds": delay}), flush=True)
                    time.sleep(min(delay, 60))
            (output / name).write_bytes(data)
            time.sleep(4)
        record = {
            "file": name,
            "url": url,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        if name.endswith(".zip"):
            with zipfile.ZipFile(output / name) as archive:
                members = safe_members(archive)
                record["members"] = [{"name": i.filename, "bytes": i.file_size} for i in members]
        print(json.dumps({k: v for k, v in record.items() if k != "members"}), flush=True)
        return record

    with ThreadPoolExecutor(max_workers=1) as pool:
        records = list(pool.map(fetch, RESOURCES.items()))
    pages = {}
    for name, url in [
        ("wdc-products", "https://webdatacommons.org/largescaleproductcorpus/wdc-products/"),
        ("legacy", "https://webdatacommons.org/largescaleproductcorpus/v2/"),
    ]:
        data = urllib.request.urlopen(url, timeout=30).read(2 * 1024 * 1024)
        (output / (name + ".html")).write_bytes(data)
        pages[name] = {"url": url, "sha256": hashlib.sha256(data).hexdigest()}
    manifest = {
        "captured_at": datetime.now(UTC).isoformat(),
        "resources": records,
        "source_pages": pages,
        "rights": "Publisher-offered public benchmark; private evaluation only. No blanket redistribution/commercial-training license inferred. Framework software license is not a dataset license.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reuse-from", type=Path)
    args = parser.parse_args()
    capture(args.output, args.reuse_from)
