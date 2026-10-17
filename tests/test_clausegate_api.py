from clausegate_api.api import create_app
from fastapi.testclient import TestClient
from test_clausegate_core import setup


def signed(client, actor):
    r = client.post(
        "/v1/auth/session", json={"username": actor, "password": "long-test-password-123"}
    )
    assert r.status_code == 200
    client.headers["X-CSRF-Token"] = r.json()["csrf"]


def test_real_session_csrf_scope_and_strict_fields(tmp_path):
    store, c = setup(tmp_path)
    app = create_app(store=store)
    a, b = TestClient(app), TestClient(app)
    assert a.get("/v1/cases").status_code == 401
    signed(a, "owner")
    signed(b, "outsider")
    assert a.get(f"/v1/cases/{c['id']}").status_code == 200
    assert b.get(f"/v1/cases/{c['id']}").status_code == 403
    assert b.get(f"/v1/documents/{c['document_id']}").status_code == 403
    assert b.get("/v1/approval-requests").json() == []
    assert (
        a.put(
            f"/v1/cases/{c['id']}/context",
            headers={"Origin": "https://attacker.example"},
            json={"expected_revision": c["revision"], "side": "mutual", "purpose": "Testing"},
        ).status_code
        == 403
    )
    token = a.headers.pop("X-CSRF-Token")
    assert a.post("/v1/workspaces", json={"name": "Bad mutation"}).status_code == 403
    a.headers["X-CSRF-Token"] = token
    assert a.post("/v1/workspaces", json={"name": "Strict", "admin": True}).status_code == 422


def test_no_public_readiness_private_counts_and_no_force_resume(tmp_path):
    s, c = setup(tmp_path)
    client = TestClient(create_app(store=s))
    assert client.get("/health/live").json() == {"status": "live"}
    assert "case" not in str(client.get("/health/ready").json())
    signed(client, "owner")
    r = client.post(f"/v1/cases/{c['id']}/resume", json={"force": True})
    assert r.status_code in {409, 422}
    assert client.get(f"/v1/cases/{c['id']}/export").status_code == 409
