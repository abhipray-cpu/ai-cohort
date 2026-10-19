"""Reselect frozen GitHub logs without network calls; preserve and verify source hashes."""

import argparse
import hashlib
import json
from pathlib import Path

from buildrelay_api.github import select_archive


def reselect(source, output):
    source, output = Path(source), Path(output)
    original = (source / "manifest.json").read_bytes()
    manifest = json.loads(original)
    output.mkdir(parents=True, exist_ok=False)
    manifest["derived_from"] = {
        "path": str(source),
        "manifest_sha256": hashlib.sha256(original).hexdigest(),
        "operation": "production selector rerun on unchanged source archives; no API fetch",
        "selector_module_sha256": hashlib.sha256(
            Path(select_archive.__code__.co_filename).read_bytes()
        ).hexdigest(),
    }
    for record in manifest["records"]:
        case = output / record["id"]
        case.mkdir()
        for name, artifact in record["artifacts"].items():
            raw = (source / record["id"] / name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
                raise ValueError("source hash mismatch")
            (case / name).write_bytes(raw)
        if record["status"] == "evidence_captured":
            evidence = select_archive((case / "logs.zip").read_bytes(), record["source_url"])
            raw = (json.dumps(evidence, indent=2) + "\n").encode()
            (case / "evidence.json").write_bytes(raw)
            record["artifacts"]["evidence.json"] = {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
            record.update(truncated=evidence["truncated"], evidence_chars=len(evidence["text"]))
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps({"records": len(manifest["records"]), "output": str(output), "network_calls": 0})
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    reselect(args.source, args.output)
