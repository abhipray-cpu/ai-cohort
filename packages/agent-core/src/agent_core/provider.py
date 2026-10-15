"""Provider boundary for local structured AI execution."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class ProviderTimeoutError(RuntimeError):
    """The local model process exceeded its bounded execution time."""


class StructuredGeneration(BaseModel):
    """Auditable raw result returned by an AI runtime."""

    text: str
    exit_code: int
    elapsed_ms: int
    stderr: str = ""
    tools_audited: bool = False


class StructuredProvider(Protocol):
    """Contract every AI runtime adapter must satisfy."""

    def generate(self, *, prompt: str, schema: dict[str, object]) -> StructuredGeneration:
        """Generate schema-directed text without interpreting it."""
        ...
