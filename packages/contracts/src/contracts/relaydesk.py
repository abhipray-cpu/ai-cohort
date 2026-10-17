"""Strict RelayDesk trust-boundary contracts, not model-supplied authority."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Kind = Literal[
    "episode",
    "environment",
    "attempt",
    "outcome",
    "workaround",
    "hypothesis",
    "decision",
    "commitment",
    "open_question",
]
State = Literal["reported", "proposed", "disputed", "superseded", "suppressed"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Login(Strict):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserCreate(Login):
    admin: bool = False


class Named(Strict):
    name: str = Field(min_length=1, max_length=120)


class SourceMessage(Strict):
    source_key: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=32768)

    @field_validator("body")
    @classmethod
    def body_bytes(cls, value):
        if len(value.encode("utf-8")) > 32768:
            raise ValueError("Source body exceeds 32 KiB UTF-8")
        return value

    created_at: str
    updated_at: str
    bot: bool = False

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamp(cls, value):
        parsed = datetime.fromisoformat(value)
        if not parsed.tzinfo:
            raise ValueError("Timezone is required")
        if parsed > datetime.now(UTC):
            raise ValueError("Future source timestamp")
        return parsed.astimezone(UTC).isoformat()


class ImportBatch(Strict):
    messages: list[SourceMessage] = Field(min_length=1, max_length=2000)
    origin: str = Field(default="uploaded conversation", max_length=300)
    complete: bool = True
    gaps: list[str] = Field(default_factory=list, max_length=100)


class Policy(Strict):
    expected_revision: int = Field(ge=1)
    model_egress: bool = False
    github_repositories: list[str] = Field(default_factory=list, max_length=20)


class Membership(Strict):
    username: str = Field(min_length=1, max_length=80)
    roles: list[Literal["investigator", "reviewer"]] = Field(max_length=2)


class Message(Strict):
    content: str = Field(min_length=1, max_length=6000)
    session_id: str = Field(min_length=1, max_length=80)


class Recall(Strict):
    question: str = Field(min_length=1, max_length=6000)
    as_of: str | None = None
    history: bool = False
    minimum_revision: int = Field(default=0, ge=0)
    limit: int = Field(default=10, ge=1, le=30)

    @field_validator("as_of")
    @classmethod
    def cutoff(cls, value):
        return SourceMessage.timestamp(value) if value else None


class ExpectedRevision(Strict):
    expected_revision: int = Field(ge=1)


class Correction(Strict):
    expected_revision: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=4000)
    kind: Kind = "episode"
    state: State = "reported"
    reason: str = Field(min_length=3, max_length=1000)


class Erasure(Strict):
    source_ids: list[str] = Field(min_length=1, max_length=2000)
    confirmation: Literal["ERASE"]


class Review(Strict):
    acknowledge_limits: bool = False


class Proposal(Strict):
    source_id: str
    quote: str = Field(min_length=1, max_length=3000)
    text: str = Field(min_length=1, max_length=1200)
    kind: Kind


class Extraction(Strict):
    proposals: list[Proposal] = Field(max_length=40)


class Claim(Strict):
    text: str = Field(
        min_length=1,
        max_length=1200,
        description="An exact verbatim span from the cited evidence.quote. No paraphrase, attribution prefix or invented outcome. Preserve negation.",
    )
    memory_ids: list[str] = Field(
        min_length=1,
        max_length=1,
        description="The single supplied memory whose original source quote contains text.",
    )


class Reply(Strict):
    summary: str = Field(
        min_length=1,
        max_length=2400,
        description="Non-authoritative planning note; factual user-facing summary is assembled by the server from validated quotes, not this prose.",
    )
    claims: list[Claim] = Field(max_length=12)
    questions: list[str] = Field(max_length=10)
    limitations: list[str] = Field(max_length=15)


class GithubInput(Strict):
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    issue: int = Field(ge=1)
