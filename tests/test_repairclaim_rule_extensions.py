"""Programme-specific date semantics and vehicle identity; authored rules only."""

import pytest
from contracts.repairclaim import Fact
from pydantic import ValidationError
from repairclaim_api.core import evaluate_programme, next_question
from test_repairclaim_core import fact, programme, rule, snapshot


def test_differing_vins_block_a_programme_even_without_a_vin_specific_predicate():
    first = Fact(field="vin", value="1HGCM82633A004352", status="confirmed")
    second = Fact(field="vin", value="1HGCM82633A004353", status="confirmed")
    result = evaluate_programme(
        snapshot([fact("make", "Honda"), fact(), first, second]), programme()
    )
    assert result.state == "conflicting_information"
    assert next_question(result).field == "vin"


@pytest.mark.parametrize("vin", ["123", "1HGCM82633I004352", "1HGCM82633O004352"])
def test_invalid_vin_is_not_an_attributed_valid_vehicle_identity(vin):
    with pytest.raises(ValidationError):
        Fact(field="vin", value=vin, status="user_reported")


def relative_rule(**changes):
    return rule(
        field="repair_date",
        operator="within_months",
        expected=12,
        unit=None,
        reference_field="in_service_date",
        anniversary_policy="clamp_to_last_day",
        **changes,
    )


@pytest.mark.parametrize(
    "repair,status", [("2025-02-28", "satisfied"), ("2025-03-01", "not_satisfied")]
)
def test_relative_age_uses_an_explicit_reviewed_calendar_anniversary(repair, status):
    result = evaluate_programme(
        snapshot(
            [
                fact("make", "Honda"),
                fact("in_service_date", "2024-02-29"),
                fact("repair_date", repair),
            ]
        ),
        programme((relative_rule(),)),
    )
    assert result.conditions[0].status == status


def test_missing_in_service_date_is_not_replaced_by_model_year_and_question_is_specific():
    result = evaluate_programme(
        snapshot(
            [fact("make", "Honda"), fact("model_year", 2024), fact("repair_date", "2025-02-28")]
        ),
        programme((relative_rule(),)),
    )
    assert result.state == "missing_evidence"
    assert next_question(result).field == "in_service_date"


def test_relative_rule_requires_explicit_origin_and_anniversary_policy():
    with pytest.raises(ValidationError):
        rule(field="repair_date", operator="within_months", expected=12, unit=None)


def test_impossible_repair_chronology_requires_review():
    result = evaluate_programme(
        snapshot(
            [
                fact("make", "Honda"),
                fact("in_service_date", "2025-01-01"),
                fact("repair_date", "2024-12-31"),
            ]
        ),
        programme((relative_rule(),)),
    )
    assert result.state == "conflicting_information"
