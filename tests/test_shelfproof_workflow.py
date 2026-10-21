"""Durable workflow tests with controlled providers, not product-quality evidence."""

import json

import pytest
from contracts.shelfproof import CorrectionPlan, Draft, PlanItem
from shelfproof_api.core import digest
from shelfproof_api.store import Conflict, Forbidden, Store
from shelfproof_api.workflow import Worker
from test_shelfproof_core import draft, evaluation, facts


class Provider:
    def __init__(self, answers):
        self.answers = iter(answers)
        self.prompts = []

    def generate(self, *, prompt, schema):
        self.prompts.append(json.loads(prompt))
        answer = next(self.answers)
        if isinstance(answer, Exception):
            raise answer
        self.last_receipt = {"audited": True, "input_tokens": 10, "output_tokens": 5}
        return answer.model_dump_json()


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path)
    store.create_user("maker", "long-password-123")
    store.create_user("checker", "different-password-456")
    workspace = store.create_workspace("maker", "Demo")
    store.add_member("maker", workspace, "checker", "reviewer")
    grant = store.authorize(
        "maker",
        workspace,
        basis="owned source",
        expires=store.now() + 3600,
        max_calls=32,
        egress=True,
    )
    return store, workspace, grant


def job(setup, original=None):
    store, workspace, grant = setup
    return store.create_task("maker", workspace, facts(), grant, "task-key", original=original)


def test_success_requires_separate_current_version_review_before_patch(setup):
    store, workspace, _ = setup
    task = job(setup)
    Worker(store, Provider([draft(), evaluation()])).run_once()
    result = store.task("maker", task)
    assert result["state"] == "review_ready"
    assert result["calls"] == 2
    assert store.export("maker", workspace)["patches"] == []
    with pytest.raises(Forbidden):
        store.review("maker", task, result["selected_hash"], "accept", "Looks correct")
    store.review("checker", task, result["selected_hash"], "accept", "Compared with facts")
    patch = store.export("maker", workspace)["patches"][0]
    assert patch["product_id"] == "000123"
    assert patch["structured_title"]["digital_source_type"] == "trained_algorithmic_media"


def test_independent_judge_receives_same_channel_constraints_without_producer_history(setup):
    store, _, _ = setup
    job(setup)
    provider = Provider([draft(), evaluation()])
    Worker(store, provider).run_once()
    producer, judge = provider.prompts
    assert judge["profile"] == producer["profile"]
    assert "Google Merchant" in judge["profile"]
    assert "ingredient list" in judge["profile"]
    assert "previous_score" not in judge
    assert "desired_score" not in judge
    assert "producer_reasoning" not in judge


def test_judge_span_parse_retry_receives_safe_actionable_feedback(setup):
    from contracts.shelfproof import Finding

    store, _, _ = setup
    task = job(setup)
    invalid = evaluation()
    invalid.findings = [
        Finding(
            family="clarity",
            severity="minor",
            field="title",
            explanation="Mismatched evidence",
            start=0,
            end=3,
            quote="PRIVATE REJECTED OUTPUT",
        )
    ]
    provider = Provider([draft(), invalid, evaluation()])
    Worker(store, provider).run_once()
    feedback = provider.prompts[2]["validation_feedback"]
    assert feedback["code"] == "evidence_span_mismatch"
    assert "PRIVATE REJECTED OUTPUT" not in json.dumps(provider.prompts[2])
    assert store.task("maker", task)["state"] == "review_ready"


def test_reflection_plan_is_finding_bound_and_improvements_are_logged(setup):
    store, _, _ = setup
    original = Draft(title="Example Oat flakes 700 g", description="Whole grain oats")
    task = job(setup, original)
    # Controller-owned check IDs use their list index, never model-generated aliases.
    plan = CorrectionPlan(
        items=[
            PlanItem(
                finding_id=f"check:{i}",
                operation="replace_from_fact",
                rationale="Use net package facts",
                refs=["net_quantity"],
            )
            for i in range(3)
        ]
    )
    provider = Provider([evaluation(2), plan, draft(), evaluation()])
    Worker(store, provider).run_once()
    result = store.task("maker", task)
    assert result["state"] == "review_ready"
    assert len(result["versions"]) == 2
    assert len(result["plans"]) == 1
    assert result["metrics"][0]["resolved"] == 3
    judge_context = provider.prompts[0]
    assert "previous_score" not in json.dumps(judge_context)
    assert "desired_score" not in json.dumps(provider.prompts[2])


