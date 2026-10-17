import pytest
from fastapi.testclient import TestClient
from relaydesk_api.api import create_app
from relaydesk_api.ingest import GithubSources
from test_relaydesk_core import setup


def test_github_pagination_and_bot_coverage():
    def request(url):
        if url.endswith("/repos/org/repo"):
            return {"id": 42, "full_name": "org/repo"}
        if "/comments?" not in url:
            return {
                "id": 7,
                "number": 2,
                "body": "Initial failure",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "user": {"login": "person"},
                "comments": 2,
            }
        if url.endswith("&page=1"):
            return [
                {
                    "id": 8,
                    "body": "First reply",
                    "created_at": "2025-01-02T00:00:00Z",
                    "updated_at": "2025-01-02T00:00:00Z",
                    "user": {"login": "person", "type": "User"},
                }
            ]
        return []

    result = GithubSources(request=request, page_size=1).fetch("org/repo", 2)
    assert len(result.messages) == 2
    assert not result.complete and result.gaps


def test_api_auth_csrf_and_two_independent_sessions(tmp_path):
    store, case = setup(tmp_path)
    app = TestClient(create_app(store=store))
    assert app.get("/v1/cases").status_code == 401
    login = app.post(
        "/v1/auth/session", json={"username": "alice", "password": "alice-long-password"}
    )
    assert login.status_code == 200
    assert app.post("/v1/accounts", json={"name": "Denied"}).status_code == 403
    csrf = login.json()["csrf"]
    headers = {"X-CSRF-Token": csrf}
    conversation = app.post(
        f"/v1/cases/{case['id']}/conversations", headers=headers, json={}
    ).json()
    session = app.post(
        f"/v1/conversations/{conversation['id']}/sessions", headers=headers, json={}
    ).json()
    assert session["id"] != conversation["session"]["id"]
    bob = TestClient(create_app(store=store))
    bob.post("/v1/auth/session", json={"username": "bob", "password": "bob-long-password"})
    assert bob.get(f"/v1/cases/{case['id']}").status_code == 403


def test_non_allowlisted_source_never_dispatches():
    with pytest.raises(ValueError):
        GithubSources().fetch("https://evil.example", 1)


def test_takeover_idempotency_minimum_revision_and_strict_schema(tmp_path):
    store, case = setup(tmp_path)
    client = TestClient(create_app(store=store))
    login = client.post(
        "/v1/auth/session", json={"username": "alice", "password": "alice-long-password"}
    ).json()
    headers = {"X-CSRF-Token": login["csrf"], "Idempotency-Key": "takeover-test"}
    route = f"/v1/cases/{case['id']}/takeover"
    first = client.post(route, headers=headers, json={"question": "What is known?"})
    assert first.status_code == 200
    repeated = client.post(route, headers=headers, json={"question": "What is known?"})
    assert repeated.json()["id"] == first.json()["id"]
    assert "lease" not in repeated.json()
    assert client.post(route, headers=headers, json={"question": "Different"}).status_code == 409
    assert (
        client.post(
            route, headers=headers, json={"question": "What?", "minimum_revision": 999}
        ).status_code
        == 409
    )
    assert (
        client.post(
            route, headers=headers, json={"question": "What?", "history": "true"}
        ).status_code
        == 422
    )


def test_duplicate_batch_and_partial_import_are_not_silent(tmp_path):
    from contracts.relaydesk import ImportBatch
    from relaydesk_api.worker import run_once
    from test_relaydesk_core import batch
    from test_relaydesk_worker import Provider

    store, case = setup(tmp_path)
    value = batch()
    with pytest.raises(ValueError):
        store.import_messages("alice", case["id"], ImportBatch(messages=value.messages * 2))
    value.complete = False
    store.import_messages("alice", case["id"], value)
    conv = store.conversation("alice", case["id"])
    job = store.enqueue("alice", conv["id"], conv["session"]["id"], "What failed?", "partial")
    run_once(store, encoder=None, provider=Provider([]))
    assert any(
        "incomplete" in g.lower()
        for g in store.job("alice", job["id"])["output"]["payload"]["coverage_gaps"]
    )
