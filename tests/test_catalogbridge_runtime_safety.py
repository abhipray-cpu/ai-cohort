import json
import subprocess

import pytest
from catalogbridge_api.model_boundary import MeteredCodex, ModelResult
from catalogbridge_api.store import Store
from catalogbridge_api.worker import run_once
from contracts.catalogbridge import BatchSpec
from test_catalogbridge_core import setup_batch


def test_failed_cli_preserves_safe_error_evidence_without_credentials(monkeypatch):
    adapter = MeteredCodex("economy")
    raw = json.dumps(
        {"type": "error", "message": "rate_limit_exceeded Bearer secret-token customer@example.com"}
    )
    monkeypatch.setattr(
        adapter, "_execute", lambda *_: subprocess.CompletedProcess([], 1, raw, "password=private")
    )
    result = adapter.generate_metered("task", {"type": "object"})
    assert result.diagnostics["category"] == "rate_limit"
    assert result.diagnostics["exit_code"] == 1
    assert result.diagnostics["stdout_sha256"]
    assert not any(
        secret in json.dumps(result.diagnostics)
        for secret in ["secret-token", "customer@", "private"]
    )


def test_unknown_usage_blocks_other_batches_after_restart_without_refund(tmp_path):
    store, first = setup_batch(tmp_path, 30000)
    task = store.tasks("w", first["id"])[0]
    attempt = store.reserve(first["id"], task["id"], "economy", 12000)
    store.settle(attempt, None)
    second = store.create_batch("w", BatchSpec.model_validate(first["spec"]))
    restarted = Store(tmp_path)
    other_task = restarted.tasks("w", second["id"])[0]
    with pytest.raises(ValueError, match="circuit"):
        restarted.reserve(second["id"], other_task["id"], "economy", 12000)
    assert restarted.analytics("w", first["id"])["reserved_tokens"] == 12000
    assert restarted.analytics("w", second["id"])["runtime_circuit"]["open"]


