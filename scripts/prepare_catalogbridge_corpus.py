"""Normalize one explicitly selected official WDC split; gold stays separate."""

import argparse
import gzip
import hashlib
import json
import zipfile
from pathlib import Path

from catalogbridge_api.corpus import normalize_pair, safe_members


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument(
        "--member", required=True, help="Exact JSON/JSON.GZ member for one frozen split"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument(
        "--rights-note",
        required=True,
        help="Operator's recorded source permissions/notice; not automatic license acceptance",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists; preserve previous evidence")
    with zipfile.ZipFile(args.archive) as archive:
        members = safe_members(archive)
        if args.member not in {m.filename for m in members}:
            parser.error("requested split member missing")
        raw = archive.read(args.member)
    if args.member.endswith(".gz"):
        import io

        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(512 * 1024 * 1024 + 1)
    if len(raw) > 512 * 1024 * 1024:
        parser.error("expanded split too large")
    pairs = [normalize_pair(json.loads(line)) for line in raw.splitlines() if line.strip()]
    args.output.mkdir(parents=True)
    seen, inputs, gold = set(), [], []
    for pair in pairs:
        encoded = json.dumps(pair["input"], sort_keys=True)
        key = hashlib.sha256(encoded.encode()).hexdigest()
        if key in seen:
            raise ValueError("duplicate pair in split; resolve before evaluation")
        seen.add(key)
        inputs.append(json.dumps({"id": key, **pair["input"]}))
        gold.append(json.dumps({"id": key, "label": pair["gold"]}))
    (args.output / "inputs.jsonl").write_text("\n".join(inputs) + "\n", encoding="utf-8")
    # Evaluator-only file. Never pass this path to the model or store it in product DB.
    (args.output / "gold.jsonl").write_text("\n".join(gold) + "\n", encoding="utf-8")
    manifest = {
        "archive_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        "split_member": args.member,
        "split_sha256": hashlib.sha256(raw).hexdigest(),
        "source_url": args.source_url,
        "rights_note": args.rights_note,
        "pairs": len(pairs),
        "input_sha256": hashlib.sha256((args.output / "inputs.jsonl").read_bytes()).hexdigest(),
        "gold_sha256": hashlib.sha256((args.output / "gold.jsonl").read_bytes()).hexdigest(),
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
