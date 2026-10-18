from catalogbridge_api.api import create_app
from catalogbridge_api.ingest import parse_feed
from fastapi.testclient import TestClient
from test_catalogbridge_api import batch

pytest_plugins = ["test_catalogbridge_api"]


def test_idempotent_batch_creation_and_payload_conflict(web):
    client, _store = web
    b = batch(client)
    response = client.post("/api/batches", json=b["spec"], headers={"Idempotency-Key": "one-batch"})
    replay = client.post("/api/batches", json=b["spec"], headers={"Idempotency-Key": "one-batch"})
    assert response.json()["id"] == replay.json()["id"]
    changed = client.post(
        "/api/batches",
        json=b["spec"] | {"token_budget": 1234},
        headers={"Idempotency-Key": "one-batch"},
    )
    assert changed.status_code == 409


def test_literal_whitespace_is_preserved_and_blank_titles_rejected():
    row = parse_feed(b'id,title\na,"  Literal product  "', "csv")[0]
    assert row.title == "  Literal product  "
    import pytest

    with pytest.raises(ValueError):
        parse_feed(b'id,title\na,"   "', "csv")


def test_manual_master_lookup_is_scoped_and_unknown_is_404(web):
    client, _store = web
    b = batch(client)
    source = client.get(f"/api/feeds/{b['spec']['master_id']}/record", params={"id": "x"})
    assert source.status_code == 200 and source.json()["title"] == "Crucial 8GB"
    assert (
        client.get(
            f"/api/feeds/{b['spec']['master_id']}/record", params={"id": "missing"}
        ).status_code
        == 404
    )


def test_health_does_not_claim_live_model_acceptance(tmp_path):
    client = TestClient(create_app(tmp_path, username="owner", password="long-test-password"))
    ready = client.get("/health/ready").json()
    assert ready["hard_token_limit"] is False
    assert ready["ai_acceptance"] == "unverified"
