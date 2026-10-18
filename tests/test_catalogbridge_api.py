import pytest
from catalogbridge_api.api import create_app
from catalogbridge_api.auth import add_user
from catalogbridge_api.worker import run_once
from fastapi.testclient import TestClient


@pytest.fixture
def web(tmp_path):
    app = create_app(tmp_path, username="owner", password="long-test-password")
    client = TestClient(app)
    response = client.post(
        "/api/session", json={"username": "owner", "password": "long-test-password"}
    )
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf"]
    return client, app.state.store


def feed(client, kind, body="id,title\nx,Crucial 8GB\n"):
    r = client.post(
        "/api/feeds",
        params={"kind": kind, "format": "csv"},
        content=body,
        headers={"Content-Type": "text/csv"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def batch(client):
    master = feed(client, "master")
    supplier = feed(client, "supplier")
    response = client.post(
        "/api/batches", json={"master_id": master, "supplier_id": supplier, "egress": False}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_auth_csrf_and_owner_bootstrap_are_not_bypassed(web, tmp_path):
    client, store = web
    assert TestClient(client.app).get("/api/batches").status_code == 401
    assert (
        client.post(
            "/api/feeds",
            content="id,title\nx,ok",
            params={"kind": "master"},
            headers={"X-CSRF-Token": "bad"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/feeds", content="", headers={"Origin": "https://evil.invalid"}
        ).status_code
        == 403
    )
    with pytest.raises(ValueError, match="existing"):
        add_user(store, "owner", "other-password", "default", "owner")


def test_local_profile_status_is_authenticated_and_exposes_no_paths_or_weights(
    web, tmp_path, monkeypatch
):
    import json

    from test_catalogbridge_local_router import profile

    client, _ = web
    assert TestClient(client.app).get("/api/routing-profile").status_code == 401
    monkeypatch.delenv("CATALOGBRIDGE_ROUTER_PROFILE", raising=False)
    assert client.get("/api/routing-profile").json()["available"] is False
    path = tmp_path / "private-profile.json"
    path.write_text(json.dumps(profile()))
    monkeypatch.setenv("CATALOGBRIDGE_ROUTER_PROFILE", str(path))
    result = client.get("/api/routing-profile").json()
    assert result["available"] and not result["automatic_acceptance"]
    assert "private-profile" not in json.dumps(result) and "trees" not in result


def test_real_http_manual_workflow_export_and_stale_review(web):
    client, store = web
    b = batch(client)
    assert client.post(f"/api/batches/{b['id']}/start").status_code == 200
    run_once(store)
    task = client.get(f"/api/batches/{b['id']}/tasks").json()[0]
    assert task["state"] == "needs_review"
    empty = client.post(f"/api/batches/{b['id']}/exports").json()
    assert empty["manifest"]["included"] == 0
    response = client.post(
        f"/api/tasks/{task['id']}/review",
        json={
            "expected_revision": task["revision"],
            "action": "correct",
            "candidate_id": "x",
            "reason": "Checked original supplied fields",
        },
    )
    assert response.status_code == 200, response.text
    assert (
        client.post(
            f"/api/tasks/{task['id']}/review",
            json={"expected_revision": task["revision"], "action": "reject", "reason": "stale"},
        ).status_code
        == 409
    )
    exported = client.post(f"/api/batches/{b['id']}/exports").json()
    assert exported["manifest"]["included"] == 1
    assert "x,x,owner" in exported["csv"]
    assert client.get(f"/api/batches/{b['id']}/analytics").json()["rows"] == 1


def test_runtime_acknowledgement_is_owner_only_and_never_releases_unknown_usage(web):
    client, store = web
    b = batch(client)
    task = store.tasks("default", b["id"])[0]
    store.settle(store.reserve(b["id"], task["id"], "economy", 100), None)
    assert client.get("/api/runtime").json()["open"]
    assert (
        client.post(
            "/api/runtime/acknowledge", json={"reason": "Investigated runtime availability"}
        ).status_code
        == 409
    )
    add_user(store, "reader", "another-long-password", "default", "reviewer")
    reviewer = TestClient(client.app)
    login = reviewer.post(
        "/api/session", json={"username": "reader", "password": "another-long-password"}
    )
    reviewer.headers["X-CSRF-Token"] = login.json()["csrf"]
    assert (
        reviewer.post(
            "/api/runtime/acknowledge", json={"reason": "Investigated runtime availability"}
        ).status_code
        == 403
    )
    assert store.analytics("default", b["id"])["reserved_tokens"] == 100


def test_owner_cannot_self_declare_empirical_calibration(web):
    client, _ = web
    body = {
        "id": "claimed",
        "binding": "fixture",
        "threshold": 0.99,
        "precision_lower_bound": 0.995,
        "accepted_samples": 1000,
        "economy_score": 0.995,
        "strong_score": 0.995,
        "evidence_status": "empirically_verified",
    }
    assert client.post("/api/calibrations", json=body).status_code == 409
    body["evidence_status"] = "operator_attested"
    response = client.post("/api/calibrations", json=body)
    assert response.status_code == 200
    assert response.json()["evidence_status"] == "operator_attested_not_independently_verified"


def test_other_workspace_cannot_read_feeds_tasks_or_analytics(web):
    client, store = web
    b = batch(client)
    add_user(store, "other", "another-password", "other-space", "owner")
    other = TestClient(client.app)
    assert (
        other.post(
            "/api/session", json={"username": "other", "password": "another-password"}
        ).status_code
        == 200
    )
    for path in [
        f"/api/batches/{b['id']}",
        f"/api/batches/{b['id']}/tasks",
        f"/api/batches/{b['id']}/analytics",
        f"/api/feeds/{b['spec']['master_id']}",
    ]:
        assert other.get(path).status_code == 404


def test_reviewer_cannot_authorize_budget_or_model_egress(web):
    client, store = web
    b = batch(client)
    add_user(store, "reviewer", "reviewer-password", "default", "reviewer")
    viewer = TestClient(client.app)
    r = viewer.post("/api/session", json={"username": "reviewer", "password": "reviewer-password"})
    viewer.headers["X-CSRF-Token"] = r.json()["csrf"]
    assert (
        viewer.post(f"/api/batches/{b['id']}/budget-increases", json={"tokens": 10}).status_code
        == 403
    )
    assert viewer.post("/api/batches", json=b["spec"]).status_code == 403


def test_formula_export_and_unknown_fields(web):
    client, store = web
    m = feed(client, "master", "id,title\n=evil,Crucial 8GB\n")
    s = feed(client, "supplier", "id,title\n+evil,Crucial 8GB\n")
    b = client.post("/api/batches", json={"master_id": m, "supplier_id": s}).json()
    client.post(f"/api/batches/{b['id']}/start")
    run_once(store)
    t = store.tasks("default", b["id"])[0]
    client.post(
        f"/api/tasks/{t['id']}/review",
        json={
            "expected_revision": t["revision"],
            "action": "correct",
            "candidate_id": "=evil",
            "reason": "fixture",
        },
    )
    assert "'+evil,'=evil" in client.post(f"/api/batches/{b['id']}/exports").json()["csv"]
    assert (
        client.post(
            "/api/feeds", params={"kind": "master"}, content="id,title,label\na,x,1"
        ).status_code
        == 422
    )
