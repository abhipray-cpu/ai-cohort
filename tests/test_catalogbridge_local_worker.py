import json

import pytest
from catalogbridge_api.local_router import PairRouter
from catalogbridge_api.worker import run_once
from contracts.catalogbridge import BatchSpec
from test_catalogbridge_core import setup_batch
from test_catalogbridge_local_router import profile
from test_catalogbridge_worker import FakeModels


def enable(store, batch, monkeypatch, tmp_path, body=None):
    body = body or profile()
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(body))
    monkeypatch.setenv("CATALOGBRIDGE_ROUTER_PROFILE", str(path))
    spec = BatchSpec.model_validate(
        batch["spec"]
        | {"routing_policy": "local_review_v1", "local_router_sha256": PairRouter(body).fingerprint}
    )
    with store.write() as db:
        db.execute("UPDATE batches SET spec=? WHERE id=?", (spec.model_dump_json(), batch["id"]))
    return spec


def test_local_exit_requires_no_reservation_even_with_one_token_budget(tmp_path, monkeypatch):
    store, batch = setup_batch(tmp_path, 1)
    enable(store, batch, monkeypatch, tmp_path)
    store.start("w", batch["id"])
    provider = FakeModels()
    run_once(store, provider)
    task = store.tasks("w", batch["id"])[0]
    assert provider.calls == [] and task["result"]["exit_stage"] == "local_pair"
    assert task["state"] == "needs_review" and task["result"]["calibrated"] is False
    assert store.analytics("w", batch["id"])["attempts"] == 0
    assert store.export("w", batch["id"])[1]["included"] == 0
    assert any(e["kind"] == "local_route_exit" for e in store.audit("w", batch["id"]))


def test_ambiguous_local_score_falls_back_to_budgeted_codex(tmp_path, monkeypatch):
    store, batch = setup_batch(tmp_path, 30000)
    body = profile()
    body["bias"] = 0.0
    enable(store, batch, monkeypatch, tmp_path, body)
    store.start("w", batch["id"])
    provider = FakeModels()
    run_once(store, provider)
    assert len(provider.calls) == 1
    assert store.analytics("w", batch["id"])["tokens"] == 30


def test_profile_drift_is_audited_and_cannot_authorize_exit(tmp_path, monkeypatch):
    store, batch = setup_batch(tmp_path, 30000)
    enable(store, batch, monkeypatch, tmp_path)
    body = profile()
    body["bias"] = -7.0
    (tmp_path / "profile.json").write_text(json.dumps(body))
    store.start("w", batch["id"])
    provider = FakeModels()
    run_once(store, provider)
    assert len(provider.calls) == 1
    assert any(e["kind"] == "local_route_unavailable" for e in store.audit("w", batch["id"]))


def test_local_exit_cannot_bypass_workspace_hold(tmp_path, monkeypatch):
    store, batch = setup_batch(tmp_path, 30000)
    enable(store, batch, monkeypatch, tmp_path)
    store.open_runtime_circuit("w", batch["id"], {"category": "network"})
    store.start("w", batch["id"])
    run_once(store, FakeModels())
    task = store.tasks("w", batch["id"])[0]
    assert "local_routing" not in task["result"]


def test_explicit_profile_hash_required_and_llm_default_is_unchanged():
    assert BatchSpec(master_id="a", supplier_id="b").routing_policy == "llm_only"
    with pytest.raises(ValueError):
        BatchSpec(master_id="a", supplier_id="b", routing_policy="local_review_v1")


def test_real_campaign_local_exits_are_counted_without_dispatch(tmp_path):
    from scripts.run_catalogbridge_real_models import campaign

    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile()))
    inputs = tmp_path / "inputs.jsonl"
    gold = tmp_path / "gold.jsonl"
    inputs.write_text(
        json.dumps(
            {
                "id": "1",
                "supplier": {"id": "a", "title": "RAM"},
                "master": {"id": "b", "title": "Mouse"},
            }
        )
        + "\n"
    )
    gold.write_text(json.dumps({"id": "1", "label": 0}) + "\n")
    provider = FakeModels()
    campaign(
        inputs,
        gold,
        tmp_path / "campaign",
        4,
        modes=["router"],
        provider=provider,
        local_profile=path,
    )
    report = json.loads((tmp_path / "campaign/report.json").read_text())
    assert report["actual_calls"] == 0 and provider.calls == []
    assert report["modes"]["router"]["agreement_full_denominator"]["correct"] == 1
