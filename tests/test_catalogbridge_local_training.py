import numpy as np

from scripts.train_catalogbridge_local_router import (
    fit_trees,
    group_role,
    independent_band,
    predict,
)


def test_groups_always_have_one_role_and_cross_role_negatives_are_excluded():
    assert group_role("same", "same") in {"fit", "tune", "qualification"}
    for i in range(50):
        for j in range(20):
            if group_role(str(i), str(i)) != group_role(str(j), str(j)):
                assert group_role(str(i), str(j)) is None


def test_tree_training_is_deterministic_and_separates_toy_records():
    x = np.array([[0.0]] * 40 + [[1.0]] * 40)
    y = np.array([0] * 40 + [1] * 40)
    first = fit_trees(x, y, rounds=20, min_leaf=5)
    assert first == fit_trees(x, y, rounds=20, min_leaf=5)
    scores = predict(x, first)
    assert max(scores[:40]) < 0.1 and min(scores[40:]) > 0.9


def test_qualification_deduplicates_offers_and_reports_entity_reuse():
    rows = [
        {"id": "a", "offers": ["1", "2"], "groups": ["x", "y"], "label": 0},
        {"id": "b", "offers": ["1", "3"], "groups": ["x", "z"], "label": 0},
        {"id": "c", "offers": ["4", "5"], "groups": ["x", "w"], "label": 0},
    ]
    result = independent_band(rows, np.array([0.0, 0.0, 0.0]), 0.01, 0)
    assert result["samples"] == 2 and result["correct"] == 2
    assert result["internal_offer_overlap"] == 0
    assert result["reused_entity_groups"] == 1
    assert not result["qualified"]
