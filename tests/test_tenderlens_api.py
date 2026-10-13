import base64

import pymupdf
from fastapi.testclient import TestClient
from tenderlens_api.api import create_app
from tenderlens_api.worker import run_once


class FixedProvider:
    def generate(self, *, prompt, schema):
        from agent_core.provider import StructuredGeneration

        return StructuredGeneration(
            text='{"schema_version":"1.0","title":"City roads","claims":[{"kind":"deadline","value":"1 Dec 2026","status":"verified","citations":[{"document_id":"DOC_ID","page":1,"quote":"Deadline 1 Dec 2026"}]}],"open_questions":[]}'.replace(
                "DOC_ID", prompt.split("Document ")[1].split(",")[0]
            ),
            exit_code=0,
            elapsed_ms=1,
        )


def sample_pdf():
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "City roads tender. Deadline 1 Dec 2026")
    data = document.tobytes()
    document.close()
    return data


def auth():
    return {"Authorization": "Basic " + base64.b64encode(b"reviewer:secret").decode()}


def test_upload_run_review_export_end_to_end(tmp_path):
    app = create_app(data_dir=tmp_path, username="reviewer", password="secret")
    client = TestClient(app)
    assert client.get("/v1/opportunities").status_code == 401

    opportunity = client.post(
        "/v1/opportunities", json={"title": "City roads"}, headers=auth()
    ).json()
    response = client.post(
        f"/v1/opportunities/{opportunity['id']}/documents",
        files={"file": ("tender.pdf", sample_pdf(), "application/pdf")},
        headers=auth(),
    )
    assert response.status_code == 201
    document = response.json()
    assert document["page_count"] == 1

    created = client.post(f"/v1/opportunities/{opportunity['id']}/runs", headers=auth())
    assert created.status_code == 202
    run_id = created.json()["id"]
    assert run_once(app.state.store, FixedProvider()) == run_id

    result = client.get(f"/v1/runs/{run_id}", headers=auth()).json()
    assert result["status"] == "draft"
    assert result["brief"]["claims"][0]["status"] == "verified"
    claim_id = result["brief"]["claims"][0]["id"]
    assert client.post(f"/v1/runs/{run_id}/exports", headers=auth()).status_code == 409
    review = client.patch(
        f"/v1/claims/{claim_id}/review",
        json={"status": "accepted", "reason": "Checked source page"},
        headers=auth(),
    )
    assert review.status_code == 200
    export = client.post(f"/v1/runs/{run_id}/exports", headers=auth())
    assert export.status_code == 200
    assert export.json()["claims"][0]["review_status"] == "accepted"


def test_upload_rejects_non_pdf(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, username="reviewer", password="secret"))
    opportunity = client.post("/v1/opportunities", json={"title": "Roads"}, headers=auth()).json()
    response = client.post(
        f"/v1/opportunities/{opportunity['id']}/documents",
        files={"file": ("bad.pdf", b"not a pdf", "application/pdf")},
        headers=auth(),
    )
    assert response.status_code == 422


def test_document_route_requires_authentication(tmp_path):
    app = create_app(data_dir=tmp_path, username="reviewer", password="secret")
    client = TestClient(app)
    opportunity = app.state.store.create_opportunity("Private tender")
    document = app.state.store.add_document(opportunity["id"], "tender.pdf", sample_pdf())
    assert client.get(f"/v1/documents/{document['id']}/file").status_code == 401
    assert client.get(f"/v1/documents/{document['id']}/file", headers=auth()).status_code == 200


def test_uncited_claim_cannot_be_accepted_or_exported(tmp_path):
    from contracts.tenderlens import Claim, DraftBrief

    app = create_app(data_dir=tmp_path, username="reviewer", password="secret")
    store = app.state.store
    opportunity = store.create_opportunity("Uncited example")
    with store.connect() as db:
        db.execute(
            "INSERT INTO runs(id,opportunity_id,status,document_hashes,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?)",
            ("run-uncited", opportunity["id"], "running", "{}", "2026-01-01", "2026-01-01"),
        )
    store.finish_run(
        "run-uncited",
        DraftBrief(
            schema_version="1.0",
            title="Uncited example",
            claims=[Claim(kind="scope", value="Build roads", citations=[])],
            open_questions=[],
        ),
    )
    client = TestClient(app)
    claim_id = store.run("run-uncited")["brief"]["claims"][0]["id"]
    response = client.patch(
        f"/v1/claims/{claim_id}/review",
        json={"status": "accepted", "reason": "Looks fine"},
        headers=auth(),
    )
    assert response.status_code == 409
    assert client.post("/v1/runs/run-uncited/exports", headers=auth()).status_code == 409


def test_worker_persists_validation_failure_and_repair(tmp_path):
    from agent_core.provider import StructuredGeneration

    class RepairingProvider:
        calls = 0

        def generate(self, *, prompt, schema):
            self.calls += 1
            text = (
                "not json"
                if self.calls == 1
                else '{"schema_version":"1.0","title":"Recovered","claims":[],"open_questions":[]}'
            )
            return StructuredGeneration(text=text, exit_code=0, elapsed_ms=1)

    app = create_app(data_dir=tmp_path, username="reviewer", password="secret")
    store = app.state.store
    opportunity = store.create_opportunity("Repair case")
    store.add_document(opportunity["id"], "tender.pdf", sample_pdf())
    run_id = store.create_run(opportunity["id"])["id"]
    run_once(store, RepairingProvider())
    result = store.run(run_id)
    assert result["status"] == "draft"
    assert len(result["events"]) == 1
    assert result["events"][0]["stage"] == "parse"
    assert result["events"][0]["attempt"] == 1
