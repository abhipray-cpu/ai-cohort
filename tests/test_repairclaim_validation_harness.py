"""Validation tooling contracts. These tests do not acquire real documents."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "validate_repairclaim", Path(__file__).parents[1] / "scripts/validate_repairclaim.py"
)
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


def test_acquisition_plan_is_bounded_unique_and_official_only():
    with pytest.raises(ValueError):
        harness.validate_plan([{"id": "one", "url": "https://example.com/private.pdf"}])
    with pytest.raises(ValueError):
        harness.validate_plan([{"id": "../bad", "url": "https://static.nhtsa.gov/a.pdf"}])
    with pytest.raises(ValueError):
        harness.validate_plan([{"id": "same", "url": "https://static.nhtsa.gov/a.pdf"}] * 2)
    with pytest.raises(ValueError):
        harness.validate_plan(
            [{"id": str(n), "url": f"https://static.nhtsa.gov/{n}.pdf"} for n in range(121)]
        )


def test_summary_never_calls_public_source_testing_consumer_or_provider_acceptance():
    report = harness.summary(
        [
            {"status": "parsed", "sha256": "a", "pages": 2},
            {"status": "parsed", "sha256": "a", "pages": 2},
            {"status": "failed"},
        ]
    )
    assert report["attempted"] == 3
    assert report["distinct_documents"] == 1
    assert report["failed"] == 1
    assert report["consumer_e2e"] is False
    assert report["actual_provider_calls"] == 0
