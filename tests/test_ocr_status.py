import shutil

import pymupdf
import pytest
from tenderlens_api.store import Store


def test_image_only_pdf_is_not_silently_treated_as_text(tmp_path):
    pdf = pymupdf.open()
    pdf.new_page()
    data = pdf.tobytes()
    pdf.close()
    store = Store(tmp_path)
    opportunity = store.create_opportunity("Scanned tender")
    document = store.add_document(opportunity["id"], "scan.pdf", data)
    assert store.page(document["id"], 1)["quality"] == "needs_ocr"


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract not installed")
def test_image_only_page_is_ocr_readable(tmp_path):
    source = pymupdf.open()
    page = source.new_page()
    page.insert_text((72, 100), "Technical proposal maximum points 70", fontsize=18)
    page.insert_text((72, 140), "Supplier must provide two client references", fontsize=18)
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    scanned = pymupdf.open()
    scan_page = scanned.new_page(width=page.rect.width, height=page.rect.height)
    scan_page.insert_image(scan_page.rect, stream=pixmap.tobytes("png"))
    data = scanned.tobytes()
    assert not pymupdf.open(stream=data, filetype="pdf")[0].get_text().strip()
    source.close()
    scanned.close()

    store = Store(tmp_path)
    opportunity = store.create_opportunity("Scanned tender")
    document = store.add_document(opportunity["id"], "scan.pdf", data)
    result = store.page(document["id"], 1)
    assert result["quality"] == "ocr"
    assert "maximum points 70" in result["text"].lower()
    assert "client references" in result["text"].lower()
