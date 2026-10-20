# ruff: noqa: F811 -- imported pytest fixture
import json
import time

import pytest
from casecouncil_api.consensus import digest
from casecouncil_api.controller import Controller
from test_casecouncil_protocol import ControlledProvider
from test_casecouncil_store import seeded, start  # noqa: F401


def authorize(seeded):
    s, w, job, attempt, head, evidence = failed(seeded)
    s.reconcile_attempt(
        "owner",
        attempt["id"],
        head,
        evidence,
        "Independently checked authored provider evidence",
        "reconcile",
    )
    with s.connect() as db:
        new_head = db.execute("SELECT journal_head FROM meta").fetchone()[0]
    return s, w, job, attempt, head, new_head, evidence


def failed(seeded):
    store, w, case = seeded
    j = start(store, case)
    provider = ControlledProvider(fail_stage="ballot:customer")
    original = provider.generate

    def generate(**kwargs):
        if json.loads(kwargs["prompt"].split("\nCONTEXT_JSON:\n")[1])["stage"] == "ballot:customer":
            provider.last_receipt = {
                "status": "provider_exit",
                "usage": None,
                "tools_audited": False,
                "elapsed_ms": 100,
                "diagnostic": {
                    "category": "provider_exit",
                    "exit_code": 1,
                    "error_events": 1,
                    "unsafe_tool_event": False,
                },
            }
        return original(**kwargs)

    provider.generate = generate
    Controller(store, provider).once()
    job = store.job("owner", j["id"])
    attempt = next(a for a in job["attempts"] if a["stage"] == "ballot:customer")
    with store.connect() as db:
        head = db.execute("SELECT journal_head FROM meta").fetchone()[0]
    evidence = {
        "attempt_id": attempt["id"],
        "prompt_hash": attempt["prompt_hash"],
        "receipt": {
            "status": "returned",
            "tools_audited": True,
            "usage": {"input_tokens": 42, "output_tokens": 3, "cached_input_tokens": 0},
            "elapsed_ms": 100,
        },
    }
    return store, w, job, attempt, head, evidence


def test_resume_retains_usage_and_successful_checkpoints_and_archives_partial(seeded):
    s, w, j, attempt, head, evidence = failed(seeded)
    original_receipt = attempt["receipt"]
    before = {k: digest(v) for k, v in j["checkpoints"].items() if v.get("value") is not None}
    with s.connect() as db:
        seconds = db.execute("SELECT seconds FROM jobs WHERE id=?", (j["id"],)).fetchone()[0]
    recon = s.reconcile_attempt(
        "owner",
        attempt["id"],
        head,
        evidence,
        "Verified provider evidence from an authored engineering test",
        "reconcile",
    )
    assert s.workspace("owner", w)["hold"]  # reconciliation alone never dispatches
    with s.connect() as db:
        head = db.execute("SELECT journal_head FROM meta").fetchone()[0]
    s.resume_job(
        "owner",
        j["id"],
        j["packet_hash"],
        head,
        600,
        "Explicitly resume the same snapshot after verified reconciliation",
        "resume",
    )
    recovered = s.job("owner", j["id"])
    assert recovered["state"] == "queued" and recovered["calls"] == j["calls"]
    assert recovered["attempts"][4]["receipt"] == original_receipt
    assert recovered["prior_packets"][0]["packet"] == j["packet"]
    assert recon["usage_observed_by_original_call"] is False
    assert all(
        digest(recovered["checkpoints"][k]) == v for k, v in before.items() if k != "consensus"
    )
    with s.connect() as db:
        assert (
            db.execute("SELECT seconds FROM jobs WHERE id=?", (j["id"],)).fetchone()[0] == seconds
        )
        assert (
            db.execute("SELECT count(*) FROM packet_history WHERE job=?", (j["id"],)).fetchone()[0]
            == 1
        )
    p = ControlledProvider()
    Controller(s, p).once()
    assert [x["stage"] for x in p.prompts] == [
        "ballot:customer",
        "ballot:insurer",
        "ballot:fairness",
        "synthesis",
    ]
    assert s.job("owner", j["id"])["calls"] == j["calls"] + 4


