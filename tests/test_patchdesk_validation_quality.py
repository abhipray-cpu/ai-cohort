"""Evaluation integrity tests; fixtures here are labelled synthetic, not gold data."""

from pathlib import Path

import pytest
from agent_core.provider import ProviderTimeoutError
from contracts.patchdesk import CapabilityRequest, InputUpload, ProjectCreate, ProjectPolicy
from patchdesk_api.adapters import make_result
from patchdesk_api.corpus import FrozenSources, load_capture
from patchdesk_api.store import Store
from patchdesk_api.worker import run_once
from test_patchdesk_worker import Provider

from scripts.capture_patchdesk_cohort import split_repositories


@pytest.mark.parametrize("position", [0, 2, 5, 6])
@pytest.mark.parametrize("fault", ["late_model_timeout", "invalid_model_json", "wrong_tool_hash"])
def test_real_project_fault_retains_honest_partial_evidence(tmp_path, position, fault):
    path = Path("var/patchdesk-corpus/20261015-expanded")
    if not path.exists():
        pytest.skip("Requires captured actual public data")
    payload = load_capture(path)
    captured = payload["projects"][position]
    store = Store(tmp_path)
    store.add_user("audit", "audit-fixture-only-password", admin=True)
    project = store.create_project(
        "audit", ProjectCreate(name=captured["repository"], client="Real-data fault validation")
    )
    artifact = store.import_input(
        "audit",
        project["id"],
        InputUpload(manifest=captured["manifest"], lockfile=captured["lockfile"]),
    )
    names = sorted(
        {
            p["name"]
            for p in artifact["payload"]["inventory"]["packages"]
            if p["source_type"] != "private_or_unknown"
        }
    )
    store.update_policy(
        "audit",
        project["id"],
        ProjectPolicy(expected_revision=1, public_packages=names, model_egress=True),
    )
    run = store.enqueue("audit", project["id"], "Prepare a qualified plan", "fault", {})

    class FaultSources(FrozenSources):
        def execute(self, adapter, request):
            result = super().execute(adapter, request)
            if fault == "wrong_tool_hash" and request.capability == "releases.lookup":
                result["sha256"] = "0" * 64
            return result

    provider = Provider(
        [ProviderTimeoutError("Labelled fault after real-source checkpoints")]
        if fault == "late_model_timeout"
        else ["{", "{"]
    )
    run_once(store, sources=FaultSources(payload), provider=provider)
    completed = store.run("audit", run["id"])
    assert completed["status"] == "partial"
    assert completed["report"]["payload"]["gaps"]
    assert any(r.get("snapshot_id") for r in completed["results"].values())
    if fault == "late_model_timeout":
        assert any(e["stage"] == "provider_timeout" for e in completed["events"])
    if fault == "wrong_tool_hash":
        assert any(
            e["stage"] == "tool_response" and e["outcome"] == "failed" for e in completed["events"]
        )


def test_cohort_split_has_no_repository_leakage_and_is_stable():
    projects = [
        {"repository": f"org/repo-{i}", "commit": str(j)} for i in range(20) for j in range(2)
    ]
    splits = split_repositories(projects)
    assert splits == split_repositories(list(reversed(projects)))
    assert list(splits.values()).count("development") == 10
    assert list(splits.values()).count("calibration") == 4
    assert list(splits.values()).count("held_out") == 6


def test_frozen_replay_does_not_upgrade_truncated_source_coverage():
    row = {"package": "example", "version": "1.0.0", "advisory_ids": []}
    capture = {
        "lookup": make_result("osv", "advisories.lookup", [row], {}, completeness="truncated"),
        "snapshots": {},
    }
    result = FrozenSources(capture).execute(
        "osv",
        CapabilityRequest(
            capability="advisories.lookup",
            arguments={"packages": [{"name": "example", "version": "1.0.0"}]},
        ),
    )
    assert result["completeness"] == "truncated"
    assert result["outcome"] == "partial"
