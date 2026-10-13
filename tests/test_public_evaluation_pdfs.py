import hashlib
import json
from pathlib import Path

import pytest
from tenderlens_api.store import Store

ROOT = Path(__file__).resolve().parents[1]
SOURCES = json.loads(
    (ROOT / "data/tenderlens/manifests/public-evaluation-sources.json").read_text()
)["sources"]


@pytest.mark.parametrize("source", SOURCES, ids=lambda source: source["id"])
def test_public_pdf_ingestion_and_source_integrity(source, tmp_path):
    path = ROOT / source["local_path"]
    if not path.exists():
        pytest.skip("Run scripts/fetch_public_evaluation.py to download public sources")
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == source["sha256"]
    store = Store(tmp_path)
    opportunity = store.create_opportunity(source["id"])
    document = store.add_document(opportunity["id"], path.name, data)
    assert document["page_count"] == source["pages"]
    assert all(
        store.page(document["id"], page)["quality"] == "text"
        for page in range(1, document["page_count"] + 1)
    )


def test_serbia_source_has_conflicting_dates(tmp_path):
    source = next(source for source in SOURCES if source["id"] == "serbia-rfp")
    path = ROOT / source["local_path"]
    if not path.exists():
        pytest.skip("Run scripts/fetch_public_evaluation.py")
    store = Store(tmp_path)
    opportunity = store.create_opportunity("Serbia")
    document = store.add_document(opportunity["id"], path.name, path.read_bytes())
    special_notes = store.page(document["id"], 7)["text"]
    schedule = store.page(document["id"], 8)["text"]
    assert "18 February 2026" in special_notes
    assert "5 March 2026" in special_notes
    assert "9 March 2026" in schedule


def test_nepal_annex_has_mismatched_procurement_reference(tmp_path):
    rfp = next(source for source in SOURCES if source["id"] == "nepal-rfp")
    price = next(source for source in SOURCES if source["id"] == "nepal-price")
    if not (ROOT / rfp["local_path"]).exists() or not (ROOT / price["local_path"]).exists():
        pytest.skip("Run scripts/fetch_public_evaluation.py")
    store = Store(tmp_path)
    opportunity = store.create_opportunity("Nepal")
    rfp_doc = store.add_document(
        opportunity["id"], "rfp.pdf", (ROOT / rfp["local_path"]).read_bytes()
    )
    price_doc = store.add_document(
        opportunity["id"], "price.pdf", (ROOT / price["local_path"]).read_bytes()
    )
    assert "9205846" in store.page(rfp_doc["id"], 1)["text"]
    assert "9203888" in store.page(price_doc["id"], 1)["text"]
