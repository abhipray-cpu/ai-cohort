# ruff: noqa: F811 -- imported pytest fixture
import json
import subprocess
import sys

import pytest
from casecouncil_api.controller import Controller
from test_casecouncil_protocol import ControlledProvider
from test_casecouncil_resume import failed
from test_casecouncil_store import seeded  # noqa: F401


def head(store):
    with store.connect() as db:
        return db.execute("SELECT journal_head FROM meta").fetchone()[0]


def close(store, attempt, expected=None, **changes):
    value = {
        "actor": "owner",
        "aid": attempt["id"],
        "expected_head": expected or head(store),
        "reason": "Explicit user approval of irreversible receipt loss; no usage or safety inference",
        "isolation_reference": "Operator stopped dispatch and checked no surviving CaseCouncil runtime tree",
        "acknowledge_unknown": True,
        "runtime_isolated": True,
        "key": "incident-one",
    }
    value.update(changes)
    return store.close_incident(**value)


def test_incident_retains_unknown_receipt_full_charge_and_requires_separate_resume(seeded):
    s, w, j, a, old, _e = failed(seeded)
    incident = close(s, a, old)
    assert incident["usage_remains_unknown"] and incident["tool_safety_unverified"]
    assert incident["reserved_seconds_retained"] == a["reserved"]
    saved = s.job("owner", j["id"])
    assert saved["attempts"] == j["attempts"]
    assert saved["seconds"] == j["seconds"] and saved["calls"] == j["calls"]
    assert saved["state"] == "manual_required" and s.workspace("owner", w)["hold"]
    assert saved["incidents"][0]["id"] == incident["id"]
    assert close(s, a, old) == incident
    s.resume_job(
        "owner",
        j["id"],
        j["packet_hash"],
        head(s),
        600,
        "Explicit bounded continuation after owner-approved incident closure",
        "resume",
    )
    provider = ControlledProvider()
    Controller(s, provider).once()
    assert len(provider.prompts) == 4
    saved = s.job("owner", j["id"])
    assert saved["calls"] == 9 and saved["attempts"][4]["receipt"]["usage"] is None
    assert saved["packet"]["incident_notices"][0]["id"] == incident["id"]
    assert "runtime_incident" in saved["packet"]["review_requirements"]
    assert s.export("owner", j["id"])["incidents"][0]["tool_safety_unverified"]


@pytest.mark.parametrize(
    "changes",
    [
        {"actor": "reviewer"},
        {"acknowledge_unknown": False},
        {"runtime_isolated": False},
        {"reason": "short"},
        {"isolation_reference": "short"},
        {"expected_head": "stale"},
    ],
)
def test_closure_rejects_missing_authority_evidence_or_acknowledgement(seeded, changes):
    s, _w, _j, a, _head, _e = failed(seeded)
    with pytest.raises((ValueError, PermissionError)):
        close(s, a, **changes)


def test_known_or_explicit_unsafe_call_is_not_an_irrecoverable_incident(seeded):
    s, _w, j, a, _head, _e = failed(seeded)
    with pytest.raises(ValueError):
        close(s, j["attempts"][0])
    with s.write() as db:
        receipt = {
            **a["receipt"],
            "diagnostic": {"category": "unsafe_tool", "unsafe_tool_event": True},
        }
        db.execute("UPDATE attempts SET receipt=? WHERE id=?", (json.dumps(receipt), a["id"]))
    with pytest.raises(ValueError):
        close(s, a)


def test_closure_requires_stopped_dispatch_and_exclusive_runtime_lock(seeded):
    from casecouncil_api.runtime_guard import runtime_guard

    s, _w, j, a, _head, _e = failed(seeded)
    with runtime_guard(s.root), pytest.raises(ValueError):
        close(s, a)
    with s.write() as db:
        db.execute("UPDATE jobs SET state='running' WHERE id=?", (j["id"],))
    with pytest.raises(ValueError):
        close(s, a)


