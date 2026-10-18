import json
import subprocess
from pathlib import Path

import pytest
from catalogbridge_api.matching import binding
from catalogbridge_api.model_boundary import InstalledModels, MeteredCodex, ModelResult
from catalogbridge_api.worker import run_once
from contracts.catalogbridge import Calibration, Citation, Proposal, Usage
from test_catalogbridge_core import setup_batch


class FakeModels:
    def __init__(self, outcomes=None, verified=True):
        self.calls = []
        self.outcomes = list(outcomes or ["same_product"])
        self.verified = verified

    def generate_pair(self, supplier, gallery, model, timeout):
        self.calls.append(model)
        outcome = self.outcomes.pop(0)
        if outcome == "timeout":
            raise TimeoutError("provider timed out")
        proposal = Proposal(
            candidate_id=gallery[0].id,
            outcome=outcome,
            reason="fixture",
            evidence=[
                Citation(side="supplier", field="title", quote=supplier.title),
                Citation(side="candidate", field="title", quote=gallery[0].title),
            ],
        )
        return ModelResult(
            proposal.model_dump_json(),
            Usage(input_tokens=20, output_tokens=10),
            model if self.verified else None,
            True,
            10,
        )


def qualify(store, batch):
    from contracts.catalogbridge import BatchSpec

    spec = BatchSpec.model_validate(batch["spec"])
    cal = Calibration(
        id="test-cal",
        binding=binding(spec),
        threshold=0.99,
        precision_lower_bound=0.995,
        accepted_samples=1000,
        economy_score=0.995,
        strong_score=0.996,
        evidence_status="empirically_verified",  # explicit test fixture, never real calibration
    )
    with store.write() as db:
        db.execute("INSERT INTO calibrations VALUES(?,?)", (cal.id, cal.model_dump_json()))
        spec.calibration_id = cal.id
        db.execute("UPDATE batches SET spec=? WHERE id=?", (spec.model_dump_json(), batch["id"]))


def test_calibrated_exit_skips_stronger_call_and_records_cost(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    qualify(store, batch)
    store.start("w", batch["id"])
    provider = FakeModels()
    assert run_once(store, provider)
    assert provider.calls == [batch["spec"]["economy_model"]]
    task = store.tasks("w", batch["id"])[0]
    assert task["state"] == "recommended_match"
    assert task["result"]["exit_stage"] == "economy"
    assert store.analytics("w", batch["id"])["tokens"] == 30


def test_uncalibrated_decisive_proposal_stays_review_without_wasteful_escalation(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    store.start("w", batch["id"])
    provider = FakeModels(["same_product", "same_product"])
    run_once(store, provider)
    assert len(provider.calls) == 1
    assert store.tasks("w", batch["id"])[0]["state"] == "needs_review"


def test_insufficient_evidence_escalates_even_without_identity_attestation(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    store.start("w", batch["id"])
    provider = FakeModels(["insufficient_evidence", "same_product"], verified=False)
    run_once(store, provider)
    task = store.tasks("w", batch["id"])[0]
    assert len(provider.calls) == 2
    assert task["state"] == "needs_review"
    assert task["result"]["proposal"]["outcome"] == "same_product"
    assert len(task["result"]["proposal_history"]) == 2


def test_escalation_timeout_retains_partial_proposal_and_unknown_liability(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    store.start("w", batch["id"])
    run_once(store, FakeModels(["insufficient_evidence", "timeout"], verified=False))
    task = store.tasks("w", batch["id"])[0]
    assert task["state"] == "needs_review"
    assert task["result"]["degraded"] is True
    assert task["result"]["proposal"]["outcome"] == "insufficient_evidence"
    assert store.analytics("w", batch["id"])["unknown_attempts"] == 1


def test_oversized_prompt_refused_before_reservation_or_dispatch(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    # Feeds are frozen: construct a separate supported feed, never mutate it.
    from contracts.catalogbridge import BatchSpec, Product

    supplier = store.import_feed(
        "w", "supplier", [Product(id="large", title="Memory 8GB", description="界" * 19000)]
    )
    spec = BatchSpec.model_validate(batch["spec"])
    spec.supplier_id = supplier["id"]
    large = store.create_batch("w", spec)
    store.start("w", large["id"])
    run_once(store, InstalledModels(command="must-not-be-executed"))
    metrics = store.analytics("w", large["id"])
    assert metrics["attempts"] == metrics["unknown_attempts"] == 0
    assert store.tasks("w", large["id"])[0]["state"] == "failed"


def test_timeout_holds_usage_and_keeps_explicit_failure_history(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    store.start("w", batch["id"])
    run_once(store, FakeModels(["timeout"]))
    assert store.analytics("w", batch["id"])["unknown_attempts"] == 1
    assert store.tasks("w", batch["id"])[0]["state"] == "failed"
    assert any(e["kind"] == "provider_failure" for e in store.audit("w", batch["id"]))


def test_unverified_effective_identity_never_auto_accepts(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    qualify(store, batch)
    store.start("w", batch["id"])
    run_once(store, FakeModels(verified=False))
    assert store.tasks("w", batch["id"])[0]["state"] == "needs_review"


def test_owner_attested_constant_scores_are_not_empirical_confidence(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    qualify(store, batch)
    with store.write() as db:
        row = db.execute("SELECT body FROM calibrations WHERE id='test-cal'").fetchone()
        body = json.loads(row[0])
        body.pop("evidence_status", None)  # legacy/API uploads are unverified
        db.execute("UPDATE calibrations SET body=? WHERE id='test-cal'", (json.dumps(body),))
    store.start("w", batch["id"])
    run_once(store, FakeModels())
    task = store.tasks("w", batch["id"])[0]
    assert task["state"] == "needs_review"
    assert not task["result"]["calibrated"]


def test_denied_egress_uses_no_model(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    with store.write() as db:
        spec = batch["spec"] | {"egress": False}
        db.execute("UPDATE batches SET spec=? WHERE id=?", (json.dumps(spec), batch["id"]))
    store.start("w", batch["id"])
    provider = FakeModels()
    run_once(store, provider)
    assert not provider.calls


def test_metered_adapter_extracts_runtime_usage_not_model_text(monkeypatch):
    adapter = MeteredCodex("economy")

    def run(args, prompt):
        Path(args[args.index("--output-last-message") + 1]).write_text("{}")
        events = [
            {"type": "thread.started", "model": "economy"},
            {
                "type": "turn.completed",
                "usage": {"input_tokens": 20, "cached_input_tokens": 10, "output_tokens": 5},
            },
        ]
        return subprocess.CompletedProcess(args, 0, "\n".join(map(json.dumps, events)), "")

    monkeypatch.setattr(adapter, "_execute", run)
    result = adapter.generate_metered("task", {"type": "object"})
    assert result.usage.total == 25
    assert result.effective_model == "economy"


def test_metered_adapter_rejects_internal_tool_and_unknown_usage(monkeypatch):
    adapter = MeteredCodex("economy")

    def run(args, prompt):
        Path(args[args.index("--output-last-message") + 1]).write_text("{}")
        return subprocess.CompletedProcess(
            args,
            0,
            json.dumps({"type": "item.completed", "item": {"type": "command_execution"}}),
            "",
        )

    monkeypatch.setattr(adapter, "_execute", run)
    with pytest.raises(ValueError, match="tool"):
        adapter.generate_metered("task", {"type": "object"})
