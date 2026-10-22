"""Explicit zero-inference diagnostic replay of preserved real live metadata."""

import json
import os
import sqlite3
from pathlib import Path

from contracts.releasefence import Span
from releasefence_api.backends import Backend

from scripts.releasefence_backend_lab import BackendLab, eventually


def test_replay_all_preserved_actual_cohort_spans_to_real_backends(tmp_path):
    """No inference; replay real retained live metadata, not invented task traffic."""
    source = Path(os.environ["RELEASEFENCE_REPLAY_MLFLOW_DB"]).resolve()
    with sqlite3.connect("file:" + str(source) + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM spans ORDER BY start_time_unix_nano,span_id").fetchall()
    spans = []
    for row in rows:
        content = json.loads(row["content"])
        attrs = {key: json.loads(value) for key, value in content["attributes"].items()}
        spans.append(
            Span(
                trace_id=row["trace_id"].removeprefix("tr-"),
                span_id=row["span_id"],
                parent_span_id=row["parent_span_id"],
                release=attrs["releasefence.release"],
                name=row["name"],
                kind=row["name"],
                started_ns=row["start_time_unix_nano"],
                ended_ns=row["end_time_unix_nano"],
                status=row["status"].lower(),
            )
        )
    assert len(spans) == 439, "bound this diagnostic to the retained failed cohort"
    with BackendLab(
        tmp_path / "replay-backends",
        os.environ["RELEASEFENCE_MLFLOW_PYTHON"],
        os.environ["RELEASEFENCE_PHOENIX_PYTHON"],
    ) as lab:
        config = lab.provision("retained-live-span-replay")
        backends = [
            Backend(
                "mlflow",
                lab.urls["mlflow"] + "/v1/traces",
                lab.urls["mlflow"],
                config["secret"],
                config["project"],
                lab_loopback=True,
            ),
            Backend(
                "phoenix",
                lab.urls["phoenix"] + "/v1/traces",
                lab.urls["phoenix"],
                "lab",
                "retained-live-span-replay",
                lab_loopback=True,
            ),
        ]
        for backend in backends:
            for offset in range(0, len(spans), 40):
                backend.export(spans[offset : offset + 40])
            for offset in range(0, len(spans), 40):
                batch = spans[offset : offset + 40]
                eventually(
                    lambda backend=backend, batch=batch: backend.verify(batch)["verified"],
                    seconds=30,
                )
