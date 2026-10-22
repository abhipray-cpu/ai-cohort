from decimal import Decimal

import pytest
from contracts.releasefence import Event, Policy, Release, Usage
from pydantic import ValidationError
from releasefence_api.core import analyze, assignment, detect, digest, metrics


def release(**kw):
    return Release(
        application="support",
        code_digest="a" * 64,
        prompt_digest="b" * 64,
        model_config_digest="c" * 64,
        tools_digest="d" * 64,
        policy_revision="one",
        **kw,
    )


def event(key="1", kind="accepted", **kw):
    return Event(
        **{
            "id": key,
            "session": "s",
            "task": "t",
            "release": "a" * 64,
            "kind": kind,
            "at": 100,
            **kw,
        }
    )


def test_manifest_is_content_addressed_and_extra_fields_nonfinite_usage_rejected():
    assert digest(release()) != digest(release(index_digest="e" * 64))
    with pytest.raises(ValidationError):
        release(unsafe=True)
    with pytest.raises(ValidationError):
        Usage(attempt="call", reported_cost="NaN")
    with pytest.raises(ValidationError):
        Usage(attempt="call", estimated_cost="1")
    with pytest.raises(ValidationError):
        Usage(attempt="call", input_tokens=2, cached_input_tokens=3)
    with pytest.raises(ValidationError):
        event(
            "inconsistent",
            kind="terminal",
            outcome="success",
            model_calls=0,
            stop_reason="iteration_exhausted",
        )


def test_metrics_dedup_failures_unknown_cost_and_zero_success_are_honest():
    events = [
        event(),
        event("2", "terminal", outcome="failure", duration_ms=1000, model_calls=1),
        event("3", "usage", usage=Usage(attempt="call", reported_cost=Decimal("0.2"))),
    ]
    value = metrics(events + events)
    assert value["accepted"] == 1 and value["failed"] == 1 and value["p95_ms"] == 1000
    assert value["known_cost"] == "0.2" and value["cost_per_success"] is None
    assert value["unknown_calls"] == 0
    with pytest.raises(ValueError):
        metrics(events + [event(kind="heartbeat")])
    assert metrics([event()])["coverage"] == 0
    assert metrics([])["p95_ms"] is None
    assert (
        metrics([event(), event("x", "terminal", outcome="success", duration_ms=2, model_calls=1)])[
            "unknown_calls"
        ]
        == 1
    )


def test_inclusive_parent_usage_never_counted_as_another_charge():
    rows = [
        event(),
        event("end", "terminal", outcome="success", duration_ms=20, model_calls=1),
        event("u", "usage", usage=Usage(attempt="call", reported_cost="0.1")),
        event(
            "parent", "usage", usage=Usage(attempt="parent", reported_cost="0.1", inclusive=True)
        ),
    ]
    assert metrics(rows)["known_cost"] == "0.1"
    assert metrics(rows)["cost_per_success"] == "0.1"


def test_token_categories_are_deduped_and_missing_tokens_are_not_zero():
    rows = [
        event(),
        event("end", "terminal", outcome="success", duration_ms=20, model_calls=1),
        event(
            "usage",
            "usage",
            usage=Usage(
                attempt="call",
                input_tokens=100,
                cached_input_tokens=30,
                output_tokens=20,
                reported_cost="0.1",
            ),
        ),
    ]
    result = metrics(rows + rows)
    assert (
        result["input_tokens"] == 100
        and result["cached_input_tokens"] == 30
        and result["uncached_input_tokens"] == 70
        and result["output_tokens"] == 20
    )
    assert (
        metrics(
            [event(), event("end", "terminal", outcome="success", duration_ms=20, model_calls=1)]
        )["input_tokens"]
        is None
    )


def test_session_assignment_is_sticky_and_scoped():
    a = assignment("org:app:env", "session", "seed", 5)
    assert a == assignment("org:app:env", "session", "seed", 5)
    assert {assignment("o", "s" + str(i), "seed", 25) for i in range(100)} == {
        "stable",
        "candidate",
    }
    with pytest.raises(ValueError):
        assignment("o", "s", "seed", 101)


def samples(n=1000, prefix="s", **kw):
    return [
        {"session": prefix + str(i), "success": True, "duration_ms": 100, "cost": "0.1", **kw}
        for i in range(n)
    ]


def test_canary_never_promotes_no_data_small_n_unknown_cost_or_dependent_sessions():
    policy = Policy()
    assert analyze([], [], policy)["decision"] == "inconclusive"
    assert analyze(samples(10), samples(10), policy)["decision"] == "inconclusive"
    assert analyze(samples(), samples(cost=None), policy)["decision"] == "inconclusive"
    assert analyze(samples(), samples(session="same"), policy)["decision"] == "inconclusive"
    assert analyze(samples(), samples(), policy, coverage=0.98)["decision"] == "inconclusive"


def test_fixed_look_analysis_is_reproducible_and_detects_latency_regression():
    p = Policy()
    a = analyze(samples(), samples(prefix="c"), p)
    assert a["decision"] == "pass"
    assert a == analyze(samples(), samples(prefix="c"), p)
    assert analyze(samples(), samples(prefix="c", duration_ms=300), p)["decision"] == "fail"


def test_two_hundred_even_perfect_known_cost_sessions_cannot_manufacture_a_pass():
    # Minimum admission counts are not statistical power. No policy floor changes.
    result = analyze(samples(100), samples(100, prefix="c"), Policy())
    assert result["decision"] == "inconclusive"
    assert result["bounds"]["failure_difference"][1] > Policy().failure_margin


def test_default_zero_failure_bound_crosses_margin_at_403_per_arm_not_at_402():
    for count, expected in [(402, "inconclusive"), (403, "pass")]:
        result = analyze(samples(count), samples(count, prefix="c"), Policy())
        assert result["decision"] == expected


def test_loop_detection_distinguishes_polling_human_wait_and_missing_terminal():
    rows = [event()] + [
        event(str(i), "tool", tool_fingerprint="z", progress="same", sequence=i)
        for i in range(3, 6)
    ]
    assert "repeated_action" in {x["rule"] for x in detect(rows, Policy(), now=110)}
    polling = [r.model_copy(update={"polling": True}) for r in rows]
    assert not detect(polling, Policy(), now=110)
    assert detect([event()], Policy(), now=1000)[0]["rule"] == "missing_terminal"
    assert not detect([event(), event("wait", "heartbeat", waiting_until=1500)], Policy(), now=1000)
    assert (
        detect(
            [
                event(),
                event(
                    "cap",
                    "terminal",
                    outcome="failure",
                    model_calls=0,
                    stop_reason="iteration_exhausted",
                ),
            ],
            Policy(),
            now=110,
        )[0]["severity"]
        == "critical"
    )
