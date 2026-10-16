import asyncio

from contracts.patchdesk import CapabilityRequest
from patchdesk_api.adapters import make_result
from patchdesk_api.worker import Investigation
from test_patchdesk_worker import EmptySources, job


def test_registry_revocation_is_live_across_store_configuration(tmp_path):
    store, _, run = job(tmp_path, model=False)
    claimed = store.claim()
    investigation = Investigation(store, claimed, sources=EmptySources())
    store.set_setting("disabled_adapters", ["npm"])
    asyncio.run(
        investigation.batch(
            [
                (
                    CapabilityRequest(
                        capability="releases.lookup",
                        arguments={"package": "axios", "version": "1.7.9"},
                    ),
                    None,
                )
            ]
        )
    )
    result = next(iter(store.run("alice", run["id"])["results"].values()))
    assert result["outcome"] == "denied"


def test_sampling_limits_force_partial_even_with_validated_narrative(tmp_path):
    store, _, _ = job(tmp_path)
    investigation = Investigation(store, store.claim(), sources=EmptySources())
    investigation.ai_ok = True
    investigation.results = {"lookup": make_result("osv", "advisories.lookup", [], [])}
    investigation.notes.append("Required detail cap reached")
    result = investigation.report()
    assert result["status"] == "partial"


def test_result_adapter_identity_cannot_be_swapped(tmp_path):
    class Broken(EmptySources):
        def execute(self, adapter, request):
            value = super().execute(adapter, request)
            value["adapter"] = "untrusted-other"
            return value

    store, _, run = job(tmp_path)
    investigation = Investigation(store, store.claim(), sources=Broken())
    asyncio.run(
        investigation.batch(
            [
                (
                    CapabilityRequest(
                        capability="releases.lookup",
                        arguments={"package": "axios", "version": "1.7.9"},
                    ),
                    None,
                )
            ]
        )
    )
    assert next(iter(store.run("alice", run["id"])["results"].values()))["outcome"] == "unavailable"


def test_codex_environment_excludes_project_and_other_product_secrets(monkeypatch):
    from patchdesk_api.worker import codex_environment

    monkeypatch.setenv("PATCHDESK_GITHUB_PUBLISH_TOKEN", "must-not-inherit")
    monkeypatch.setenv("TENDERLENS_PASSWORD", "must-not-inherit")
    monkeypatch.setenv("UNRELATED_DATABASE_PASSWORD", "must-not-inherit")
    value = codex_environment()
    assert "PATH" in value
    assert not {
        "PATCHDESK_GITHUB_PUBLISH_TOKEN",
        "TENDERLENS_PASSWORD",
        "UNRELATED_DATABASE_PASSWORD",
    }.intersection(value)
