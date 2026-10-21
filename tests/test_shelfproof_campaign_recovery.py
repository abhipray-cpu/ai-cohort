import importlib.util
import json
import sys
from pathlib import Path

import pytest
from shelfproof_api.store import Conflict
from shelfproof_api.workflow import Worker
from test_shelfproof_core import facts
from test_shelfproof_workflow import Provider, job, setup  # noqa: F401


def module():
    spec = importlib.util.spec_from_file_location(
        "recover_shelfproof", Path(__file__).parents[1] / "scripts/recover_shelfproof_campaign.py"
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_exact_queue_parking_is_audited_and_cannot_reset_calls(setup):  # noqa: F811
    store, _, _ = setup
    failed = job(setup)
    Worker(store, Provider([TimeoutError()])).run_once()
    pending = store.create_task("maker", setup[1], facts(), setup[2], "second-task")
    before = store.task("maker", failed)["attempts"]
    helper = module()
    with pytest.raises(Conflict):
        helper.park_queue(store, "maker", [pending], "wrong", "user-approved recovery")
    head = store.journal_head()
    helper.park_queue(store, "maker", [pending], head, "user-approved recovery")
    assert store.task("maker", pending)["state"] == "manual_required"
    assert store.task("maker", pending)["calls"] == 0
    assert store.task("maker", failed)["attempts"] == before
    assert store.journal_head() == head
    assert any(e["event"] == "recovery_queue_parked" for e in store.audit("maker", pending))
    store.accept_incident("maker", failed, head, "approved", "isolated", True, "accept")
    store.resume("maker", failed, None, "resume-failed")
    store.resume("maker", pending, None, "resume-pending")
    assert store.task("maker", failed)["calls"] == 1
    assert store.task("maker", pending)["state"] == "queued"


def test_queue_parking_requires_complete_exact_queue_and_runtime_isolation(setup):  # noqa: F811
    store, _, _ = setup
    first = job(setup)
    second = store.create_task("maker", setup[1], facts(), setup[2], "second-task")
    helper = module()
    with pytest.raises(Conflict):
        helper.park_queue(store, "maker", [first], store.journal_head(), "incomplete")
    from shelfproof_api.runtime import runtime_lock

    with runtime_lock(store.root), pytest.raises(Conflict):
        helper.park_queue(store, "maker", [first, second], store.journal_head(), "busy")
    assert store.task("maker", first)["state"] == "queued"


def test_diagnostics_never_return_raw_provider_text():
    helper = module()
    result = helper.classify_failure(b"SECRET invalid api key customer data", 1)
    assert result == {"exit_code": 1, "category": "authentication"}
    assert helper.classify_failure(b"unknown private text", 1)["category"] == "unclassified"


def test_diagnostic_adapter_preserves_real_process_exit_and_redacts_stderr(tmp_path):
    helper = module()
    output = tmp_path / "diagnostics.jsonl"
    provider = helper.DiagnosticProvider(output)
    result = provider._run(
        [
            sys.executable,
            "-c",
            "import sys; sys.stderr.write('SECRET invalid schema'); sys.exit(2)",
        ],
        "",
    )
    assert result.returncode == 2
    assert provider._exit_code == 2
    assert result.stderr == ""
    assert json.loads(output.read_text()) == {"exit_code": 2, "category": "schema"}
    assert "SECRET" not in output.read_text()


def test_report_correction_is_new_only_and_preserves_original_measurements(tmp_path):
    helper = module()
    original = {
        "actual_calls": 11,
        "unknown_attempts": 1,
        "recovery_elapsed_seconds": 141.5,
        "elapsed_seconds": 2.3,
        "grant_or_liability_changed": False,
    }
    path = tmp_path / "report-recovery.json"
    path.write_text(json.dumps(original))
    result = helper.review_report(tmp_path)
    assert result["actual_calls"] == 11 and result["unknown_attempts"] == 1
    assert result["grant_or_liability_changed"] is True
    assert result["grant_ceiling_changed"] is False
    assert result["elapsed_seconds"] == 141.5
    assert json.loads(path.read_text()) == original
    with pytest.raises(FileExistsError):
        helper.review_report(tmp_path)
