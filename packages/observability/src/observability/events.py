"""Portable event contracts for validation and repair telemetry."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from contracts.common import ValidationStage
from pydantic import BaseModel, Field


class ValidationFailureEvent(BaseModel):
    """A safe record that a generated value failed validation."""

    event_type: Literal["validation_failed"] = "validation_failed"
    occurred_at: datetime
    run_id: str
    product: str
    stage: ValidationStage
    schema_version: str
    attempt: int = Field(ge=1)
    error_code: str
    error_summary: str
    provider: str = "local_codex"
    elapsed_ms: int = Field(ge=0)
