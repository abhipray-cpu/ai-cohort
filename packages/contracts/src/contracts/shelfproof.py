"""Bounded ShelfProof contracts. Models never decide adoption or review authority."""

import re
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

Text = Annotated[str, Field(min_length=1, max_length=2000)]
FactPath = Literal["product_id", "brand", "name", "net_quantity", "net_unit", "ingredients"]
RESTRICTED = re.compile(
    r"\b(organic|gluten[ -]free|allergen[ -]free|sugar[ -]free|non[ -]gmo|"
    r"certified|cures?|treats?|prevents?|healthy|healthier|low[ -]fat|vegan|"
    r"kosher|halal|boosts? immunity|fat[ -]free)\b",
    re.IGNORECASE,
)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class FactPack(Contract):
    product_id: Annotated[str, Field(min_length=1, max_length=128)]
    brand: Annotated[str, Field(min_length=1, max_length=150)]
    name: Annotated[str, Field(min_length=1, max_length=150)]
    net_quantity: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=4)]
    net_unit: Literal["g", "kg", "ml", "l", "oz", "lb", "fl oz"]
    ingredients: Annotated[str, Field(min_length=1, max_length=5000)]
    source_ref: Text

    @model_validator(mode="after")
    def supported(self):
        if RESTRICTED.search(self.name) or RESTRICTED.search(self.brand):
            raise ValueError("out_of_scope: restricted official identity")
        if any(
            not v.strip()
            for v in (self.product_id, self.brand, self.name, self.ingredients, self.source_ref)
        ):
            raise ValueError("needs_data: blank required fact")
        return self


class Claim(Contract):
    field: Literal["title", "description"]
    start: Annotated[StrictInt, Field(ge=0, le=5000)]
    end: Annotated[StrictInt, Field(ge=1, le=5000)]
    quote: Text
    refs: Annotated[list[FactPath], Field(min_length=1, max_length=8)]


class Draft(Contract):
    title: Annotated[str, Field(min_length=1, max_length=150)]
    description: Annotated[str, Field(min_length=1, max_length=5000)]
    claims: Annotated[list[Claim], Field(max_length=40)] = Field(default_factory=list)


class Finding(Contract):
    family: Literal[
        "restricted_claim",
        "numeric",
        "coverage",
        "reference",
        "semantic",
        "channel",
        "clarity",
        "brand",
    ]
    severity: Literal["critical", "material", "minor"]
    field: Literal["title", "description"]
    explanation: Text
    refs: Annotated[list[FactPath], Field(max_length=10)] = Field(default_factory=list)
    start: Annotated[StrictInt | None, Field(ge=0, le=5000)] = None
    end: Annotated[StrictInt | None, Field(ge=1, le=5000)] = None
    quote: Annotated[str | None, Field(max_length=5000)] = None
    missing_source: bool = False


class CheckFinding(Finding):
    rule: Annotated[str, Field(min_length=1, max_length=128)]


class Rating(Contract):
    value: Annotated[StrictInt | None, Field(ge=0, le=4)]
    rationale: Text
    refs: Annotated[list[FactPath], Field(max_length=10)] = Field(default_factory=list)


DIMENSIONS = {"fidelity": 30, "coverage": 25, "channel": 20, "clarity": 15, "brand": 10}


class Ratings(Contract):
    fidelity: Rating
    coverage: Rating
    channel: Rating
    clarity: Rating
    brand: Rating

    def items(self):
        return [(key, getattr(self, key)) for key in DIMENSIONS]

    def values(self):
        return [getattr(self, key) for key in DIMENSIONS]

    def __getitem__(self, key):
        if key not in DIMENSIONS:
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key, value):
        if key not in DIMENSIONS:
            raise KeyError(key)
        setattr(self, key, Rating.model_validate(value))


class JudgeEvaluation(Contract):
    ratings: Ratings
    findings: Annotated[list[Finding], Field(max_length=20)]


class PlanItem(Contract):
    finding_id: Annotated[str, Field(min_length=1, max_length=128)]
    operation: Literal[
        "remove", "replace_from_fact", "clarify_basis", "request_source", "retain_with_reason"
    ]
    rationale: Text
    refs: Annotated[list[FactPath], Field(max_length=10)] = Field(default_factory=list)


class CorrectionPlan(Contract):
    items: Annotated[list[PlanItem], Field(max_length=40)]


class SelectionDecision(Contract):
    adopt: bool
    reason: str