def test_runtime_fence_is_shared_between_real_processes_and_released(seeded):
    from casecouncil_api.runtime_guard import runtime_guard

    s, _w, _case = seeded
    code = """import sys
from casecouncil_api.runtime_guard import runtime_guard, RuntimeBusy
try:
    with runtime_guard(sys.argv[1]):
        pass
except RuntimeBusy:
    raise SystemExit(23)
"""

    def child():
        return subprocess.run(
            [sys.executable, "-c", code, str(s.root)], capture_output=True, timeout=10, check=False
        )

    with runtime_guard(s.root):
        assert child().returncode == 23
    assert child().returncode == 0


def test_other_workspace_cannot_bypass_unclosed_liability(seeded):
    from test_casecouncil_store import CONTEXT

    s, _w, _j, _a, _head, _e = failed(seeded)
    workspace = s.create_workspace("owner", "Other workspace", "other")
    s.set_policy(
        "owner",
        workspace,
        1,
        {
            "name": "Other policy",
            "instructions": "No conclusions",
            "required_documents": ["policy"],
            "egress_enabled": True,
        },
    )
    case = s.create_case("owner", workspace, CONTEXT, "case")
    with pytest.raises(ValueError):
        s.start("owner", case["id"], s.preview("owner", case["id"])["binding"], "bypass")


def test_closure_is_journal_bound_and_retained_after_erasure(seeded, monkeypatch):
    from casecouncil_api.recovery import liabilities_resolved

    s, _w, j, a, _head, _e = failed(seeded)
    incident = close(s, a)
    case = s.case("owner", j["case_id"])
    s.erase("owner", case["id"], case["revision"], "Authorized erasure of complaint evidence")
    with s.connect() as db:
        liabilities_resolved(s, db)
        assert db.execute("SELECT count(*) FROM attempt_incidents").fetchone()[0] == 1
    with s.write() as db:
        db.execute("UPDATE attempt_incidents SET hash='corrupt' WHERE id=?", (incident["id"],))
    with s.connect() as db, pytest.raises(ValueError):
        liabilities_resolved(s, db)


def test_second_incident_cannot_reset_store_lifetime_risk_allowance(seeded):
    s, _w, j, a, _head, _e = failed(seeded)
    close(s, a)
    other = j["attempts"][0]
    with s.write() as db:
        db.execute(
            "UPDATE attempts SET receipt=? WHERE id=?", (json.dumps(a["receipt"]), other["id"])
        )
    with pytest.raises(ValueError, match="allowance"):
        close(s, other, key="second")


def test_fsync_failure_leaves_hold_and_no_incident(seeded, monkeypatch):
    s, w, _j, a, _head, _e = failed(seeded)

    def unavailable(*args):
        raise OSError("authored journal failure")

    monkeypatch.setattr("casecouncil_api.journal.append", unavailable)
    with pytest.raises(OSError):
        close(s, a)
    assert s.workspace("owner", w)["hold"]
    with s.connect() as db:
        assert db.execute("SELECT count(*) FROM attempt_incidents").fetchone()[0] == 0


def test_persistent_call_ceiling_counts_old_attempts_and_cannot_be_raised(seeded):
    from casecouncil_api.campaign import limit_store_calls

    s, w, j, a, _head, _e = failed(seeded)
    close(s, a)
    limit_store_calls(s, "owner", w, 6, "Authored cumulative six-call test grant")
    with pytest.raises(ValueError):
        limit_store_calls(s, "owner", w, 132, "A larger new grant must not reset this campaign")
    s.resume_job(
        "owner",
        j["id"],
        j["packet_hash"],
        head(s),
        600,
        "Explicitly retain old calls under cumulative grant",
        "resume",
    )
    provider = ControlledProvider()
    Controller(s, provider).once()
    assert len(provider.prompts) == 1
    assert s.job("owner", j["id"])["calls"] == 6


def test_incident_cannot_be_added_after_human_review(seeded):
    s, _w, j, a, _head, _e = failed(seeded)
    s.review(
        "reviewer",
        j["id"],
        {
            "packet_hash": j["packet_hash"],
            "reason": "Human reviewed the original incomplete engineering fixture",
            "response": "Seek missing evidence; no final determination is authorized.",
            "resolutions": {
                k: "Reviewed blocker; require further human investigation"
                for k in j["packet"]["review_requirements"]
            },
            "overrides": {},
        },
        "review",
    )
    with pytest.raises(ValueError):
        close(s, a)


