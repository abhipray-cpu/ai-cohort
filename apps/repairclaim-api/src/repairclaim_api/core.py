"""Pure condition/evidence/outcome rules. No network, inference or action authority."""

import calendar
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Literal

from contracts.repairclaim import (
    DATE_FIELDS,
    NUMERIC_FIELDS,
    CaseSnapshot,
    Condition,
    ConditionFinding,
    EvidenceAnchor,
    EvidenceQuestion,
    ExcludedCandidate,
    Fact,
    OutcomeEvent,
    ProgrammeAssessment,
    ProgrammeRevision,
    SearchAssessment,
    quantity,
)


def _canonical(field: str, value: object, unit: str | None):
    if field in NUMERIC_FIELDS:
        number = quantity(value)
        if unit in {"mi", "km"}:
            return number * (Decimal("1.609344") if unit == "mi" else Decimal(1))
        return number
    if field in DATE_FIELDS:
        return date.fromisoformat(value)
    return value.strip().casefold() if isinstance(value, str) else value


def _usable_facts(snapshot: CaseSnapshot, field: str) -> tuple[list[Fact], str | None]:
    facts = [fact for fact in snapshot.facts if fact.field == field]
    if any(fact.status == "conflicting" for fact in facts):
        return facts, "conflicting"
    usable = [fact for fact in facts if fact.status != "extracted"]
    values = {
        (
            _canonical(field, fact.value, fact.unit),
            fact.unit if field in {"paid_amount", "invoice_total"} else None,
        )
        for fact in facts
    }
    if len(values) > 1:
        return usable, "conflicting"
    return usable, None if usable else "unknown"


def _condition(snapshot: CaseSnapshot, condition: Condition) -> ConditionFinding:
    facts, issue = _usable_facts(snapshot, condition.field)
    missing_field = None
    if condition.operator == "manufacturer_confirmation" and issue != "conflicting":
        status, reason = "confirmation_required", "manufacturer_confirmation_required"
    elif issue:
        status, reason = issue, "conflicting_facts" if issue == "conflicting" else "needs_evidence"
    elif condition.operator == "manufacturer_confirmation":
        status, reason = "confirmation_required", "manufacturer_confirmation_required"
    elif condition.operator == "present":
        status, reason = "satisfied", "attributed_fact_present"
    elif condition.operator == "within_months":
        origins, origin_issue = _usable_facts(snapshot, condition.reference_field)
        if origin_issue:
            status, reason, missing_field = origin_issue, "needs_in_service_date", "in_service_date"
        else:
            start, repair = date.fromisoformat(origins[0].value), date.fromisoformat(facts[0].value)
            months = start.year * 12 + start.month - 1 + condition.expected
            year, month = divmod(months, 12)
            end = date(year, month + 1, min(start.day, calendar.monthrange(year, month + 1)[1]))
            status = (
                "conflicting"
                if repair < start
                else "satisfied"
                if repair <= end
                else "not_satisfied"
            )
            reason = "invalid_chronology" if repair < start else "reviewed_calendar_anniversary"
    elif condition.field in {"paid_amount", "invoice_total"} and facts[0].unit != condition.unit:
        status, reason = "unknown", "currency_mismatch"
    else:
        actual = _canonical(condition.field, facts[0].value, facts[0].unit)
        values = (
            condition.expected if isinstance(condition.expected, tuple) else (condition.expected,)
        )
        expected = [_canonical(condition.field, value, condition.unit) for value in values]
        checks = {
            "equals": lambda: actual == expected[0],
            "one_of": lambda: actual in expected,
            "at_most": lambda: actual <= expected[0],
            "at_least": lambda: actual >= expected[0],
            "before": lambda: actual < expected[0],
            "on_or_before": lambda: actual <= expected[0],
            "after": lambda: actual > expected[0],
            "on_or_after": lambda: actual >= expected[0],
        }
        status = "satisfied" if checks[condition.operator]() else "not_satisfied"
        reason = "documented_condition_comparison"
    return ConditionFinding(
        condition_id=condition.id,
        field=condition.field,
        mandatory=condition.mandatory,
        status=status,
        reason=reason,
        anchor=condition.anchor,
        missing_field=missing_field,
    )


def _overall(findings: tuple[ConditionFinding, ...], scope_status: str):
    if scope_status == "conflicting" or any(f.status == "conflicting" for f in findings):
        return "conflicting_information"
    required = [finding for finding in findings if finding.mandatory]
    if scope_status == "not_satisfied" or any(f.status == "not_satisfied" for f in required):
        return "appears_outside_conditions"
    if scope_status == "unknown" or any(f.status == "unknown" for f in required):
        return "missing_evidence"
    return "potentially_applicable"


