import pytest
from casecouncil_api.evidence import evidence_for, extract, validate_citations
from contracts.casecouncil import Citation


def test_redaction_does_not_claim_raw_offsets():
    source = extract("source", "sample.txt", b"Policy: token=secret-value\nRefund if covered.")
    assert "secret-value" not in source["text"]
    assert source["original_hash"] != source["text_hash"]
    assert source["mapping"] == "redacted canonical Unicode offsets; not raw PDF offsets"


def test_exact_unicode_offsets_selected_membership_and_corruption():
    source = extract("s", "source.txt", "Policy café 😀 requires premiums.".encode())
    ev = evidence_for([source])
    span = ev["spans"][0]
    citation = Citation(source_id="s", start=span["start"], end=span["end"], quote=span["text"])
    validate_citations([citation], ev)
    for patch in ({"end": citation.end + 1}, {"source_id": "another"}, {"quote": "invented"}):
        with pytest.raises(ValueError):
            validate_citations([citation.model_copy(update=patch)], ev)
    ev["sources"][0]["text"] = "corrupt"
    with pytest.raises(ValueError):
        validate_citations([citation], ev)


def test_partial_large_text_and_unsupported_inputs():
    ev = evidence_for([extract("s", "big.txt", ("paragraph of evidence\n" * 6000).encode())])
    assert ev["partial"] and sum(len(s["text"]) for s in ev["spans"]) <= 64000
    for name, data in (("evil.zip", b"PK"), ("bad.pdf", b"not a pdf"), ("x.txt", b"\xff")):
        with pytest.raises(ValueError):
            extract("s", name, data)


def test_actual_pdf_child_parser_and_unreadable_or_encrypted_inputs():
    import pymupdf as fitz

    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 72), "Personally authored policy: premiums are due monthly.")
        raw = pdf.tobytes()
        encrypted = pdf.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner-password",
            user_pw="reader-password",
        )
    parsed = extract("pdf", "policy.pdf", raw)
    assert "premiums are due monthly" in parsed["text"]
    with pytest.raises(ValueError):
        extract("pdf", "locked.pdf", encrypted)
    with fitz.open() as pdf:
        pdf.new_page()
        blank = pdf.tobytes()
    with pytest.raises(ValueError):
        extract("pdf", "no-text.pdf", blank)