def test_timeout_retains_original_and_records_validation_history(setup):
    store, _, _ = setup
    task = job(setup, draft())
    Worker(store, Provider([TimeoutError("secret raw diagnostic")])).run_once()
    result = store.task("maker", task)
    assert result["state"] == "manual_required"
    assert len(result["versions"]) == 1
    assert result["selected_hash"] == digest(draft())
    assert result["attempts"][0]["status"] == "unknown"
    assert "secret raw" not in json.dumps(result)
    assert any(e["event"] == "validation_failure" for e in store.audit("maker", task))
    assert store.liability_hold()


def test_idempotency_scoping_and_cancel_fence(setup):
    store, workspace, grant = setup
    task = job(setup)
    assert job(setup) == task
    with pytest.raises(Conflict):
        store.create_task("maker", workspace, facts(name="Rice"), grant, "task-key")
    store.create_user("outsider", "another-password-789")
    with pytest.raises(Forbidden):
        store.task("outsider", task)
    lease = store.claim()
    store.cancel("maker", task)
    with pytest.raises(Conflict):
        store.checkpoint(task, lease["lease"], "versions", {"draft": draft().model_dump()})


def test_schema_errors_retry_once_and_do_not_become_success(setup):
    store, _, _ = setup
    task = job(setup)
    provider = Provider([evaluation(), evaluation()])  # wrong contract for producer
    Worker(store, provider).run_once()
    result = store.task("maker", task)
    assert result["state"] == "manual_required"
    assert result["calls"] == 2
    assert len([e for e in store.audit("maker", task) if e["event"] == "validation_failure"]) == 2
    assert not store.liability_hold()  # Audited parse error has known usage.


def test_expired_source_and_stale_hash_cannot_be_reviewed_or_exported(setup):
    store, workspace, _ = setup
    task = job(setup)
    Worker(store, Provider([draft(), evaluation()])).run_once()
    with pytest.raises(Conflict):
        store.review("checker", task, "not-current", "accept", "test")
    store.invalidate("maker", workspace)
    assert store.export("maker", workspace)["patches"] == []


def test_grant_calls_are_shared_and_not_reset_per_task(setup):
    store, workspace, _ = setup
    grant = store.authorize(
        "maker",
        workspace,
        basis="small approved test",
        expires=store.now() + 60,
        max_calls=1,
        egress=True,
    )
    task = store.create_task("maker", workspace, facts(), grant, "bounded")
    Worker(store, Provider([draft()])).run_once()
    result = store.task("maker", task)
    assert result["calls"] == 1
    assert result["state"] == "manual_required"


def test_empty_plan_cannot_waive_a_blocking_finding(setup):
    store, _, _ = setup
    task = job(setup, Draft(title="Example Oat flakes 700 g", description="Whole grain oats"))
    Worker(
        store, Provider([evaluation(2), CorrectionPlan(items=[]), CorrectionPlan(items=[])])
    ).run_once()
    result = store.task("maker", task)
    assert result["state"] == "manual_required"
    assert len(result["versions"]) == 1


def test_audited_receipt_disagreement_is_global_hold(setup):
    store, _, _ = setup
    task = job(setup)
    lease = store.claim()["lease"]
    attempt = store.reserve(task, lease, "draft:0")
    store.settle(attempt, {"audited": True, "input_tokens": 10, "output_tokens": 5})
    assert not store.liability_hold()
    # Journal fsynced before database commit; simulate rollback after durable receipt.
    with store.db() as db:
        db.execute("UPDATE attempts SET status='reserved' WHERE id=?", (attempt,))
    assert store.liability_hold()


def test_later_timeout_keeps_last_adopted_improvement_not_only_original(setup):
    store, _, _ = setup
    original = Draft(title="Example Oat flakes 700 g", description="Whole grain oats")
    task = job(setup, original)
    plan = CorrectionPlan(
        items=[
            PlanItem(
                finding_id=f"check:{i}",
                operation="replace_from_fact",
                rationale="Use approved net size",
                refs=["net_quantity"],
            )
            for i in range(3)
        ]
    )
    Worker(
        store,
        Provider(
            [evaluation(2), plan, draft(), evaluation(3), CorrectionPlan(items=[]), TimeoutError()]
        ),
    ).run_once()
    result = store.task("maker", task)
    assert result["state"] == "manual_required"
    assert result["selected_hash"] == digest(draft())
    assert len(result["versions"]) == 2


