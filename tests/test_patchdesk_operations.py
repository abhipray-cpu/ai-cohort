import sqlite3

import pytest
from contracts.patchdesk import Approval
from patchdesk_api.backup import backup, restore
from patchdesk_api.publisher import Publisher
from patchdesk_api.store import Store
from test_patchdesk_publication_api import reviewed


def test_backup_restore_hashes_reports_and_write_quarantine(tmp_path):
    store, _project, report = reviewed(tmp_path / "live")
    publisher = Publisher(store, enabled=True)
    draft = publisher.draft("alice", report, "Backup safety check")
    publisher.approve(
        "alice", draft["id"], Approval(expected_revision=1, payload_hash=draft["payload_hash"])
    )
    backup(store.root, tmp_path / "backup")
    restore(tmp_path / "backup", tmp_path / "restored")
    restored = Store(tmp_path / "restored")
    assert restored.object("alice", report) == store.object("alice", report)
    assert restored.setting("publisher_quarantine") is True
    assert Publisher(restored).get("alice", draft["id"])["status"] == "quarantined"
    with restored.connect() as db:
        assert not db.execute("SELECT 1 FROM sessions").fetchone()
    with pytest.raises(ValueError):
        restore(tmp_path / "backup", store.root)


def test_restore_rejects_tampered_database(tmp_path):
    store, _, _ = reviewed(tmp_path / "live")
    backup(store.root, tmp_path / "backup")
    with sqlite3.connect(tmp_path / "backup/patchdesk.sqlite3") as db:
        db.execute("UPDATE objects SET payload='{}'")
    with pytest.raises(ValueError, match="hash"):
        restore(tmp_path / "backup", tmp_path / "restored")
