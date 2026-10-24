"""Bounded, immutable RepairClaim contracts; no coverage or action authority."""

import re
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    model_validator,
)

Identifier = Annotated[
    str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
]
Text = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=2000)]
ShortText = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=200)]
Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-f0-9]{64}$")]
Scalar = ShortText | StrictInt | StrictBool
FactField = Literal[
    "make",
    "model",
    "model_year",
    "component",
    "repair_date",
    "in_service_date",
    "repair_mileage",
    "current_mileage",
    "diagnostic_code",
    "payment_proof",
    "vehicle_confirmation",
    "paid_amount",
    "vin",
    "invoice_total",
    "repair_description",
    "diagnosis",
]
Unit = Literal["mi", "km", "USD", "EUR", "GBP"]
ConditionStatus = Literal[
    "satisfied", "not_satisfied", "unknown", "conflicting", "confirmation_required"
]
AssessmentState = Literal[
    "potentially_applicable",
    "missing_evidence",
    "appears_outside_conditions",
    "conflicting_information",
    "no_supported_programme_found",
]
OutcomeKind = Literal["requested", "confirmed_covered", "approved", "received", "avoided_cost"]
NUMERIC_FIELDS = frozenset(
    {"repair_mileage", "current_mileage", "paid_amount", "invoice_total", "model_year"}
)
DATE_FIELDS = frozenset({"repair_date", "in_service_date"})
BOOL_FIELDS = frozenset({"payment_proof", "vehicle_confirmation"})


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


def quantity(value: object) -> Decimal:
    if type(value) not in (str, int, Decimal):
        raise ValueError("invalid_quantity")
    if not re.fullmatch(r"[0-9]{1,12}(?:\.[0-9]{1,6})?", str(value)):
        raise ValueError("invalid_quantity")
    result = Decimal(str(value))
    if result > Decimal(999999999):
        raise ValueError("invalid_quantity")
    return result


def _money(value: object) -> Decimal:
    if type(value) not in (str, Decimal):
        raise ValueError("money_requires_decimal_string")
    if not re.fullmatch(r"[0-9]{1,12}(?:\.[0-9]{1,2})?", str(value)):
        raise ValueError("invalid_money")
    return Decimal(value)


class Money(Contract):
    amount: Annotated[
        Decimal, BeforeValidator(_money), Field(ge=0, max_digits=14, decimal_places=2)
    ]
    currency: Literal["USD", "EUR", "GBP"]


class EvidenceAnchor(Contract):
    document_id: Identifier
    sha256: Digest
    page: Annotated[StrictInt, Field(ge=1, le=100)]
    quote: Text

    @model_validator(mode="after")
    def meaningful_quote(self):
        if not self.quote.strip():
            raise ValueError("empty_quote")
        return self


def _validate_value(field: str, value: object, unit: str | None) -> None:
    if field in NUMERIC_FIELDS:
        quantity(value)
        if field == "model_year":
            if type(value) is not int or not 1980 <= value <= 2100 or unit is not None:
                raise ValueError("invalid_model_year")
        elif field in {"paid_amount", "invoice_total"}:
            if unit not in {"USD", "EUR", "GBP"}:
                raise ValueError("money_unit_required")
            _money(str(value))
        elif unit not in {"mi", "km"}:
            raise ValueError("mileage_unit_required")
    elif field in DATE_FIELDS:
        if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("iso_date_required")
        date.fromisoformat(value)
        if unit is not None:
            raise ValueError("unexpected_unit")
    elif field in BOOL_FIELDS:
        if type(value) is not bool or unit is not None:
            raise ValueError("boolean_required")
    elif field == "vin":
        if (
            type(value) is not str
            or not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", value)
            or unit is not None
        ):
            raise ValueError("invalid_vin")
    elif type(value) is not str or not value.strip() or unit is not None:
        raise ValueError("text_required")


class Fact(Contract):
    field: FactField
    value: Scalar
    status: Literal[
        "extracted", "user_reported", "confirmed", "conflicting", "manufacturer_response"
    ]
    unit: Unit | None = None
    anchor: EvidenceAnchor | None = None

    @model_validator(mode="after")
    def valid_fact(self):
        _validate_value(self.field, self.value, self.unit)
        if self.status in {"extracted", "manufacturer_response"} and self.anchor is None:
            raise ValueError("document_anchor_required")
        return self


