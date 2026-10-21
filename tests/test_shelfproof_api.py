import json

from fastapi.testclient import TestClient
from shelfproof_api.api import create_app
from shelfproof_api.store import Store
from shelfproof_api.workflow import Worker
from test_shelfproof_core import draft, evaluation, facts
from test_shelfproof_workflow import Provider


def clients(tmp_path):
    store = Store(tmp_path)
    store.create_user("maker", "long-password-123")
    store.create_user("checker", "different-password-456")
    workspace = store.create_workspace("maker", "Demo")
    store.add_member("maker", workspace, "checker", "reviewer")
    app = create_app(store)
    client = TestClient(app)
    response = client.post(
        "/api/session", json={"username": "maker", "password": "long-password-123"}
    )
    assert response.status_code == 200
    headers = {"X-CSRF-Token": response.json()["csrf"], "Origin": "http://testserver"}
    return store, workspace, client, headers, app


def test_real_http_contract_import_to_independent_review_patch(tmp_path):
    store, workspace, client, headers, app = clients(tmp_path)
    grant = client.post(
        f"/api/workspaces/{workspace}/rights",
        headers=headers,
        json={
            "basis": "Owned fixture for software test only",
            "expires": store.now() + 3600,
            "max_calls": 8,
            "egress": True,
        },
    ).json()["id"]
    raw = json.dumps([facts().model_dump(mode="json")]).encode()
    preview = client.post(
        f"/api/workspaces/{workspace}/imports/preview",
        headers=headers,
        files={"file": ("facts.json", raw, "application/json")},
    )
    assert preview.status_code == 200
    assert preview.json()["columns"] == list(type(facts()).model_fields)
    mapping = {key: key for key in type(facts()).model_fields}
    frozen = client.post(
        f"/api/workspaces/{workspace}/imports",
        headers=headers,
        data={"mapping": json.dumps(mapping)},
        files={"file": ("facts.json", raw, "application/json")},
    )
    assert frozen.status_code == 200
    response = client.post(
        f"/api/workspaces/{workspace}/tasks",
        headers={**headers, "Idempotency-Key": "one"},
        json={"import_id": frozen.json()["id"], "row": 0, "grant": grant},
    )
    assert response.status_code == 200, response.text
    task = response.json()["id"]
    Worker(store, Provider([draft(), evaluation()])).run_once()
    current = client.get(f"/api/tasks/{task}").json()
    version = current["selected_hash"]
    checker = TestClient(app)
    login = checker.post(
        "/api/session", json={"username": "checker", "password": "different-password-456"}
    )
    checked = checker.post(
        f"/api/tasks/{task}/reviews",
        headers={"X-CSRF-Token": login.json()["csrf"], "Origin": "http://testserver"},
        json={
            "version_hash": version,
            "decision": "accept",
            "reason": "Compared with source",
            "artifact_hash": current["selected_artifact_hash"],
        },
    )
    assert checked.status_code == 200
    patch = client.post(f"/api/workspaces/{workspace}/exports", headers=headers)
    assert patch.json()["approved_count"] == 1


def test_csrf_origin_scope_and_login_throttle(tmp_path):
    _, workspace, client, headers, app = clients(tmp_path)
    assert client.post("/api/workspaces", json={"name": "x"}).status_code == 403
    assert (
        client.post(
            "/api/workspaces",
            headers={**headers, "Origin": "https://evil.example"},
            json={"name": "x"},
        ).status_code
        == 403
    )
    assert TestClient(app).get(f"/api/workspaces/{workspace}/tasks").status_code == 401
    anonymous = TestClient(app)
    for _ in range(10):
        response = anonymous.post(
            "/api/session", json={"username": "unknown", "password": "invalid"}
        )
    assert response.status_code == 429


def test_health_no_model_invocation_and_oversized_mapping_is_rejected(tmp_path):
    _, _, client, _, _ = clients(tmp_path)
    assert client.get("/health/live").status_code == 200
    # Readiness is unavailable without a worker heartbeat, not fabricated healthy.
    assert client.get("/health/ready").status_code == 503


def test_batch_policy_and_csv_routes_are_scoped(tmp_path):
    store, workspace, client, headers, _ = clients(tmp_path)
    policy = client.post(
        f"/api/workspaces/{workspace}/policy",
        headers={**headers, "Idempotency-Key": "brief"},
        json={"brief": "Neutral factual copy."},
    )
    assert policy.status_code == 200
    grant = store.authorize(
        "maker", workspace, basis="owned", expires=store.now() + 60, max_calls=16, egress=True
    )
    from shelfproof_api.core import freeze_import

    raw = json.dumps([facts().model_dump(mode="json")]).encode()
    source = store.save_import(
        "maker",
        workspace,
        raw,
        freeze_import(raw, "json", {k: k for k in type(facts()).model_fields}),
    )
    batch = client.post(
        f"/api/workspaces/{workspace}/batches",
        headers={**headers, "Idempotency-Key": "batch"},
        json={"import_id": source, "rows": [0], "grant": grant},
    )
    assert batch.status_code == 200
    batch_id = batch.json()["id"]
    preview = client.get(f"/api/batches/{batch_id}/egress-preview").json()
    assert (
        client.post(
            f"/api/batches/{batch_id}/start", headers=headers, json={"binding": preview["binding"]}
        ).status_code
        == 200
    )
    assert client.get(f"/api/batches/{batch_id}").json()["total_rows"] == 1
    csv = client.get(f"/api/workspaces/{workspace}/review.csv")
    assert csv.status_code == 200 and "text/csv" in csv.headers["content-type"]
    imports = client.get(f"/api/workspaces/{workspace}/imports").json()
    assert imports[0]["id"] == source and "raw" not in imports[0]
    batches = client.get(f"/api/workspaces/{workspace}/batches").json()
    assert batches[0]["id"] == batch_id
    tasks = client.get(f"/api/workspaces/{workspace}/tasks").json()
    assert tasks[0]["name"] == facts().name and tasks[0]["batch_id"] == batch_id


def test_oversized_csv_cell_is_a_bounded_input_error_not_server_crash(tmp_path):
    _, workspace, client, headers, _ = clients(tmp_path)
    response = client.post(
        f"/api/workspaces/{workspace}/imports/preview",
        headers=headers,
        files={"file": ("facts.csv", b"id\n" + b"x" * 200000 + b"\n", "text/csv")},
    )
    assert response.status_code == 422


def test_import_errors_identify_row_and_field_without_echoing_private_value(tmp_path):
    _, workspace, client, headers, _ = clients(tmp_path)
    broken = facts().model_dump(mode="json")
    broken["net_quantity"] = "private-invalid-value"
    result = client.post(
        f"/api/workspaces/{workspace}/imports",
        headers=headers,
        data={"mapping": json.dumps({k: k for k in broken})},
        files={"file": ("facts.json", json.dumps([broken]).encode(), "application/json")},
    )
    assert result.status_code == 422
    assert result.json()["issues"][0]["row"] == 1
    assert result.json()["issues"][0]["field"] == "net_quantity"
    assert "private-invalid-value" not in result.text
