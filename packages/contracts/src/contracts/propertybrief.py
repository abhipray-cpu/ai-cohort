"""Strict boundaries for the property investigation agent."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PropertyInput(StrictModel):
    address: str = Field(min_length=3, max_length=250)
    borough: Literal["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"]
    question: str = Field(
        default="Investigate recorded issues and prepare a diligence plan.",
        min_length=3,
        max_length=4000,
    )
    bin: str | None = Field(default=None, pattern=r"^[1-5]\d{6}$")
    bbl: str | None = Field(default=None, pattern=r"^[1-5]\d{9}$")


class AgentDecision(StrictModel):
    action: Literal["query", "inspect", "compare", "finish", "clarify"]
    tool: str = Field(max_length=60)
    summary: str = Field(min_length=1, max_length=1200)
    reflection: str = Field(max_length=2000)
    record_ids: list[str] = Field(default_factory=list, max_length=12)


class EvidenceRef(StrictModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    source: Literal[
        "buildings",
        "hpd_violations",
        "hpd_complaints",
        "vacate",
        "underlying",
        "aep",
        "dob_complaints",
        "dob_violations",
        "dob_ecb",
    ]
    record_id: str = Field(min_length=1, max_length=150)
    field: str = Field(min_length=1, max_length=100)
    value: str = Field(max_length=3000)


class Finding(StrictModel):
    id: str = Field(min_length=1, max_length=50)
    text: str = Field(min_length=1, max_length=1800)
    kind: Literal["recorded_fact", "interpretation", "conflict"]
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=8)


class PlanTask(StrictModel):
    title: str = Field(min_length=1, max_length=250)
    recipient: Literal["seller", "inspector", "attorney", "analyst"]
    priority: Literal["high", "medium", "low"]
    reason: str = Field(min_length=1, max_length=1000)
    finding_ids: list[str] = Field(default_factory=list, max_length=12)
    verification: str = Field(min_length=1, max_length=1000)


class ReportDraft(StrictModel):
    summary: str = Field(min_length=1, max_length=2000)
    findings: list[Finding] = Field(default_factory=list, max_length=40)
    tasks: list[PlanTask] = Field(default_factory=list, max_length=24)
    limitations: list[str] = Field(default_factory=list, max_length=30)


class Critique(StrictModel):
    outcome: Literal["pass", "revise", "insufficient"]
    unsupported_finding_ids: list[str] = Field(default_factory=list, max_length=40)
    issues: list[str] = Field(default_factory=list, max_length=20)
    next_check: str = Field(default="", max_length=1000)


class Message(StrictModel):
    content: str = Field(min_length=3, max_length=4000)


class IdentitySelection(StrictModel):
    candidate_id: str = Field(min_length=1, max_length=30)
    expected_revision: int = Field(ge=1)


class Review(StrictModel):
    expected_revision: int = Field(ge=1)
    notes: str = Field(default="", max_length=4000)
    acknowledge_limits: bool = False
    draft: ReportDraft | None = None


class ExportRequest(StrictModel):
    format: Literal["json", "markdown"] = "markdown"


class SourceRecord(StrictModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    id: str = Field(min_length=1, max_length=150)
    source: str = Field(min_length=1, max_length=50)
    scope: Literal["building", "parcel"]
    status: Literal["historical", "recorded_open", "reported", "unknown"]
    description: str = Field(max_length=3000)
    flags: list[str] = Field(max_length=20)
    fields: dict[str, str] = Field(max_length=200)


class ToolResponse(StrictModel):
    source: str
    dataset: str = Field(pattern=r"^[a-z0-9]{4}-[a-z0-9]{4}$")
    catalog: str
    identity: str = Field(pattern=r"^\d+$")
    query: dict[str, str | int]
    started_at: str
    retrieved_at: str
    raw: list[dict[str, Any]] = Field(max_length=10000)
    records: list[SourceRecord] = Field(max_length=10000)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    metadata: dict[str, Any] | None
    completeness: Literal["complete_for_query", "truncated", "drift_detected", "unknown"]
    outcome: Literal["success", "no_records", "partial", "unavailable"]
    flags: list[str] = Field(max_length=20)
    error: str | None
    count: int = Field(ge=0, le=10000)
