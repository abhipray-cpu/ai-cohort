"""CaseCouncil's bounded, untrusted wire and generation contracts."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ROLES = ("customer", "insurer", "fairness")
Text = Annotated[str, Field(min_length=1, max_length=2000)]
Ident = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Citation(Strict):
    source_id: Ident
    start: int = Field(ge=0, strict=True)
    end: int = Field(gt=0, strict=True)
    quote: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("invalid citation range")
        return self


class Issue(Strict):
    id: Ident
    title: str = Field(min_length=3, max_length=200)


class Context(Strict):
    title: str = Field(min_length=3, max_length=200)
    # IE is permitted only by an explicitly isolated evaluation Store, not normal service intake.
    jurisdiction: Literal["UK", "IE"] = "UK"
    product: Literal["motor_insurance"] = "motor_insurance"
    issues: list[Issue] = Field(min_length=1, max_length=10)
    facts: str = Field(max_length=10000)
    draft: str = Field(max_length=10000)
    missing: list[Text] = Field(max_length=20)

    @model_validator(mode="after")
    def unique(self):
        if len({i.id for i in self.issues}) != len(self.issues):
            raise ValueError("duplicate issue")
        return self


class Candidate(Strict):
    issue_id: Ident
    disposition: Literal["uphold", "partial_uphold", "do_not_uphold", "undetermined"]
    remedy: Text
    conditions: list[Text] = Field(max_length=10)
    rationale: Text
    counterargument: Text
    citations: list[Citation] = Field(max_length=8)
    missing: list[Text] = Field(max_length=10)

    @model_validator(mode="after")
    def support(self):
        if self.disposition != "undetermined" and not self.citations:
            raise ValueError("substantive candidate requires source support")
        if self.disposition == "undetermined" and not self.missing:
            raise ValueError("undetermined requires named missing evidence")
        return self


class CritiqueResponse(Strict):
    finding_id: Ident
    action: Literal["accepted", "contested", "unresolved"]
    reason: Text


class Proposal(Strict):
    issues: list[Candidate] = Field(min_length=1, max_length=10)
    new_issues: list[Text] = Field(max_length=10)
    critique_responses: list[CritiqueResponse] = Field(max_length=16)


class Finding(Strict):
    id: Ident
    issue_id: Ident
    target_role: Literal["customer", "insurer", "fairness"]
    severity: Literal["minor", "material", "critical"]
    assertion: Text
    reason: Text
    citations: list[Citation] = Field(max_length=8)


class Critique(Strict):
    findings: list[Finding] = Field(max_length=16)


class Choice(Strict):
    issue_id: Ident
    candidate_id: Ident | None
    reason: Text
    missing: list[Text] = Field(max_length=10)


class Ballot(Strict):
    snapshot: str = Field(min_length=1, max_length=100)
    registry_hash: str = Field(min_length=1, max_length=100)
    issues: list[Choice] = Field(min_length=1, max_length=10)


class SupportedStatement(Strict):
    text: Text
    citations: list[Citation] = Field(min_length=1, max_length=8)


class Synthesis(Strict):
    observations: list[SupportedStatement] = Field(max_length=12)
    proposed_response: str = Field(max_length=10000)
    next_actions: list[Text] = Field(min_length=1, max_length=10)


class Policy(Strict):
    name: str = Field(min_length=3, max_length=150)
    instructions: str = Field(max_length=6000)
    required_documents: list[Text] = Field(min_length=1, max_length=20)
    egress_enabled: bool = False


class Rights(Strict):
    basis: Literal["authorized_customer", "licensed", "reviewed_legal_basis", "owned_test"]
    reference: str = Field(min_length=10, max_length=500)
    expires: float = Field(gt=0)
    egress: bool


class Review(Strict):
    packet_hash: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=10, max_length=2000)
    response: str = Field(max_length=10000)
    resolutions: dict[Ident, Text] = Field(max_length=16)
    overrides: dict[Ident, Text] = Field(max_length=10)
