import importlib.util
from pathlib import Path

import pytest


def module(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_multispan_overlap_does_not_double_count_qualifiers():
    score = module("score_clausegate")
    assert score.span_counts([(0, 10), (5, 15)], [(7, 20)]) == (8, 15, 13)
    assert score.span_counts([], []) == (0, 0, 0)


def test_semantic_missing_predictions_are_false_negatives():
    score = module("score_clausegate")
    result = score.classification(
        [("Entailment", None), ("Contradiction", "Contradiction"), ("NotMentioned", "Entailment")]
    )
    assert result["pairs"] == 3 and result["correct"] == 1 and result["missing"] == 1
    assert result["per_class"]["Entailment"]["recall"] == 0


def test_acceptance_never_accepts_missing_or_failed_gates():
    gate = module("accept_clausegate")
    assert gate.verdict({"scope": "passed", "human": "blocked"}) == "blocked"
    assert gate.verdict({"scope": "failed", "human": "blocked"}) == "rejected"
    assert gate.verdict({}) == "blocked"


def test_length_sample_is_deterministic_distinct_and_covers_extremes():
    validator = module("validate_clausegate")
    rows = [{"id": i, "document": {"text": "x" * (i + 1), "text_hash": str(i)}} for i in range(61)]
    selected = validator.length_sample(list(reversed(rows)), 30)
    assert len(selected) == len({r["id"] for r in selected}) == 30
    assert selected[0]["id"] == 0 and selected[-1]["id"] == 60
    assert selected == validator.length_sample(rows, 30)
    assert validator.length_sample(rows, 0) == []
    assert validator.length_sample(rows, 1)[0]["id"] == 30
    assert len(validator.length_sample(rows + [rows[0]], 100)) == 61


def test_complement_cohort_excludes_prior_ids_and_duplicate_text_not_gold():
    validator = module("validate_clausegate")
    rows = [
        {"id": 1, "document": {"text_hash": "same"}},
        {"id": 2, "document": {"text_hash": "same"}},
        {"id": 3, "document": {"text_hash": "new"}},
    ]
    assert validator.remaining_rows(rows, {1}) == [rows[2]]
    assert validator.remaining_rows(rows, set()) == rows


def test_duplicate_screen_normalizes_case_and_punctuation_not_word_order():
    screen = module("screen_clausegate_corpus")
    a = screen.shingles("ONE two, three four five six seven")
    b = screen.shingles("one TWO three four five six seven")
    assert screen.similarity(a, b) == 1
    assert screen.similarity(a, screen.shingles("seven six five four three two one")) == 0


def test_evidence_token_score_unions_overlapping_ranges_and_keeps_unicode():
    score = module("score_clausegate")
    assert score.token_counts("Café, NDA!", [(0, 5), (0, 4)], [(0, 4)]) == (1, 2, 1)
    assert score.token_counts("Café, NDA!", [], [(6, 10)]) == (0, 0, 2)


def test_majority_baseline_uses_training_only():
    score = module("score_clausegate")
    rows = [
        {"split": "train", "gold": {"h": {"choice": "Entailment"}}},
        {"split": "dev", "gold": {"h": {"choice": "NotMentioned"}}},
        {"split": "test", "gold": {"h": {"choice": "NotMentioned"}}},
    ]
    assert score.majorities(rows) == {"h": "Entailment"}


def test_live_acceptance_counts_distinct_documents_not_repeated_jobs():
    gate = module("accept_clausegate")
    job = {"source_id": 1, "job": {"status": "completed"}}
    assert gate.live_gate([job] * 30) == "blocked"
    jobs = [{"source_id": i, "job": {"status": "completed"}} for i in range(30)]
    assert gate.live_gate(jobs) == "passed"
    jobs[-1]["job"]["status"] = "partial"
    assert gate.live_gate(jobs) == "blocked"


def test_paired_comparison_separates_restored_availability_from_semantic_correction():
    comparison = module("compare_clausegate_campaigns")
    before = [
        {"source_id": 1, "hypothesis": "a", "gold": "Entailment", "predicted": None},
        {"source_id": 1, "hypothesis": "b", "gold": "Entailment", "predicted": "Entailment"},
    ]
    after = [{**before[0], "predicted": "Entailment"}, {**before[1], "predicted": "NotMentioned"}]
    result = comparison.paired_changes(before, after)
    assert result["newly_available_pairs"] == 1 and result["newly_available_correct"] == 1
    assert result["previously_available_old_correct"] == 1
    assert result["previously_available_new_correct"] == 0
    assert result["corrected"] == result["regressed"] == 1


def test_development_aggregation_pools_counts_not_average_f1():
    aggregation = module("aggregate_clausegate_development")
    result = aggregation.pool_evidence(
        [
            {"intersection": 0, "predicted": 1000, "gold": 1000},
            {"intersection": 1, "predicted": 1, "gold": 1},
        ]
    )
    assert result["f1"] == pytest.approx(1 / 1001)
    with pytest.raises(ValueError):
        aggregation.pool_evidence([{"intersection": 2, "predicted": 1, "gold": 1}])


def test_development_aggregation_rejects_duplicate_predictions():
    aggregation = module("aggregate_clausegate_development")
    pair = {"source_id": 1, "hypothesis": "h"}
    assert aggregation.merge_pairs([[pair]]) == [pair]
    with pytest.raises(ValueError):
        aggregation.merge_pairs([[pair], [pair]])
