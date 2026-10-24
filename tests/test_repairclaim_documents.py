"""Authored documents only. No manufacturer data or real consumer records."""

import hashlib

import pymupdf
import pytest
from repairclaim_api.documents import parse_document, render_packet, sanitized_attachment
from repairclaim_api.errors import DomainError


def pdf(text="Repair mileage: 90000 mi\nInvoice total: USD 1200.50\nDiagnostic code: P0301"):
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((50, 70), text)
    result = document.tobytes()
    document.close()
    return result


def test_pdf_parse_preserves_exact_bytes_hash_pages_and_unconfirmed_fact_proposals():
    raw = pdf()
    result = parse_document(raw, "invoice.pdf")
    assert result["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["page_count"] == 1
    assert "90000" in result["pages"][0]["text"]
    proposal = next(item for item in result["proposals"] if item["field"] == "repair_mileage")
    assert proposal["value"] == "90000"
    assert proposal["status"] == "extracted"
    assert proposal["page"] == 1


def test_dealer_dtc_code_label_is_supported_without_promoting_estimate_to_payment():
    result = parse_document(
        pdf(
            "diagnose check engine light dtc code\n|\n|\np0133,p0430,p0153\nSub Total: 109.95\nPre-Invoice"
        ),
        "dealer.pdf",
    )
    codes = [p for p in result["proposals"] if p["field"] == "diagnostic_code"]
    assert len(codes) == 1
    assert codes[0]["value"] == "P0133"
    assert codes[0]["quote"] in result["pages"][0]["text"]
    assert not any(p["field"] in {"paid_amount", "payment_proof"} for p in result["proposals"])


@pytest.mark.parametrize(
    "data,name",
    [(b"<script>bad</script>", "bill.pdf"), (b"PK\x03\x04", "archive.zip"), (b"", "empty.pdf")],
)
def test_bad_or_unsupported_uploads_are_not_successful_extractions(data, name):
    with pytest.raises(DomainError):
        parse_document(data, name)


def test_encrypted_pdf_is_rejected():
    source = pymupdf.open(stream=pdf(), filetype="pdf")
    encrypted = source.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret"
    )
    source.close()
    with pytest.raises(DomainError, match="encrypted_document"):
        parse_document(encrypted, "bill.pdf")


def test_redaction_is_rasterized_and_removes_underlying_text_metadata_and_links():
    raw = pdf("PRIVATE-ADDRESS\nRepair compressor\nUSD 1200.50")
    result = sanitized_attachment(raw, "bill.pdf", ["PRIVATE-ADDRESS"])
    document = pymupdf.open(stream=result, filetype="pdf")
    assert "PRIVATE-ADDRESS" not in "".join(page.get_text() for page in document)
    assert all(not page.get_links() and not list(page.annots() or []) for page in document)
    assert document.embfile_count() == 0
    assert len(document[0].get_images()) >= 1
    document.close()
    with pytest.raises(DomainError, match="redaction_not_found"):
        sanitized_attachment(raw, "bill.pdf", ["NOT-PRESENT"])


def test_packet_paginates_and_has_draft_watermark_without_clipping():
    data = render_packet(
        title="Coverage enquiry",
        paragraphs=["Source-supported text " * 15] * 80,
        manifest_hash="a" * 64,
        approved=False,
    )
    document = pymupdf.open(stream=data, filetype="pdf")
    text = "\n".join(page.get_text() for page in document)
    assert len(document) > 1
    assert "UNAPPROVED" in text
    assert text.count("Source-supported") == 80 * 15
    for page in document:
        for word in page.get_text("words"):
            assert 0 <= word[0] < word[2] <= page.rect.width
            assert 0 <= word[1] < word[3] <= page.rect.height
    document.close()


def test_jpeg_and_png_are_accepted_but_oversized_images_are_not():
    source = pymupdf.open(stream=pdf("Image fixture"), filetype="pdf")
    image = source[0].get_pixmap().tobytes("png")
    result = parse_document(image, "scan.png", ocr=False)
    assert result["page_count"] == 1
    assert result["needs_ocr"] is True
    source.close()
