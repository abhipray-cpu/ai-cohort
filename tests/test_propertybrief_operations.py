import json
import sqlite3

import pytest
from agent_core.provider import ProviderTimeoutError
from propertybrief_api.backup import backup, restore
from propertybrief_api.store import Store
from propertybrief_api.worker import run_once
from test_propertybrief import make_case
from test_propertybrief_agent import Scripted, decision, fake_sources


def test_backup_restore_preserves_evidence_and_reports(tmp_path):
    store = Store(tmp_path / "live")
    case = make_case(store)
    run = store.enqueue(case["id"], "Investigate", "k", "tester")
    run_once(
        store,
        provider=Scripted([decision(), ProviderTimeoutError("timeout")]),
        sources=fake_sources(),
    )
    backup(store.root, tmp_path / "backup")
    restore(tmp_path / "backup", tmp_path / "restored")
    copied = Store(tmp_path / "restored").run(run["id"])
    assert copied["observations"] == store.run(run["id"])["observations"]
    assert copied["report"] == store.run(run["id"])["report"]
    with pytest.raises(ValueError):
        restore(tmp_path / "backup", tmp_path / "live")


def test_restore_rejects_changed_evidence(tmp_path):
    store = Store(tmp_path / "live")
    case = make_case(store)
    store.enqueue(case["id"], "Investigate", "k", "tester")
    run_once(
        store,
        provider=Scripted([decision(), ProviderTimeoutError("timeout")]),
        sources=fake_sources(),
    )
    backup(store.root, tmp_path / "backup")
    with sqlite3.connect(tmp_path / "backup/propertybrief.sqlite3") as db:
        row = db.execute("SELECT id,payload_json FROM snapshots LIMIT 1").fetchone()
        value = json.loads(row[1])
        value["raw"] = []
        db.execute("UPDATE snapshots SET payload_json=? WHERE id=?", (json.dumps(value), row[0]))
    with pytest.raises(ValueError, match="hash"):
        restore(tmp_path / "backup", tmp_path / "restore")


def test_single_active_worker_and_resume_conflicts(tmp_path):
    store = Store(tmp_path)
    first = make_case(store)
    second = make_case(store)
    store.enqueue(first["id"], "Investigate first", "k", "tester")
    store.enqueue(second["id"], "Investigate second", "k", "tester")
    assert store.claim()
    assert store.claim() is None
