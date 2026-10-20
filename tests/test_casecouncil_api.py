import time
import uuid

import pytest
from casecouncil_api.api import create_app
from casecouncil_api.controller import Controller
from fastapi.testclient import TestClient
from test_casecouncil_protocol import ControlledProvider
from test_casecouncil_store import CONTEXT, PASSWORD


def login(client, user="owner"):
    r = client.post("/api/session", json={"username": user, "password": PASSWORD})
    assert r.status_code == 200
    client.headers["X-CSRF-Token"] = r.json()["csrf"]
    client.headers["Idempotency-Key"] = uuid.uuid4().hex


def post(client, path, **kwargs):
    return client.post(
        path, headers={"Idempotency-Key": uuid.uuid4().hex, **kwargs.pop("headers", {})}, **kwargs
    )


@pytest.fixture
def service(tmp_path):
    app = create_app(tmp_path, username="owner", password=PASSWORD)
    client = TestClient(app)
    login(client)
    return app, client


def setup_case(app, client):
    w = post(client, "/api/workspaces", json={"name": "Authorized test client"}).json()["id"]
    assert (
        post(client, "/api/users", json={"username": "reviewer", "password": PASSWORD}).status_code
        == 201
    )
    assert (
        client.put(
            f"/api/workspaces/{w}/members", json={"username": "reviewer", "role": "reviewer"}
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/workspaces/{w}/policy",
            json={
                "revision": 1,
                "policy": {
                    "name": "Owned test policy",
                    "instructions": "Review evidence fairly.",
                    "required_documents": ["complaint", "policy"],
                    "egress_enabled": True,
                },
            },
        ).status_code
        == 200
    )
    right = post(
        client,
        f"/api/workspaces/{w}/rights",
        json={
            "basis": "owned_test",
            "reference": "Test-author permission to use engineering fixtures",
            "expires": time.time() + 86400,
            "egress": True,
        },
    ).json()["id"]
    c = post(client, "/api/cases", json={"workspace": w, "context": CONTEXT}).json()["id"]
    for revision, kind in ((1, "complaint"), (2, "policy")):
        r = post(
            client,
            f"/api/cases/{c}/sources",
            data={"revision": revision, "kind": kind, "rights_id": right},
            files={
                "file": (kind + ".txt", b"Policy and service need separate review.", "text/plain")
            },
        )
        assert r.status_code == 201, r.text
    return w, c, right


def test_http_intake_debate_review_and_current_export(service):
    app, c = service
    _w, case, _right = setup_case(app, c)
    preview = c.get(f"/api/cases/{case}/egress-preview").json()
    j = post(c, f"/api/cases/{case}/runs", json={"binding": preview["binding"]}).json()["id"]
    assert Controller(app.state.store, ControlledProvider()).once()
    run = c.get(f"/api/runs/{j}").json()
    assert run["packet"]["approved"] is False
    assert c.get(f"/api/runs/{j}/export").json()["label"] == "UNAPPROVED DRAFT"
    review = {
        "packet_hash": run["packet_hash"],
        "reason": "Independent human check of the authored fixture.",
        "response": "Approved for the fixture only.",
        "resolutions": {},
        "overrides": {},
    }
    assert post(c, f"/api/runs/{j}/reviews", json=review).status_code == 403
    reviewer = TestClient(app)
    login(reviewer, "reviewer")
    assert post(reviewer, f"/api/runs/{j}/reviews", json=review).status_code == 201
    assert reviewer.get(f"/api/runs/{j}/export?reviewed=true").json()["approved"]
    old = app.state.store.case("owner", case)
    app.state.store.update_case(
        "owner", case, old["revision"], {**CONTEXT, "facts": "A new material fact"}, "revision"
    )
    assert reviewer.get(f"/api/runs/{j}/export?reviewed=true").status_code == 409


def test_unauthenticated_csrf_origin_and_cross_workspace_access(service):
    app, c = service
    _w, case, _right = setup_case(app, c)
    stranger = TestClient(app)
    assert stranger.get(f"/api/cases/{case}").status_code == 401
    app.state.store.add_user("owner", "other", PASSWORD)
    login(stranger, "other")
    assert stranger.get(f"/api/cases/{case}").status_code == 404
    assert (
        c.post(
            "/api/workspaces", headers={"X-CSRF-Token": "wrong"}, json={"name": "Other"}
        ).status_code
        == 403
    )
    assert (
        post(
            c, "/api/workspaces", headers={"origin": "https://evil.example"}, json={"name": "Other"}
        ).status_code
        == 403
    )


def test_sources_require_rights_and_expiry_blocks_old_run_reads(service):
    app, c = service
    w, case, right = setup_case(app, c)
    preview = c.get(f"/api/cases/{case}/egress-preview").json()
    j = post(c, f"/api/cases/{case}/runs", json={"binding": preview["binding"]}).json()["id"]
    app.state.store.revoke_rights("owner", w, right)
    assert c.get(f"/api/runs/{j}").status_code == 403
    assert c.get(f"/api/cases/{case}/egress-preview").status_code == 409


def test_real_sensitive_validation_input_is_not_echoed(service):
    _, c = service
    r = post(c, "/api/users", json={"username": "bad", "password": "private"})
    assert r.status_code == 422 and "private" not in r.text


def test_ready_requires_current_schema_and_worker_heartbeat(service):
    app, client = service
    assert client.get("/health/ready").status_code == 503
    app.state.store.beat()
    assert client.get("/health/ready").status_code == 200


def test_admin_policy_retry_does_not_reactivate_or_conflict(service):
    app, client = service
    w, _case, _right = setup_case(app, client)
    current = app.state.store.workspace("owner", w)
    body = {
        "revision": current["policy_revision"],
        "policy": {**current["policy"], "name": "Revised test policy"},
    }
    headers = {"Idempotency-Key": "one-policy-intent"}
    assert client.put(f"/api/workspaces/{w}/policy", json=body, headers=headers).status_code == 200
    assert client.put(f"/api/workspaces/{w}/policy", json=body, headers=headers).status_code == 200
    assert (
        app.state.store.workspace("owner", w)["policy_revision"] == current["policy_revision"] + 1
    )
    body["policy"]["name"] = "Conflicting intent"
    assert client.put(f"/api/workspaces/{w}/policy", json=body, headers=headers).status_code == 409
