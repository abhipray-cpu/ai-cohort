from fastapi.testclient import TestClient
from repairclaim_api.api import BASE, create_app
from repairclaim_api.worker import run_once
from test_repairclaim_workflow import FixtureParser, flow, make_pdf, register


def client_for(store, user="owner"):
    client = TestClient(
        create_app(
            store, public_origin="http://localhost", secure_cookies=False, parser=FixtureParser()
        ),
        base_url="http://localhost",
    )
    client.headers["origin"] = "http://localhost"
    login = client.post(
        BASE + "/sessions", json={"username": user, "password": "workflow-test-password"}
    )
    client.headers["x-csrf-token"] = login.json()["csrf_token"]
    return client


def test_http_local_document_casework_and_private_controls(flow):
    store, _, _, _, vehicle, case = flow
    register(store)
    client = client_for(store)
    assert client.get(BASE + "/me").json()["csrf_token"]
    assert client.get(BASE + "/vehicles").status_code == 200
    upload = client.post(
        BASE + f"/cases/{case['id']}/documents?filename=invoice.pdf&kind=invoice&revision=2",
        content=make_pdf("Repair mileage: 90000 mi"),
        headers={"content-type": "application/octet-stream"},
    )
    assert upload.status_code == 202, upload.text
    run_once(store, parser=FixtureParser())
    doc = upload.json()
    assert (
        client.post(
            BASE + f"/documents/{doc['id']}/confirm", json={"selected": [0], "expected_revision": 3}
        ).status_code
        == 200
    )
    job = client.post(
        BASE + f"/cases/{case['id']}/investigations",
        json={"expected_revision": 4, "key": "http-job"},
    ).json()
    run_once(store, parser=FixtureParser())
    packet = client.post(
        BASE + f"/cases/{case['id']}/packets",
        json={"job_id": job["id"], "recipient": "Dealer", "key": "http-packet"},
    ).json()
    render = client.post(BASE + f"/packets/{packet['id']}/render", json={})
    assert render.status_code == 202, render.text
    run_once(store, parser=FixtureParser())
    rendered = client.get(BASE + f"/packets/{packet['id']}").json()
    assert (
        client.get(BASE + f"/packets/{packet['id']}/preview?page=1").headers["content-type"]
        == "image/png"
    )
    assert client.post(BASE + f"/packets/{packet['id']}/download", json={}).status_code == 409
    assert (
        client.post(
            BASE + f"/packets/{packet['id']}/approve", json={"fingerprint": rendered["fingerprint"]}
        ).status_code
        == 200
    )
    assert client.post(BASE + f"/packets/{packet['id']}/download", json={}).content.startswith(
        b"PK"
    )
    assert (
        client.post(
            BASE + f"/vehicles/{vehicle['id']}/monitoring",
            json={"case_ids": [case["id"]], "ttl": 86400},
        ).status_code
        == 200
    )
    assert client.get(BASE + f"/cases/{case['id']}/workspace").json()["monitoring"]
    invite = client.post(BASE + f"/cases/{case['id']}/invitations", json={"role": "viewer"}).json()
    other = client_for(store, "other")
    assert (
        other.post(BASE + "/invitations/accept", json={"invitation": invite["token"]}).status_code
        == 200
    )
    assert other.get(BASE + f"/cases/{case['id']}/workspace").status_code == 200
    assert other.get(BASE + f"/cases/{case['id']}/export").status_code == 404
    assert client.get(BASE + f"/cases/{case['id']}/export").content.startswith(b"PK")


def test_upload_boundary_and_cross_household_denial(flow):
    store, _, _, _, _, case = flow
    client = client_for(store, "other")
    assert client.get(BASE + f"/cases/{case['id']}/workspace").status_code == 404
    assert (
        client.post(
            BASE + "/cases/missing/documents?filename=a.pdf&kind=invoice&revision=1",
            content=b"%PDF",
            headers={"content-type": "application/octet-stream", "x-csrf-token": "bad"},
        ).status_code
        == 403
    )


def test_http_outcomes_reminders_response_and_invitation_revocation(flow):
    store, _, owner, _, _, case = flow
    client = client_for(store)
    for kind in ("requested", "confirmed_covered", "approved", "received", "avoided_cost"):
        result = client.post(
            BASE + f"/cases/{case['id']}/outcomes",
            json={
                "key": kind,
                "event": {
                    "id": kind,
                    "kind": kind,
                    "amount": {"amount": "123.45", "currency": "USD"},
                    "evidence_class": "user_reported",
                    "evidence_ref": "user-statement",
                    "repair_line_id": "line",
                },
            },
        )
        assert result.status_code == 201, result.text
    reminder = client.post(
        BASE + f"/cases/{case['id']}/reminders",
        json={
            "due_at": "2026-11-01T12:00:00Z",
            "timezone": "UTC",
            "provenance": "user_entered",
            "label": "Fixture follow-up",
        },
    )
    assert reminder.status_code == 201, reminder.text
    assert client.delete(BASE + f"/reminders/{reminder.json()['id']}").status_code == 204
    invitation = client.post(
        BASE + f"/cases/{case['id']}/invitations", json={"role": "editor"}
    ).json()
    workspace = client.get(BASE + f"/cases/{case['id']}/workspace").json()
    assert "token_hash" not in str(workspace["invitations"])
    assert client.delete(BASE + f"/invitations/{invitation['id']}").status_code == 204
    other = client_for(store, "other")
    assert (
        other.post(
            BASE + "/invitations/accept", json={"invitation": invitation["token"]}
        ).status_code
        == 404
    )
    from test_repairclaim_continuity import upload

    document = upload(store, owner.token, case["id"], "Please provide missing records.")
    response = client.post(
        BASE + f"/cases/{case['id']}/responses",
        json={"document_id": document["id"], "key": "response"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["comparison"]["manufacturer_confirmation"] is False


def test_http_frozen_source_preview_and_readiness_do_not_fetch_or_call_provider(flow):
    store, *_ = flow
    programme = register(store)
    client = client_for(store)
    anchor = programme.conditions[0].anchor
    assert client.get(
        BASE + f"/sources/{anchor.document_id}/revisions/{anchor.sha256}/preview"
    ).content.startswith(b"\x89PNG")
    assert client.get("/health/ready").status_code == 503
    assert client.get(BASE + "/capabilities").json()["codex_enabled"] is False
