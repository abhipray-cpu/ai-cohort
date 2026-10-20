"""Campaign acceptance must not confuse terminal packets with full protocols."""

import pytest
from casecouncil_api.campaign import summarize_replay
from contracts.casecouncil import ROLES


def complete(case_id):
    return {
        "id": case_id,
        "state": "draft_ready",
        "calls": 8,
        "usage_known": 8,
        "all_tools_audited": True,
        "proposers": list(ROLES),
        "critic_available": True,
        "ballots": list(ROLES),
        "synthesis_available": True,
        "unavailable": [],
    }


def test_two_full_one_partial_three_pending_is_not_a_campaign_pass():
    partial = {**complete("c"), "state": "manual_required", "usage_known": 7}
    result = summarize_replay(list("abcdef"), [complete("a"), complete("b"), partial])
    assert result["terminal_packets"] == 3
    assert result["full_protocols"] == 2
    assert result["partial_or_failed"] == 1
    assert result["pending_ids"] == list("def")
    assert result["unknown_usage_calls"] == 1
    assert result["protocol_campaign_passed"] is False


@pytest.mark.parametrize(
    "change",
    [
        {"critic_available": False},
        {"ballots": list(ROLES)[:2]},
        {"proposers": list(ROLES)[:2]},
        {"synthesis_available": False},
        {"unavailable": ["synthesis"]},
        {"all_tools_audited": False},
        {"calls": 0, "usage_known": 0},
    ],
)
def test_draft_state_alone_cannot_pass_protocol_acceptance(change):
    result = summarize_replay(["a"], [{**complete("a"), **change}])
    assert result["full_protocols"] == 0
    assert result["protocol_campaign_passed"] is False


def test_full_protocols_do_not_claim_semantic_or_product_acceptance():
    result = summarize_replay(["a"], [complete("a")])
    assert result["protocol_campaign_passed"] is True
    assert result["full_protocols"] == 1
    assert result["full_product_accepted"] is False
    assert result["independent_semantic_accuracy"] == "not_measured"


def test_present_artifacts_with_unknown_history_are_not_a_fully_audited_pass():
    result = summarize_replay(
        ["a"], [{**complete("a"), "usage_known": 7, "all_tools_audited": False}]
    )
    assert result["all_protocol_artifacts_present"] is True
    assert result["protocol_artifacts_present"] == 1
    assert result["full_protocols"] == 0 and not result["protocol_campaign_passed"]


def test_empty_campaign_does_not_pass():
    assert summarize_replay([], [])["protocol_campaign_passed"] is False


@pytest.mark.parametrize(
    "selected,results",
    [(["a", "a"], []), (["a"], [complete("b")]), (["a"], [complete("a"), complete("a")])],
)
def test_duplicate_or_unselected_results_are_rejected(selected, results):
    with pytest.raises(ValueError):
        summarize_replay(selected, results)
