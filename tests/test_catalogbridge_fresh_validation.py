import pytest

from scripts.prepare_catalogbridge_fresh_validation import select_pairs
from scripts.summarize_catalogbridge_fresh_validation import detail


def test_fresh_selection_balances_strata_and_excludes_reused_offers():
    rows, labels = [], {}
    for hard in (20, 50, 80):
        for label in (0, 1):
            for number in range(3):
                key = f"{hard}-{label}-{number}"
                rows.append({"id": key, "supplier": {"id": key + "s"}, "master": {"id": key + "m"}})
                labels[key] = {"hard": hard, "label": label}
    excluded = {"20-0-0s", "50-1-1m"}
    result = select_pairs(rows, labels, excluded, per_stratum=2)
    assert len(result) == 12
    ids = [r[side]["id"] for r in result for side in ("supplier", "master")]
    assert len(set(ids)) == len(ids) and not set(ids) & excluded
    assert select_pairs(list(reversed(rows)), labels, excluded, per_stratum=2) == result


def test_fresh_selection_refuses_incomplete_strata():
    with pytest.raises(ValueError, match="insufficient"):
        select_pairs([], {}, set())


def test_fresh_report_distinguishes_bad_links_from_abstentions():
    labels = {str(i): {"label": value} for i, value in enumerate([0, 1, 1, 0, 1, 0])}
    rows = [{"id": str(i), "prediction": value} for i, value in enumerate([1, 0, None, None, 1, 0])]
    report = detail(rows, labels)
    assert report["total"] == 6 and report["resolved"] == 4 and report["correct"] == 2
    assert report["binary_wrong_links"] == report["binary_wrong_nonmatches"] == 1
    assert report["abstained_positive"] == report["abstained_negative"] == 1
