from pathlib import Path

import pytest
from patchdesk_api.corpus import load_capture
from patchdesk_api.inventory import osv_match, parse_inventory
from patchdesk_api.reconcile import github_match

CORPUS = Path("var/patchdesk-corpus/20261015-expanded")


@pytest.fixture(scope="module")
def actual():
    if not CORPUS.exists():
        pytest.skip("Acquire actual corpus; no fabricated substitute")
    return load_capture(CORPUS)


def test_actual_five_repositories_ten_snapshots_hashes(actual):
    assert actual["kind"] == "actual-public-data"
    assert len(actual["projects"]) == 10
    assert len({p["repository"] for p in actual["projects"]}) == 5
    assert sum(p["inventory_entries"] for p in actual["projects"]) == 11780
    for project in actual["projects"]:
        assert len(project["commit"]) == 40
        assert (
            parse_inventory(project["manifest"], project["lockfile"])["sha256"]
            == project["inventory_hash"]
        )


def test_actual_advisory_boundary_and_release_existence(actual):
    entries = list(actual["snapshots"].values())
    osv = next(
        e["result"]["records"][0]
        for e in entries
        if e["result"]["adapter"] == "osv"
        and e["request"]["arguments"]["id"] == "GHSA-jr5f-v2jv-69x6"
    )
    assert osv_match(osv, "axios", "1.8.1") is True
    assert osv_match(osv, "axios", "1.8.2") is False
    releases = [e["result"]["records"][0] for e in entries if e["result"]["adapter"] == "npm"]
    assert {r["version"] for r in releases} == {"1.7.9", "1.8.1", "1.8.2"}
    assert all(r["dist"].get("integrity") for r in releases)


def test_actual_publisher_and_reviewed_ranges_disagree(actual):
    entries = list(actual["snapshots"].values())
    publisher = next(
        e["result"]["records"][0] for e in entries if e["result"]["adapter"] == "github_publisher"
    )
    reviewed = next(
        e["result"]["records"][0] for e in entries if e["result"]["adapter"] == "github_advisory"
    )
    # Version-boundary probe, not a claim that this dependency exists in a captured project.
    assert github_match(publisher, "axios", "1.8.1") is False
    assert github_match(reviewed, "axios", "1.8.1") is True


@pytest.mark.parametrize("position", range(10))
def test_actual_inventory_replay(position, actual):
    project = actual["projects"][position]
    value = parse_inventory(project["manifest"], project["lockfile"])
    assert value["entry_count"] == project["inventory_entries"]
    assert len({p["id"] for p in value["packages"]}) == len(value["packages"])
    assert value["parser_version"] == "patchdesk-inventory-3"
    assert all(isinstance(gap, str) for gap in value["gaps"])
