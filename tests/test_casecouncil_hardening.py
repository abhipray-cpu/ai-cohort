# ruff: noqa: F811 -- imported pytest fixture intentionally supplies these arguments
import json
import time

import pytest
from casecouncil_api.consensus import aggregate, registry
from casecouncil_api.controller import Controller
from contracts.casecouncil import ROLES
from test_casecouncil_consensus import proposals, vote
from test_casecouncil_protocol import ControlledProvider
from test_casecouncil_store import PASSWORD, seeded, start  # noqa: F401


def test_registry_tampering_cannot_change_a_frozen_remedy():
    r = registry(dict(zip(ROLES, proposals())), "snapshot")
    ballots = {role: vote(r["candidates"][0]["id"], registry_hash=r["hash"]) for role in ROLES}
    r["candidates"][0]["remedy"] = "Injected new remedy"
    with pytest.raises(ValueError):
        aggregate(["premium"], r, ballots, [])


def test_source_write_denied_before_untrusted_parser_runs(seeded, monkeypatch):
    s, w, c = seeded
    s.add_user("owner", "viewer", PASSWORD)
    s.set_member("owner", w, "viewer", "viewer")

    def parser(*args):
        raise AssertionError("Unauthorized parser invocation")

    monkeypatch.setattr("casecouncil_api.store.extract", parser)
    with pytest.raises(PermissionError):
        s.add_source("viewer", c, 3, "bad.pdf", b"%PDF", "other", "fake", "denied")


def test_unknown_usage_receipt_shape_does_not_clear_a_reservation(seeded):
    s, w, c = seeded
    start(s, c)
    j = s.claim()
    aid = s.reserve(j, "test", "prompt")
    s.settle(
        aid,
        {
            "usage": {"input_tokens": -1, "output_tokens": 0},
            "tools_audited": True,
            "elapsed_ms": 1,
            "status": "returned",
        },
    )
    assert s.workspace("owner", w)["hold"]


def test_snapshot_body_corruption_is_not_a_new_authorized_input(seeded):
    s, _w, c = seeded
    start(s, c)
    j = s.claim()
    snapshot = json.loads(j["snapshot"])
    snapshot["context"]["facts"] = "An injected material fact"
    with s.write() as db:
        db.execute("UPDATE jobs SET snapshot=?", (json.dumps(snapshot),))
    with pytest.raises(ValueError):
        s.reserve(j, "test", "prompt")


def test_error_after_expiry_does_not_crash_or_modify_replacement(seeded):
    s, _w, c = seeded
    start(s, c)
    provider = ControlledProvider()

    def failure(**kwargs):
        with s.write() as db:
            db.execute("UPDATE jobs SET token='replacement',lease_until=?", (time.time() + 600,))
        raise RuntimeError("simulated late network failure")

    provider.generate = failure
    assert Controller(s, provider).once()
    with s.connect() as db:
        row = dict(db.execute("SELECT * FROM jobs").fetchone())
    assert row["state"] == "running" and row["token"] == "replacement"
    assert not row["packet"]


def test_automatic_rights_expiry_stales_job_instead_of_crash_loop(seeded):
    s, _w, c = seeded
    j = start(s, c)
    p = ControlledProvider()
    original = p.generate

    def expire(**kwargs):
        with s.write() as db:
            db.execute("UPDATE rights SET expires=0")
        return original(**kwargs)

    p.generate = expire
    assert Controller(s, p).once()
    with s.connect() as db:
        row = dict(db.execute("SELECT * FROM jobs WHERE id=?", (j["id"],)).fetchone())
    assert row["state"] == "stale"


def test_cancelled_job_retains_receipts_but_cannot_publish(seeded):
    s, _w, c = seeded
    j = start(s, c)
    p = ControlledProvider()
    original = p.generate

    def cancel(**kwargs):
        s.cancel("owner", j["id"])
        return original(**kwargs)

    p.generate = cancel
    Controller(s, p).once()
    row = s.job("owner", j["id"])
    assert row["state"] == "cancelled" and row["packet"] is None and row["attempts"][0]["receipt"]


def test_membership_retry_is_naturally_idempotent(seeded):
    s, w, c = seeded
    start(s, c)
    s.set_member("owner", w, "reviewer", "reviewer")
    assert s.list_jobs("owner", c)[0]["state"] == "queued"


def test_unsettled_call_prevents_a_second_provider_invocation(seeded):
    s, _w, c = seeded
    start(s, c)
    j = s.claim()
    s.reserve(j, "one", "prompt")
    with pytest.raises(ValueError):
        s.reserve(j, "two", "prompt")


def test_four_crashed_claims_publish_available_work_as_a_manual_packet(seeded):
    s, _w, c = seeded
    j = start(s, c)
    for attempt in range(4):
        claimed = s.claim()
        if attempt == 0:
            s.checkpoint(claimed, "proposal:customer", {"value": proposals()[0].model_dump()})
        with s.write() as db:
            db.execute("UPDATE jobs SET lease_until=0")
    assert s.claim() is None
    saved = s.job("owner", j["id"])
    assert saved["state"] == "manual_required" and saved["packet"]["proposals"]["customer"]


def test_corrupt_checkpoint_cannot_trap_exhausted_claim_in_infinite_recovery(seeded):
    s, _w, c = seeded
    j = start(s, c)
    claimed = s.claim()
    s.checkpoint(claimed, "proposal:customer", {"value": proposals()[0].model_dump()})
    with s.write() as db:
        db.execute("UPDATE jobs SET claims=4,lease_until=0")
        db.execute("UPDATE checkpoints SET body='{}'")
    assert s.claim() is None
    with s.connect() as db:
        row = db.execute("SELECT state,error,packet FROM jobs WHERE id=?", (j["id"],)).fetchone()
    assert row["state"] == "failed" and row["error"] == "checkpoint_integrity"
    assert row["packet"] is None
