import gzip
import io
import zipfile

import pytest

from scripts.audit_catalogbridge_corpus import load_rows, normalize_legacy_pair, normalized_offer
from scripts.run_catalogbridge_real_models import fingerprint


def test_real_source_reader_preserves_labels_only_for_evaluation():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "split.json.gz",
            gzip.compress(b'{"id":1,"title":"Real source","label":7,"cluster_id":7}\n'),
        )
    stream.seek(0)
    with zipfile.ZipFile(stream) as archive:
        rows = load_rows(archive, "split.json.gz")
    assert rows[0]["cluster_id"] == 7
    product = normalized_offer(rows[0]).model_dump()
    assert product["id"] == "1" and "cluster_id" not in product and "label" not in product


def test_real_source_intake_limit_is_not_silently_truncated():
    with pytest.raises(ValueError):
        normalized_offer({"id": 1, "title": "Actual source", "description": "x" * 20001})


def test_product_fingerprint_covers_controller_adapter_and_shared_runtime():
    hashes = fingerprint()
    assert any(p.endswith("catalogbridge_api/worker.py") for p in hashes)
    assert any(p.endswith("agent_core/codex_local.py") for p in hashes)
    assert all(len(v) == 64 for v in hashes.values())
    assert hashes == fingerprint()


def test_legacy_publisher_string_labels_are_adapted_without_relaxing_runtime_inputs():
    pair = {
        "id_left": 1,
        "id_right": 2,
        "title_left": "Product A",
        "title_right": "Product B",
        "label": "1",
    }
    result = normalize_legacy_pair(pair)
    assert result["gold"] == 1 and "label" not in result["input"]["supplier"]
    with pytest.raises(ValueError):
        normalize_legacy_pair(pair | {"label": "probably"})
