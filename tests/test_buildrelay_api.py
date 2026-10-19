import hashlib
import hmac
import json

import pytest
from buildrelay_api.api import create_app
from fastapi.testclient import TestClient
from test_buildrelay_transports import payload


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("BUILDRELAY_SHOP_SECRET", "a-secret-for-testing")
    a = create_app(tmp_path, username="owner", password="a-secure-test-password")
    s = a.state.store
    s.create_client("client", "Shop")
    s.create_client("other", "Other client")
    s.create_repo(
        "repo",
        "client",
        "acme/shop",
        123,
        "BUILDRELAY_SHOP_SECRET",
        "BUILDRELAY_SHOP_TOKEN",
        "Engineering",
        False,
    )
    return a


def login(client, name="owner", password="a-secure-test-password"):
    r = client.post("/api/session", json={"username": name, "password": password})
    assert r.status_code == 200, r.text
    client.headers["X-CSRF-Token"] = r.json()["csrf"]


def signed(client, body=None, signature=None):
    b = json.dumps(body or payload()).encode()
    sig = signature or "sha256=" + hmac.new(b"a-secret-for-testing", b, hashlib.sha256).hexdigest()
    return client.post(
        "/hooks/github/repo",
        content=b,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Delivery": "d1",
            "X-GitHub-Event": "workflow_run",
        },
    )


def test_webhook_auth_raw_body_limits_and_durable_dedup(app):
    c = TestClient(app)
    assert signed(c, signature="sha256=invalid").status_code == 401
    assert (
        c.post(
            "/hooks/github/repo", content=b"{}", headers=[(b"X-Hub-Signature-256", b"\xff")]
        ).status_code
        == 401
    )
    assert signed(c).status_code == 202
    assert signed(c).status_code == 202
    assert len(app.state.store.events()) == 1
    assert c.get("/api/overview").status_code == 401
    assert c.post("/hooks/github/repo", content=b"x" * 2_000_001).status_code == 413


def test_login_csrf_and_no_client_data_leak(app):
    c = TestClient(app)
    login(c)
    assert c.get("/api/overview").status_code == 200
    assert (
        c.post("/api/clients", json={"name": "new"}, headers={"X-CSRF-Token": "bad"}).status_code
        == 403
    )
    assert (
        c.post(
            "/api/users",
            json={
                "username": "viewer",
                "password": "viewer-password-123",
                "role": "viewer",
                "clients": ["other"],
            },
        ).status_code
        == 201
    )
    signed(c)
    outsider = TestClient(app)
    login(outsider, "viewer", "viewer-password-123")
    overview = outsider.get("/api/overview").json()
    assert overview["repos"] == [] and overview["events"] == []
    ident = app.state.store.events()[0]["id"]
    assert outsider.get(f"/api/events/{ident}").status_code == 404
    assert (
        outsider.post(
            f"/api/events/{ident}/replay", json={"reason": "reviewed failure"}
        ).status_code
        == 403
    )


def test_origin_check_logout_and_credential_validation(app, tmp_path):
    c = TestClient(app)
    login(c)
    assert (
        c.post(
            "/api/users",
            json={
                "username": "lead",
                "password": "a-second-owner-password",
                "role": "owner",
                "clients": [],
            },
        ).status_code
        == 201
    )
    login(c, "lead", "a-second-owner-password")
    assert c.post("/api/clients", json={"name": "Lead's client"}).status_code == 201
    assert (
        next(a for a in app.state.store.audit() if a["action"] == "client_created")["actor"]
        == "lead"
    )
    assert (
        c.post(
            "/api/clients", json={"name": "new"}, headers={"Origin": "https://attacker.test"}
        ).status_code
        == 403
    )
    assert c.delete("/api/session").status_code == 200
    assert c.get("/api/overview").status_code == 401
    with pytest.raises(ValueError):
        create_app(tmp_path / "weak", username="owner", password="replace-me")


def test_repo_config_does_not_return_or_accept_secret_values(app):
    c = TestClient(app)
    login(c)
    r = c.post(
        "/api/repos",
        json={
            "client_id": "other",
            "name": "acme/other",
            "github_id": 999,
            "secret_ref": "PATH",
            "token_ref": "BUILDRELAY_OTHER_TOKEN",
            "owner": "QA",
            "issues": False,
        },
    )
    assert r.status_code == 422
    assert "a-secret-for-testing" not in c.get("/api/overview").text


def test_readiness_reports_worker_absence_not_fake_ready(app):
    c = TestClient(app)
    r = c.get("/health/ready")
    assert r.status_code == 503
    assert r.json()["status"] == "degraded"
    app.state.store.beat("workflow")
    assert c.get("/health/ready").status_code == 200
