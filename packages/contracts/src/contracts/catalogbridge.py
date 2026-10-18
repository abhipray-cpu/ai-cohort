"""Strict supplier-catalog matching and resource contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class Product(Strict):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=20000)
    brand: str = Field(default="", max_length=1000)
    description: str = Field(default="", max_length=20000)
    model: str = Field(default="", max_length=1000)
    gtin: str = Field(default="", max_length=100)
    price: str = Field(default="", max_length=100)
    currency: str = Field(default="", max_length=20)

    @model_validator(mode="after")
    def nonblank(self):
        if not self.id.strip() or not self.title.strip():
            raise ValueError("blank identity/title")
        return self


class Usage(Strict):
    input_tokens: int = Field(ge=0, strict=True)
    cached_input_tokens: int = Field(default=0, ge=0, strict=True)
    output_tokens: int = Field(ge=0, strict=True)
    reasoning_output_tokens: int = Field(default=0, ge=0, strict=True)

    @model_validator(mode="after")
    def valid_cache(self):
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached tokens exceed input")
        if self.reasoning_output_tokens > self.output_tokens:
            raise ValueError("reasoning tokens exceed output")
        return self

    @property
    def total(self):
        return self.input_tokens + self.output_tokens


class RateCard(Strict):
    id: str = "reference-unpriced"
    basis: Literal["unpriced", "reference_estimate", "applicable_credit"] = "unpriced"
    unit: str = "USD"
    input_microunits_per_million: int = Field(default=0, ge=0)
    cached_microunits_per_million: int = Field(default=0, ge=0)
    output_microunits_per_million: int = Field(default=0, ge=0)
    source: str = Field(default="", max_length=2000)


class BatchSpec(Strict):
    master_id: str
    supplier_id: str
    token_budget: int = Field(default=100000, ge=1, le=100000000)
    row_token_budget: int = Field(default=30000, ge=1, le=1000000)
    call_budget: int = Field(default=100, ge=1, le=10000)
    budget_mode: Literal["strict", "advisory"] = "advisory"
    economy_model: str = Field(default="gpt-6-luna", min_length=1, max_length=100)
    strong_model: str = Field(default="gpt-6.1-sol", min_length=1, max_length=100)
    egress: bool = False
    instruction_profile: Literal["legacy", "compact_classifier_v1"] = "legacy"
    reuse_validated_drafts: bool = Field(default=False, strict=True)
    routing_policy: Literal["llm_only", "local_review_v1"] = "llm_only"
    local_router_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    rate_card: RateCard = Field(default_factory=RateCard)
    model_rates: dict[str, RateCard] = Field(default_factory=dict)
    calibration_id: str | None = None

    @model_validator(mode="after")
    def distinct(self):
        if self.economy_model == self.strong_model:
            raise ValueError("distinct models required")
        if (self.routing_policy == "local_review_v1") != bool(self.local_router_sha256):
            raise ValueError("explicit local routing profile hash required only for local policy")
        return self


class Citation(Strict):
    side: Literal["supplier", "candidate"]
    field: Literal["title", "brand", "description", "model", "gtin"]
    quote: str = Field(min_length=1, max_length=2000)


class Proposal(Strict):
    candidate_id: str = Field(min_length=1, max_length=200)
    outcome: Literal["same_product", "different_product", "insufficient_evidence"]
    reason: str = Field(min_length=1, max_length=4000)
    evidence: list[Citation] = Field(min_length=1, max_length=20)


class Review(Strict):
    expected_revision: int = Field(ge=0)
    action: Literal["accept", "correct", "reject"]
    candidate_id: str | None = None
    reason: str = Field(min_length=1, max_length=2000)


class Calibration(Strict):
    id: str
    binding: str
    threshold: float = Field(ge=0, le=1)
    precision_lower_bound: float = Field(ge=0, le=1)
    accepted_samples: int = Field(ge=500)
    economy_score: float = Field(ge=0, le=1)
    strong_score: float = Field(ge=0, le=1)
    evidence_status: Literal["operator_attested", "empirically_verified"] = "operator_attested"

    @model_validator(mode="after")
    def qualified(self):
        if self.precision_lower_bound < 0.99:
            raise ValueError("unqualified acceptance calibration")
        return self
