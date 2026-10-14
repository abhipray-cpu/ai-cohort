"""ResolveDesk contracts: evidence labels are distinct from human approval."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseInput(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    question: str = Field(min_length=1, max_length=20000)
    server_version: str | None = Field(default=None, pattern=r"^\d{1,2}(\.\d{1,3})?$")
    client_version: str | None = Field(default=None, pattern=r"^\d{1,2}(\.\d{1,3})?$")
    os: str | None = Field(default=None, max_length=80)


class Citation(StrictModel):
    passage_id: str = Field(min_length=1, max_length=100)
    quote: str = Field(min_length=8, max_length=4000)


class RetrievedPassage(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    snapshot_id: str = Field(min_length=1, max_length=100)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=3500)
    title: str = Field(max_length=200)
    url: str = Field(max_length=2000)
    version: Literal["16", "17"]
    visibility: Literal["public", "internal"]
    origin: Literal["indexed", "search"]
    heading: str = Field(default="", max_length=1000)
    anchor: str = Field(default="", max_length=500)
    score: float = 0


class AnswerClaim(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    text: str = Field(min_length=3, max_length=3000)
    version: str = Field(pattern=r"^(16|17|both)$")
    category: Literal["diagnosis", "explanation", "next_check", "caution"]
    citations: list[Citation] = Field(min_length=1, max_length=5)


class AnswerDraft(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    claims: list[AnswerClaim] = Field(max_length=12)
    reply_order: list[str] = Field(max_length=12)
    questions: list[str] = Field(max_length=8)
    limitations: list[str] = Field(max_length=12)
    evidence_state: Literal["supported", "partial", "conflicting", "insufficient"]

    @model_validator(mode="after")
    def reference_integrity(self):
        ids = [c.id for c in self.claims]
        if len(set(ids)) != len(ids) or len(set(self.reply_order)) != len(self.reply_order):
            raise ValueError("Claim IDs and reply references must be unique")
        if set(ids) != set(self.reply_order):
            raise ValueError("Every claim must appear exactly once in reply_order")
        if not self.claims and self.evidence_state == "supported":
            raise ValueError("An empty answer cannot be supported")
        return self


class SupportVerdict(StrictModel):
    supported_claim_ids: list[str] = Field(max_length=12)
    unsupported_claim_ids: list[str] = Field(max_length=12)
    conflicting_claim_ids: list[str] = Field(max_length=12)
    reason: str = Field(min_length=1, max_length=1500)


class ReviewAction(StrictModel):
    expected_revision: int = Field(ge=1)
    action: Literal["approve", "edit", "escalate"]
    reason: str = Field(min_length=3, max_length=1000)
    claim_texts: dict[str, str] = Field(default_factory=dict, max_length=12)
    acknowledge_limits: bool = False
    allow_internal: bool = False


class SourceInput(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    version: Literal["16", "17"]
    text: str = Field(min_length=20, max_length=2000000)
    visibility: Literal["public", "internal"] = "internal"


class SearchHit(StrictModel):
    url: str = Field(min_length=8, max_length=2000)
    title: str = Field(max_length=500)
    snippet: str = Field(default="", max_length=4000)


class ChatCreate(StrictModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)
    server_version: str | None = Field(default=None, pattern=r"^\d{1,2}(\.\d{1,3})?$")
    client_version: str | None = Field(default=None, pattern=r"^\d{1,2}(\.\d{1,3})?$")
    os: str | None = Field(default=None, max_length=80)


class ChatMessage(StrictModel):
    content: str = Field(min_length=1, max_length=8000)
    expected_turn_count: int = Field(ge=0)

    @model_validator(mode="after")
    def nonblank(self):
        if not self.content.strip():
            raise ValueError("Message cannot be blank")
        return self


class ChatResolution(StrictModel):
    question: str = Field(min_length=1, max_length=4000)
    documentation_versions: list[Literal["16", "17"]] = Field(min_length=1, max_length=2)
    server_version: str | None = Field(pattern=r"^\d{1,2}(\.\d{1,3})?$")
    client_version: str | None = Field(pattern=r"^\d{1,2}(\.\d{1,3})?$")
    os: str | None = Field(max_length=80)
    needs_clarification: bool
    questions: list[str] = Field(max_length=4)

    @model_validator(mode="after")
    def clarification_has_question(self):
        if self.needs_clarification and not self.questions:
            raise ValueError("Clarification requires a concrete question")
        return self