def test_prompt_and_schema_are_bound_to_attempt_before_invocation(setup):
    store, _, _ = setup
    task = job(setup)
    Worker(store, Provider([draft(), evaluation()])).run_once()
    records, _ = store._journal_records()
    reservations = [r for r in records if r.get("status") == "reserved"]
    assert all(len(r["prompt_hash"]) == 64 and len(r["schema_hash"]) == 64 for r in reservations)
    assert store.task("maker", task)["snapshot"]["code_fingerprint"]


def test_duplicate_approved_product_identity_is_an_export_conflict(setup):
    store, workspace, grant = setup
    for key in ("run-one", "run-two"):
        task = store.create_task("maker", workspace, facts(), grant, key)
        Worker(store, Provider([draft(), evaluation()])).run_once()
        store.review(
            "checker",
            task,
            store.task("maker", task)["selected_hash"],
            "accept",
            "Compared with source",
        )
    exported = store.export("maker", workspace)
    assert exported["patches"] == []
    assert len(exported["unresolved"]) == 2
    assert all(
        row["reason"] == "duplicate_approved_product_identity" for row in exported["unresolved"]
    )


def test_scope_is_checked_before_hydrating_corrupt_artifacts(setup):
    store, _, _ = setup
    task = job(setup)
    store.create_user("outsider", "outsider-password-123")
    with store.db() as db:
        db.execute("UPDATE tasks SET fact_json='{}' WHERE id=?", (task,))
    with pytest.raises(Forbidden):
        store.task("outsider", task)


def test_identical_text_revisions_keep_distinct_evaluations_and_two_revision_limit(setup):
    store, _, _ = setup
    task = job(setup)
    provider = Provider(
        [
            draft(),
            evaluation(3),
            CorrectionPlan(items=[]),
            draft(),
            evaluation(3),
            CorrectionPlan(items=[]),
            draft(),
            evaluation(),
        ]
    )
    Worker(store, provider).run_once()
    result = store.task("maker", task)
    assert result["calls"] == 8
    assert [v["version_index"] for v in result["versions"]] == [0, 1, 2]
    assert result["selected_revision"] == 2
    assert result["state"] == "review_ready"
    store.review(
        "checker", task, result["selected_hash"], "accept", "Evaluated exact current revision"
    )


def test_unassessable_judge_stops_with_partial_draft_without_extra_generation(setup):
    from contracts.shelfproof import Rating

    store, _, _ = setup
    task = job(setup)
    uncertain = evaluation()
    uncertain.ratings["fidelity"] = Rating(
        value=None, rationale="Source support cannot be assessed"
    )
    Worker(store, Provider([draft(), uncertain])).run_once()
    result = store.task("maker", task)
    assert result["calls"] == 2 and result["state"] == "manual_required"
    assert result["plans"] == []


def test_missing_source_cannot_be_downgraded_to_minor_and_export_ready(setup):
    from contracts.shelfproof import Finding

    store, _, _ = setup
    task = job(setup)
    uncertain = evaluation()
    uncertain.findings = [
        Finding(
            family="semantic",
            severity="minor",
            field="description",
            explanation="Missing required source",
            missing_source=True,
        )
    ]
    plan = CorrectionPlan(
        items=[PlanItem(finding_id="judge:0", operation="request_source", rationale="Need source")]
    )
    Worker(store, Provider([draft(), uncertain, plan])).run_once()
    result = store.task("maker", task)
    assert result["state"] == "needs_data"


def test_store_admission_has_a_finite_global_queue_limit(setup):
    store, workspace, grant = setup
    task = job(setup)
    with store.db() as db:
        db.execute(
            "WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<999) "
            "INSERT INTO tasks(id,workspace,maker,epoch,fact_json,fact_hash,grant_id,state,created) "
            "SELECT 'capacity-'||x,t.workspace,t.maker,t.epoch,t.fact_json,t.fact_hash,t.grant_id,t.state,t.created "
            "FROM n CROSS JOIN tasks t WHERE t.id=?",
            (task,),
        )
    with pytest.raises(Conflict):
        store.create_task("maker", workspace, facts(), grant, "over-capacity")


def test_active_call_poll_does_not_write_a_lease_renewal_every_poll(setup):
    store, _, _ = setup
    task = job(setup)
    claimed = store.claim()
    before = store.internal_task(task)["lease_until"]
    assert store.active(task, claimed["lease"])
    assert store.internal_task(task)["lease_until"] == before
