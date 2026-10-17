"""Acquire the official licensed ContractNLI archive; keep labels evaluator-only."""

import argparse
import json
import urllib.request
from pathlib import Path

from clausegate_api.common import byte_hash, now
from clausegate_api.intake import archive_members, normalize_dataset

URL = "https://stanfordnlp.github.io/contract-nli/resources/contract-nli.zip"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument(
        "--archive",
        help="Reuse an explicitly selected retained local archive without another download",
    )
    args = p.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    raw = root / "contract-nli.zip"
    if args.archive:
        content = bytearray(Path(args.archive).read_bytes())
    else:
        content = download()
    raw.write_bytes(content)
    quarantine = []
    files = archive_members(content, quarantined=quarantine)
    counts, corpus = {}, []
    for split in ["train", "dev", "test"]:
        names = [
            n
            for n in files
            if n.rsplit("/", 1)[-1] == split + ".json" and not n.startswith("__MACOSX/")
        ]
        if len(names) != 1:
            raise ValueError("Missing or ambiguous published split")
        rows = normalize_dataset(json.loads(files[names[0]]), split)
        counts[split] = {"documents": len(rows), "pairs": sum(len(r["gold"]) for r in rows)}
        corpus.extend(rows)
    target = root / "evaluator-only.json"
    target.write_text(json.dumps(corpus, ensure_ascii=False), encoding="utf-8")
    manifest = {
        "created_at": now(),
        "url": URL,
        "bytes": len(content),
        "sha256": byte_hash(content),
        "normalized_sha256": byte_hash(target.read_bytes()),
        "license": "Publisher states CC BY 4.0; retain attribution and published use notices",
        "attribution": "Koreeda and Manning (2021), ContractNLI: A Dataset for Document-level Natural Language Inference for Contracts, Findings of EMNLP",
        "terms_url": "https://stanfordnlp.github.io/contract-nli/",
        "splits": counts,
        "documents": len(corpus),
        "pairs": sum(len(r["gold"]) for r in corpus),
        "unique_text_hashes": len({r["document"]["text_hash"] for r in corpus}),
        "archive_entries": len(files),
        "quarantined_unsafe_member_names": quarantine,
        "original_pdfs": sum(n.lower().endswith(".pdf") for n in files),
        "role": "Dataset gold never enters product imports/model context",
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


def download():
    with urllib.request.urlopen(
        urllib.request.Request(URL, headers={"User-Agent": "ClauseGate-Evaluation/0.1"}), timeout=60
    ) as response:
        if response.geturl() != URL:
            raise ValueError("Unapproved redirect")
        content = bytearray()
        while block := response.read(1024 * 1024):
            content.extend(block)
            if len(content) > 256 * 1024**2:
                raise ValueError("Archive byte allowance exceeded")
    return content


if __name__ == "__main__":
    main()
