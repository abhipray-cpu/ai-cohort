import hashlib
from pathlib import Path

import pytest
from tenderlens_api.store import Store
from tenderlens_api.worker import run_once

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "data/tenderlens/raw/unicef-montenegro-lrps-2026-9202732.pdf"
)


@pytest.mark.skipif(not SOURCE.exists(), reason="download seed PDF from manifest")
def test_public_unicef_rfp_extracts_real_pages_and_evidence(tmp_path):
    data = SOURCE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == (
        "f64e41551ec6bd0287373ca0d1d3fef7edd1ff2da10e660c3be18b60069a8e2d"
    )
    store = Store(tmp_path)
    opportunity = store.create_opportunity("UNICEF Montenegro graphic design")
    document = store.add_document(opportunity["id"], SOURCE.name, data)
    assert document["page_count"] == 2
    page = store.page(document["id"], 1)
    assert "Technical proposal - Maximum points: 70" in page["text"]
    assert "At least 2 references" in page["text"]

    class DeterministicProvider:
        def generate(self, *, prompt, schema):
            from agent_core.provider import StructuredGeneration

            return StructuredGeneration(
                text=(
                    '{"schema_version":"1.0","title":"UNICEF graphic design RFP",'
                    '"claims":[{"kind":"evaluation_criterion",'
                    '"value":"Technical proposal: 70 points","status":"verified",'
                    f'"citations":[{{"document_id":"{document["id"]}","page":1,'
                    '"quote":"Technical proposal - Maximum points: 70"}]}],'
                    '"open_questions":[]}'
                ),
                exit_code=0,
                elapsed_ms=1,
            )

    run_id = store.create_run(opportunity["id"])["id"]
    assert run_once(store, DeterministicProvider()) == run_id
    result = store.run(run_id)
    assert result["status"] == "draft"
    assert result["brief"]["claims"][0]["status"] == "verified"
