"""Unmasked regressions for defects discovered by the frozen real-corpus campaign."""

import numpy as np
import pytest
from agent_core.provider import StructuredGeneration
from contracts.relaydesk import Recall
from relaydesk_api.backup import backup, restore
from relaydesk_api.common import now
from relaydesk_api.context import compress
from relaydesk_api.recall import RecallEngine, index_case
from relaydesk_api.store import Store
from relaydesk_api.worker import run_once
from test_relaydesk_core import batch, setup
from test_relaydesk_worker import Provider, queued


def test_source_edit_fences_late_vector_publish(tmp_path):
    store, case = setup(tmp_path)
    value = batch()
    store.import_messages("alice", case["id"], value)
    memory = store.memories("alice", case["id"])[0]

    class UnitEncoder:
        # Unit boundary only. Not fabricated semantic acceptance evidence.
        fingerprint = "unit-fence-model"

        def chunks(self, text):
            return [(0, len(text), text)]

        def encode(self, texts):
            return [np.ones(384, dtype=np.float32) / np.sqrt(384) for _ in texts]

    calls = 0

    def change():
        nonlocal calls
        calls += 1
        if calls == 2:
            edited = value.model_copy(deep=True)
            edited.messages[0].body = "Updated source report"
            edited.messages[0].updated_at = now()
            store.import_messages("alice", case["id"], edited)

    index_case(store, "alice", case["id"], UnitEncoder(), change)
    with store.connect() as db:
        assert (
            db.execute(
                "SELECT count(*) FROM vectors WHERE memory_id=?", (memory["id"],)
            ).fetchone()[0]
            == 0
        )


def test_changed_source_body_without_hash_change_is_rejected(tmp_path):
    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    source = store.sources("alice", case["id"])[0]
    with store.connect() as db:
        db.execute("UPDATE sources SET body='CORRUPTED CONTENT' WHERE id=?", (source["id"],))
    with pytest.raises(ValueError):
        RecallEngine(store).search("alice", case["id"], Recall(question="rollback server failed"))


def test_restore_rejects_an_unrelated_valid_ledger(tmp_path):
    store, case = setup(tmp_path)
    store.import_messages("alice", case["id"], batch())
    snapshot = tmp_path / "snapshot"
    backup(store, snapshot)
    source = store.sources("alice", case["id"])[0]
    store.erase("alice", case["id"], [source["id"]], "ERASE")
    unrelated = Store(tmp_path / "unrelated", ledger_dir=tmp_path / "unrelated-ledger")
    with pytest.raises((ValueError, RuntimeError)):
        restore(snapshot, tmp_path / "restored-with-wrong-ledger", ledger_dir=unrelated.ledger_dir)


def test_negated_verification_is_not_rejected_as_a_positive_claim(tmp_path):
    store, _, _, job = queued(tmp_path, True)
    qualified = {
        "summary": "There is no evidence that tests passed or that the root cause was confirmed.",
        "claims": [],
        "questions": ["Confirm current environment."],
        "limitations": ["No technical verification established."],
    }
    run_once(store, encoder=None, provider=Provider([{"proposals": []}, qualified, qualified]))
    assert store.job("alice", job["id"])["output"]["payload"]["ai_succeeded"] is True


def test_valid_memory_id_does_not_make_a_fabricated_outcome_supported(tmp_path):
    import json

    store, _, _, job = queued(tmp_path, True)

    class Fabricated:
        def __init__(self):
            self.calls = 0

        def generate(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                value = {"proposals": []}
            else:
                mid = kwargs["schema"]["$defs"]["Claim"]["properties"]["memory_ids"]["items"][
                    "enum"
                ][0]
                value = {
                    "summary": "Every environment has recovered.",
                    "claims": [
                        {
                            "text": "The customer confirmed that every affected environment recovered.",
                            "memory_ids": [mid],
                        }
                    ],
                    "questions": [],
                    "limitations": [],
                }
            return StructuredGeneration(
                text=json.dumps(value), exit_code=0, elapsed_ms=1, tools_audited=True
            )

    run_once(store, encoder=None, provider=Fabricated())
    assert store.job("alice", job["id"])["output"]["payload"]["ai_succeeded"] is False


def test_compression_metadata_does_not_overflow_the_model_context():
    import json

    memories = [
        {
            "id": f"{i:032}",
            "body": "Participant report",
            "kind": "episode",
            "state": "reported",
            "source_id": f"source-{i}",
        }
        for i in range(10000)
    ]
    compressed = compress(memories, 6000)
    assert len(json.dumps(compressed)) < 48000


def test_current_question_does_not_cite_itself_as_investigation_evidence(tmp_path):
    store, case, _, job = queued(tmp_path)
    result = RecallEngine(store).search("alice", case["id"], Recall(question=job["question"]))
    assert all(
        store.source("alice", h["evidence"]["source_id"])["source_key"] != "turn:" + job["id"]
        for h in result["hits"]
    )
