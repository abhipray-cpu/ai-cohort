"""Conversational RAG: persistent turns, contextual retrieval, and grounded follow-ups."""

import base64
import json

import pytest
from agent_core.provider import ProviderTimeoutError, StructuredGeneration
from contracts.resolvedesk import ChatCreate, ChatMessage
from fastapi.testclient import TestClient
from resolvedesk_api.api import create_app
from resolvedesk_api.store import Store
from resolvedesk_api.worker import run_once

RULE = "pg_dump cannot dump from PostgreSQL servers newer than its own major version."


@pytest.fixture(autouse=True)
def offline_search(monkeypatch):
    monkeypatch.setenv("RESOLVEDESK_SEARCH_PROVIDER", "disabled")


def seed(store):
    for version in ("16", "17"):
        store.import_source(
            title=f"pg_dump {version}",
            url=f"https://www.postgresql.org/docs/{version}/app-pgdump.html",
            version=version,
            text=RULE,
        )


class ChatProvider:
    def __init__(self, timeout=False):
        self.contexts = []
        self.timeout = timeout

    def generate(self, *, prompt, schema):
        if self.timeout:
            raise ProviderTimeoutError("Timed out")
        if schema["title"] == "ChatResolution":
            context = json.loads(prompt.split("CHAT_CONTEXT_JSON\n")[1])
            self.contexts.append(context)
            follow_up = "also" in context["message"].lower()
            version = "16" if follow_up else "17"
            value = {
                "question": f"pg_dump client server version compatibility PostgreSQL {version}",
                "documentation_versions": [version],
                "server_version": context["environment"]["server_version"],
                "client_version": context["environment"]["client_version"],
                "os": context["environment"]["os"],
                "needs_clarification": False,
                "questions": [],
            }
        elif schema["title"] == "SupportVerdict":
            value = {
                "supported_claim_ids": ["c1"],
                "unsupported_claim_ids": [],
                "conflicting_claim_ids": [],
                "reason": "Checked supporting passage",
            }
        else:
            evidence = json.loads(prompt.split("EVIDENCE_JSON\n")[1].split("\nEND_EVIDENCE")[0])
            value = {
                "schema_version": "1.0",
                "claims": [
                    {
                        "id": "c1",
                        "text": RULE,
                        "version": evidence[0]["version"],
                        "category": "explanation",
                        "citations": [{"passage_id": evidence[0]["id"], "quote": RULE}],
                    }
                ],
                "reply_order": ["c1"],
                "questions": [],
                "limitations": [],
                "evidence_state": "supported",
            }
        return StructuredGeneration(text=json.dumps(value), exit_code=0, elapsed_ms=1)


def test_multi_turn_chat_retrieves_again_with_context_and_persists(tmp_path):
    store = Store(tmp_path)
    seed(store)
    chat = store.create_chat(ChatCreate(server_version="17", client_version="16"), "reviewer")
    provider = ChatProvider()
    first = store.send_message(
        chat["id"],
        ChatMessage(content="Why does my pg_dump backup fail?", expected_turn_count=0),
        "first",
        "reviewer",
    )
    run_once(store, provider)
    first_run = store.run(first["turns"][0]["run"]["id"])
    assert first_run["status"] == "draft"
    second = store.send_message(
        chat["id"],
        ChatMessage(content="Does that also apply to 16?", expected_turn_count=1),
        "second",
        "reviewer",
    )
    run_once(store, provider)
    current = store.chat(chat["id"])
    assert len(current["turns"]) == 2
    history = provider.contexts[-1]["history"]
    assert any(
        "pg_dump backup" in message["content"] for message in history if message["role"] == "user"
    )
    assert any(message["role"] == "assistant" for message in history)
    assert all(p["version"] == "16" for p in current["turns"][1]["run"]["answer"]["evidence"])
    assert current["turns"][0]["run"]["answer"]["id"] == first_run["answer"]["id"]
    assert Store(tmp_path).chat(chat["id"])["turns"][1]["content"] == "Does that also apply to 16?"
    assert second["turns"][1]["run"]["index_revision"] == store.index_revision()


def test_message_idempotency_and_pending_turn_guard_are_atomic(tmp_path):
    store = Store(tmp_path)
    chat = store.create_chat(ChatCreate(), "r")
    value = ChatMessage(content="What is pg_dump?", expected_turn_count=0)
    first = store.send_message(chat["id"], value, "same", "r")
    duplicate = store.send_message(chat["id"], value, "same", "r")
    assert first["turns"][0]["id"] == duplicate["turns"][0]["id"]
    with pytest.raises(ValueError):
        store.send_message(
            chat["id"],
            ChatMessage(content="Different question", expected_turn_count=0),
            "same",
            "r",
        )
    with pytest.raises(ValueError, match="Wait"):
        store.send_message(
            chat["id"], ChatMessage(content="Another question", expected_turn_count=1), "next", "r"
        )