def evaluate_programme(snapshot: CaseSnapshot, programme: ProgrammeRevision) -> ProgrammeAssessment:
    """Compare reviewed conditions; never authenticate manufacturer coverage or ownership."""
    if programme.category in {"bulletin_only", "unsupported_other"}:
        raise ValueError("not_coverage_authority")
    facts, issue = _usable_facts(snapshot, "make")
    scope_status = issue or (
        "satisfied"
        if snapshot.jurisdiction == programme.jurisdiction
        and str(facts[0].value).strip().casefold() == programme.make.strip().casefold()
        else "not_satisfied"
    )
    scope_field = "make"
    for identity_field in ("vin", "model", "model_year"):
        if _usable_facts(snapshot, identity_field)[1] == "conflicting":
            scope_status, scope_field = "conflicting", identity_field
            break
    findings = tuple(_condition(snapshot, condition) for condition in programme.conditions)
    return ProgrammeAssessment(
        family_id=programme.family_id,
        programme_revision=programme.revision,
        case_revision=snapshot.revision,
        state=_overall(findings, scope_status),
        scope_status=scope_status,
        scope_field=scope_field,
        conditions=findings,
    )


def evaluate_search(
    snapshot: CaseSnapshot,
    programmes: tuple[ProgrammeRevision, ...],
    *,
    search_status: Literal["complete", "unavailable", "stale", "unsupported"] = "complete",
) -> SearchAssessment:
    if search_status not in {"complete", "unavailable", "stale", "unsupported"}:
        raise ValueError("invalid_search_status")
    if len(programmes) > 100:
        raise ValueError("too_many_programmes")
    if search_status != "complete":
        return SearchAssessment(
            search_status=search_status, state=None, reason="search_not_complete"
        )
    make, problem = _usable_facts(snapshot, "make")
    if snapshot.jurisdiction != "US":
        return SearchAssessment(
            search_status="unsupported", state=None, reason="unsupported_jurisdiction"
        )
    if problem:
        return SearchAssessment(
            search_status="complete",
            state=("conflicting_information" if problem == "conflicting" else "missing_evidence"),
            reason="vehicle_make_needs_review",
        )
    if str(make[0].value).strip().casefold() != "honda":
        return SearchAssessment(search_status="unsupported", state=None, reason="unsupported_make")
    candidates, excluded, seen, families = [], [], set(), set()
    for programme in programmes:
        identity = (programme.family_id, programme.revision)
        if identity in seen:
            raise ValueError("duplicate_programme")
        if programme.family_id in families:
            raise ValueError("programme_revision_conflict")
        seen.add(identity)
        families.add(programme.family_id)
        if programme.category in {"bulletin_only", "unsupported_other"}:
            reason = "not_coverage_authority"
        elif (
            programme.jurisdiction != snapshot.jurisdiction
            or programme.make.strip().casefold() != "honda"
        ):
            reason = "outside_supported_scope"
        else:
            candidates.append(evaluate_programme(snapshot, programme))
            continue
        excluded.append(
            ExcludedCandidate(
                family_id=programme.family_id, programme_revision=programme.revision, reason=reason
            )
        )
    if not candidates:
        state = "no_supported_programme_found"
    else:
        order = [
            "potentially_applicable",
            "conflicting_information",
            "missing_evidence",
            "appears_outside_conditions",
        ]
        state = next(value for value in order if any(item.state == value for item in candidates))
    return SearchAssessment(
        search_status="complete",
        state=state,
        reason="bounded_supported_inventory_only",
        candidates=tuple(candidates),
        excluded=tuple(excluded),
    )


def next_question(assessment: ProgrammeAssessment) -> EvidenceQuestion | None:
    if assessment.state == "appears_outside_conditions":
        return None
    if assessment.scope_status in {"unknown", "conflicting"}:
        return EvidenceQuestion(
            condition_id="vehicle_identity",
            field=assessment.scope_field,
            reason="vehicle_identity_needs_review",
        )
    for status in ("conflicting", "unknown", "confirmation_required"):
        for finding in assessment.conditions:
            if finding.mandatory and finding.status == status:
                return EvidenceQuestion(
                    condition_id=finding.condition_id,
                    field=finding.missing_field or finding.field,
                    reason=finding.reason,
                )
    return None


def verify_anchor(anchor: EvidenceAnchor, pages: list[dict]) -> bool:
    """Reference existence only; not contextual entailment or document authentication."""

    def normalize(value):
        return re.sub(r"\s+", " ", value).strip()

    return any(
        page.get("document_id") == anchor.document_id
        and page.get("sha256") == anchor.sha256
        and page.get("page") == anchor.page
        and normalize(anchor.quote) in normalize(page.get("text", ""))
        for page in pages
    )


def summarize_outcomes(events: tuple[OutcomeEvent, ...]) -> dict:
    totals = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))
    seen, reversed_amounts = {}, defaultdict(Decimal)
    for event in events:
        if event.id in seen:
            if event != seen[event.id]:
                raise ValueError("conflicting_event")
            continue
        if event.reverses:
            original = seen.get(event.reverses)
            if (
                original is None
                or original.reverses is not None
                or (
                    original.kind,
                    original.amount.currency,
                    original.repair_line_id,
                    original.evidence_class,
                )
                != (event.kind, event.amount.currency, event.repair_line_id, event.evidence_class)
                or reversed_amounts[original.id] + event.amount.amount > original.amount.amount
            ):
                raise ValueError("invalid_reversal")
            reversed_amounts[original.id] += event.amount.amount
        seen[event.id] = event
        totals[event.amount.currency][event.kind][event.evidence_class] += (
            -event.amount.amount if event.reverses else event.amount.amount
        )
    return {
        currency: {kind: dict(amounts) for kind, amounts in kinds.items()}
        for currency, kinds in totals.items()
    }
