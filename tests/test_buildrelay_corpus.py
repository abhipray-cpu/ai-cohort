import hashlib
import json
import zipfile

import pytest
from buildrelay_api.corpus import audit_capture


def test_capture_audit_checks_hashes_references_and_counts_without_running_code(tmp_path):
    path = tmp_path / "logchunks.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("LogChunks/logs/Python/owner@repo/failed/1.log", "ERROR: checkout failed")
        z.writestr(
            "LogChunks/build-failure-reason/Python/owner@repo.xml",
            "<Examples><Example><Log>Python/owner@repo/failed/1.log</Log><Chunk>ERROR: checkout failed</Chunk><Category>0</Category></Example></Examples>",
        )
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "file": "logchunks.zip",
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                ]
            }
        )
    )
    result = audit_capture(tmp_path)
    assert result["logs"] == 1 and result["annotations"] == 1
    assert result["missing_log_references"] == []
    assert result["ai_semantic_validation"] == "not_run"
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash"):
        audit_capture(tmp_path)
