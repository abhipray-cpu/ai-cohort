"""Strict ClauseGate boundaries. Schema validity never grants approval authority."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Label = Literal["Entailment", "Contradiction", "NotMentioned"]
Role = Literal["owner", "requester", "reviewer", "approver", "final_reviewer", "auditor"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Named(Strict):
    name: str = Field(min_length=1, max_length=160)


class Login(Strict):
    username: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=1, max_length=256)


class UserCreate(Login):
    admin: bool = False


class Expected(Strict):
    expected_revision: int = Field(ge=1)


class Membership(Strict):
    username: str = Field(min_length=1, max_length=80)
    roles: list[Role] = Field(max_length=6)
    case_ids: list[str] = Field(max_length=200)
    expires_at: str | None = None


class Rule(Strict):
    id: str = Field(min_length=1, max_length=80)
    hypothesis: str = Field(min_length=5, max_length=1200)
    action: Literal["record", "require_review", "require_exception", "block"] = "require_review"
    trigger_labels: list[Label] = Field(
        default_factory=lambda: ["Entailment", "Contradiction", "NotMentioned"],
        min_length=1,
        max_length=3,
    )
    roles: list[Literal["reviewer", "approver"]] = Field(
        default_factory=lambda: ["approver"], min_length=1, max_length=2
    )
    expiry_hours: int = Field(default=168, ge=1, le=720)

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.roles)) != len(self.roles) or len(set(self.trigger_labels)) != len(
            self.trigger_labels
        ):
            raise ValueError("Duplicate role or label")
        return self


class Playbook(Strict):
    name: str = Field(min_length=1, max_length=160)
    rules: list[Rule] = Field(min_length=1, max_length=25)

    @model_validator(mode="after")
    def unique(self):
        if len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("Duplicate rule ID")
        return self


class PlaybookInput(Expected):
    playbook: Playbook


class ContextInput(Expected):
    side: Literal["recipient", "discloser", "mutual", "unknown"]
    purpose: str = Field(max_length=1500)


class TextInput(Expected):
    name: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=500000)


class EvidenceQuote(Strict):
    span_id: str = Field(min_length=1, max_length=80)
    quote: str = Field(min_length=1, max_length=1200)


class Finding(Strict):
    check_id: str = Field(min_length=1, max_length=80)
    label: Label
    evidence_ids: list[str] = Field(default_factory=list, max_length=30)
    evidence_quotes: list[EvidenceQuote] = Field(default_factory=list, max_length=30)
    assessment: Literal["supported", "uncertain", "unavailable", "incomplete"] = "uncertain"
    rationale: str = Field(min_length=1, max_length=1800)

    @model_validator(mode="after")
    def quotes_match_ids(self):
        ids = [q.span_id for q in self.evidence_quotes]
        if len(set(ids)) != len(ids) or any(i not in self.evidence_ids for i in ids):
            raise ValueError("Each exact quote must reference a unique cited span")
        return self


class FindingsInput(Expected):
    findings: list[Finding] = Field(min_length=1, max_length=25)
    rationale: str = Field(min_length=1, max_length=1800)


class Analysis(Strict):
    findings: list[Finding] = Field(min_length=1, max_length=25)


class GrantInput(Expected):
    key: str = Field(min_length=1, max_length=100)


class DecisionInput(Strict):
    expected_revision: int = Field(ge=1)
    binding: str = Field(min_length=64, max_length=64)
    kind: Literal[
        "clarify",
        "confirm_interpretation",
        "correct_interpretation",
        "approve_exception",
        "reject",
        "request_revision",
    ]
    rationale: str = Field(min_length=3, max_length=1800)
    key: str = Field(min_length=1, max_length=100)
    side: Literal["recipient", "discloser", "mutual"] | None = None
    purpose: str | None = Field(default=None, max_length=1500)
    label: Label | None = None
    evidence_ids: list[str] = Field(default_factory=list, max_length=30)


class Assignment(Expected):
    username: str = Field(min_length=1, max_length=80)
    expires_at: str | None = None


class ReviewInput(Expected):
    packet_hash: str = Field(min_length=64, max_length=64)
    rationale: str = Field(min_length=3, max_length=1800)
    acknowledge_limits: bool


class EgressInput(Expected):
    allowed: bool


class ErasureInput(Expected):
    confirmation: Literal["ERASE"]