def test_unreconciled_or_stale_or_forged_recovery_is_rejected(seeded):
    s, _w, j, attempt, head, evidence = failed(seeded)
    with pytest.raises(ValueError):
        s.resume_job(
            "owner", j["id"], j["packet_hash"], head, 600, "Acknowledge only is insufficient", "bad"
        )
    with pytest.raises(PermissionError):
        s.reconcile_attempt(
            "reviewer",
            attempt["id"],
            head,
            evidence,
            "Not an owner with runtime authority",
            "denied",
        )
    for bad in (
        {**evidence, "prompt_hash": "wrong"},
        {**evidence, "receipt": {"usage": None, "tools_audited": True}},
    ):
        with pytest.raises(ValueError):
            s.reconcile_attempt(
                "owner", attempt["id"], head, bad, "This evidence must fail validation", "bad-proof"
            )
    assert s.job("owner", j["id"])["attempts"][4]["receipt"]["usage"] is None


def test_reconciliation_and_resume_retries_are_idempotent_and_keep_old_deadline_history(seeded):
    s, _w, j, a, head, new_head, evidence = authorize(seeded)
    first = s.reconcile_attempt(
        "owner",
        a["id"],
        head,
        evidence,
        "Independently checked authored provider evidence",
        "reconcile",
    )
    assert first["attempt_id"] == a["id"]
    with s.write() as db:
        db.execute("UPDATE jobs SET deadline=0 WHERE id=?", (j["id"],))
    one = s.resume_job(
        "owner",
        j["id"],
        j["packet_hash"],
        new_head,
        600,
        "Explicit bounded same-job recovery after evidence verification",
        "resume",
    )
    two = s.resume_job(
        "owner",
        j["id"],
        j["packet_hash"],
        new_head,
        600,
        "Explicit bounded same-job recovery after evidence verification",
        "resume",
    )
    assert one == two
    with s.connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (j["id"],)).fetchone()
        assert row["calls"] == j["calls"] and row["claims"] == j["claims"]
        assert time.time() < row["deadline"] <= time.time() + 601
        assert (
            db.execute("SELECT count(*) FROM packet_history WHERE job=?", (j["id"],)).fetchone()[0]
            == 1
        )


@pytest.mark.parametrize("field,value", [("calls", 22), ("seconds", 1790), ("claims", 4)])
def test_resume_cannot_reset_exhausted_allowances(seeded, field, value):
    s, _w, j, _a, _old, head, _ev = authorize(seeded)
    with s.write() as db:
        db.execute(f"UPDATE jobs SET {field}=? WHERE id=?", (value, j["id"]))
    with pytest.raises(ValueError):
        s.resume_job(
            "owner",
            j["id"],
            j["packet_hash"],
            head,
            600,
            "No amount of acknowledgement adds an exhausted allowance",
            "denied",
        )


def test_resume_rejects_changed_context_stale_head_and_corrupt_reconciliation(seeded):
    s, _w, j, _a, old, head, _ev = authorize(seeded)
    with pytest.raises(ValueError):
        s.resume_job(
            "owner",
            j["id"],
            j["packet_hash"],
            old,
            600,
            "Stale usage authority must fail before changing work",
            "stale-head",
        )
    with s.write() as db:
        db.execute("UPDATE attempt_reconciliations SET hash='corrupt'")
    with pytest.raises(ValueError):
        s.resume_job(
            "owner",
            j["id"],
            j["packet_hash"],
            head,
            600,
            "Corrupt supplemental evidence must fail verification",
            "corrupt",
        )
    case = s.case("owner", j["case_id"])
    s.update_case(
        "owner",
        case["id"],
        case["revision"],
        {**case["context"], "facts": "Changed material facts"},
        "edit",
    )
    with pytest.raises(ValueError):
        s.resume_job(
            "owner",
            j["id"],
            j["packet_hash"],
            head,
            600,
            "A stale analysis cannot be rebased through recovery",
            "stale-context",
        )


def test_partial_history_is_erased_with_case_evidence(seeded):
    s, _w, j, _a, _old, head, _ev = authorize(seeded)
    s.resume_job(
        "owner",
        j["id"],
        j["packet_hash"],
        head,
        600,
        "Archive old partial work before a bounded retry",
        "resume",
    )
    case = s.case("owner", j["case_id"])
    s.erase("owner", case["id"], case["revision"], "Authorized test erasure of case evidence")
    with s.connect() as db:
        for table in ("packet_history", "checkpoint_history"):
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM attempts").fetchone()[0] == j["calls"]


