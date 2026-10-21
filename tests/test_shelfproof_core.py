"""ShelfProof's deterministic safety boundary; no model quality claims."""

from decimal import Decimal

import pytest
from contracts.shelfproof import Draft, FactPack, JudgeEvaluation, Rating
from pydantic import ValidationError
from shelfproof_api.core import check_draft, freeze_import, select_version, weighted_score


def facts(**overrides):
    return FactPack.model_validate(
        {
            "product_id": "000123",
            "brand": "Example",
            "name": "Oat flakes",
            "net_quantity": "500",
            "net_unit": "g",
            "ingredients": "Whole grain oats",
            "source_ref": "approved:row:1",
            **overrides,
        }
    )


def draft(**overrides):
    return Draft(
        **{"title": "Example Oat flakes 500 g", "description": "Whole grain oats", **overrides}
    )


def evaluation(value=4):
    return JudgeEvaluation(
        ratings={
            key: Rating(value=value, rationale="Supported")
            for key in ("fidelity", "coverage", "channel", "clarity", "brand")
        },
        findings=[],
    )


def test_fact_pack_preserves_identity_and_decimal_and_rejects_unknowns():
    assert facts().product_id == "000123"
    assert facts().net_quantity == Decimal(500)
    with pytest.raises(ValidationError):
        facts(extra="injected")
    with pytest.raises(ValidationError):
        facts(net_quantity="NaN")
    with pytest.raises(ValidationError):
        facts(net_quantity="-1")


def test_duplicate_json_keys_and_csv_headers_are_not_silently_overwritten():
    with pytest.raises(ValueError, match="duplicate"):
        freeze_import(b'[{"id":"1","id":"2"}]', "json", {"product_id": "id"})
    with pytest.raises(ValueError, match="duplicate"):
        freeze_import(b"id,id\n1,2\n", "csv", {"product_id": "id"})


def test_explicit_mapping_freeze_keeps_raw_lineage_and_gtin_zeros():
    raw = b"id,brand,name,quantity,unit,ingredients,source\n000123,Example,Oat flakes,500,g,Whole grain oats,approved:row:1\n"
    mapping = dict(
        zip(
            (
                "product_id",
                "brand",
                "name",
                "net_quantity",
                "net_unit",
                "ingredients",
                "source_ref",
            ),
            ("id", "brand", "name", "quantity", "unit", "ingredients", "source"),
        )
    )
    result = freeze_import(raw, "csv", mapping)
    assert result.facts[0].product_id == "000123"
    assert result.raw_hash != result.fact_hash
    assert result.mapping == mapping
    with pytest.raises(ValueError):
        freeze_import(raw, "csv", {})


def test_hard_checks_do_not_trust_judge_or_infer_allergen_claims():
    findings = check_draft(
        facts(), Draft(title="Example gluten-free Oat flakes 500 g", description="Whole grain oats")
    )
    assert any(f.family == "restricted_claim" and f.severity == "critical" for f in findings)
    bad = check_draft(facts(), Draft(title="Example Oat flakes 700 g", description="Healthy"))
    assert {f.family for f in bad} >= {"numeric", "coverage"}


def test_required_ingredient_order_and_brand_identity_cannot_disappear():
    findings = check_draft(
        facts(ingredients="Oats, salt"), Draft(title="Oat flakes 500 g", description="Salt, oats")
    )
    assert {f.rule for f in findings} >= {"required:brand", "required:ingredients"}


def test_unknown_scores_not_zero_and_rating_schema_is_bounded():
    result = evaluation()
    assert weighted_score(result) == 100
    result.ratings["fidelity"] = Rating(value=None, rationale="No source")
    assert weighted_score(result) is None
    with pytest.raises(ValidationError):
        Rating(value=5, rationale="invalid")
    with pytest.raises(ValidationError):
        Rating(value=True, rationale="bool is not a rating")


def test_selector_rejects_new_defect_even_when_score_rises():
    good = check_draft(facts(), draft())
    bad = check_draft(
        facts(), Draft(title="Example Organic Oat flakes 500 g", description="Whole grain oats")
    )
    decision = select_version(good, evaluation(3), bad, evaluation(4))
    assert not decision.adopt
    assert decision.reason == "new_blocking_defect"


def test_selector_ties_keep_incumbent_and_small_score_gains_do_not_churn():
    checks = check_draft(facts(), draft())
    assert not select_version(checks, evaluation(), checks, evaluation()).adopt
    assert select_version(checks, evaluation(3), checks, evaluation(4)).adopt


def test_restricted_official_name_is_out_of_scope_not_silently_renamed():
    with pytest.raises(ValueError, match="out_of_scope"):
        facts(name="Organic Oat flakes")


def test_judge_schema_has_finite_dimensions_not_unbounded_property_bag():
    schema = JudgeEvaluation.model_json_schema()
    ratings = schema["properties"]["ratings"]
    assert "$ref" in ratings
    definition = schema["$defs"][ratings["$ref"].split("/")[-1]]
    assert set(definition["properties"]) == {"fidelity", "coverage", "channel", "clarity", "brand"}
    assert definition["additionalProperties"] is False


def test_deep_json_and_nonliteral_cells_rejected_before_freeze():
    with pytest.raises(ValueError):
        freeze_import(b"[" * 2000 + b"]" * 2000, "json", {})


def test_unmapped_descriptive_claims_are_blocked_even_without_annotations():
    checked = check_draft(
        facts(), draft(description="Whole grain oats. Supercharged premium energy.")
    )
    assert any(f.rule == "unmapped_text" and f.severity == "material" for f in checked)


@pytest.mark.parametrize(
    "ingredients", ["Vitamin B12, oats", "OATS, SALT (LESS THAN 2%)", "Oats (50 g), salt"]
)
def test_literal_ingredient_numbers_are_not_reinterpreted_as_net_package_claims(ingredients):
    assert check_draft(facts(ingredients=ingredients), draft(description=ingredients)) == []
