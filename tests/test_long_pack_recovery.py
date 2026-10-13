import base64
import hashlib
import json
import re
import sys

import pymupdf
import pytest
from agent_core.provider import ProviderTimeoutError, StructuredGeneration
from contracts.tenderlens import DraftBrief
from fastapi.testclient import TestClient
from tenderlens_api.api import create_app
from tenderlens_api.store import Store
from tenderlens_api.worker import run_once

from scripts import benchmark_public_evaluation


def long_pdf(pages=5):
    document = pymupdf.open()
    for number in range(1, pages + 1):
        page = document.new_page()
        page.insert_text((72, 72), f"Page marker {number}. Required item {number}.")
    data = document.tobytes()
    document.close()
    return data


class ThresholdProvider:
    def __init__(self, max_pages=2, fail_page=None):
        self.max_pages = max_pages
        self.fail_page = fail_page
        self.calls = []

    def generate(self, *, prompt, schema):
        pages = [(document_id, int(number)) for document_id, number in re.findall(
            r"Document ([^,]+), page (\d+):", prompt
        )]
        self.calls.append(pages)
        if len(pages) > self.max_pages or any(number == self.fail_page for _, number in pages):
            raise ProviderTimeoutError("Codex invocation timed out")
        return StructuredGeneration(
            text=json.dumps(
                {
                    "schema_version": "1.0",
                    "title": "Long pack",
                    "claims": [
                        {
                            "kind": "required_document",
                            "value": f"Required item {number}",
                            "status": "verified",
                            "citations": [{
                                "document_id": document_id,
                                "page": number,
                                "quote": f"Page marker {number}",
                            }],
                        }
                        for document_id, number in pages
                    ],
                    "open_questions": [],
                }
            ),
            exit_code=0,
            elapsed_ms=1,
        )


def queued_store(tmp_path):
    store = Store(tmp_path)
    opportunity = store.create_opportunity("Long pack")
    store.add_document(opportunity["id"], "long.pdf", long_pdf())
    run = store.create_run(opportunity["id"])
    return store, run["id"]


def test_adaptive_split_finishes_and_logs_timeouts(tmp_path):
    store, run_id = queued_store(tmp_path)
    provider = ThresholdProvider(max_pages=2)
    assert run_once(store, provider) == run_id
    result = store.run(run_id)
    assert result["status"] == "draft"
    assert sorted(claim["value"] for claim in result["brief"]["claims"]) == [
        f"Required item {number}" for number in range(1, 6)
    ]
    assert any(event["stage"] == "provider_timeout" for event in result["events"])
    assert result["progress"]["done"] == result["progress"]["total"]


def test_partial_brief_survives_timeout_and_retry_resumes_checkpoint(tmp_path):
    store, run_id = queued_store(tmp_path)
    assert run_once(store, ThresholdProvider(max_pages=2, fail_page=3)) == run_id
    partial = store.run(run_id)
    assert partial["status"] == "partial"
    assert partial["brief"] is not None
    assert {claim["value"] for claim in partial["brief"]["claims"]} == {
        "Required item 1", "Required item 2"
    }
    assert partial["progress"]["done"] < partial["progress"]["total"]
    try:
        store.export_run(run_id)
    except ValueError:
        pass
    else:
        raise AssertionError("partial run must never be exportable")
    claim_id = partial["brief"]["claims"][0]["id"]
    try:
        store.review_claim(claim_id, "accepted", None, "Looked at source")
    except ValueError:
        pass
    else:
        raise AssertionError("partial claim must not be approvable")

    client = TestClient(create_app(data_dir=tmp_path, username="reviewer", password="secret"))
    auth = {"Authorization": "Basic " + base64.b64encode(b"reviewer:secret").decode()}
    assert client.post(f"/v1/runs/{run_id}/retry").status_code == 401
    assert client.post(f"/v1/runs/{run_id}/retry", headers=auth).status_code == 202
    assert client.post(f"/v1/runs/{run_id}/retry", headers=auth).status_code == 409

    resumed_provider = ThresholdProvider(max_pages=2)
    assert run_once(store, resumed_provider) == run_id
    final = store.run(run_id)
    assert final["status"] == "draft"
    assert len(final["brief"]["claims"]) == 5
    assert all(1 not in [page for _, page in call] for call in resumed_provider.calls)
    assert all(2 not in [page for _, page in call] for call in resumed_provider.calls)


