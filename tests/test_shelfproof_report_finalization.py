# ruff: noqa: F811
import json

from shelfproof_api.core import canonical
from shelfproof_api.workflow import Worker
from test_shelfproof_core import draft
from test_shelfproof_workflow import Provider, job, setup  # noqa: F401

from scripts.finalize_shelfproof_report import finalize


def test_shutdown_snapshot_preserves_original_report_and_final_task_state(setup, tmp_path):
    store, _, _ = setup
    task = job(setup, draft())
    Worker(store, Provider([TimeoutError()])).run_once()
    original = {
        "mode": "actual_installed_codex",
        "products": [{"task": task}],
        "states": {"running": 1},
        "terminal": 0,
        "fixture_not_actual_inference": True,
    }
    path = tmp_path / "report.json"
    path.write_text(canonical(original))
    result = finalize(tmp_path, store.root, "maker")
    assert result["states"] == {"manual_required": 1}
    assert result["terminal"] == 1 and result["unknown_attempts"] == 1
    assert json.loads(path.read_text()) == original
    assert (tmp_path / "report-final.json").exists()
    assert result["gates"]["production_accepted"] is False
