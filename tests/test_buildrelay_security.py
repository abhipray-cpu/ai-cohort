import httpx
import pytest
from buildrelay_api.api import create_app
from buildrelay_api.github import GitHub
from buildrelay_api.workflow import Failure
from fastapi.testclient import TestClient
from test_buildrelay_api import login


def test_owner_can_revoke_access_but_cannot_remove_last_owner(tmp_path):
    app = create_app(tmp_path, username="owner", password="test-password-123")
    app.state.store.create_client("client", "Shop")
    owner = TestClient(app)
    login(owner, password="test-password-123")
    owner.post(
        "/api/users",
        json={
            "username": "operator",
            "password": "operator-test-password",
            "role": "operator",
            "clients": ["client"],
        },
    )
    other = TestClient(app)
    login(other, "operator", "operator-test-password")
    assert other.get("/api/overview").json()["clients"]
    assert owner.put("/api/users/operator/grants", json={"clients": []}).status_code == 200
    assert other.get("/api/overview").json()["clients"] == []
    assert owner.delete("/api/users/operator").status_code == 200
    assert other.get("/api/overview").status_code == 401
    assert owner.delete("/api/users/owner").status_code == 409


def test_unsafe_log_redirect_never_receives_a_request():
    calls = []
    gh = GitHub(httpx.Client(transport=httpx.MockTransport(lambda r: calls.append(r))))
    for url in (
        "http://127.0.0.1/private",
        "https://evil.test/logs",
        "https://githubusercontent.com.evil.test/logs",
    ):
        with pytest.raises(Failure):
            gh.download(url)
    assert calls == []


def test_unknown_client_cannot_be_granted(tmp_path):
    c = TestClient(create_app(tmp_path, username="owner", password="test-password-123"))
    login(c, password="test-password-123")
    assert (
        c.post(
            "/api/users",
            json={
                "username": "viewer",
                "password": "viewer-test-password",
                "role": "viewer",
                "clients": ["missing"],
            },
        ).status_code
        == 409
    )