def test_journal_failure_rolls_back_recovery_and_keeps_partial_packet(seeded, monkeypatch):
    s, w, j, _a, _old, head, _ev = authorize(seeded)

    def unavailable(*args):
        raise OSError("authored fsync failure")

    monkeypatch.setattr("casecouncil_api.journal.append", unavailable)
    with pytest.raises(OSError):
        s.resume_job(
            "owner",
            j["id"],
            j["packet_hash"],
            head,
            600,
            "Recovery cannot publish ahead of usage authority",
            "disk-fault",
        )
    assert s.job("owner", j["id"])["packet_hash"] == j["packet_hash"]
    assert s.workspace("owner", w)["hold"]
    with s.connect() as db:
        assert db.execute("SELECT count(*) FROM packet_history").fetchone()[0] == 0


def test_restore_uses_supplemental_evidence_without_rewriting_unknown_receipt(seeded, tmp_path):
    from casecouncil_api.backup import authorize_restored_runtime, backup, restore
    from casecouncil_api.store import Store

    s, _w, j, attempt, _head, _new_head, _ev = authorize(seeded)
    snapshot = tmp_path / "reconciled.sqlite3"
    backup(s, snapshot)
    root = tmp_path / "restored"
    info = restore(snapshot, root, s.journal_path)
    restored = Store(root)
    assert authorize_restored_runtime(
        restored,
        info["authority_head"],
        "Verified latest usage authority and reconciled provider evidence",
    )["authorized"]
    with restored.connect() as db:
        receipt = json.loads(
            db.execute("SELECT receipt FROM attempts WHERE id=?", (attempt["id"],)).fetchone()[0]
        )
        assert receipt["usage"] is None
        assert db.execute("SELECT count(*) FROM attempt_reconciliations").fetchone()[0] == 1
        assert db.execute("SELECT state FROM jobs WHERE id=?", (j["id"],)).fetchone()[0] == "stale"


def test_crash_window_after_journal_fsync_fails_closed_without_replaying(seeded, monkeypatch):
    from casecouncil_api import journal

    s, _w, j, _a, _old, head, _ev = authorize(seeded)
    append = journal.append

    def fsynced_then_failed(*args):
        append(*args)
        raise OSError("authored crash after fsync, before database commit")

    monkeypatch.setattr(journal, "append", fsynced_then_failed)
    with pytest.raises(OSError):
        s.resume_job(
            "owner",
            j["id"],
            j["packet_hash"],
            head,
            600,
            "Fsync alone cannot publish a partial database transition",
            "crash",
        )
    assert s.job("owner", j["id"])["packet_hash"] == j["packet_hash"]
    with s.connect() as db, pytest.raises(ValueError):
        journal.assert_current(db, s.journal_path)
    with pytest.raises(ValueError):
        s.resume_job(
            "owner",
            j["id"],
            j["packet_hash"],
            head,
            600,
            "Retry must not overwrite a mismatched authority head",
            "retry",
        )


def test_failure_diagnostic_is_sanitized_in_both_receipt_and_validation_history(seeded):
    s, w, case = seeded
    j = start(s, case)
    p = ControlledProvider(fail_stage="proposal:customer")
    p.last_receipt = {
        "status": "provider_exit",
        "usage": None,
        "tools_audited": False,
        "elapsed_ms": 10,
        "diagnostic": {
            "category": "rate_limit",
            "exit_code": 7,
            "error_events": 1,
            "message": "CANARY_PRIVATE_ERROR_9308",
        },
    }
    Controller(s, p).once()
    run = s.job("owner", j["id"])
    assert "CANARY_PRIVATE_ERROR_9308" not in json.dumps(run)
    assert "CANARY_PRIVATE_ERROR_9308" not in json.dumps(s.audit("owner", w))
    events = [x for x in s.audit("owner", w) if x["action"] == "validation_failed"]
    assert json.loads(events[0]["detail"])["diagnostic"]["category"] == "rate_limit"
