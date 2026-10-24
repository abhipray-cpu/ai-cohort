"""RepairClaim deterministic foundations; all programmes and facts are authored fixtures."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from contracts.repairclaim import (
    CaseSnapshot,
    Condition,
    EvidenceAnchor,
    Fact,
    Money,
    OutcomeEvent,
    ProgrammeRevision,
)
from pydantic import ValidationError
from repairclaim_api.core import (
    evaluate_programme,
    evaluate_search,
    next_question,
    summarize_outcomes,
    verify_anchor,
)


def anchor(**changes):
    return EvidenceAnchor.model_validate(
        {
            "document_id": "source-1",
            "sha256": "a" * 64,
            "page": 1,
            "quote": "At most 100000 miles at repair.",
            **changes,
        }
    )


def rule(**changes):
    return Condition.model_validate(
        {
            "id": "mileage",
            "field": "repair_mileage",
            "operator": "at_most",
            "expected": "100000",
            "unit": "mi",
            "anchor": anchor(),
            **changes,
        }
    )


def fact(field="repair_mileage", value="90000", **changes):
    return Fact.model_validate(
        {
            "field": field,
            "value": value,
            "status": "user_reported",
            "unit": "mi" if field in {"repair_mileage", "current_mileage"} else None,
            **changes,
        }
    )


def snapshot(facts=None, **changes):
    return CaseSnapshot.model_validate(
        {
            "case_id": "case-1",
            "revision": 1,
            "jurisdiction": "US",
            "facts": facts
            if facts is not None
            else (fact("make", "Honda"), fact(), fact("component", "compressor")),
            **changes,
        }
    )


def programme(conditions=None, **changes):
    return ProgrammeRevision.model_validate(
        {
            "family_id": "fixture-only",
            "revision": "r1",
            "category": "warranty_extension",
            "jurisdiction": "US",
            "make": "Honda",
            "reviewer_id": "reviewer-1",
            "reviewed_at": datetime(2026, 10, 22, tzinfo=UTC),
            "conditions": conditions if conditions is not None else (rule(),),
            **changes,
        }
    )


def event(id="e1", **changes):
    return OutcomeEvent.model_validate(
        {
            "id": id,
            "kind": "received",
            "amount": Money(amount="100.10", currency="USD"),
            "evidence_class": "documented",
            "evidence_ref": "receipt-1",
            "repair_line_id": "repair-1",
            **changes,
        }
    )


def test_unknown_contract_fields_and_mutation_are_rejected():
    with pytest.raises(ValidationError):
        snapshot(coverage_guaranteed=True)
    with pytest.raises(ValidationError):
        fact().value = "80000"


@pytest.mark.parametrize("amount", [True, 1.1, "NaN", "Infinity", "-1", "1.001", "1e100"])
def test_money_rejects_unsafe_or_imprecise_values(amount):
    with pytest.raises(ValidationError):
        Money(amount=amount, currency="USD")


def test_money_preserves_decimal_and_currency_without_conversion():
    assert Money(amount="0001.20", currency="USD").amount == Decimal("1.20")
    with pytest.raises(ValidationError):
        Money(amount="1", currency="usd")


@pytest.mark.parametrize(
    "changes",
    [
        {"value": True},
        {"value": "NaN"},
        {"value": "-2"},
        {"value": 1.5},
        {"unit": "meters"},
        {"field": "invented_fact"},
    ],
)
def test_fact_schema_rejects_invalid_quantities_and_unknown_fields(changes):
    with pytest.raises(ValidationError):
        fact(**changes)


def test_document_attribution_and_dates_are_not_optional_for_extracted_facts():
    with pytest.raises(ValidationError):
        fact(status="extracted")
    assert fact(status="extracted", anchor=anchor()).anchor.page == 1
    with pytest.raises(ValidationError):
        fact("repair_date", "2026-02-30")


@pytest.mark.parametrize(
    "changes",
    [
        {"field": "component"},
        {"expected": True},
        {"expected": "NaN"},
        {"expected": "-1"},
        {"unit": None},
        {"operator": "guess"},
    ],
)
def test_conditions_cannot_pair_numeric_rules_with_incompatible_fields(changes):
    with pytest.raises(ValidationError):
        rule(**changes)


def test_empty_or_duplicate_programme_conditions_are_rejected():
    with pytest.raises(ValidationError):
        programme(conditions=())
    with pytest.raises(ValidationError):
        programme(conditions=(rule(), rule()))
    with pytest.raises(ValidationError):
        programme(reviewed_at=datetime(2026, 10, 22))


@pytest.mark.parametrize(
    "value,status", [("99999", "satisfied"), ("100000", "satisfied"), ("100001", "not_satisfied")]
)
def test_explicit_mileage_boundaries(value, status):
    result = evaluate_programme(snapshot([fact("make", "Honda"), fact(value=value)]), programme())
    assert result.conditions[0].status == status
    assert result.state == (
        "appears_outside_conditions" if status == "not_satisfied" else "potentially_applicable"
    )
    assert result.requires_manufacturer_confirmation


def test_kilometres_convert_exactly_and_current_mileage_does_not_fill_repair_mileage():
    matched = evaluate_programme(
        snapshot([fact("make", "Honda"), fact(value="160934.4", unit="km")]), programme()
    )
    assert matched.conditions[0].status == "satisfied"
    missing = evaluate_programme(
        snapshot([fact("make", "Honda"), fact("current_mileage", "50000")]), programme()
    )
    assert missing.state == "missing_evidence"
    assert next_question(missing).field == "repair_mileage"


def test_unconfirmed_extraction_cannot_satisfy_a_condition():
    result = evaluate_programme(
        snapshot([fact("make", "Honda"), fact(status="extracted", anchor=anchor())]), programme()
    )
    assert result.conditions[0].status == "unknown"
    assert result.state == "missing_evidence"


def test_duplicate_disagreeing_facts_conflict_instead_of_last_value_wins():
    result = evaluate_programme(
        snapshot([fact("make", "Honda"), fact(), fact(value="110000")]), programme()
    )
    assert result.state == "conflicting_information"
    assert result.conditions[0].status == "conflicting"
    assert next_question(result).field == "repair_mileage"


def test_equivalent_units_are_not_a_false_conflict():
    result = evaluate_programme(
        snapshot([fact("make", "Honda"), fact(value="100000"), fact(value="160934.4", unit="km")]),
        programme(),
    )
    assert result.conditions[0].status == "satisfied"


def test_material_conflict_has_precedence_over_another_failed_condition():
    conditions = (
        rule(),
        rule(
            id="component", field="component", operator="equals", expected="compressor", unit=None
        ),
    )
    result = evaluate_programme(
        snapshot(
            [fact("make", "Honda"), fact(), fact(value="110000"), fact("component", "brakes")]
        ),
        programme(conditions),
    )
    assert result.state == "conflicting_information"


@pytest.mark.parametrize(
    "operator,value,status",
    [
        ("before", "2026-10-22", "not_satisfied"),
        ("on_or_before", "2026-10-22", "satisfied"),
        ("after", "2026-10-22", "not_satisfied"),
        ("on_or_after", "2026-10-22", "satisfied"),
        ("before", "2026-10-21", "satisfied"),
    ],
)
def test_date_operators_do_not_invent_inclusivity(operator, value, status):
    condition = rule(field="repair_date", operator=operator, expected="2026-10-22", unit=None)
    result = evaluate_programme(
        snapshot([fact("make", "Honda"), fact("repair_date", value)]), programme((condition,))
    )
    assert result.conditions[0].status == status


def test_a_manufacturer_confirmation_is_not_derived_from_a_user_boolean():
    condition = rule(
        field="vehicle_confirmation", operator="manufacturer_confirmation", expected=None, unit=None
    )
    result = evaluate_programme(
        snapshot([fact("make", "Honda"), fact("vehicle_confirmation", True)]),
        programme((condition,)),
    )
    assert result.conditions[0].status == "confirmation_required"


@pytest.mark.parametrize("state", ["unavailable", "stale", "unsupported"])
def test_source_failures_are_not_completed_negative_searches(state):
    result = evaluate_search(snapshot(), (), search_status=state)
    assert result.state is None
    assert result.search_status == state


def test_complete_empty_search_is_qualified_and_bulletin_is_not_coverage():
    assert evaluate_search(snapshot(), ()).state == "no_supported_programme_found"
    result = evaluate_search(snapshot(), (programme(category="bulletin_only"),))
    assert result.state == "no_supported_programme_found"
    assert result.excluded[0].reason == "not_coverage_authority"


def test_unsupported_vehicle_cannot_look_like_a_supported_negative():
    assert evaluate_search(snapshot(jurisdiction="IN"), ()).search_status == "unsupported"
    assert evaluate_search(snapshot([fact("make", "Toyota")]), ()).search_status == "unsupported"
    assert evaluate_search(snapshot([]), ()).state == "missing_evidence"


def test_good_candidate_is_not_overruled_by_a_different_candidate_failure():
    bad = programme(family_id="other-fixture", conditions=(rule(expected="100"),))
    result = evaluate_search(snapshot(), (bad, programme()))
    assert result.state == "potentially_applicable"
    assert len(result.candidates) == 2


def test_relevance_cannot_override_wrong_component():
    condition = rule(
        id="component", field="component", operator="equals", expected="engine", unit=None
    )
    result = evaluate_search(snapshot(), (programme((condition,)),))
    assert result.state == "appears_outside_conditions"


def test_anchor_binds_hash_page_and_literal_quote_but_not_contextual_truth():
    page = {
        "document_id": "source-1",
        "sha256": "a" * 64,
        "page": 1,
        "text": "Rules: At most 100000\n miles at repair.",
    }
    assert verify_anchor(anchor(), [page])
    assert not verify_anchor(anchor(sha256="b" * 64), [page])
    assert not verify_anchor(anchor(page=2), [page])
    assert not verify_anchor(anchor(quote="All repairs are free"), [page])


def test_outcome_totals_do_not_double_count_approval_as_payment():
    result = summarize_outcomes(
        (
            event(),
            event("approval", kind="approved"),
            event("euro", amount=Money(amount="2", currency="EUR")),
            event("asserted", evidence_class="user_reported"),
        )
    )
    assert result["USD"]["received"]["documented"] == Decimal("100.10")
    assert result["USD"]["approved"]["documented"] == Decimal("100.10")
    assert result["USD"]["received"]["user_reported"] == Decimal("100.10")
    assert result["EUR"]["received"]["documented"] == Decimal(2)


def test_outcome_idempotency_partial_reversals_and_conflicts():
    paid = event()
    reversal = event("reverse", amount=Money(amount="20.05", currency="USD"), reverses="e1")
    assert summarize_outcomes((paid, paid, reversal))["USD"]["received"]["documented"] == Decimal(
        "80.05"
    )
    with pytest.raises(ValueError, match="conflicting_event"):
        summarize_outcomes((paid, event(kind="approved")))
    with pytest.raises(ValueError, match="invalid_reversal"):
        summarize_outcomes((reversal,))
    with pytest.raises(ValueError, match="invalid_reversal"):
        summarize_outcomes((paid, reversal, event("reverse2", reverses="e1")))
    with pytest.raises(ValueError, match="invalid_reversal"):
        summarize_outcomes((paid, event("reverse3", reverses="e1", kind="approved")))


def test_empty_outcomes_are_unknown_not_a_savings_counter():
    assert summarize_outcomes(()) == {}


def test_two_revisions_of_one_programme_require_authority_resolution():
    with pytest.raises(ValueError, match="programme_revision_conflict"):
        evaluate_search(snapshot(), (programme(), programme(revision="r2")))


def test_noncoverage_documents_cannot_bypass_search_filter_via_direct_evaluation():
    with pytest.raises(ValueError, match="not_coverage_authority"):
        evaluate_programme(snapshot(), programme(category="bulletin_only"))


def test_contradictory_unreviewed_extraction_is_not_silently_ignored():
    result = evaluate_programme(
        snapshot(
            [
                fact("make", "Honda"),
                fact(),
                fact(value="110000", status="extracted", anchor=anchor()),
            ]
        ),
        programme(),
    )
    assert result.state == "conflicting_information"


def test_known_exclusion_does_not_prompt_for_irrelevant_missing_records():
    missing = rule(id="code", field="diagnostic_code", operator="present", expected=None, unit=None)
    result = evaluate_programme(snapshot(), programme((rule(expected="100"), missing)))
    assert result.state == "appears_outside_conditions"
    assert next_question(result) is None


def test_external_confirmation_is_a_distinct_condition_without_a_guessed_boolean():
    condition = rule(
        field="vehicle_confirmation", operator="manufacturer_confirmation", expected=None, unit=None
    )
    result = evaluate_programme(snapshot(), programme((condition,)))
    assert result.conditions[0].status == "confirmation_required"
    assert result.state == "potentially_applicable"


def test_schema_roundtrip_retains_immutable_fact_values_and_bounded_collections():
    original = snapshot()
    assert CaseSnapshot.model_validate_json(original.model_dump_json()) == original
    with pytest.raises(ValidationError):
        snapshot(facts=[fact()] * 101)
    with pytest.raises(ValidationError):
        anchor(quote=" ")
