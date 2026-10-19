"""BuildRelay wire and generation contracts. Logs are data, never instructions."""

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunEvent(StrictModel):
    repository_id: int = Field(gt=0, strict=True)
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", max_length=200)
    run_id: int = Field(gt=0, strict=True)
    attempt: int = Field(ge=1, le=10000, strict=True)
    conclusion: Literal[
        "failure",
        "timed_out",
        "success",
        "cancelled",
        "action_required",
        "skipped",
        "neutral",
        "stale",
        "startup_failure",
    ]
    workflow: str = Field(min_length=1, max_length=200)
    branch: str = Field(max_length=250)
    sha: str = Field(pattern=r"^[a-fA-F0-9]{40,64}$")
    source_url: str

    @model_validator(mode="after")
    def source_matches_identity(self):
        u = urlparse(self.source_url)
        if (
            u.scheme != "https"
            or u.netloc != "github.com"
            or u.query
            or u.fragment
            or u.path.rstrip("/").lower()
            != f"/{self.repository}/actions/runs/{self.run_id}".lower()
        ):
            raise ValueError("source URL must match GitHub run identity")
        return self


class Citation(StrictModel):
    line: int = Field(ge=1, strict=True)
    quote: str = Field(min_length=1, max_length=800)


class Triage(StrictModel):
    category: Literal["test", "compilation", "dependency", "infrastructure", "unknown"]
    summary: str = Field(min_length=10, max_length=1500)
    hypothesis: str = Field(max_length=1500)
    confidence: float = Field(ge=0, le=1)
    next_steps: list[str] = Field(min_length=1, max_length=5)
    citations: list[Citation] = Field(min_length=1, max_length=8)
    client_update: str = Field(min_length=10, max_length=1500)


class QueueEnvelope(StrictModel):
    schema_version: Literal[1]
    repo_id: str = Field(min_length=1, max_length=100)
    delivery_id: str = Field(min_length=1, max_length=200)
    event: RunEvent