def test_incident_and_fsync_database_crash_window_stays_fail_closed(seeded, monkeypatch):
    from casecouncil_api import journal

    s, _w, _j, a, _head, _e = failed(seeded)
    append = journal.append

    def failed_after_fsync(*args):
        append(*args)
        raise OSError("authored failure after fsync, before database commit")

    monkeypatch.setattr(journal, "append", failed_after_fsync)
    with pytest.raises(OSError):
        close(s, a)
    with s.connect() as db, pytest.raises(ValueError):
        journal.assert_current(db, s.journal_path)


def test_http_review_requires_incident_acknowledgement_and_exports_keep_unknown(seeded):
    from casecouncil_api.api import create_app
    from fastapi.testclient import TestClient
    from test_casecouncil_api import login, post
    from test_casecouncil_store import PASSWORD

    s, _w, j, a, _head, _e = failed(seeded)
    incident = close(s, a)
    s.resume_job(
        "owner",
        j["id"],
        j["packet_hash"],
        head(s),
        600,
        "Explicit bounded continuation for HTTP engineering acceptance",
        "resume",
    )
    Controller(s, ControlledProvider()).once()
    app = create_app(s.root, username="owner", password=PASSWORD)
    client = TestClient(app)
    login(client, "reviewer")
    run = client.get(f"/api/runs/{j['id']}").json()
    assert run["incidents"][0]["id"] == incident["id"]
    from casecouncil_api.verification import verify_packet

    modified = json.loads(json.dumps(run["packet"]))
    modified.pop("incident_notices")
    with pytest.raises(ValueError):
        verify_packet(modified, run["snapshot"], run["incidents"])
    review = {
        "packet_hash": run["packet_hash"],
        "reason": "Authored engineering check, not real domain approval",
        "response": "Ask for missing evidence before making a determination.",
        "resolutions": {},
        "overrides": {},
    }
    assert post(client, f"/api/runs/{j['id']}/reviews", json=review).status_code == 409
    review["resolutions"] = {
        k: "Checked authored fixture blocker, not customer approval"
        for k in run["packet"]["review_requirements"]
    }
    assert post(client, f"/api/runs/{j['id']}/reviews", json=review).status_code == 201
    exported = client.get(f"/api/runs/{j['id']}/export?reviewed=true").json()
    assert exported["approved"] and exported["incidents"][0]["usage_remains_unknown"]
    assert (
        "tool_safety_unverified"
        in client.get(f"/api/runs/{j['id']}/export?reviewed=true&format=html").text
    )


@pytest.mark.parametrize("snapshot_before_closure", [False, True])
def test_restore_retains_incident_authority_without_forging_receipts(
    seeded, snapshot_before_closure
):
    from casecouncil_api.backup import authorize_restored_runtime, backup, restore
    from casecouncil_api.store import Store

    s, _w, j, a, _head, _e = failed(seeded)
    snapshot = s.root / "sealed.sqlite3"
    if snapshot_before_closure:
        backup(s, snapshot)
    incident = close(s, a)
    if not snapshot_before_closure:
        backup(s, snapshot)
    target = s.root / "restored"
    info = restore(snapshot, target, s.journal_path)
    restored = Store(target)
    authorize_restored_runtime(
        restored,
        info["authority_head"],
        "Checked current incident authority and stopped prior runtime",
    )
    with restored.connect() as db:
        assert (
            json.loads(
                db.execute("SELECT receipt FROM attempts WHERE id=?", (a["id"],)).fetchone()[0]
            )["usage"]
            is None
        )
        assert db.execute("SELECT id FROM attempt_incidents").fetchone()[0] == incident["id"]
        assert db.execute("SELECT state FROM jobs WHERE id=?", (j["id"],)).fetchone()[0] == "stale"
    with pytest.raises(ValueError):
        close(restored, a, key="not-a-new-allowance")
