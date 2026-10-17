"""Release gating must not convert failed, blocked or stale evidence into acceptance."""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "accept_relaydesk", Path(__file__).resolve().parents[1] / "scripts" / "accept_relaydesk.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_every_gate_must_pass():
    assert MODULE.verdict([{"status": "passed"}, {"status": "passed"}]) == "accepted"
    assert MODULE.verdict([{"status": "passed"}, {"status": "blocked"}]) == "blocked"
    assert MODULE.verdict([{"status": "failed"}, {"status": "blocked"}]) == "rejected"


def test_empty_gate_set_is_not_acceptance():
    assert MODULE.verdict([]) == "blocked"


def test_skip_and_expected_failure_are_not_passing_acceptance():
    for status in ["skipped", "xfail", "unrun", "unknown"]:
        assert MODULE.verdict([{"status": status}]) != "accepted"
