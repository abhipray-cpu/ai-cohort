import json

import pytest
from contracts.clausegate import DecisionInput, Playbook, Rule
from test_clausegate_core import analyzed, decide, findings, setup


@pytest.mark.parametrize("surface", ["case", "audit", "verify", "backup"])
def test_case_read_cannot_mix_audit_and_state_across_a_committed_write(
    tmp_path, monkeypatch, surface
):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from clausegate_api import authority

    s, c = setup(tmp_path)
    reached, committed = threading.Event(), threading.Event()
    original = authority.head
    fired = False

    def head(*args):
        nonlocal fired
        value = original(*args)
        if threading.current_thread() is threading.main_thread() and not fired:
            fired = True
            reached.set()
            committed.wait(0.15)
        return value

    def write():
        assert reached.wait(3)
        result = s.set_context("owner", c["id"], c["revision"], "mutual", "Concurrent purpose")
        s.anchor("owner", c["id"])
        committed.set()
        return result

    monkeypatch.setattr(authority, "head", head)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(write)
        if surface == "case":
            read = s.case("owner", c["id"])
        elif surface == "audit":
            read = s.audit("owner", c["id"])
        elif surface == "verify":
            read = s.verify_audit("owner", c["id"])
        else:
            from clausegate_api.backup import backup

            read = backup(s, tmp_path / "snapshot")
        updated = future.result(timeout=5)
    if surface == "case":
        assert read["revision"] == c["revision"]
    assert updated["revision"] > c["revision"]
    assert s.verify_audit("owner", c["id"])["valid"]


def test_citations_can_narrow_only_to_unique_exact_source_substrings(tmp_path):
    from contracts.clausegate import Finding

    s, c = setup(tmp_path)
    c = s.import_text(
        "owner",
        c["id"],
        c["revision"],
        "Preamble. Return all copies. Unrelated text.",
        "narrow.txt",
    )
    doc = s.document("owner", c["document_id"])
    value = {
        "check_id": "h",
        "label": "Entailment",
        "assessment": "supported",
        "evidence_ids": [doc["spans"][0]["id"]],
        "evidence_quotes": [{"span_id": doc["spans"][0]["id"], "quote": "Return all copies."}],
        "rationale": "Exact clause",
    }
    c = s.submit_findings(
        "reviewer",
        c["id"],
        c["revision"],
        [Finding.model_validate(value)],
        "Explicit source review",
    )
    e = c["findings"][0]["evidence"][0]
    assert e["quote"] == "Return all copies."
    assert doc["text"][e["start"] : e["end"]] == e["quote"]
    value["evidence_quotes"][0]["quote"] = "Invented clause."
    with pytest.raises(ValueError):
        s.submit_findings(
            "reviewer", c["id"], c["revision"], [Finding.model_validate(value)], "Invalid quote"
        )


def test_independent_erasure_receipt_blocks_content_before_local_reconcile(tmp_path):
    from clausegate_api import authority

    s, c = setup(tmp_path)
    authority.erase(s.ledger_dir, s.store_id, s.binding, c["id"])
    with pytest.raises(PermissionError):
        s.case("owner", c["id"])
    with pytest.raises(PermissionError):
        s.original("owner", c["document_id"])
    s.reconcile_erasures()
    assert s.case("owner", c["id"])["state"] == "erased"


def test_expired_manual_reviewer_cannot_leave_a_valid_packet(tmp_path):
    s, c = setup(tmp_path, action="require_review")
    s.membership("owner", c["workspace_id"], "second", ["final_reviewer"], [c["id"]])
    c = s.case("owner", c["id"])
    c = s.submit_findings("reviewer", c["id"], c["revision"], findings(s, c), "Reviewed fixture")
    assert c["state"] == "review_ready"
    c = s.finalize(
        "second", c["id"], c["revision"], c["packet"]["sha256"], "Independent internal review", True
    )
    with s.connect() as db:
        db.execute("UPDATE members SET expires='2000-01-01' WHERE actor='reviewer'")
    with pytest.raises((PermissionError, ValueError)):
        s.export("owner", c["id"])


def test_blank_rationale_is_not_human_input(tmp_path):
    s, c = analyzed(tmp_path)
    r = c["requests"][0]
    v = DecisionInput(
        expected_revision=1,
        binding=r["binding"],
        kind="approve_exception",
        rationale="   ",
        key="blank",
    )
    with pytest.raises(ValueError):
        s.decide("reviewer", r["id"], v)


def test_confirmation_cannot_secretly_change_interpretation(tmp_path):
    s, c = setup(tmp_path)
    c = s.submit_findings(
        "reviewer", c["id"], c["revision"], findings(s, c, "uncertain"), "Uncertain"
    )
    r = c["requests"][0]
    v = DecisionInput(
        expected_revision=r["revision"],
        binding=r["binding"],
        kind="confirm_interpretation",
        label="Contradiction",
        rationale="Actually a different interpretation",
        key="changed",
    )
    with pytest.raises(ValueError):
        s.decide("reviewer", r["id"], v)


