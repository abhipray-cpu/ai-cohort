import io
import json
import zipfile

import pytest
from catalogbridge_api.backup import backup, restore
from catalogbridge_api.corpus import normalize_pair, safe_members, score_pairs
from catalogbridge_api.store import Store
from test_catalogbridge_core import setup_batch


def archive(name):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr(name, "{}")
    stream.seek(0)
    return zipfile.ZipFile(stream)


@pytest.mark.parametrize(
    "name", ["../bad", "/absolute", "C:/windows", "a/CON.txt", "a/.. /file", "a\\..\\evil"]
)
def test_dataset_archive_rejects_windows_and_traversal_members(name):
    with archive(name) as z, pytest.raises(ValueError):
        safe_members(z)


def test_gold_fields_never_enter_normalized_pair():
    pair = {
        "id_left": 1,
        "id_right": 2,
        "title_left": "Product A",
        "title_right": "Product B",
        "label": 1,
        "cluster_id_left": 17,
        "cluster_id_right": 17,
        "is_hard_negative": False,
    }
    result = normalize_pair(pair)
    assert result["gold"] == 1
    assert "cluster_id" not in json.dumps(result["input"])
    assert "label" not in json.dumps(result["input"])


def test_score_keeps_failed_and_abstained_rows_in_denominator():
    score = score_pairs([1, 0, 1], [1, None, None])
    assert score["total"] == 3 and score["resolved"] == 1 and score["correct"] == 1
    assert score["coverage"] == pytest.approx(1 / 3)


def test_backup_restore_is_quarantined_and_requires_current_journal(tmp_path):
    store, b = setup_batch(tmp_path / "live")
    backup(store, tmp_path / "snapshot")
    with pytest.raises(ValueError, match="journal"):
        restore(tmp_path / "snapshot", tmp_path / "restored", tmp_path / "missing")
    restored = restore(tmp_path / "snapshot", tmp_path / "restored", store.journal_dir)
    assert Store(restored, store.journal_dir).batch("w", b["id"])["state"] == "partial"
    with pytest.raises(ValueError, match="exist"):
        restore(tmp_path / "snapshot", tmp_path / "restored", store.journal_dir)


def test_launcher_catalogbridge_independent_configuration():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "cb_launcher", Path(__file__).parents[1] / "scripts/dev_stack.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.configure("catalogbridge")
    assert module.DEFAULT_PORT == "8006"
    assert "catalogbridge_api.worker" in module.COMMANDS["worker"]
    assert module.STATE_DIR.name == "catalogbridge-dev"
