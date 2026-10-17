import io
import zipfile

import pytest
from clausegate_api.intake import archive_members, normalize_dataset, text_document


def test_archive_traversal_and_expansion_are_rejected():
    for name in ["../escape.json", "/absolute.json", "C:/escape.json", "bad\\escape.json"]:
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w") as z:
            z.writestr(name, "{}")
        with pytest.raises(ValueError):
            archive_members(raw.getvalue())
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as z:
        z.writestr("train.json", "x" * 100)
    with pytest.raises(ValueError):
        archive_members(raw.getvalue(), max_bytes=50)


def test_explicit_quarantine_never_extracts_an_unsafe_member():
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as z:
        z.writestr("raw/T:\\source.pdf", "inert")
        z.writestr("train.json", "{}")
    quarantine = []
    assert archive_members(raw.getvalue(), quarantined=quarantine) == {"train.json": b"{}"}
    assert quarantine == ["raw/T:\\source.pdf"]


def test_unicode_spans_and_missing_annotations_are_not_invented():
    text = "Confidentialité 🔐\nReturn all copies.\nExcept archival backups."
    doc = text_document(text, "nda.txt")
    assert doc["complete"] and doc["text"] == text
    assert all(text[s["start"] : s["end"]] == s["quote"] for s in doc["spans"])
    raw = {
        "documents": [{"id": 1, "text": text, "spans": [[0, 16]], "annotation_sets": []}],
        "labels": {},
    }
    with pytest.raises(ValueError):
        normalize_dataset(raw, "train")


def test_dataset_gold_stays_outside_model_document():
    raw = {
        "documents": [
            {
                "id": 1,
                "text": "Return copies.",
                "spans": [[0, 14]],
                "annotation_sets": [{"annotations": {"h": {"choice": "Entailment", "spans": [0]}}}],
            }
        ],
        "labels": {"h": {"hypothesis": "Copies must be returned."}},
    }
    rows = normalize_dataset(raw, "test")
    assert rows[0]["gold"]["h"]["choice"] == "Entailment"
    assert "gold" not in rows[0]["document"] and "annotation_sets" not in rows[0]["document"]
    assert rows[0]["split"] == "test"


def test_mixed_image_and_text_pdf_does_not_claim_complete_ocr(monkeypatch):
    import pymupdf
    from clausegate_api.intake import pdf_document

    class Page:
        def get_text(self, mode):
            return "Heading only; agreement body is an image."

        def get_images(self, full=True):
            return [(1,)]

    class PDF:
        is_encrypted = False

        def __len__(self):
            return 1

        def __iter__(self):
            return iter([Page()])

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(pymupdf, "open", lambda **kwargs: PDF())
    doc = pdf_document(b"labelled parser mock", "mixed.pdf")
    assert not doc["complete"] and any("image" in g.lower() for g in doc["gaps"])


@pytest.mark.parametrize("quote", ["Return copies.", "Invented text."])
def test_exact_quote_resolver_rejects_ambiguous_or_invented_text(quote):
    from clausegate_api.intake import resolve_evidence

    spans = [{"id": "s0", "start": 10, "end": 39, "quote": "Return copies. Return copies."}]
    with pytest.raises(ValueError):
        resolve_evidence(
            spans, {"evidence_ids": ["s0"], "evidence_quotes": [{"span_id": "s0", "quote": quote}]}
        )
