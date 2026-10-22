"""Finite ReleaseFence wire contracts. Models do not grant control authority."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_.:-]+$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Money = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=10)]
Timestamp = Annotated[float, Field(ge=0, le=4102444800)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)


class Release(Contract):
    application: Identifier
    code_digest: Digest
    prompt_digest: Digest
    model_config_digest: Digest
    tools_digest: Digest
    policy_revision: Identifier
    index_digest: Digest | None = None
    model_identity: Annotated[str, Field(max_length=200)] = "unverified"
    predecessor: Digest | None = None


class Policy(Contract):
    version: Literal["fixed-looks-v1"] = "fixed-looks-v1"
    trace_profile: Literal["langsmith-phoenix-v1", "mlflow-phoenix-v1"] = "langsmith-phoenix-v1"
    minimum_sessions: Annotated[StrictInt, Field(ge=100, le=10000)] = 100
    coverage: Annotated[float, Field(ge=0.99, le=1)] = 0.99
    failure_margin: Annotated[float, Field(ge=0, le=0.02)] = 0.02
    latency_margin: Annotated[float, Field(ge=0, le=0.2)] = 0.2
    cost_margin: Annotated[float, Field(ge=0, le=0.2)] = 0.2
    alpha: Annotated[float, Field(gt=0, le=0.05)] = 0.05
    max_iterations: Annotated[StrictInt, Field(ge=1, le=100)] = 8
    repeated_calls: Annotated[StrictInt, Field(ge=3, le=20)] = 3
    deadline_seconds: Annotated[StrictInt, Field(ge=10, le=3600)] = 300
    stage_seconds: Annotated[StrictInt, Field(ge=60, le=86400)] = 300
    lateness_seconds: Annotated[StrictInt, Field(ge=1, le=300)] = 30


class Usage(Contract):
    attempt: Identifier
    input_tokens: Annotated[StrictInt | None, Field(ge=0, le=10**9)] = None
    output_tokens: Annotated[StrictInt | None, Field(ge=0, le=10**9)] = None
    cached_input_tokens: Annotated[StrictInt | None, Field(ge=0, le=10**9)] = None
    reported_cost: Money | None = None
    estimated_cost: Money | None = None
    price_revision: Identifier | None = None
    currency: Literal["USD"] = "USD"
    inclusive: StrictBool = False
    model: Annotated[str, Field(max_length=200)] = "unknown"

    @model_validator(mode="after")
    def coherent(self):
        if self.reported_cost is not None and self.estimated_cost is not None:
            raise ValueError("cost provenance must be exclusive")
        if self.estimated_cost is not None and not self.price_revision:
            raise ValueError("estimate requires pinned price")
        if self.cached_input_tokens is not None and (
            self.input_tokens is None or self.cached_input_tokens > self.input_tokens
        ):
            raise ValueError("invalid inclusive cached token count")
        return self


class Event(Contract):
    id: Identifier
    session: Identifier
    task: Identifier
    release: Digest
    kind: Literal["accepted", "terminal", "usage", "tool", "heartbeat"]
    at: Timestamp  # UTC Unix seconds on the wire, not local wall-clock text.
    sequence: Annotated[StrictInt, Field(ge=0, le=10**9)] = 0
    outcome: Literal["success", "failure", "abstained", "manual_required", "unknown"] | None = None
    duration_ms: Annotated[float | None, Field(ge=0, le=86400000)] = None
    model_calls: Annotated[StrictInt | None, Field(ge=0, le=1000)] = None
    usage: Usage | None = None
    tool_fingerprint: Annotated[str | None, Field(max_length=128)] = None
    progress: Annotated[str | None, Field(max_length=128)] = None
    polling: StrictBool = False
    iteration: Annotated[StrictInt | None, Field(ge=0, le=10000)] = None
    stop_reason: (
        Literal["iteration_exhausted", "deadline", "schema_exhausted", "complete"] | None
    ) = None
    waiting_until: Timestamp | None = None

    @model_validator(mode="after")
    def shape(self):
        if self.outcome == "success" and self.stop_reason in {
            "iteration_exhausted",
            "deadline",
            "schema_exhausted",
        }:
            raise ValueError("exhausted work cannot be successful")
        if self.kind == "terminal" and (self.outcome is None or self.model_calls is None):
            raise ValueError("terminal outcome and model-call counter required")
        if (self.kind == "usage") != (self.usage is not None):
            raise ValueError("usage belongs only on usage events")
        if self.kind != "terminal" and (self.outcome is not None or self.duration_ms is not None):
            raise ValueError("outcome belongs only on terminal event")
        if self.waiting_until is not None and self.waiting_until > self.at + 86400:
            raise ValueError("human wait must be bounded")
        return self


class Command(Contract):
    id: Identifier
    enrollment: Identifier
    application: Identifier
    environment: Identifier
    rollout: Identifier
    epoch: Annotated[StrictInt, Field(ge=1)]
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    expires: Timestamp
    action: Literal["canary", "promote", "rollback"]
    stable: Digest
    candidate: Digest
    weight: Annotated[StrictInt, Field(ge=0, le=100)]
    seed: Identifier
    authority: Identifier


class LifecycleCounter(Contract):
    release: Digest
    accepted: Annotated[StrictInt, Field(ge=0)]
    terminal: Annotated[StrictInt, Field(ge=0)]


class Attestation(Contract):
    command: Identifier
    enrollment: Identifier
    revision: Annotated[StrictInt, Field(ge=0)]
    epoch: Annotated[StrictInt, Field(ge=0)]
    at: Timestamp
    stable: Digest
    candidate: Digest
    weight: Annotated[StrictInt, Field(ge=0, le=100)]
    probe_session: Identifier
    probe_release: Digest
    probe_kind: Literal["routing_only", "http_bundle"] = "routing_only"
    probe_receipt: Digest | None = None
    active_candidate: Annotated[StrictInt, Field(ge=0)]
    available_bundles: Annotated[list[Digest], Field(max_length=256)] = Field(default_factory=list)
    counters: Annotated[list[LifecycleCounter], Field(max_length=256)] = Field(default_factory=list)
    window_start: Timestamp | None = None
    window_end: Timestamp | None = None

    @model_validator(mode="after")
    def finite_window(self):
        if (self.window_start is None) != (self.window_end is None):
            raise ValueError("both window bounds required")
        if self.window_start is not None and not 0 < self.window_end - self.window_start <= 86400:
            raise ValueError("bounded window required")
        if len({c.release for c in self.counters}) != len(self.counters):
            raise ValueError("duplicate lifecycle counter")
        return self


class Span(Contract):
    trace_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    span_id: Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]
    parent_span_id: Annotated[str | None, Field(pattern=r"^[0-9a-f]{16}$")] = None
    name: Annotated[str, Field(min_length=1, max_length=200)]
    release: Digest
    started_ns: Annotated[StrictInt, Field(ge=0)]
    ended_ns: Annotated[StrictInt, Field(ge=0)]
    kind: Literal["agent", "llm", "tool", "retriever"] = "agent"
    status: Literal["ok", "error", "unset"] = "unset"

    @model_validator(mode="after")
    def interval(self):
        if (
            self.ended_ns < self.started_ns
            or int(self.trace_id, 16) == 0
            or int(self.span_id, 16) == 0
        ):
            raise ValueError("invalid span identity or interval")
        return self
