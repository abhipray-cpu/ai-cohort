"""Strict PatchDesk input, orchestration and review boundaries."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Capability = Literal[
    "advisories.lookup",
    "advisories.detail",
    "releases.lookup",
    "threat.epss",
    "threat.kev",
    "dependency.context",
    "repository.snapshot.read",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Strict):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class UserCreate(Login):
    admin: bool = False


class ProjectCreate(Strict):
    name: str = Field(min_length=2, max_length=150)
    client: str = Field(min_length=2, max_length=150)


class ProjectPolicy(Strict):
    expected_revision: int = Field(ge=1)
    public_packages: list[str] = Field(default_factory=list, max_length=2000)
    model_egress: bool = False
    repository: str = Field(default="", pattern=r"^$|^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    repository_id: int | None = Field(default=None, gt=0)
    node_version: str = Field(default="", max_length=40)
    connector_epoch: str = Field(default="default", max_length=80)


class Membership(Strict):
    username: str = Field(max_length=80)
    roles: list[Literal["analyst", "reviewer", "publisher"]] = Field(max_length=3)


class InputUpload(Strict):
    manifest: dict[str, Any]
    lockfile: dict[str, Any]
    origin: str = Field(default="uploaded", max_length=300)
    commit: str = Field(default="", max_length=64, pattern=r"^$|^[a-fA-F0-9]{40,64}$")


class RepositoryInput(Strict):
    ref: str = Field(default="HEAD", min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._/-]+$")


class Message(Strict):
    content: str = Field(
        default="Prepare an evidence-backed security maintenance plan.",
        min_length=3,
        max_length=4000,
    )


class CapabilityRequest(Strict):
    capability: Capability
    arguments: dict[str, Any]


class ToolDescriptor(Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_.-]{1,50}$")
    version: str = "1.0"
    capabilities: list[Capability] = Field(min_length=1, max_length=8)
    provider: str = Field(max_length=50)
    packages: list[str] = Field(default_factory=list, max_length=2000)
    permission: Literal["public", "repository"] = "public"
    enabled: bool = True
    priority: int = Field(default=10, ge=0, le=100)
    schema_version: str = "patchdesk-tool-1"


class ToolResult(Strict):
    adapter: str
    capability: Capability
    outcome: Literal[
        "success",
        "no_matches",
        "partial",
        "unavailable",
        "denied",
        "unsupported",
        "cancelled",
        "failed",
    ]
    completeness: Literal[
        "complete_for_query", "truncated", "drift_detected", "unknown", "not_applicable"
    ]
    records: list[dict[str, Any]] = Field(default_factory=list, max_length=5000)
    raw: Any = None
    error: str | None = None
    retrieved_at: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class AgentPlan(Strict):
    requests: list[CapabilityRequest] = Field(default_factory=list, max_length=4)
    summary: str = Field(min_length=1, max_length=1500)


class PlanTask(Strict):
    title: str = Field(min_length=1, max_length=250)
    finding_ids: list[str] = Field(default_factory=list, max_length=30)
    priority: Literal["high", "medium", "low"]
    reason: str = Field(min_length=1, max_length=1000)
    verification: str = Field(min_length=1, max_length=1000)


class Narrative(Strict):
    summary: str = Field(min_length=1, max_length=2000)
    tasks: list[PlanTask] = Field(default_factory=list, max_length=24)
    limitations: list[str] = Field(default_factory=list, max_length=30)


class Review(Strict):
    expected_revision: int = Field(ge=1)
    notes: str = Field(default="", max_length=4000)
    acknowledge_limits: bool = False
    narrative: Narrative | None = None


class PublicationDraft(Strict):
    title: str = Field(min_length=3, max_length=250)


class Approval(Strict):
    expected_revision: int = Field(ge=1)
    payload_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class RegistryChange(Strict):
    adapter: str = Field(max_length=80)
    enabled: bool