def test_nonzero_result_is_provider_failure_not_parse_failure(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    store.start("w", batch["id"])

    class Broken:
        def generate_pair(self, *_):
            return ModelResult("", None, None, False, 10, 1)

    run_once(store, Broken())
    kinds = [e["kind"] for e in store.audit("w", batch["id"])]
    assert "provider_failure" in kinds
    assert "validation_failure" not in kinds
    assert "provider_circuit_opened" in kinds


def test_campaign_stops_across_modes_after_first_missing_usage(tmp_path):
    from scripts.run_catalogbridge_real_models import campaign

    inputs = tmp_path / "inputs.jsonl"
    gold = tmp_path / "gold.jsonl"
    inputs.write_text(
        "".join(
            json.dumps(
                {
                    "id": str(i),
                    "supplier": {"id": "s", "title": "RAM"},
                    "master": {"id": "m", "title": "RAM"},
                }
            )
            + "\n"
            for i in range(10)
        )
    )
    gold.write_text("".join(json.dumps({"id": str(i), "label": 1}) + "\n" for i in range(10)))

    class Broken:
        calls = 0

        def generate_pair(self, *_):
            self.calls += 1
            return ModelResult("", None, None, True, 10, 0, {"category": "ok"})

    provider = Broken()
    campaign(inputs, gold, tmp_path / "campaign", 30, provider=provider)
    report = json.loads((tmp_path / "campaign/report.json").read_text())
    assert provider.calls <= 3  # already-authorized in-flight calls only
    assert report["runtime_stop"]["open"]
    assert report["actual_calls"] == provider.calls
    assert report["comparison_eligible"] is False
    assert report["runtime_stop"]["reason"] == "usage_unknown"


def test_known_usage_is_retained_even_when_runtime_exit_fails(monkeypatch):
    adapter = MeteredCodex("economy")
    event = {"type": "turn.completed", "usage": {"input_tokens": 20, "output_tokens": 5}}
    monkeypatch.setattr(
        adapter,
        "_execute",
        lambda *_: subprocess.CompletedProcess([], 1, json.dumps(event), "connection reset"),
    )
    result = adapter.generate_metered("task", {"type": "object"})
    assert result.usage.total == 25 and result.exit_code == 1
    assert result.diagnostics["category"] == "network"


def test_generated_text_cannot_impersonate_runtime_error_category(monkeypatch):
    from catalogbridge_api.runtime import diagnostics

    output = json.dumps(
        {"type": "item.completed", "item": {"type": "agent_message", "text": "rate_limit_exceeded"}}
    )
    assert diagnostics(output, exit_code=0)["category"] == "ok"


def test_model_failure_does_not_leak_circuit_state_to_another_workspace(tmp_path):
    from contracts.catalogbridge import Product

    store, first = setup_batch(tmp_path, 30000)
    task = store.tasks("w", first["id"])[0]
    store.settle(store.reserve(first["id"], task["id"], "economy", 12000), None)
    master = store.import_feed("other", "master", [Product(id="m", title="RAM")])
    supplier = store.import_feed("other", "supplier", [Product(id="s", title="RAM")])
    batch = store.create_batch(
        "other", BatchSpec(master_id=master["id"], supplier_id=supplier["id"])
    )
    assert not store.analytics("other", batch["id"])["runtime_circuit"]["open"]


def test_later_batch_stays_manual_without_spending_after_runtime_failure(tmp_path):
    store, first = setup_batch(tmp_path, 30000)
    store.start("w", first["id"])

    class Broken:
        calls = 0

        def generate_pair(self, *_):
            self.calls += 1
            return ModelResult("", None, None, False, 10, 1)

    provider = Broken()
    run_once(store, provider)
    second = store.create_batch("w", BatchSpec.model_validate(first["spec"]))
    store.start("w", second["id"])
    run_once(Store(tmp_path), provider)
    assert provider.calls == 1
    task = store.tasks("w", second["id"])[0]
    assert task["state"] == "needs_review"
    assert store.analytics("w", second["id"])["attempts"] == 0


def test_acknowledgement_never_clears_unknown_usage(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    task = store.tasks("w", batch["id"])[0]
    store.settle(store.reserve(batch["id"], task["id"], "economy", 12000), None)
    with pytest.raises(ValueError, match="unknown"):
        store.acknowledge_runtime("w", "owner", "Investigated provider availability")
    assert store.runtime_status("w")["open"]


def test_acknowledged_known_failure_is_audited_but_does_not_claim_recovery(tmp_path):
    store, batch = setup_batch(tmp_path, 30000)
    store.open_runtime_circuit("w", batch["id"], {"category": "rate_limit"})
    store.acknowledge_runtime("w", "owner", "Investigated provider availability")
    assert not store.runtime_status("w")["open"]
    assert any(e["kind"] == "runtime_retry_authorized" for e in store.audit("w", batch["id"]))


def test_compact_classifier_is_explicit_and_invalidates_legacy_calibration():
    from catalogbridge_api.matching import binding

    legacy = BatchSpec(master_id="m", supplier_id="s")
    compact = BatchSpec(master_id="m", supplier_id="s", instruction_profile="compact_classifier_v1")
    assert legacy.instruction_profile == "legacy"
    assert binding(legacy) != binding(compact)
    adapter = MeteredCodex("economy", instruction_profile="compact_classifier_v1")
    assert any(x.startswith("model_instructions_file=") for x in adapter.config_overrides)
    assert 'web_search="disabled"' in adapter.config_overrides
    assert "features.shell_tool=false" in adapter.config_overrides


def test_runtime_receipt_is_durable_atomic_with_settlement_and_sanitized(tmp_path):
    from contracts.catalogbridge import Usage

    store, batch = setup_batch(tmp_path, 30000)
    task = store.tasks("w", batch["id"])[0]
    attempt = store.reserve(batch["id"], task["id"], "economy", 12000)
    usage = Usage(input_tokens=20, output_tokens=5)
    evidence = {
        "category": "timeout",
        "runtime_thread_ids": ["0199a7bc-1234-7123-8123-123456789abc", "Bearer secret-token"],
        "raw_stdout": "private customer text",
        "stdout_sha256": "a" * 64,
    }
    store.settle(attempt, usage, runtime_evidence=evidence)
    store.settle(attempt, usage, runtime_evidence=evidence)
    reopened = Store(tmp_path)
    receipts = [e for e in reopened.audit("w", batch["id"]) if e["kind"] == "runtime_receipt"]
    assert len(receipts) == 1
    body = json.loads(receipts[0]["body"])
    assert body["attempt"] == attempt
    assert body["diagnostics"]["runtime_thread_ids"] == ["0199a7bc-1234-7123-8123-123456789abc"]
    assert "private" not in receipts[0]["body"] and "secret-token" not in receipts[0]["body"]
    assert reopened.analytics("w", batch["id"])["tokens"] == 25
    assert reopened.analytics("w", batch["id"])["journal_consistent"]


def test_worker_records_runtime_receipt_even_on_success(tmp_path):
    from test_catalogbridge_worker import FakeModels

    store, batch = setup_batch(tmp_path, 30000)
    store.start("w", batch["id"])
    run_once(store, FakeModels())
    assert any(e["kind"] == "runtime_receipt" for e in store.audit("w", batch["id"]))


def test_real_subprocess_timeout_keeps_reported_usage_and_holds_runtime(tmp_path, monkeypatch):
    import sys

    from agent_core.codex_local import LocalCodexProvider

    store, batch = setup_batch(tmp_path, 30000)
    store.start("w", batch["id"])
    adapter = MeteredCodex("economy", timeout=0.5)
    code = (
        "import json,time; print(json.dumps({'type':'turn.completed',"
        "'usage':{'input_tokens':20,'output_tokens':5}}),flush=True); time.sleep(30)"
    )
    monkeypatch.setattr(
        adapter,
        "_execute",
        lambda *_: LocalCodexProvider._run(adapter, [sys.executable, "-u", "-c", code], ""),
    )

    class Boundary:
        def generate_pair(self, *_):
            return adapter.generate_metered("task", {"type": "object"})

    run_once(store, Boundary())
    metrics = Store(tmp_path).analytics("w", batch["id"])
    assert metrics["tokens"] == 25 and metrics["unknown_attempts"] == 0
    assert metrics["runtime_circuit"]["open"]
    events = store.audit("w", batch["id"])
    assert any(e["kind"] == "provider_failure" and "timeout" in e["body"] for e in events)
    assert any(e["kind"] == "runtime_receipt" for e in events)