def test_general_chat_question_does_not_require_ticket_environment(tmp_path):
    store = Store(tmp_path)
    seed(store)
    chat = store.create_chat(ChatCreate(), "r")
    turn = store.send_message(
        chat["id"], ChatMessage(content="What is pg_dump?", expected_turn_count=0), "one", "r"
    )
    run_once(store, ChatProvider())
    assert store.run(turn["turns"][0]["run"]["id"])["status"] == "draft"


def test_chat_failure_preserves_user_message_and_retry(tmp_path):
    store = Store(tmp_path)
    seed(store)
    chat = store.create_chat(ChatCreate(), "r")
    turn = store.send_message(
        chat["id"], ChatMessage(content="What is pg_dump?", expected_turn_count=0), "one", "r"
    )
    rid = turn["turns"][0]["run"]["id"]
    run_once(store, ChatProvider(timeout=True))
    assert store.chat(chat["id"])["turns"][0]["content"] == "What is pg_dump?"
    assert store.run(rid)["status"] == "failed"
    store.retry(rid)
    run_once(store, ChatProvider())
    assert store.run(rid)["status"] == "draft"


def test_new_thread_never_receives_another_threads_history(tmp_path):
    store = Store(tmp_path)
    seed(store)
    provider = ChatProvider()
    for index in range(2):
        chat = store.create_chat(ChatCreate(), "r")
        store.send_message(
            chat["id"],
            ChatMessage(content=f"What is pg_dump? thread {index}", expected_turn_count=0),
            "one",
            "r",
        )
        run_once(store, provider)
    assert len(provider.contexts) == 2
    assert provider.contexts[0]["history"] == provider.contexts[1]["history"] == []


def test_failed_old_turn_cannot_be_retried_after_followup(tmp_path):
    store = Store(tmp_path)
    seed(store)
    chat = store.create_chat(ChatCreate(), "r")
    first = store.send_message(
        chat["id"], ChatMessage(content="What is pg_dump?", expected_turn_count=0), "one", "r"
    )
    rid = first["turns"][0]["run"]["id"]
    run_once(store, ChatProvider(timeout=True))
    store.send_message(
        chat["id"],
        ChatMessage(content="Does that also apply to 16?", expected_turn_count=1),
        "two",
        "r",
    )
    with pytest.raises(ValueError, match="latest"):
        store.retry(rid)


def test_chat_search_fallback_fetches_grounded_evidence(tmp_path):
    store = Store(tmp_path)
    chat = store.create_chat(ChatCreate(), "r")
    turn = store.send_message(
        chat["id"], ChatMessage(content="What is pg_dump?", expected_turn_count=0), "one", "r"
    )

    class Search:
        configured = True

        def search(self, query):
            return [
                {
                    "title": "pg_dump",
                    "url": "https://www.postgresql.org/docs/17/app-pgdump.html",
                    "snippet": "Not evidence",
                }
            ]

    run_once(
        store, ChatProvider(), Search(), lambda url: f"<main><h1>pg_dump</h1><p>{RULE}</p></main>"
    )
    run = store.run(turn["turns"][0]["run"]["id"])
    assert run["status"] == "draft"
    assert run["answer"]["evidence"][0]["origin"] == "search"
    assert any(
        event["stage"] == "search" and event["outcome"] == "succeeded" for event in run["events"]
    )
    assert store.retrieve("pg_dump", ["17"]) == []


def test_chat_without_evidence_flags_uncertainty(tmp_path):
    store = Store(tmp_path)
    chat = store.create_chat(ChatCreate(), "r")
    turn = store.send_message(
        chat["id"], ChatMessage(content="What is pg_dump?", expected_turn_count=0), "one", "r"
    )
    run_once(store, ChatProvider())
    run = store.run(turn["turns"][0]["run"]["id"])
    assert run["status"] == "escalated"
    assert run["answer"]["draft"]["evidence_state"] == "insufficient"
    assert run["answer"]["draft"]["limitations"]


def test_chat_api_auth_and_persistent_transcript(tmp_path):
    app = create_app(data_dir=tmp_path, username="reviewer", password="secret")
    seed(app.state.store)
    client = TestClient(app)
    headers = {"Authorization": "Basic " + base64.b64encode(b"reviewer:secret").decode()}
    assert client.get("/v1/chats").status_code == 401
    chat = client.post("/v1/chats", json={}, headers=headers).json()
    response = client.post(
        f"/v1/chats/{chat['id']}/messages",
        json={"content": "What is pg_dump?", "expected_turn_count": 0},
        headers={**headers, "Idempotency-Key": "one"},
    )
    assert response.status_code == 202
    run_once(app.state.store, ChatProvider())
    transcript = client.get(f"/v1/chats/{chat['id']}", headers=headers).json()
    assert transcript["turns"][0]["run"]["answer"]["draft"]["claims"]
    assert client.get(f"/v1/chats/{chat['id']}").status_code == 401
