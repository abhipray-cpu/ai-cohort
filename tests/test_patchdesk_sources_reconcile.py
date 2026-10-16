import pytest
from contracts.patchdesk import CapabilityRequest, Narrative
from patchdesk_api.adapters import Sources, Transport, make_result
from patchdesk_api.inventory import parse_inventory
from patchdesk_api.reconcile import reconcile, validate_narrative
from test_patchdesk_inventory import pair


def test_transport_rejects_non_allowlisted_or_credential_urls():
    transport = Transport()
    for url in (
        "http://api.osv.dev/a",
        "https://127.0.0.1/a",
        "https://api.osv.dev.evil/a",
        "https://user:secret@api.osv.dev/a",
    ):
        with pytest.raises(ValueError):
            transport.request(url)


def test_osv_batch_mapping_pagination_and_no_match():
    calls = []

    def request(url, data=None, **_):
        calls.append(data)
        query = data["queries"][0]
        return {
            "results": [
                {
                    "vulns": [{"id": "GHSA-1111-2222-3333", "modified": "2026"}],
                    "next_page_token": "more",
                }
                if not query.get("page_token")
                else {}
            ]
        }

    source = Sources(request=request)
    req = CapabilityRequest(
        capability="advisories.lookup",
        arguments={"packages": [{"name": "axios", "version": "1.7.9"}]},
    )
    value = source.execute("osv", req)
    assert value["records"][0]["package"] == "axios"
    assert value["records"][0]["advisory_ids"] == ["GHSA-1111-2222-3333"]
    assert value["completeness"] == "complete_for_query" and len(calls) == 2
    empty = Sources(request=lambda *_args, **_kwargs: {"results": [{}]}).execute("osv", req)
    assert empty["outcome"] == "no_matches"


def test_wrong_batch_shape_and_failed_source_are_not_no_match():
    req = CapabilityRequest(
        capability="advisories.lookup",
        arguments={"packages": [{"name": "axios", "version": "1.7.9"}]},
    )
    assert (
        Sources(request=lambda *_args, **_kwargs: {"results": []}).execute("osv", req)["outcome"]
        == "unavailable"
    )

    def fail(*_args, **_kwargs):
        raise TimeoutError("injected timeout")

    assert Sources(request=fail).execute("osv", req)["completeness"] == "unknown"


def test_real_shaped_range_conflict_and_candidate_not_certified():
    # Source-shaped synthetic unit fixture; actual captures are tested separately.
    inventory = parse_inventory(*pair())
    osv = {
        "id": "GHSA-jr5f-v2jv-69x6",
        "aliases": ["CVE-2025-27152"],
        "affected": [
            {
                "package": {"name": "axios", "ecosystem": "npm"},
                "ranges": [
                    {"type": "SEMVER", "events": [{"introduced": "1.0.0"}, {"fixed": "1.8.2"}]}
                ],
            }
        ],
    }
    publisher = {
        "ghsa_id": osv["id"],
        "severity": "moderate",
        "vulnerabilities": [
            {
                "package": {"name": "axios", "ecosystem": "npm"},
                "vulnerable_version_range": "<=1.7.9",
                "first_patched_version": {"identifier": "1.8.2"},
            }
        ],
    }
    results = {
        "osv": {**make_result("osv", "advisories.detail", [osv], osv), "snapshot_id": "s1"},
        "publisher": {
            **make_result("github_publisher", "advisories.detail", [publisher], publisher),
            "snapshot_id": "s2",
        },
        "release": {
            **make_result(
                "npm",
                "releases.lookup",
                [{"name": "axios", "version": "1.8.2", "engines": {"node": ">=20"}}],
                {},
            ),
            "snapshot_id": "s3",
        },
    }
    # This exact installed version distinguishes the two source ranges.
    for package in inventory["packages"]:
        if package["name"] == "axios":
            package["version"] = "1.8.1"
    value = reconcile(inventory, results, {"node_version": "18.20.0"})
    assert value["findings"] and value["conflicts"]
    assert value["findings"][0]["status"] == "needs_investigation"
    assert value["candidates"][0]["verification"] == "pending"
    assert value["candidates"][0]["engine_check"] is False
    assert value == reconcile(
        inventory, dict(reversed(list(results.items()))), {"node_version": "18.20.0"}
    )

    lookup = [{"package": "axios", "version": "1.8.2", "advisory_ids": ["GHSA-9999-8888-7777"]}]
    results["target_lookup"] = {
        **make_result("osv", "advisories.lookup", lookup, lookup),
        "snapshot_id": "target-query",
    }
    checked = reconcile(inventory, results, {"node_version": "18.20.0"})
    assert checked["candidates"][0]["other_advisories_check"] == "additional_advisories_reported"
    assert checked["candidates"][0]["additional_advisory_ids"] == ["GHSA-9999-8888-7777"]


def test_narrative_rejects_unknown_ids_and_unsafe_guarantees():
    with pytest.raises(ValueError):
        validate_narrative(Narrative(summary="Guaranteed secure"), [])
    with pytest.raises(ValueError):
        validate_narrative(
            Narrative(
                summary="Recorded evidence",
                tasks=[
                    {
                        "title": "Test",
                        "finding_ids": ["invented"],
                        "priority": "high",
                        "reason": "test",
                        "verification": "Verify",
                    }
                ],
            ),
            [],
        )


def test_shared_aliases_deduplicate_within_npm_package_scope():
    inventory = parse_inventory(*pair())
    records = []
    for aid in ("GHSA-1111-2222-3333", "GHSA-4444-5555-6666"):
        records.append(
            {
                "id": aid,
                "aliases": ["CVE-2025-99999"],
                "affected": [
                    {
                        "package": {"name": "axios", "ecosystem": "npm"},
                        "ranges": [
                            {"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": "1.8.2"}]}
                        ],
                    }
                ],
            }
        )
    result = {
        **make_result("osv", "advisories.detail", records, records),
        "snapshot_id": "actual-test-snapshot",
    }
    value = reconcile(inventory, {"detail": result}, {})
    assert len(value["findings"]) == 1
    assert len(value["findings"][0]["evidence"]) == 2
    assert "GHSA-4444-5555-6666" in value["findings"][0]["aliases"]
