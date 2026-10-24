"""In-process HTTP boundary checks. Not actual-browser, inference or private-data acceptance."""

import pytest
from fastapi.testclient import TestClient
from repairclaim_api.api import app_from_env, create_app
from repairclaim_api.store import Store

BASE = "/api/repairclaim/v1"
ORIGIN = "https://repairclaim.test"
PASSWORD = "api-test-only-strong-password"


@pytest.fixture
def api(tmp_path):
    store = Store(tmp_path / "repairclaim.sqlite3")
    store.provision_owner("owner", PASSWORD)
    other = store.provision_owner("other", PASSWORD)
    return store, create_app(store, public_origin=ORIGIN), other


def login(app, name="owner"):
    client = TestClient(app, base_url=ORIGIN)
    response = client.post(
        f"{BASE}/sessions",
        json={"username": name, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    csrf = response.json()["csrf_token"]
    client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": csrf})
    return client, response


def make_case(client):
    vehicle = client.post(
        f"{BASE}/vehicles",
        json={"make": "Honda", "model": "Fixture", "model_year": 2018, "jurisdiction": "US"},
    )
    assert vehicle.status_code == 201
    response = client.post(
        f"{BASE}/cases", json={"vehicle_id": vehicle.json()["id"], "title": "Fixture repair"}
    )
    assert response.status_code == 201
    return response.json()


def test_login_sets_scoped_secure_cookie_without_exposing_session_token(api):
    _, app, _ = api
    client, response = login(app)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=strict" in cookie
    assert f"path={BASE}" in cookie
    assert "token" not in response.json()  # only csrf_token, not the authentication secret
    assert client.get(f"{BASE}/me").json()["username"] == "owner"


def test_unauthenticated_and_wrong_origin_requests_do_not_mutate(api):
    _, app, _ = api
    client = TestClient(app, base_url=ORIGIN)
    assert client.get(f"{BASE}/cases").status_code == 401
    response = client.post(
        f"{BASE}/sessions",
        json={"username": "owner", "password": PASSWORD},
        headers={"Origin": "https://attacker.test"},
    )
    assert response.status_code == 403
    assert "set-cookie" not in response.headers


def test_csrf_is_required_for_writes_but_reads_work_after_login(api):
    _, app, _ = api
    client, _ = login(app)
    client.headers.pop("X-CSRF-Token")
    assert client.get(f"{BASE}/cases").status_code == 200
    assert (
        client.post(f"{BASE}/cases", json={"vehicle_id": "fake", "title": "fake"}).status_code
        == 403
    )


def test_fact_update_and_timeline_are_scoped_and_revision_checked(api):
    _, app, _ = api
    client, _ = login(app)
    case = make_case(client)
    facts = client.get(f"{BASE}/cases/{case['id']}/snapshot").json()["facts"]
    facts.append(
        {"field": "repair_mileage", "value": "90000", "unit": "mi", "status": "user_reported"}
    )
    payload = {"expected_revision": 1, "facts": facts}
    url = f"{BASE}/cases/{case['id']}/fact-revisions"
    response = client.post(url, json=payload)
    assert response.status_code == 200
    assert response.json()["revision"] == 2
    assert client.post(url, json=payload).status_code == 409
    assert len(client.get(f"{BASE}/cases/{case['id']}/timeline").json()) == 2
    other, _ = login(app, "other")
    for suffix in ("", "/snapshot", "/timeline"):
        assert other.get(f"{BASE}/cases/{case['id']}{suffix}").status_code == 404
    assert other.post(url, json=payload).status_code == 404
    assert other.get(f"{BASE}/cases").json() == []


def test_grant_read_edit_and_revocation_are_enforced_on_the_next_request(api):
    _, app, target = api
    owner, _ = login(app)
    other, _ = login(app, "other")
    case = make_case(owner)
    grant = owner.post(
        f"{BASE}/cases/{case['id']}/grants", json={"user_id": target["id"], "role": "viewer"}
    )
    assert grant.status_code == 201
    assert other.get(f"{BASE}/cases/{case['id']}").status_code == 200
    assert (
        other.post(
            f"{BASE}/cases/{case['id']}/fact-revisions", json={"expected_revision": 1, "facts": []}
        ).status_code
        == 404
    )
    assert owner.delete(f"{BASE}/cases/{case['id']}/grants/{target['id']}").status_code == 204
    assert other.get(f"{BASE}/cases/{case['id']}").status_code == 404


def test_delete_needs_revision_and_erases_access(api):
    _, app, _ = api
    client, _ = login(app)
    case = make_case(client)
    url = f"{BASE}/cases/{case['id']}"
    assert client.delete(url).status_code == 422
    assert client.delete(url, headers={"If-Match": "2"}).status_code == 409
    assert client.delete(url, headers={"If-Match": "1"}).status_code == 204
    assert client.get(url).status_code == 404


def test_logout_clears_cookie_and_revokes_the_original_secret(api):
    store, app, _ = api
    client, _ = login(app)
    raw = client.cookies.get("repairclaim_session")
    assert client.delete(f"{BASE}/sessions/current").status_code == 204
    assert client.get(f"{BASE}/me").status_code == 401
    from repairclaim_api.errors import DomainError

    with pytest.raises(DomainError):
        store.authenticate(raw)


def test_validation_errors_do_not_echo_credentials_or_raw_values(api):
    _, app, _ = api
    client = TestClient(app, base_url=ORIGIN)
    response = client.post(
        f"{BASE}/sessions",
        json={"username": "owner", "password": "PRIVATE-PASSWORD", "extra": "PRIVATE-INJECTED"},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 422
    assert "PRIVATE" not in response.text
    client, _ = login(app)
    response = client.post(
        f"{BASE}/vehicles",
        json={"make": "Honda", "model": "PRIVATE-MODEL", "model_year": True, "jurisdiction": "US"},
    )
    assert response.status_code == 422
    assert "PRIVATE" not in response.text


def test_json_size_limit_applies_with_and_without_content_length(api):
    _, app, _ = api
    client, _ = login(app)
    body = b'{"title":"' + b"x" * 70000 + b'"}'
    for content in (body, iter([body[:35000], body[35000:]])):
        response = client.post(
            f"{BASE}/cases", content=content, headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 413


def test_api_headers_disable_sensitive_caching_and_analysis_requires_valid_input(api):
    _, app, _ = api
    client, _ = login(app)
    response = client.get(f"{BASE}/me")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert client.get("/health/live").json()["stage"] == "implementation"
    assert client.post(f"{BASE}/cases/nonexistent/investigations", json={}).status_code == 422
    assert (
        client.post(
            f"{BASE}/cases/nonexistent/investigations",
            json={"expected_revision": 1, "key": "absent"},
        ).status_code
        == 404
    )


def test_factory_requires_explicit_own_configuration_without_borrowing_credentials(monkeypatch):
    for key in ("REPAIRCLAIM_DATA_DIR", "REPAIRCLAIM_PUBLIC_ORIGIN"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="REPAIRCLAIM"):
        app_from_env()


@pytest.mark.parametrize(
    "origin", ["*", "https://a.test/path", "https://user:pass@a.test", "http://public.test"]
)
def test_unsafe_public_origin_is_rejected(api, origin):
    store, _, _ = api
    with pytest.raises(ValueError):
        create_app(store, public_origin=origin)


def test_duplicate_keys_nonfinite_json_and_wrong_content_type_are_rejected(api):
    _, app, _ = api
    client, _ = login(app)
    for body in ('{"title":"a","title":"b"}', '{"value":NaN}'):
        response = client.post(
            f"{BASE}/cases", content=body, headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        assert response.json()["code"] == "invalid_json"
    assert (
        client.post(
            f"{BASE}/cases", content="{}", headers={"Content-Type": "text/plain"}
        ).status_code
        == 415
    )


def test_absurd_content_length_is_rejected_without_integer_conversion_failure(api):
    _, app, _ = api
    client, _ = login(app)
    response = client.post(
        f"{BASE}/cases",
        content="{}",
        headers={"Content-Type": "application/json", "Content-Length": "9" * 5000},
    )
    assert response.status_code == 400


def test_untrusted_host_is_rejected_even_with_an_allowed_origin(api):
    _, app, _ = api
    client, _ = login(app)
    assert client.get(f"{BASE}/me", headers={"Host": "attacker.test"}).status_code == 400
