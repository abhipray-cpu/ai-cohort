import pytest
from clausegate_api.store import Store
from contracts.clausegate import DecisionInput, Finding, Playbook, Rule


def setup(tmp_path, *, action="require_exception", roles=None):
    store = Store(tmp_path / "data", ledger_dir=tmp_path / "authority")
    for user in ["owner", "reviewer", "outsider", "second"]:
        store.add_user(user, "long-test-password-123", admin=user == "owner")
    w = store.create_workspace("owner", "Fixture workspace")
    c = store.create_case("owner", w["id"], "NDA fixture")
    store.membership(
        "owner", w["id"], "reviewer", roles or ["reviewer", "approver", "final_reviewer"], [c["id"]]
    )
    store.set_context(
        "owner", c["id"], store.case("owner", c["id"])["revision"], "recipient", "Evaluation"
    )
    store.set_playbook(
        "owner",
        c["id"],
        store.case("owner", c["id"])["revision"],
        Playbook(
            name="Explicit fixture, not legal advice",
            rules=[Rule(id="h", hypothesis="All copies must be returned.", action=action)],
        ),
    )
    store.import_text(
        "owner", c["id"], store.case("owner", c["id"])["revision"], "Return all copies.", "nda.txt"
    )
    return store, store.case("owner", c["id"])


def findings(store, case, assessment="supported"):
    doc = store.document("owner", case["document_id"])
    return [
        Finding(
            check_id="h",
            label="Entailment",
            evidence_ids=[doc["spans"][0]["id"]],
            assessment=assessment,
            rationale="Fixture interpretation",
        )
    ]


def analyzed(tmp_path, **kwargs):
    store, c = setup(tmp_path, **kwargs)
    store.submit_findings(
        "reviewer", c["id"], c["revision"], findings(store, c), "Manual fixture review"
    )
    return store, store.case("owner", c["id"])


def decide(store, c, *, actor="reviewer", kind="approve_exception", key="decision"):
    r = next(r for r in c["requests"] if r["state"] == "pending")
    value = DecisionInput(
        expected_revision=r["revision"],
        binding=r["binding"],
        kind=kind,
        rationale="Reviewed the precise exception and source.",
        key=key,
    )
    return store.decide(actor, r["id"], value)


def test_scope_and_self_approval_are_not_role_names_from_client(tmp_path):
    s, c = analyzed(tmp_path)
    with pytest.raises(PermissionError):
        s.case("outsider", c["id"])
    with pytest.raises(PermissionError):
        decide(s, c, actor="owner")
    assert s.inbox("outsider") == []


def test_pause_survives_restart_and_idempotent_decision_resumes_once(tmp_path):
    s, c = analyzed(tmp_path)
    assert c["state"] == "waiting_human" and len(c["requests"]) == 1
    s = Store(s.root, ledger_dir=s.ledger_dir)
    first = decide(s, c)
    assert decide(s, c) == first
    current = s.case("owner", c["id"])
    assert current["state"] == "resume_queued"
    assert len(s.jobs("owner", c["id"])) == 1
    assert s.verify_audit("owner", c["id"])["valid"]


def test_revised_document_rejects_prior_form_and_old_decision(tmp_path):
    s, c = analyzed(tmp_path)
    s.import_text("owner", c["id"], c["revision"], "Retain all copies.", "nda.txt")
    with pytest.raises(ValueError):
        decide(s, c)
    assert s.case("owner", c["id"])["state"] == "stale"


def test_hard_block_cannot_be_waived(tmp_path):
    s, c = analyzed(tmp_path, action="block")
    with pytest.raises((PermissionError, ValueError)):
        decide(s, c)
    assert s.case("owner", c["id"])["state"] == "waiting_human"


def test_uncertainty_is_not_a_permitted_exception_approval(tmp_path):
    s, c = setup(tmp_path)
    s.submit_findings(
        "reviewer", c["id"], c["revision"], findings(s, c, "uncertain"), "Ambiguous fixture"
    )
    c = s.case("owner", c["id"])
    assert c["requests"][0]["kind"] == "interpretation"
    with pytest.raises(ValueError):
        decide(s, c)


def test_grant_revocation_fences_queued_continuation(tmp_path):
    s, c = analyzed(tmp_path)
    decide(s, c)
    s.membership("owner", c["workspace_id"], "reviewer", [], [c["id"]])
    with pytest.raises((PermissionError, ValueError)):
        s.resume("owner", c["id"])
    assert s.case("owner", c["id"])["state"] == "stale"


def test_quote_corruption_and_unknown_evidence_cannot_publish(tmp_path):
    s, c = setup(tmp_path)
    f = findings(s, c)[0].model_copy(update={"evidence_ids": ["foreign"]})
    with pytest.raises(ValueError):
        s.submit_findings("reviewer", c["id"], c["revision"], [f], "Fixture")
    with s.connect() as db:
        db.execute("UPDATE documents SET text='tampered' WHERE id=?", (c["document_id"],))
    with pytest.raises(ValueError, match="integrity"):
        s.document("owner", c["document_id"])


def test_current_case_state_is_bound_to_the_audit_head(tmp_path):
    import json

    s, c = analyzed(tmp_path)
    with s.connect() as db:
        value = json.loads(
            db.execute("SELECT payload FROM cases WHERE id=?", (c["id"],)).fetchone()[0]
        )
        value["state"] = "finalized"
        db.execute("UPDATE cases SET payload=? WHERE id=?", (json.dumps(value), c["id"]))
    with pytest.raises(ValueError, match="integrity"):
        s.verify_audit("owner", c["id"])