def test_public_benchmark_session_resumes_without_reingesting(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    source.write_bytes(long_pdf())
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"sources": [{
        "id": "test-pack",
        "case": "serbia",
        "local_path": "source.pdf",
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "pages": 5,
    }]}))
    monkeypatch.setattr(benchmark_public_evaluation, "ROOT", tmp_path)
    monkeypatch.setattr(benchmark_public_evaluation, "MANIFEST", manifest)
    monkeypatch.setattr(benchmark_public_evaluation, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(
        sys, "argv", ["benchmark_public_evaluation.py", "--case", "serbia", "--session", "resume"]
    )
    providers = []

    def provider_with_timeout():
        provider = ThresholdProvider(max_pages=2, fail_page=3)
        providers.append(provider)
        return provider

    monkeypatch.setattr(benchmark_public_evaluation, "LocalCodexProvider", provider_with_timeout)
    with pytest.raises(SystemExit) as first:
        benchmark_public_evaluation.main()
    assert first.value.code == 1
    first_report = json.loads((tmp_path / "reports/resume.json").read_text())
    assert first_report["status"] == "partial"
    assert first_report["progress"]["done"] > 0
    first_run_id = json.loads((tmp_path / "reports/sessions/resume/session.json").read_text())[
        "run_id"
    ]

    def provider_after_recovery():
        provider = ThresholdProvider(max_pages=2)
        providers.append(provider)
        return provider

    monkeypatch.setattr(
        benchmark_public_evaluation, "LocalCodexProvider", provider_after_recovery
    )
    benchmark_public_evaluation.main()
    final_report = json.loads((tmp_path / "reports/resume.json").read_text())
    assert final_report["status"] == "draft"
    assert final_report["progress"] == {"done": 4, "total": 4}
    assert final_report["codex_calls"] == len(providers[-1].calls)
    assert all(1 not in [page for _, page in call] for call in providers[-1].calls)
    assert all(2 not in [page for _, page in call] for call in providers[-1].calls)
    assert json.loads((tmp_path / "reports/sessions/resume/session.json").read_text())[
        "run_id"
    ] == first_run_id


def test_stale_running_job_resumes_saved_chunks_after_worker_crash(tmp_path):
    store, run_id = queued_store(tmp_path)
    claimed = store.claim_next_run()
    assert claimed["id"] == run_id
    document_id = store.documents_for(claimed["opportunity_id"])[0]["id"]
    store.ensure_chunks(run_id, [
        [(document_id, 1), (document_id, 2)],
        [(document_id, 3), (document_id, 4), (document_id, 5)],
    ])
    first_key = store.pending_chunks(run_id)[0][0]
    first_prompt = "\n".join(
        f"Document {document_id}, page {page}:\nPage marker {page}"
        for page in (1, 2)
    )
    first_output = ThresholdProvider(max_pages=2).generate(prompt=first_prompt, schema={})
    store.save_chunk(run_id, first_key, DraftBrief.model_validate_json(first_output.text))
    with store.connect() as db:
        db.execute("UPDATE runs SET updated_at='2000-01-01T00:00:00+00:00' WHERE id=?", (run_id,))

    resumed = ThresholdProvider(max_pages=2)
    assert run_once(store, resumed) == run_id
    result = store.run(run_id)
    assert result["status"] == "draft"
    assert len(result["brief"]["claims"]) == 5
    assert all(page > 2 for call in resumed.calls for _, page in call)
