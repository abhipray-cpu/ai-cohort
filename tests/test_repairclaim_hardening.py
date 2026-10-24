import pytest
from repairclaim_api.documents import parse_document
from repairclaim_api.errors import DomainError
from repairclaim_api.operations import restore_backup
from repairclaim_api.parser import RestrictedParser
from test_repairclaim_workflow import flow, make_pdf, register


def test_container_parser_cannot_inherit_a_remote_docker_context(monkeypatch):
    monkeypatch.setattr("repairclaim_api.parser.shutil.which", lambda _: "/fixture/docker")
    monkeypatch.setenv("DOCKER_HOST", "ssh://remote.invalid")
    command = RestrictedParser(mode="container", engine="docker").command("/fixture/tmp")
    assert "--host" in command
    host = command[command.index("--host") + 1]
    assert host.startswith(("unix://", "npipe://"))
    assert "remote.invalid" not in " ".join(command)


def test_only_one_global_job_lease(flow):
    store, _, owner, _, _, case = flow
    for key in ("one", "two"):
        store.start_investigation(owner.token, case["id"], 2, key)
    assert store.claim_job() is not None
    assert store.claim_job() is None


def test_reviewing_another_programme_does_not_bless_old_source_conditions(flow):
    store, *_ = flow
    old = register(store)
    register(store, "90000", "r2")
    # A second active family still references the old bytes.
    with store._transaction() as db:
        alternate = old.model_copy(update={"family_id": "old-family"})
        db.execute(
            "INSERT INTO rc_programmes VALUES(?,?,?,1,?)",
            ("old-family", "r1", alternate.model_dump_json(), store._now()),
        )
    assert store.registry_status()["status"] == "stale"


def test_account_erasure_cannot_be_undone_by_backup_restore(flow, tmp_path):
    store, _, owner, *_ = flow
    backup = store.create_backup("backup-test-passphrase")
    store.erase_account(owner.token, "DELETE MY ACCOUNT")
    restored = restore_backup(
        backup,
        "backup-test-passphrase",
        tmp_path / "restored",
        store.path.parent / "erasure.jsonl",
        clock=store.clock,
    )
    restored.activate_restored()
    with pytest.raises(DomainError):
        restored.login("owner", "workflow-test-password")


def test_same_source_bytes_recover_after_outage(flow):
    store, *_ = flow
    register(store)
    with store._transaction() as db:
        row = db.execute("SELECT blob_id FROM rc_captures LIMIT 1").fetchone()
        raw = store._blob_read(row[0])
        db.execute("UPDATE rc_sources SET state='unavailable'")
    store.capture_source(
        "fixture-source",
        "https://static.nhtsa.gov/odi/fixture.pdf",
        raw,
        parse_document(raw, "fixture.pdf"),
    )
    assert store.registry_status()["status"] == "complete"


def test_reminder_tick_is_idempotent_and_retention_is_not_background_extended(flow):
    store, clock, owner, _, _, case = flow
    from datetime import UTC, datetime

    due = datetime.fromtimestamp(clock[0] + 5, UTC).isoformat()
    store.add_reminder(owner.token, case["id"], due, "UTC", "user_entered", "Fixture follow-up")
    clock[0] += 6
    store.tick()
    store.tick()
    assert store.case_details(owner.token, case["id"])["reminders"][0]["status"] == "due"
    with store._transaction() as db:
        assert (
            db.execute("SELECT COUNT(*) FROM audit WHERE action='reminder_due'").fetchone()[0] == 1
        )
    clock[0] += 181 * 86400
    session = store.login("owner", "workflow-test-password")
    assert store.list_cases(session.token) == []


def test_manual_correction_preserves_unrelated_document_anchors(flow):
    store, _, owner, _, _, case = flow
    from test_repairclaim_continuity import upload

    doc = upload(store, owner.token, case["id"], "Repair mileage: 90000 mi", "invoice")
    store.confirm_proposals(owner.token, doc["id"], [0], 3)
    snapshot = store.correct_fact(
        owner.token,
        case["id"],
        4,
        None,
        {"field": "diagnosis", "value": "Reported noise", "status": "user_reported"},
    )
    assert any(f.anchor is not None for f in snapshot.facts)


def test_documented_reminder_requires_current_literal_deadline_source(flow):
    import hashlib

    from contracts.repairclaim import Condition, EvidenceAnchor

    store, _, owner, _, _, case = flow
    programme = register(store)
    raw = make_pdf("Submit by 2026-11-01. Authored fixture only.")
    store.capture_source(
        "fixture-source",
        "https://static.nhtsa.gov/odi/fixture.pdf",
        raw,
        parse_document(raw, "fixture.pdf"),
    )
    anchor = EvidenceAnchor(
        document_id="fixture-source",
        sha256=hashlib.sha256(raw).hexdigest(),
        page=1,
        quote="Submit by 2026-11-01.",
    )
    revised = programme.model_copy(
        update={
            "revision": "r2",
            "conditions": (
                Condition(
                    id="date",
                    field="repair_date",
                    operator="on_or_before",
                    expected="2026-11-01",
                    anchor=anchor,
                ),
            ),
        }
    )
    store.activate_programme(revised)
    reminder = store.add_reminder(
        owner.token,
        case["id"],
        "2026-11-01T12:00:00Z",
        "UTC",
        "programme_documented",
        "Source-stated submission date",
        source_anchor=anchor,
    )
    assert reminder["source_anchor"]["sha256"] == anchor.sha256
    with pytest.raises(DomainError):
        store.add_reminder(
            owner.token,
            case["id"],
            "2026-11-02T12:00:00Z",
            "UTC",
            "programme_documented",
            "Wrong date",
            source_anchor=anchor,
        )
