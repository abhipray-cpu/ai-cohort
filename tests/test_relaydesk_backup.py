import pytest
from relaydesk_api.backup import backup, restore
from relaydesk_api.store import Store
from test_relaydesk_core import batch, setup


def test_backup_restore_reconciles_erasure_and_invalidates_sessions(tmp_path):
    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    source = store.sources("alice", case["id"])[0]
    snapshot = tmp_path / "snapshot"
    token = store.login("alice", "alice-long-password")["token"]
    backup(store, snapshot)
    epoch = store.setting("epoch")
    store.erase("alice", case["id"], [source["id"]], "ERASE")
    destination = tmp_path / "restored"
    restore(snapshot, destination, ledger_dir=store.ledger_dir)
    recovered = Store(destination, ledger_dir=store.ledger_dir)
    assert recovered.memories("alice", case["id"]) == []
    assert recovered.setting("epoch") != epoch
    with pytest.raises(PermissionError):
        recovered.authenticate(token)
    with pytest.raises(ValueError):
        restore(snapshot, destination, ledger_dir=store.ledger_dir)


def test_corrupt_backup_and_missing_ledger_fail_closed(tmp_path):
    store, _ = setup(tmp_path)
    snapshot = tmp_path / "snapshot"
    backup(store, snapshot)
    with (snapshot / "relaydesk.sqlite3").open("ab") as stream:
        stream.write(b"corruption")
    with pytest.raises(ValueError):
        restore(snapshot, tmp_path / "restore", ledger_dir=store.ledger_dir)
