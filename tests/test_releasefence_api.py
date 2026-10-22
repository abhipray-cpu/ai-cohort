from fastapi.testclient import TestClient
from releasefence_api.api import create_app
from test_releasefence_store import configured, rf, rf_admin  # noqa: F401


def login(client, user="owner", password="owned-password-123"):
    response = client.post("/api/session", json={"username": user, "password": password})
    assert response.status_code == 200, response.text
    client.headers.update({"Origin": "http://testserver", "X-CSRF-Token": response.json()["csrf"]})


def test_http_auth_csrf_scope_and_machine_credentials(rf):
    s, a, b = rf
    _, _, _, enrolled = configured(rf)
    with TestClient(create_app(s, origin="http://testserver", administrator="owner")) as c:
        assert c.get(f"/api/orgs/{a}/release").status_code == 401
        login(c)
        assert c.get(f"/api/orgs/{a}/release").status_code == 200
        assert (
            c.post(
                "/api/orgs", json={"name": "Denied"}, headers={"X-CSRF-Token": "bad"}
            ).status_code
            == 403
        )
        assert c.get("/health/live").json() == {"live": True}
        assert c.get("/api/orgs").headers["x-content-type-options"] == "nosniff"
        c.post("/api/session/logout")
        login(c, "reviewer", "review-password-123")
        assert c.get(f"/api/orgs/{b}/release").status_code == 403
        assert (
            c.post(
                f"/api/orgs/{a}/environment",
                json={"application": "support", "environment": "prod", "stable": "a" * 64},
            ).status_code
            == 403
        )
    with TestClient(create_app(s, origin="http://testserver", administrator="owner")) as machine:
        machine.headers["Authorization"] = "Bearer " + enrolled["token"]
        assert machine.post("/ingest/v1/events", json={"events": []}).status_code == 200
        assert machine.post(f"/connector/v1/{enrolled['id']}/poll").status_code == 200
        assert machine.post("/connector/v1/other/poll").status_code == 403
        from contracts.releasefence import Span
        from releasefence_api.telemetry import otlp

        span = Span(
            trace_id="1" * 32,
            span_id="2" * 16,
            name="agent",
            release=s.list("owner", a, "release")[0]["id"],
            started_ns=1,
            ended_ns=2,
        )
        assert machine.post("/ingest/v1/traces", json=otlp([span])).status_code == 200


def test_http_bounded_requests_and_redacted_validation_errors(rf):
    s, _, _ = rf
    with TestClient(create_app(s, origin="http://testserver", administrator="owner")) as c:
        assert c.post("/api/session", content=b"x" * 1048577).status_code == 413
        assert (
            c.post(
                "/api/session", content=b"compressed", headers={"Content-Encoding": "gzip"}
            ).status_code
            == 415
        )
        response = c.post(
            "/api/session", json={"username": "owner", "password": "PRIVATE", "extra": "SECRET"}
        )
        assert response.status_code == 422
        assert "PRIVATE" not in response.text and "SECRET" not in response.text


def test_ci_credential_registers_only_its_application_and_never_controls_runtime(rf):
    from test_releasefence_core import release

    s, t, _ = rf
    configured(rf)
    credential = s.registration_token("owner", t, "support", "staging", 1600)
    with TestClient(
        create_app(s, origin="http://testserver", administrator="owner"),
        headers={"Authorization": "Bearer " + credential["token"]},
    ) as client:
        assert (
            client.post(
                "/registry/v1/releases", json=release(index_digest="f" * 64).model_dump()
            ).status_code
            == 200
        )
        manifest = release().model_dump()
        manifest["application"] = "other"
        assert client.post("/registry/v1/releases", json=manifest).status_code == 403
        assert client.post("/ingest/v1/events", json={"events": []}).status_code == 403
    s.now = lambda: 1601
    with TestClient(
        create_app(s, origin="http://testserver", administrator="owner"),
        headers={"Authorization": "Bearer " + credential["token"]},
    ) as client:
        assert client.post("/registry/v1/releases", json=release().model_dump()).status_code == 403
