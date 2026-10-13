"""Version 1 TenderLens contracts used at every external boundary."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClaimKind(StrEnum):
    BUYER = "buyer"
    PROCUREMENT_ID = "procurement_id"
    DEADLINE = "deadline"
    SCOPE = "scope"
    ELIGIBILITY = "eligibility"
    REQUIRED_DOCUMENT = "required_document"
    TECHNICAL_REQUIREMENT = "technical_requirement"
    EVALUATION_CRITERION = "evaluation_criterion"
    DISQUALIFIER = "disqualifier"
    FINANCIAL_TERM = "financial_term"


class SourceCitation(StrictModel):
    document_id: str = Field(min_length=1)
    page: StrictInt = Field(ge=1)
    quote: str = Field(min_length=1)


class Claim(StrictModel):
    kind: ClaimKind
    value: str = Field(min_length=1)
    status: Literal["verified", "unverified", "unresolved"] = "unverified"
    mandatory: bool = False
    citations: list[SourceCitation] = Field(default_factory=list)

    @model_validator(mode="after")
    def verified_needs_evidence(self) -> Claim:
        if self.status == "verified" and not self.citations:
            raise ValueError("verified claim requires a citation")
        return self


class DraftBrief(StrictModel):
    schema_version: Literal["1.0"]
    title: str = Field(min_length=1)
    claims: list[Claim]
    open_questions: list[str]


class PageLookupRequest(StrictModel):
    document_id: str = Field(min_length=1)
    page: StrictInt = Field(ge=1)


class PageLookupResult(StrictModel):
    document_id: str = Field(min_length=1)
    page: StrictInt = Field(ge=1)
    text: str


class ReviewAction(StrictModel):
    status: Literal["accepted", "edited", "unresolved"]
    value: str | None = None
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def edited_needs_value(self) -> ReviewAction:
        if self.status == "edited" and not self.value:
            raise ValueError("edited review requires a value")
        return self
