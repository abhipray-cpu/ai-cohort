# ruff: noqa: F811 -- imported pytest fixture
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from casecouncil_api.evaluation import audit_corpus, campaign
from casecouncil_api.store import Store
from test_casecouncil_evaluation import corpus  # noqa: F401
from test_casecouncil_protocol import ControlledProvider


def module():
    spec = importlib.util.spec_from_file_location(
        "casecouncil_continuation",
        Path(__file__).resolve().parents[1] / "scripts/continue_casecouncil_replay.py",
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_continuation_retains_original_calls_and_does_not_reexecute_completed_cases(
    corpus, tmp_path, monkeypatch
):
    path = corpus / "manifest.json"
    manifest = json.loads(path.read_text())
    other = json.loads(json.dumps(manifest["cases"][0]))
    other.update(id="opaque_002", group="independent_002")
    other["context"]["facts"] += (
        " This separately authored dispute concerns different correspondence."
    )
    manifest["cases"].append(other)
    manifest["egress_approval"] = {"ids": [c["id"] for c in manifest["cases"]], "max_calls": 44}
    path.write_text(json.dumps(manifest))
    run = tmp_path / "original"
    report = campaign(
        corpus,
        run,
        ControlledProvider(),
        "debate",
        1,
        44,
        "Explicit owned-fixture authority for continuation regression",
    )
    store = Store(run / "service")
    for result in report["results"]:
        result["case"] = store.job("evaluator", result["job"])["case_id"]
    (run / "report.json").write_text(json.dumps(report))
    selection = {
        "ids": [report["results"][0]["id"]]
        + [c["id"] for c in manifest["cases"] if c["id"] != report["results"][0]["id"]],
        "max_calls": 44,
        "manifest_hash": audit_corpus(corpus)["manifest_hash"],
    }
    (run / "selection.json").write_text(json.dumps(selection))
    original = (run / "report.json").read_bytes()
    provider = ControlledProvider()
    script = module()
    monkeypatch.setattr(script, "provider_from_env", lambda: provider)
    args = SimpleNamespace(live=True, run=run, corpus=corpus, output=tmp_path / "continued")
    checked = script.continue_replay(args)
    assert checked["cumulative_calls"] == 16 and checked["full_protocols"] == 2
    assert len(provider.prompts) == 8
    assert "EVALUATOR_SECRET_OUTCOME_1847" not in json.dumps(provider.prompts)
    assert (run / "report.json").read_bytes() == original
    args.output = tmp_path / "continued-again"
    again = script.continue_replay(args)
    assert again["cumulative_calls"] == 16 and len(provider.prompts) == 8


def test_continuation_rejects_scope_and_budget_changes():
    script = module()
    selection = {"ids": ["one"], "max_calls": 22, "manifest_hash": "known"}
    manifest = {
        "permission": {"egress": True},
        "egress_approval": {"ids": ["one"], "max_calls": 22},
        "cases": [{"id": "one", "split": "development"}],
    }
    script.validate_selection(selection, manifest, {"manifest_hash": "known"})
    for change in ({"ids": ["other"]}, {"max_calls": 132}, {"manifest_hash": "changed"}):
        with pytest.raises(ValueError):
            script.validate_selection({**selection, **change}, manifest, {"manifest_hash": "known"})
