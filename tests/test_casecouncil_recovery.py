# ruff: noqa: F811
import json
import sqlite3

import pytest
from casecouncil_api.backup import backup, restore
from casecouncil_api.store import Store
from test_casecouncil_store import PASSWORD, seeded, start  # noqa: F401


def test_backup_restore_rekeys_sessions_and_quarantines_pending_work(seeded, tmp_path):
    s, w, c = seeded
    session = s.login("owner", PASSWORD)
    start(s, c)
    path = tmp_path / "snapshots" / "backup.sqlite3"
    manifest = backup(s, path)
    assert manifest["schema_version"] >= 1
    with pytest.raises(ValueError):
        backup(s, path)
    out = tmp_path / "restored"
    restore(path, out, s.root / "authority" / "usage.jsonl")
    restored = Store(out)
    assert restored.session(session["token"]) is None
    assert restored.list_jobs("owner", c)[0]["state"] == "stale"
    assert restored.workspace("owner", w)["hold"]
    assert restored.case("owner", c)["sources"]
    with pytest.raises(ValueError):
        start(restored, c, "new-run")


def test_corrupt_backup_is_rejected_before_target_creation(seeded, tmp_path):
    s, _w, _c = seeded
    p = tmp_path / "backup.sqlite3"
    backup(s, p)
    with sqlite3.connect(p) as db:
        db.execute("UPDATE cases SET context='{}'")
    with pytest.raises(ValueError):
        restore(p, tmp_path / "bad-target")
    assert not (tmp_path / "bad-target").exists()


def test_external_usage_journal_drift_blocks_inference(seeded):
    s, _w, c = seeded
    start(s, c)
    j = s.claim()
    aid = s.reserve(j, "first", "prompt")
    s.settle(
        aid,
        {
            "usage": {"input_tokens": 10, "output_tokens": 1},
            "tools_audited": True,
            "elapsed_ms": 1,
            "status": "returned",
        },
    )
    path = s.root / "authority" / "usage.jsonl"
    assert path.exists()
    with path.open("a") as f:
        f.write(json.dumps({"forged": "entry"}) + "\n")
    with pytest.raises(ValueError):
        s.reserve(j, "second", "prompt")
