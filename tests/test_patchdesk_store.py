import sqlite3

import pytest
from contracts.patchdesk import InputUpload, Login, ProjectCreate, ProjectPolicy, Review
from patchdesk_api.store import Store
from test_patchdesk_inventory import pair


def setup_store(tmp_path):
    store = Store(tmp_path)
    store.add_user("alice", "long-password-alice", admin=True)
    store.add_user("bob", "long-password-bob")
    project = store.create_project(
        "alice", ProjectCreate(name="API maintenance", client="Example client")
    )
    return store, project


def test_sessions_are_hashed_expiring_and_logout_revokes(tmp_path):
    store, _ = setup_store(tmp_path)
    session = store.login("alice", "long-password-alice")
    assert store.authenticate(session["token"])["username"] == "alice"
    with store.connect() as db:
        assert session["token"] not in str(db.execute("SELECT * FROM sessions").fetchall())
    store.logout(session["token"])
    with pytest.raises(PermissionError):
        store.authenticate(session["token"])
    with pytest.raises(PermissionError):
        store.login("alice", "wrong-password")


def test_project_artifacts_and_memberships_are_scoped(tmp_path):
    store, project = setup_store(tmp_path)
    manifest, lock = pair()
    artifact = store.import_input(
        "alice", project["id"], InputUpload(manifest=manifest, lockfile=lock)
    )
    assert store.object("alice", artifact["id"])["payload"]["inventory"]["packages"]
    with pytest.raises(PermissionError):
        store.object("bob", artifact["id"])
    store.set_membership("alice", project["id"], "bob", ["reviewer"])
    assert store.object("bob", artifact["id"])
    with pytest.raises(PermissionError):
        store.enqueue("bob", project["id"], "Investigate", "k", {})
    store.set_membership("alice", project["id"], "bob", [])
    assert store.projects("bob") == []
    with pytest.raises(PermissionError):
        store.object("bob", artifact["id"])


def test_idempotent_queue_single_worker_and_fencing(tmp_path):
    store, project = setup_store(tmp_path)
    manifest, lock = pair()
    store.import_input("alice", project["id"], InputUpload(manifest=manifest, lockfile=lock))
    run = store.enqueue("alice", project["id"], "Investigate", "k", {})
    assert store.enqueue("alice", project["id"], "Investigate", "k", {})["id"] == run["id"]
    with pytest.raises(ValueError):
        store.enqueue("alice", project["id"], "Different question", "k", {})
    claimed = store.claim()
    assert store.claim() is None
    with pytest.raises(ValueError):
        store.checkpoint(run["id"], "stale-lease", "a", {})
    store.checkpoint(run["id"], claimed["lease"], "a", {"outcome": "success"})
    assert store.run("alice", run["id"])["results"]["a"]["outcome"] == "success"


def test_policy_revision_and_budget_reservations(tmp_path):
    store, project = setup_store(tmp_path)
    store.update_policy(
        "alice", project["id"], ProjectPolicy(expected_revision=1, public_packages=["axios"])
    )
    with pytest.raises(ValueError):
        store.update_policy("alice", project["id"], ProjectPolicy(expected_revision=1))
    manifest, lock = pair()
    store.import_input("alice", project["id"], InputUpload(manifest=manifest, lockfile=lock))
    run = store.enqueue("alice", project["id"], "Investigate", "k", {})
    claimed = store.claim()
    store.reserve(run["id"], claimed["lease"], "model_calls", 1)
    with pytest.raises(ValueError):
        store.reserve(run["id"], claimed["lease"], "model_calls", 1)
    store.finish(
        run["id"],
        claimed["lease"],
        {
            "status": "partial",
            "coverage": {},
            "findings": [],
            "conflicts": [],
            "candidates": [],
            "narrative": {"summary": "Partial", "tasks": [], "limitations": ["Missing sources"]},
        },
        "injected stop",
    )
    report = store.latest_report("alice", project["id"])
    with pytest.raises(ValueError):
        store.review("alice", report["id"], Review(expected_revision=1))
    store.review("alice", report["id"], Review(expected_revision=1, acknowledge_limits=True))
    assert store.export("alice", report["id"])["report"]["payload"]["status"] == "partial"
    store.resume("alice", run["id"], "second-grant")
    assert store.run("alice", run["id"])["model_calls"] == 1
    assert store.resume("alice", run["id"], "second-grant")["grant"] == 2


def test_connections_close_and_password_whitespace_is_preserved(tmp_path):
    store, _ = setup_store(tmp_path)
    with store.connect() as db:
        assert db.execute("SELECT 1").fetchone()[0] == 1
    with pytest.raises(sqlite3.ProgrammingError):
        db.execute("SELECT 1")
    assert (
        Login(username="alice", password="  intentional spaces  ").password
        == "  intentional spaces  "
    )
