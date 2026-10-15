"""Opt-in captured-public-data checks, separate from independently labelled quality."""

from pathlib import Path

import pytest
from propertybrief_api.corpus import FrozenSources, load_corpus
from propertybrief_api.sources import REQUIRED

CORPUS = Path("var/propertybrief-corpus/20261014-final")


@pytest.fixture(scope="module")
def actual():
    if not (CORPUS / "manifest.json").exists():
        pytest.skip("Acquire the actual corpus first; no fabricated substitute is used")
    return load_corpus(CORPUS)[1]


def test_actual_twelve_buildings_all_boroughs_and_hashes(actual):
    assert len(actual) == 12
    assert {case["identity"]["bbl"][0] for case in actual} == set("12345")
    assert (
        sum(len(result["raw"]) for case in actual for result in case["observations"].values())
        == 3346
    )


def test_actual_historical_parcel_and_secondary_identifier_conflicts(actual):
    case = next(case for case in actual if case["identity"]["building_id"] == "375411")
    sources = FrozenSources(case)
    dob = sources.fetch("dob_violations", case["identity"])
    assert next(row for row in dob["records"] if row["id"] == "285232")["status"] == "historical"
    assert (
        "parcel_identifier_differs"
        in next(row for row in dob["records"] if row["id"] == "285232")["flags"]
    )
    complaints = sources.fetch("hpd_complaints", case["identity"])
    assert complaints["completeness"] == "unknown"
    assert any("identity_conflict" in row["flags"] for row in complaints["records"])


@pytest.mark.parametrize("position", range(12))
def test_actual_source_replay_keeps_rows_and_completeness(actual, position):
    case = actual[position]
    sources = FrozenSources(case)
    for key in REQUIRED:
        result = sources.fetch(key, case["identity"])
        assert result["sha256"] == case["observations"][key]["sha256"]
        assert result["count"] == len(result["records"])
        assert result["completeness"] == case["observations"][key]["completeness"]
