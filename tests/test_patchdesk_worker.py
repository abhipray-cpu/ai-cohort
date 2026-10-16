"""Full orchestration tests with explicitly scripted model/source fixtures."""

import json

from agent_core.provider import ProviderTimeoutError, StructuredGeneration
from contracts.patchdesk import InputUpload, ProjectPolicy
from patchdesk_api.adapters import make_result
from patchdesk_api.worker import run_once
from test_patchdesk_inventory import pair
from test_patchdesk_store import setup_store


class Provider:
    def __init__(self, values):
        self.values = iter(values)

    def generate(self, **_):
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return StructuredGeneration(
            text=json.dumps(value) if not isinstance(value, str) else value,
            exit_code=0,
            elapsed_ms=1,
        )


class EmptySources:
    def execute(self, adapter, request):
        if request.capability == "advisories.lookup":
            records = [
                {"package": p["name"], "version": p["version"], "advisory_ids": []}
                for p in request.arguments["packages"]
            ]
        elif request.capability == "releases.lookup":
            records = [
                {"name": request.arguments["package"], "version": request.arguments["version"]}
            ]
        else:
            records = []
        return make_result(adapter, request.capability, records, records)


def job(tmp_path, model=True):
    store, project = setup_store(tmp_path)
    manifest, lock = pair()
    store.import_input("alice", project["id"], InputUpload(manifest=manifest, lockfile=lock))
    store.update_policy(
        "alice",
        project["id"],
        ProjectPolicy(
            expected_revision=1,
            public_packages=["axios", "lodash", "follow-redirects"],
            model_egress=model,
        ),
    )
    run = store.enqueue("alice", project["id"], "Prepare maintenance", "job", {})
    return store, project, run


def test_full_parallel_run_and_followup_pins_evidence(tmp_path):
    store, project, run = job(tmp_path)
    provider = Provider(
        [
            {"requests": [], "summary": "Required checks attempted."},
            {
                "summary": "Review of the listed source queries completed; no application security guarantee.",
                "tasks": [],
                "limitations": ["No execution or reachability assessment."],
            },
        ]
    )
    assert run_once(store, sources=EmptySources(), provider=provider)
    value = store.run("alice", run["id"])
    assert value["status"] == "completed"
    assert value["model_calls"] == 2
    assert any(e["stage"] == "route" for e in value["events"])
    assert value["report"]["payload"]["source_manifest"]
    follow = store.enqueue("alice", project["id"], "Clarify verification", "follow", {})
    assert follow["results"] == value["results"]


def test_later_timeout_retains_successful_parallel_checkpoints(tmp_path):
    store, _, run = job(tmp_path)
    run_once(
        store,
        sources=EmptySources(),
        provider=Provider([ProviderTimeoutError("injected later timeout")]),
    )
    value = store.run("alice", run["id"])
    assert value["status"] == "partial"
    assert len(value["results"]) >= 2
    assert value["report"] and any(e["stage"] == "provider_timeout" for e in value["events"])


def test_model_denied_egress_never_invokes_provider(tmp_path):
    store, _, run = job(tmp_path, model=False)
    run_once(store, sources=EmptySources(), provider=Provider([AssertionError("must not invoke")]))
    value = store.run("alice", run["id"])
    assert value["model_calls"] == 0 and value["status"] == "partial"
    assert "model" in value["stop_reason"].lower()


def test_invalid_model_scope_is_rejected_and_repaired(tmp_path):
    store, _, run = job(tmp_path)
    provider = Provider(
        [
            {
                "requests": [
                    {
                        "capability": "advisories.detail",
                        "arguments": {"id": "GHSA-1111-2222-3333", "package": "private"},
                    }
                ],
                "summary": "untrusted attempt",
            },
            {"requests": [], "summary": "No allowed extra task"},
            {"summary": "Recorded evidence only", "tasks": [], "limitations": []},
        ]
    )
    run_once(store, sources=EmptySources(), provider=provider)
    value = store.run("alice", run["id"])
    assert any(e["stage"] == "validation" for e in value["events"])
    assert value["model_calls"] == 3
