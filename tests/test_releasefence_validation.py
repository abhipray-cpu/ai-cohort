import json

import pytest
from releasefence_api.core import digest
from releasefence_api.validation import CallBudget, campaign_checks, load_corpus, source_checks


def corpus(tmp_path, rows):
    raw = b"".join((json.dumps(r) + "\n").encode() for r in rows)
    (tmp_path / "records.jsonl").write_bytes(raw)
    (tmp_path / "manifest.json").write_text(json.dumps({"records_hash": digest(raw)}))
    return tmp_path


def record():
    return {
        "facts": {
            "product_id": "123",
            "brand": "Brand",
            "name": "Food",
            "ingredients": "WATER",
            "net_quantity": "10",
            "net_unit": "g",
            "source_ref": "USDA:FDC:42@2026-04-30",
        },
        "raw": {
            "fdcId": 42,
            "gtinUpc": "123",
            "packageWeight": "10 g",
            "brandName": "Brand",
            "description": "Food",
            "ingredients": "WATER",
        },
    }


def test_real_source_inventory_requires_hash_unique_gtins_and_valid_facts(tmp_path):
    root = corpus(tmp_path, [record()])
    rows, receipt = load_corpus(root)
    assert len(rows) == receipt["unique_products"] == 1
    assert all(source_checks(rows[0]).values())
    (root / "records.jsonl").write_text("changed")
    with pytest.raises(ValueError, match="hash"):
        load_corpus(root)
    corpus(tmp_path, [record(), record()])
    with pytest.raises(ValueError, match="duplicate"):
        load_corpus(root)


def test_fact_checks_detect_quantity_substitution_without_using_serving_size():
    row = record()
    row["facts"]["net_quantity"] = "200"
    assert not source_checks(row)["package_quantity"]


def test_published_fluid_ounce_quantity_is_preserved():
    row = record()
    row["raw"]["packageWeight"] = "12 fl oz"
    row["facts"].update(net_quantity="12", net_unit="fl oz")
    assert all(source_checks(row).values())


def test_published_literal_identity_cannot_be_silently_relabelled():
    row = record()
    row["raw"].update(brandName="Brand", description="Food", ingredients="WATER")
    row["facts"]["brand"] = "Invented brand"
    assert not source_checks(row)["brand"]


def test_live_budget_is_persistent_bound_to_approval_and_unknown_attempts_count(tmp_path):
    path = tmp_path / "budget.sqlite3"
    budget = CallBudget(path, "user-approval-2026-10-22", limit=2)
    assert budget.reserve("one") == 1
    assert CallBudget(path, "user-approval-2026-10-22", limit=2).reserve("two") == 2
    with pytest.raises(ValueError, match="exhausted"):
        budget.reserve("three")
    with pytest.raises(ValueError, match="identity"):
        CallBudget(path, "another-approval", limit=2)
    with pytest.raises(ValueError, match="identity"):
        CallBudget(path, "user-approval-2026-10-22", limit=24)


def test_successful_model_calls_do_not_hide_failed_backend_qualification():
    report = {
        "mode": "live",
        "tasks": [{"source_fidelity_passed": True, "source_ref": str(i)} for i in range(6)],
        "calls_reserved": 6,
        "notifications_received": 3,
        "organizations": [
            {"id": str(i), "rollback_verified_at": 1, "phoenix": {"status": "degraded"}}
            for i in range(3)
        ],
    }
    checks = campaign_checks(report)
    assert checks["source_fidelity"] and not checks["phoenix_readback"]
    assert not all(checks.values())


def test_oss_campaign_cannot_pass_with_only_phoenix_readback():
    report = {
        "mode": "integration",
        "trace_profile": "mlflow-phoenix-v1",
        "tasks": [],
        "organizations": [],
    }
    checks = campaign_checks(report)
    assert "mlflow_readback" in checks and not checks["mlflow_readback"]
    assert checks["bounded_calls"]  # Integration mode must not spend any inference calls.


def test_fresh_240_call_approval_is_separate_and_cannot_expand_old_grant(tmp_path):
    old = CallBudget(tmp_path / "old.db", "original", limit=24)
    old.reserve("original-attempt")
    new = CallBudget(
        tmp_path / "new.db", "user-2026-10-22-releasefence-200-products-240-calls", limit=240
    )
    assert new.reserve("fresh-attempt") == 1 and old.count() == 1
    with pytest.raises(ValueError, match="identity"):
        CallBudget(tmp_path / "old.db", "original", limit=240)
    with pytest.raises(ValueError):
        CallBudget(tmp_path / "too-large.db", "unbounded", limit=241)


def test_large_cohort_cannot_pass_partial_provider_or_dead_letter_evidence():
    from releasefence_api.validation import cohort_checks

    report = {
        "tasks": [
            {
                "source_ref": str(i),
                "source_fidelity_passed": True,
                "started_at": 1,
                "ended_at": 2,
                "attempts": [{"passed": True}],
            }
            for i in range(200)
        ],
        "calls_reserved": 200,
        "calls_cap": 240,
        "products_cap": 200,
        "approval": "user-2026-10-22-releasefence-200-products-240-calls",
        "metrics": {"stable": {"accepted": 200, "model_calls": 200}},
        "unique_spans": 400,
        "verified_export_count": 800,
        "decision": {"decision": "inconclusive"},
        "expansion_rejected_status": 409,
        "control_evidence": {"rollout": {"state": "rollback_verified"}},
        "owned_api_worker_stopped": True,
        "owned_backends_stopped": True,
    }
    assert all(cohort_checks(report).values())
    report["tasks"][5]["source_fidelity_passed"] = False
    assert not cohort_checks(report)["source_fidelity"]
    report["verified_export_count"] = 799
    assert not cohort_checks(report)["complete_dual_export"]
    report["tasks"][6]["ended_at"] = 20000
    assert not cohort_checks(report)["clock_continuity"]
    assert not all(cohort_checks({"tasks": []}).values())


def test_absolute_runner_source_is_archived_under_evidence_not_written_to_itself(tmp_path):
    from releasefence_api.validation import archive_sources

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runner = workspace / "runner.py"
    runner.write_text("original")
    target = tmp_path / "evidence"
    archive_sources([runner.resolve()], target, workspace)
    assert (target / "runner.py").read_text() == "original"
    runner.write_text("new revision")
    assert (target / "runner.py").read_text() == "original"
    with pytest.raises(ValueError):
        archive_sources([tmp_path / "outside.py"], target, workspace)
