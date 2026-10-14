"""Acceptance checks must reject false passes, not merely count generated answers."""

import importlib.util
import json
from pathlib import Path

import pytest
from contracts.resolvedesk import AnswerDraft, ChatCreate, ChatMessage
from resolvedesk_api.network import public_query
from resolvedesk_api.store import Store

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "chat_acceptance", ROOT / "scripts/validate_resolvedesk_chat.py"
)
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)


def test_real_corpus_retrieves_restore_and_dump_context_not_only_first_named_tool(tmp_path):
    manifest = json.loads((ROOT / "data/resolvedesk/manifests/sources.json").read_text())
    if any(not (ROOT / source["local_path"]).exists() for source in manifest["sources"]):
        pytest.skip("Acquire official ResolveDesk HTML fixtures first")
    documents = acceptance.corpus()
    store = Store(tmp_path)
    acceptance.seed(store, documents)
    evidence = store.retrieve(
        "In PostgreSQL 17, which utility restores a custom-format pg_dump archive, and can pg_restore select which objects to restore?",
        ["17"],
    )
    pages = {p["url"].rsplit("/", 1)[-1] for p in evidence}
    assert {"app-pgdump.html", "app-pgrestore.html"}.issubset(pages)


def test_acceptance_rejects_failed_or_empty_output(tmp_path):
    store = Store(tmp_path)
    chat = store.create_chat(ChatCreate(), "r")
    result = store.send_message(
        chat["id"], ChatMessage(content="What is pg_dump?", expected_turn_count=0), "one", "r"
    )
    run = result["turns"][0]["run"]
    assert acceptance.check_turn(
        store, run, {"expect": "answer", "required_page": "app-pgdump.html"}
    )


def test_acceptance_allows_documented_client_version_but_rejects_wrong_scope(tmp_path):
    store = Store(tmp_path)
    quote = "pg_dump cannot dump from PostgreSQL servers newer than its own major version."
    source = store.import_source(
        title="pg_dump 16",
        url="https://www.postgresql.org/docs/16/app-pgdump.html",
        version="16",
        text=quote,
    )
    passage = store.source_passages(source["id"])[0]
    chat = store.create_chat(ChatCreate(), "r")
    submitted = store.send_message(
        chat["id"],
        ChatMessage(content="Can pg_dump 16 back up PostgreSQL 17?", expected_turn_count=0),
        "one",
        "r",
    )
    rid = submitted["turns"][0]["run"]["id"]
    evidence = store.retrieve("pg_dump", ["16"])
    draft = AnswerDraft.model_validate(
        {
            "claims": [
                {
                    "id": "c1",
                    "text": quote,
                    "version": "16",
                    "category": "explanation",
                    "citations": [{"passage_id": passage["id"], "quote": quote}],
                }
            ],
            "reply_order": ["c1"],
            "questions": [],
            "limitations": [],
            "evidence_state": "supported",
        }
    )
    store.finish(rid, draft, evidence, "draft")
    expected = {
        "expect": "answer",
        "required_page": "app-pgdump.html",
        "allowed_versions": ["16", "17"],
    }
    assert acceptance.check_turn(store, store.run(rid), expected) == []
    assert acceptance.check_turn(store, store.run(rid), {**expected, "allowed_versions": ["17"]})


def test_chat_transcript_survives_backup_and_restore(tmp_path):
    from scripts.resolvedesk_restore import restore

    store = Store(tmp_path / "live")
    chat = store.create_chat(ChatCreate(), "r")
    store.send_message(
        chat["id"], ChatMessage(content="What is pg_dump?", expected_turn_count=0), "one", "r"
    )
    store.backup(tmp_path / "backup")
    restore(tmp_path / "backup", tmp_path / "restored")
    assert Store(tmp_path / "restored").chat(chat["id"]) == store.chat(chat["id"])


def test_public_search_preserves_pg_hba_topic_without_private_terms():
    query = public_query(
        "PostgreSQL 17 pg_hba.conf authentication failed acme.internal password=private-secret",
        "17",
    )
    assert "pg_hba" in query
    assert "acme" not in query and "private" not in query and "secret" not in query


def test_official_search_does_not_stop_at_unrelated_release_notes(monkeypatch):
    from resolvedesk_api import network

    paths = []

    def response(host, path, **kwargs):
        paths.append(path)
        page = "release-17-11.html" if len(paths) == 1 else "auth-pg-hba-conf.html"
        return (
            200,
            {"Content-Type": "text/html"},
            f'<a href="https://www.postgresql.org/docs/17/{page}">Official result</a>'.encode(),
        )

    monkeypatch.setattr(network, "request", response)
    hits = network.PostgresSearch().search(
        network.public_query("pg_hba authentication server", "17")
    )
    assert len(paths) == 2
    assert "q=pg_hba.conf" in paths[1]
    assert hits[0]["url"].endswith("auth-pg-hba-conf.html")
