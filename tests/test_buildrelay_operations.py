# ruff: noqa: F811
# Imported pytest fixture intentionally matches function parameter names.
import importlib.util
import sqlite3
from pathlib import Path

import pytest
from buildrelay_api.backup import backup, restore
from test_buildrelay_core import store  # noqa: F401


def test_launcher_is_independent():
    path = Path(__file__).resolve().parents[1] / "scripts/dev_stack.py"
    spec = importlib.util.spec_from_file_location("buildrelay_launcher_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.configure("buildrelay")
    assert module.DEFAULT_PORT == "8007"
    assert module.PREFIX == "BUILDRELAY"
    assert module.COMMANDS["worker"] == ["-m", "buildrelay_api.worker"]
    assert module.STATE_DIR.name == "buildrelay-dev"


def test_backup_restore_preserves_data_and_refuses_overwrite(store, tmp_path):
    dest = tmp_path / "backup.sqlite3"
    backup(store.root, dest)
    with pytest.raises(FileExistsError):
        backup(store.root, dest)
    target = tmp_path / "restored"
    restore(dest, target)
    with sqlite3.connect(target / "buildrelay.sqlite3") as db:
        assert db.execute("SELECT count(*) FROM repos").fetchone()[0] == 1
    with pytest.raises(FileExistsError):
        restore(dest, target)