class Condition(Contract):
    id: Identifier
    field: FactField
    operator: Literal[
        "equals",
        "one_of",
        "at_most",
        "at_least",
        "before",
        "on_or_before",
        "after",
        "on_or_after",
        "present",
        "manufacturer_confirmation",
        "within_months",
    ]
    expected: Scalar | tuple[Scalar, ...] | None = None
    unit: Unit | None = None
    mandatory: StrictBool = True
    anchor: EvidenceAnchor
    reference_field: Literal["in_service_date"] | None = None
    anniversary_policy: Literal["clamp_to_last_day"] | None = None

    @model_validator(mode="after")
    def compatible_rule(self):
        if self.operator == "within_months":
            if (
                self.field != "repair_date"
                or type(self.expected) is not int
                or not 1 <= self.expected <= 600
                or self.reference_field != "in_service_date"
                or self.anniversary_policy is None
                or self.unit is not None
            ):
                raise ValueError("explicit_anniversary_rule_required")
            return self
        if self.reference_field is not None or self.anniversary_policy is not None:
            raise ValueError("unexpected_reference_rule")
        if self.operator in {"present", "manufacturer_confirmation"}:
            if self.expected is not None or self.unit is not None:
                raise ValueError("unexpected_condition_value")
            if (
                self.operator == "manufacturer_confirmation"
                and self.field != "vehicle_confirmation"
            ):
                raise ValueError("invalid_confirmation_field")
            return self
        if self.operator in {"at_most", "at_least"} and self.field not in NUMERIC_FIELDS:
            raise ValueError("numeric_field_required")
        if (
            self.operator in {"before", "on_or_before", "after", "on_or_after"}
            and self.field not in DATE_FIELDS
        ):
            raise ValueError("date_field_required")
        values = self.expected if isinstance(self.expected, tuple) else (self.expected,)
        if self.operator == "one_of":
            if not isinstance(self.expected, tuple) or not 1 <= len(values) <= 50:
                raise ValueError("bounded_choices_required")
        elif isinstance(self.expected, tuple):
            raise ValueError("scalar_expected")
        for value in values:
            _validate_value(self.field, value, self.unit)
        return self


class CaseSnapshot(Contract):
    case_id: Identifier
    revision: Annotated[StrictInt, Field(ge=1)]
    jurisdiction: Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z]{2}$")]
    facts: Annotated[tuple[Fact, ...], Field(max_length=100)]


class ProgrammeRevision(Contract):
    family_id: Identifier
    revision: Identifier
    category: Literal[
        "recall",
        "warranty_extension",
        "service_campaign",
        "reimbursement_provision",
        "bulletin_only",
        "unsupported_other",
    ]
    jurisdiction: Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z]{2}$")]
    make: ShortText
    reviewer_id: Identifier
    reviewed_at: AwareDatetime
    conditions: Annotated[tuple[Condition, ...], Field(min_length=1, max_length=50)]

    @model_validator(mode="after")
    def unique_conditions(self):
        if len({condition.id for condition in self.conditions}) != len(self.conditions):
            raise ValueError("duplicate_condition")
        if not self.make.strip():
            raise ValueError("empty_make")
        return self


class ConditionFinding(Contract):
    condition_id: Identifier
    field: FactField
    mandatory: StrictBool
    status: ConditionStatus
    reason: ShortText
    anchor: EvidenceAnchor
    missing_field: FactField | None = None


class ProgrammeAssessment(Contract):
    family_id: Identifier
    programme_revision: Identifier
    case_revision: Annotated[StrictInt, Field(ge=1)]
    state: AssessmentState
    scope_status: ConditionStatus
    scope_field: FactField = "make"
    conditions: Annotated[tuple[ConditionFinding, ...], Field(max_length=50)]
    requires_manufacturer_confirmation: StrictBool = True


class ExcludedCandidate(Contract):
    family_id: Identifier
    programme_revision: Identifier
    reason: ShortText


class SearchAssessment(Contract):
    search_status: Literal["complete", "unavailable", "stale", "unsupported"]
    state: AssessmentState | None
    reason: ShortText
    candidates: Annotated[tuple[ProgrammeAssessment, ...], Field(max_length=100)] = ()
    excluded: Annotated[tuple[ExcludedCandidate, ...], Field(max_length=100)] = ()


class EvidenceQuestion(Contract):
    condition_id: Identifier
    field: FactField
    reason: ShortText


class OutcomeEvent(Contract):
    id: Identifier
    kind: OutcomeKind
    amount: Money
    evidence_class: Literal["documented", "user_reported"]
    evidence_ref: Identifier
    repair_line_id: Identifier
    reverses: Identifier | None = None

    @model_validator(mode="after")
    def valid_event(self):
        if self.amount.amount <= 0 or self.reverses == self.id:
            raise ValueError("invalid_outcome_event")
        return self
