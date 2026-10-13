"""Common contract types with explicit provenance."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    """A claim's verifiable location in an input document."""

    document_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    quote: str = Field(min_length=1)


class RunReference(BaseModel):
    """Correlation details shared across API, agent, and logs."""

    run_id: UUID
    product: str
    started_at: datetime
    schema_version: str


ValidationStage = Literal[
    "parse",
    "output_schema",
    "tool_arguments",
    "tool_response",
    "business_rule",
    "evidence",
    "provider",
    "provider_timeout",
]
