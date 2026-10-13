import pytest
from contracts.tenderlens import Claim, DraftBrief, PageLookupResult, SourceCitation
from pydantic import ValidationError


def test_material_claim_requires_citation():
    with pytest.raises(ValidationError):
        Claim(kind="deadline", value="2026-12-01", status="verified", citations=[])


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        SourceCitation(document_id="doc-1", page=1, quote="Apply by noon", invented=True)


def test_page_lookup_result_rejects_invalid_page():
    with pytest.raises(ValidationError):
        PageLookupResult(document_id="doc-1", page=0, text="hello")


def test_draft_brief_schema_and_round_trip():
    brief = DraftBrief(
        schema_version="1.0",
        title="Example tender",
        claims=[Claim(kind="buyer", value="City Council", status="unverified", citations=[])],
        open_questions=[],
    )
    assert DraftBrief.model_validate_json(brief.model_dump_json()) == brief
    assert DraftBrief.model_json_schema()["type"] == "object"