def test_failed_audit_append_rolls_back_decision(tmp_path, monkeypatch):
    s, c = analyzed(tmp_path)
    original = s._event

    def fail(db, c, actor, kind, detail):
        if kind == "human_decision_recorded":
            raise OSError("Injected disk failure")
        return original(db, c, actor, kind, detail)

    monkeypatch.setattr(s, "_event", fail)
    with pytest.raises(OSError):
        decide(s, c)
    assert s.case("owner", c["id"])["decisions"] == []
    assert s.case("owner", c["id"])["requests"][0]["state"] == "pending"


def test_two_concurrent_forms_do_not_lose_a_decision(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    s, c = analyzed(tmp_path)

    def perform(key):
        try:
            return decide(s, c, key=key)["id"]
        except ValueError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(perform, ["first", "second"]))
    assert outcomes.count("conflict") == 1
    assert len(s.case("owner", c["id"])["decisions"]) == 1


def test_incomplete_document_cannot_be_approved_as_notmentioned(tmp_path):
    from clausegate_api.intake import text_document
    from contracts.clausegate import Finding

    s, c = setup(tmp_path)
    c = s.import_document(
        "owner",
        c["id"],
        c["revision"],
        text_document("Some text.", "partial.txt", complete=False, gaps=["Missing page"]),
    )
    with pytest.raises(ValueError):
        s.submit_findings(
            "reviewer",
            c["id"],
            c["revision"],
            [
                Finding(
                    check_id="h",
                    label="NotMentioned",
                    assessment="supported",
                    rationale="Unjustified absence",
                )
            ],
            "Cannot know",
        )


def test_wrong_case_ids_and_unapproved_playbook_are_rejected(tmp_path):
    s, c = setup(tmp_path)
    with pytest.raises(ValueError):
        s.membership("owner", c["workspace_id"], "second", ["reviewer"], ["foreign-case"])
    c = s.set_playbook(
        "owner",
        c["id"],
        c["revision"],
        Playbook(name="Draft", rules=[Rule(id="h", hypothesis="All copies must be returned.")]),
        activate=False,
    )
    with pytest.raises(ValueError):
        s.enqueue("owner", c["id"], c["revision"], "draft-analysis")


def test_no_plaintext_rationale_in_audit_and_erasure_is_restart_safe(tmp_path):
    from clausegate_api.store import Store

    s, c = analyzed(tmp_path)
    decide(s, c)
    assert "Reviewed the precise exception" not in json.dumps(s.audit("owner", c["id"]))
    current = s.case("owner", c["id"])
    s.erase("owner", c["id"], current["revision"], "ERASE")
    before = s.case("owner", c["id"])["revision"]
    restarted = Store(s.root, ledger_dir=s.ledger_dir)
    assert restarted.case("owner", c["id"])["revision"] == before
    assert restarted.verify_audit("owner", c["id"])["valid"]


def test_auditor_does_not_get_contract_content_by_default(tmp_path):
    s, c = analyzed(tmp_path)
    s.membership("owner", c["workspace_id"], "second", ["auditor"], [c["id"]])
    view = s.case("second", c["id"])
    assert not view["document_id"] and not view["findings"] and not view["context"]
    with pytest.raises(PermissionError):
        s.document("second", c["document_id"])


def test_expired_queued_actor_cannot_poison_the_worker_queue(tmp_path):
    s, c = setup(tmp_path)
    s.enqueue("owner", c["id"], c["revision"], "expiry")
    with s.connect() as db:
        db.execute("UPDATE members SET expires='2000-01-01' WHERE actor='owner'")
    assert s.claim() is None
    with s.connect() as db:
        assert db.execute("SELECT status FROM jobs").fetchone()[0] == "cancelled"


def test_clarification_reopens_interpretation_not_blanket_approval(tmp_path):
    s, c = setup(tmp_path)
    c = s.set_context("owner", c["id"], c["revision"], "unknown", "")
    c = s.submit_findings(
        "reviewer", c["id"], c["revision"], findings(s, c), "Earlier context review"
    )
    r = next(r for r in c["requests"] if r["kind"] == "clarification")
    s.decide(
        "owner",
        r["id"],
        DecisionInput(
            expected_revision=r["revision"],
            binding=r["binding"],
            kind="clarify",
            rationale="New explicit company purpose",
            side="mutual",
            purpose="A different use",
            key="new-context",
        ),
    )
    c = s.case("owner", c["id"])
    assert any(r["kind"] == "interpretation" and r["state"] == "pending" for r in c["requests"])
