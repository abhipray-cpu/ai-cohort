import json

import pytest
from clausegate_api.backup import backup, restore
from clausegate_api.store import Store
from contracts.clausegate import DecisionInput
from test_clausegate_core import analyzed, decide, findings, setup


def test_audit_tamper_and_domain_state_tamper_are_not_accepted(tmp_path):
    s, c = analyzed(tmp_path)
    with s.connect() as db:
        payload = json.loads(
            db.execute("SELECT payload FROM cases WHERE id=?", (c["id"],)).fetchone()[0]
        )
        payload["state"] = "review_ready"
        db.execute("UPDATE cases SET payload=? WHERE id=?", (json.dumps(payload), c["id"]))
    with pytest.raises(ValueError, match="integrity"):
        s.verify_audit("owner", c["id"])


def test_separate_roles_require_distinct_reviewers(tmp_path):
    from contracts.clausegate import Playbook, Rule

    s, c = setup(tmp_path)
    c = s.set_playbook(
        "owner",
        c["id"],
        c["revision"],
        Playbook(
            name="Two roles fixture",
            rules=[
                Rule(
                    id="h",
                    hypothesis="All copies must be returned.",
                    action="require_exception",
                    roles=["reviewer", "approver"],
                )
            ],
        ),
    )
    c = s.submit_findings("reviewer", c["id"], c["revision"], findings(s, c), "Fixture")
    decide(s, c)
    c = s.case("owner", c["id"])
    with pytest.raises(PermissionError):
        decide(s, c, key="second-role")


def test_expiry_and_payload_replay_cannot_clear_requests(tmp_path):
    s, c = analyzed(tmp_path)
    r = c["requests"][0]
    first = decide(s, c)
    wrong = DecisionInput(
        expected_revision=r["revision"],
        binding=r["binding"],
        kind="approve_exception",
        rationale="Changed scope is not the same response.",
        key="decision",
    )
    with pytest.raises(ValueError):
        s.decide("reviewer", r["id"], wrong)
    s.withdraw("reviewer", c["id"], first["id"], s.case("reviewer", c["id"])["revision"])
    assert s.case("owner", c["id"])["state"] == "waiting_human"


def test_wrong_authority_restore_and_later_erasures_are_safe(tmp_path):
    s, c = analyzed(tmp_path)
    snap = tmp_path / "snapshot"
    backup(s, snap)
    unrelated = Store(tmp_path / "unrelated", ledger_dir=tmp_path / "other-authority")
    with pytest.raises((ValueError, RuntimeError)):
        restore(snap, tmp_path / "wrong", ledger_dir=unrelated.ledger_dir)
    assert not (tmp_path / "wrong").exists()
    s.erase("owner", c["id"], c["revision"], "ERASE")
    target = tmp_path / "restored"
    restore(snap, target, ledger_dir=s.ledger_dir)
    recovered = Store(target, ledger_dir=s.ledger_dir)
    with pytest.raises(PermissionError):
        recovered.case("owner", c["id"])
    with recovered.connect() as db:
        assert db.execute("SELECT count(*) FROM documents").fetchone()[0] == 0
        assert (
            json.loads(
                db.execute("SELECT payload FROM cases WHERE id=?", (c["id"],)).fetchone()[0]
            )["state"]
            == "erased"
        )
    assert recovered.setting("quarantined")


def test_anchored_chain_truncation_detected(tmp_path):
    s, c = analyzed(tmp_path)
    anchor = s.anchor("owner", c["id"])
    with s.connect() as db:
        db.execute("DELETE FROM events WHERE case_id=? AND seq=?", (c["id"], anchor["seq"]))
    with pytest.raises(ValueError):
        s.verify_audit("owner", c["id"])
