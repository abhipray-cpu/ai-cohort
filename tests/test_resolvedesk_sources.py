"""Regression against checksum-frozen official PostgreSQL HTML, when acquired."""

import hashlib
import json
from pathlib import Path

import pytest
from resolvedesk_api.ingest import parse_document
from resolvedesk_api.store import Store
from resolvedesk_api.worker import bounded

ROOT = Path(__file__).resolve().parents[1]


def test_actual_pg_dump_rule_reaches_bounded_context(tmp_path):
    manifest = ROOT / "data/resolvedesk/manifests/sources.json"
    if not manifest.exists():
        pytest.skip("Acquire ResolveDesk official-source fixtures first")
    sources = json.loads(manifest.read_text())["sources"]
    if any(not (ROOT / item["local_path"]).exists() for item in sources):
        pytest.skip("Fetch ignored ResolveDesk official HTML fixtures first")
    store = Store(tmp_path)
    for item in sources:
        html = (ROOT / item["local_path"]).read_text(encoding="utf-8")
        assert hashlib.sha256(html.encode()).hexdigest() == item["sha256"]
        store.import_source(
            title=item["id"], url=item["url"], version=item["version"], text=parse_document(html)
        )
    evidence = bounded(
        store.retrieve(
            "pg_dump backup fails server version 17 pg_dump version 16 Why does the backup fail",
            ["17", "16"],
        )
    )
    assert any("newer than its own major version" in p["text"] for p in evidence)
    assert sum(len(p["text"]) for p in evidence) <= 16000
