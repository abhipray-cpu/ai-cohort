# ruff: noqa: F811 -- imported pytest fixture
import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest
from casecouncil_api.controller import Controller
from casecouncil_api.verification import verify_packet
from test_casecouncil_protocol import ControlledProvider
from test_casecouncil_store import seeded, start  # noqa: F401


def test_completed_packet_can_be_rechecked_without_calling_provider_again(seeded):
    store, _w, case = seeded
    job = start(store, case)
    provider = ControlledProvider()
    Controller(store, provider).once()
    saved = store.job("owner", job["id"])
    result = verify_packet(saved["packet"], saved["snapshot"])
    assert result["consensus_recomputed"] and result["exact_citations_rechecked"] >= 3
    assert len(provider.prompts) == 8


def test_recheck_rejects_edited_consensus_and_quotes(seeded):
    store, _w, case = seeded
    job = start(store, case)
    Controller(store, ControlledProvider()).once()
    saved = store.job("owner", job["id"])
    packet = json.loads(json.dumps(saved["packet"]))
    packet["consensus"]["confidence_band"] = "high"
    with pytest.raises(ValueError):
        verify_packet(packet, saved["snapshot"])
    packet = json.loads(json.dumps(saved["packet"]))
    packet["synthesis"]["observations"][0]["citations"][0]["quote"] = "invented quote"
    with pytest.raises(ValueError):
        verify_packet(packet, saved["snapshot"])


@pytest.mark.parametrize("failed_stage", [None, "critic"])
def test_replay_verifier_counts_protocols_and_preserves_original_artifacts(seeded, failed_stage):
    store, _w, case = seeded
    job = start(store, case)
    Controller(store, ControlledProvider(fail_stage=failed_stage)).once()
    root = store.root / "reporting"
    (root / "service").mkdir(parents=True)
    with (
        sqlite3.connect(store.root / "casecouncil.sqlite3") as source,
        sqlite3.connect(root / "service/casecouncil.sqlite3") as target,
    ):
        source.backup(target)
    report = {"results": [{"id": "actual-selected-id", "job": job["id"]}]}
    (root / "report.json").write_text(json.dumps(report))
    (root / "selection.json").write_text(json.dumps({"ids": ["actual-selected-id", "pending"]}))
    (root / "verification.json").write_text("preserve previous verification")
    spec = importlib.util.spec_from_file_location(
        "casecouncil_verifier",
        Path(__file__).resolve().parents[1] / "scripts/verify_casecouncil_replay.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = root / "new-verification.json"
    checked = module.verify(root, output)
    assert checked["full_protocols"] == (1 if failed_stage is None else 0)
    assert checked["terminal_packets"] == 1
    assert checked["pending_ids"] == ["pending"]
    assert not checked["protocol_campaign_passed"]
    assert (root / "verification.json").read_text() == "preserve previous verification"
    assert json.loads((root / "report.json").read_text()) == report
    with pytest.raises(FileExistsError):
        module.verify(root, output)
