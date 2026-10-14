"""Acquire and freeze official PostgreSQL HTML sources, then index local snapshots."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from resolvedesk_api.ingest import parse_document_details
from resolvedesk_api.network import fetch_page
from resolvedesk_api.store import Store

ROOT = Path(__file__).resolve().parents[1]
TOPICS = (
    "app-pgdump",
    "app-pgrestore",
    "app-pg-dumpall",
    "pgupgrade",
    "libpq-connect",
    "client-authentication",
    "backup",
    "upgrading",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="var/resolvedesk")
    parser.add_argument("--versions", nargs="+", choices=("16", "17"), default=["16", "17"])
    parser.add_argument("--topics", nargs="+", choices=TOPICS, default=list(TOPICS))
    args = parser.parse_args()
    store = Store(args.data_dir)
    raw = ROOT / "data/resolvedesk/raw"
    raw.mkdir(parents=True, exist_ok=True)
    destination = ROOT / "data/resolvedesk/manifests/sources.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = (
        json.loads(destination.read_text())
        if destination.exists()
        else {"schema_version": "1.0", "sources": []}
    )
    existing = {s["id"]: s for s in manifest["sources"]}
    for version in args.versions:
        for topic in args.topics:
            sid = f"pg{version}-{topic}"
            path = raw / f"{sid}.html"
            url = f"https://www.postgresql.org/docs/{version}/{topic}.html"
            html = path.read_text(encoding="utf-8") if path.exists() else fetch_page(url)
            digest = hashlib.sha256(html.encode()).hexdigest()
            if sid in existing and existing[sid]["sha256"] != digest:
                raise SystemExit(
                    f"Frozen source changed: {sid}. Create a new corpus revision explicitly."
                )
            if not path.exists():
                path.write_text(html, encoding="utf-8")
            text, sections = parse_document_details(html)
            source = store.import_source(
                title=f"{topic} · PostgreSQL {version}",
                url=url,
                version=version,
                text=text,
                sections=sections,
            )
            existing[sid] = existing.get(sid) or {
                "id": sid,
                "url": url,
                "version": version,
                "sha256": digest,
                "local_path": str(path.relative_to(ROOT)),
                "captured_at": datetime.now(UTC).isoformat(),
                "license": "PostgreSQL License; preserve notices",
                "license_url": "https://www.postgresql.org/about/licence/",
            }
            # Commit the manifest after each acquisition so interruption is resumable.
            manifest["sources"] = sorted(existing.values(), key=lambda s: s["id"])
            destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            print(
                f"Indexed {sid}: snapshot={source['id']}, characters={len(source['text'])}",
                flush=True,
            )


if __name__ == "__main__":
    main()
