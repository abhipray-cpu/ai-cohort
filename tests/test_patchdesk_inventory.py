"""Contract/graph/range tests first; small fixtures here are explicitly synthetic."""

import json

import pytest
from contracts.patchdesk import CapabilityRequest, InputUpload
from patchdesk_api.corpus import freeze, load_capture
from patchdesk_api.inventory import matches, osv_match, parse_inventory
from pydantic import ValidationError


def pair():
    manifest = {
        "name": "example",
        "dependencies": {"axios": "^1.7.0", "alias": "npm:lodash@^4.17.0"},
    }
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "": manifest,
            "node_modules/axios": {
                "version": "1.7.9",
                "resolved": "https://registry.npmjs.org/axios/-/axios-1.7.9.tgz",
                "dependencies": {"follow-redirects": "^1.15.0"},
            },
            "node_modules/alias": {
                "name": "lodash",
                "version": "4.17.20",
                "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.20.tgz",
            },
            "node_modules/follow-redirects": {"version": "1.15.6", "dev": True},
            "node_modules/axios/node_modules/follow-redirects": {"version": "1.15.5"},
        },
    }
    return manifest, lock


def test_strict_capability_and_upload():
    with pytest.raises(ValidationError):
        CapabilityRequest(capability="shell", arguments={})
    with pytest.raises(ValidationError):
        CapabilityRequest(capability="advisories.lookup", arguments={}, actor="admin")
    with pytest.raises(ValidationError):
        InputUpload(manifest={}, lockfile={}, private_token="not-allowed")


@pytest.mark.parametrize("format_version", [2, 3])
def test_exact_instances_aliases_and_nested_resolution(format_version):
    manifest, lock = pair()
    lock["lockfileVersion"] = format_version
    result = parse_inventory(manifest, lock)
    assert len(result["packages"]) == 4
    alias = next(p for p in result["packages"] if p["location"] == "node_modules/alias")
    assert alias["name"] == "lodash"
    edge = next(e for e in result["edges"] if e["from"] == "node_modules/axios")
    assert edge["to"] == "node_modules/axios/node_modules/follow-redirects"
    assert result["sha256"] and result["coverage"] == "complete_for_supported_input"


def test_private_links_paths_and_stale_manifest_are_gaps():
    manifest, lock = pair()
    lock = json.loads(json.dumps(lock))
    manifest["dependencies"]["axios"] = "^2.0.0"
    lock["packages"]["node_modules/private"] = {
        "version": "1.0.0",
        "resolved": "https://secret:token@internal.example/p.tgz",
    }
    lock["packages"]["node_modules/work"] = {"link": True, "resolved": "../../outside"}
    result = parse_inventory(manifest, lock)
    assert result["coverage"] == "partial"
    assert any(p["source_type"] == "private_or_unknown" for p in result["packages"])
    assert "secret:token" not in json.dumps(result)
    assert any("manifest" in gap for gap in result["gaps"])
    assert any("link" in gap for gap in result["gaps"])
    lock["packages"]["../../escape"] = {"version": "1.0.0"}
    with pytest.raises(ValueError, match="location"):
        parse_inventory(manifest, lock)


@pytest.mark.parametrize(
    "version,spec,expected",
    [
        ("1.8.1", ">=1.0.0 <1.8.2", True),
        ("1.8.2", ">=1.0.0 <1.8.2", False),
        ("0.29.0", "<0.30.0", True),
        ("1.8.2-beta.1", "^1.7.0", False),
        ("1.8.2", "bad range", None),
        ("git+https://example", "*", None),
    ],
)
def test_npm_version_semantics(version, spec, expected):
    assert matches(version, spec) is expected


def test_osv_ranges_and_withdrawal():
    advisory = {
        "id": "GHSA-example",
        "affected": [
            {
                "package": {"ecosystem": "npm", "name": "axios"},
                "ranges": [
                    {"type": "SEMVER", "events": [{"introduced": "1.0.0"}, {"fixed": "1.8.2"}]}
                ],
            }
        ],
    }
    assert osv_match(advisory, "axios", "1.8.1") is True
    assert osv_match(advisory, "axios", "1.8.2") is False
    advisory["withdrawn"] = "2026-01-01"
    assert osv_match(advisory, "axios", "1.8.1") is None


def test_capture_is_immutable_and_hash_verified(tmp_path):
    payload = {"real": "source payload would be captured by acquisition; this is a test"}
    freeze(tmp_path / "capture", payload)
    assert load_capture(tmp_path / "capture") == payload
    with pytest.raises(ValueError):
        freeze(tmp_path / "capture", payload)
    (tmp_path / "capture/payload.json").write_text("{}")
    with pytest.raises(ValueError, match="hash"):
        load_capture(tmp_path / "capture")


def test_real_npm_spaced_comparators_legacy_names_and_workspace_links():
    assert matches("5.9.3", "~5.9.0-0") is True
    assert matches("5.10.0", "~5.9.0-0") is False
    assert matches("5.9.0-rc.1", "~5.9.0-0") is True
    assert matches("5.9.1-rc.1", "~5.9.0-0") is False
    assert matches("2.1.2", ">= 2.1.2 < 3") is True
    manifest = {"dependencies": {"JSONStream": "^1.3.0", "@example/work": "^1.0.0"}}
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "": manifest,
            "node_modules/JSONStream": {
                "version": "1.3.5",
                "resolved": "https://registry.npmjs.org/JSONStream/-/JSONStream-1.3.5.tgz",
            },
            "node_modules/@example/work": {"link": True, "resolved": "workspaces/work"},
            "workspaces/work": {"name": "@example/work", "version": "1.0.0"},
        },
    }
    inventory = parse_inventory(manifest, lock)
    assert {p["name"] for p in inventory["packages"]} == {"JSONStream", "@example/work"}
    assert any(e["to"] == "workspaces/work" for e in inventory["edges"])
    assert not inventory["gaps"]
