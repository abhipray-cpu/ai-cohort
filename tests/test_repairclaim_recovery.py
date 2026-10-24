"""Encrypted owned backups and erasure replay, not a Windows-host qualification."""

import sqlite3

import pytest
from repairclaim_api.errors import DomainError
from repairclaim_api.operations import restore_backup
from test_repairclaim_continuity import upload
from test_repairclaim_workflow import flow


def test_restore_is_quarantined_revokes_sessions_and_replays_current_erasures(flow, tmp_path):
    store, _, owner, _, _, case = flow
    upload(store, owner.token, case["id"], "PRIVATE-BACKUP-INVOICE", "invoice")
    backup = store.create_backup("backup-test-passphrase")
    assert b"PRIVATE-BACKUP-INVOICE" not in backup
    store.delete_case(owner.token, case["id"], store.get_case(owner.token, case["id"])["revision"])
    restored = restore_backup(
        backup,
        "backup-test-passphrase",
        tmp_path / "restored",
        store.path.parent / "erasure.jsonl",
        clock=store.clock,
    )
    with pytest.raises(DomainError, match="restore_quarantined"):
        restored.login("owner", "workflow-test-password")
    restored.activate_restored()
    session = restored.login("owner", "workflow-test-password")
    assert restored.list_cases(session.token) == []
    assert restored.private_orphans() == []


def test_restore_refuses_existing_target_missing_ledger_and_wrong_password(flow, tmp_path):
    store, *_ = flow
    backup = store.create_backup("backup-test-passphrase")
    with pytest.raises(DomainError):
        restore_backup(
            backup, "wrong-password", tmp_path / "wrong", store.path.parent / "erasure.jsonl"
        )
    with pytest.raises(DomainError, match="restore_target_exists"):
        restore_backup(
            backup, "backup-test-passphrase", store.path.parent, store.path.parent / "erasure.jsonl"
        )
    with pytest.raises(DomainError, match="current_erasure_ledger_required"):
        restore_backup(backup, "backup-test-passphrase", tmp_path / "missing", tmp_path / "absent")


def test_account_erasure_revokes_both_access_and_pending_monitoring(flow):
    store, _, owner, _, vehicle, case = flow
    store.set_monitoring(owner.token, vehicle["id"], [case["id"]], 86400)
    store.erase_account(owner.token, "DELETE MY ACCOUNT")
    with pytest.raises(DomainError):
        store.authenticate(owner.token)
    with pytest.raises(DomainError):
        store.login("owner", "workflow-test-password")
    assert store.rematch_monitoring() == 0


def test_private_fact_and_extraction_payloads_are_not_plaintext_in_database(flow):
    store, _, owner, _, _, case = flow
    upload(store, owner.token, case["id"], "PRIVATE-SQL-INVOICE", "invoice")
    from contracts.repairclaim import Fact

    current = store.snapshot(owner.token, case["id"])
    store.replace_facts(
        owner.token,
        case["id"],
        current.revision,
        (
            *current.facts,
            Fact(field="diagnosis", value="PRIVATE-DIAGNOSIS", status="user_reported"),
        ),
    )
    with sqlite3.connect(store.path) as db:
        dump = "\n".join(db.iterdump())
    assert "PRIVATE-SQL-INVOICE" not in dump
    assert "PRIVATE-DIAGNOSIS" not in dump


def test_account_erasure_barrier_survives_crash_before_case_ledgers(flow):
    import json

    store, _, owner, other, _, case = flow
    actor = store.authenticate(owner.token)
    store.grant(owner.token, case["id"], store.authenticate(other.token)["id"], "viewer")
    ledger = store.path.parent / "erasure.jsonl"
    with ledger.open("a") as stream:
        stream.write(
            json.dumps(
                {
                    "type": "account",
                    "user_id": actor["id"],
                    "household_id": actor["household_id"],
                    "at": store._now(),
                }
            )
            + "\n"
        )
    store.apply_erasure_ledger()
    with pytest.raises(DomainError):
        store.get_case(other.token, case["id"])
