import pytest
from shelfproof_api.validation import acceptance_gates, select_smoke_records
from test_shelfproof_core import facts


def test_smoke_selection_never_reads_holdout_and_requires_distinct_groups():
    records = [
        {
            "split": "locked",
            "group": "hidden",
            "facts": facts(product_id="gold").model_dump(mode="json"),
            "raw": {"brandOwner": "hidden"},
        }
    ]
    records += [
        {
            "split": "development",
            "group": str(i // 2),
            "facts": facts(product_id=str(i)).model_dump(mode="json"),
            "raw": {"brandOwner": str(i // 2)},
        }
        for i in range(12)
    ]
    selected = select_smoke_records(records)
    assert len(selected) == 6
    assert len({r["group"] for r in selected}) == 6
    assert all(r["split"] == "development" for r in selected)
    with pytest.raises(ValueError):
        select_smoke_records(records[:3])


def test_smoke_excludes_source_policy_conflicts_and_duplicate_owners_before_inference():
    records = [
        {
            "split": "development",
            "group": str(i),
            "facts": facts(product_id=str(i)).model_dump(mode="json"),
            "raw": {"brandOwner": "Alias owner" if i < 2 else f"Owner {i}"},
        }
        for i in range(9)
    ]
    records[2]["facts"]["ingredients"] = "Organic oats"
    selected = select_smoke_records(records)
    assert len(selected) == 6
    assert len({r["raw"]["brandOwner"] for r in selected}) == 6
    assert all(r["facts"]["product_id"] != "2" for r in selected)


def test_fixture_or_high_judge_score_cannot_pass_actual_provider_or_quality_gate():
    result = acceptance_gates(
        {
            "mode": "controlled_provider",
            "rows": 1000,
            "score": 100,
            "unknown_attempts": 0,
            "actual_calls": 2000,
            "all_concepts_observed": True,
            "terminal": 1000,
        }
    )
    assert result["actual_provider"] == "not_run"
    assert result["independent_quality"] == "not_run"
    assert result["production_accepted"] is False


def test_unknown_usage_fails_provider_gate_and_keeps_other_gates_pending():
    result = acceptance_gates(
        {
            "mode": "actual_installed_codex",
            "unknown_attempts": 1,
            "actual_calls": 1,
            "all_concepts_observed": False,
            "terminal": 1,
            "rows": 6,
        }
    )
    assert result["actual_provider"] == "fail"
    assert result["browser"] == "not_run" and result["windows_tunnel"] == "not_run"


def test_complete_but_manual_rows_cannot_pass_live_workflow_gate():
    result = acceptance_gates(
        {
            "mode": "actual_installed_codex",
            "actual_calls": 20,
            "unknown_attempts": 0,
            "all_concepts_observed": True,
            "terminal": 6,
            "rows": 6,
            "states": {"review_ready": 5, "manual_required": 1},
        }
    )
    assert result["actual_provider"] == "fail"
