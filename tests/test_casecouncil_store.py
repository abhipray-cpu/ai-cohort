import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from casecouncil_api.store import LeaseLost, Store

PASSWORD = "a-long-test-password-52"
CONTEXT = {
    "title": "Premium dispute",
    "issues": [{"id": "premium", "title": "Outstanding premium"}],
    "facts": "Customer disputes the premium deduction.",
    "draft": "Investigate the policy and the communications.",
    "missing": [],
}


@pytest.fixture
def seeded(tmp_path):
    s = Store(tmp_path)
    s.bootstrap("owner", PASSWORD)
    w = s.create_workspace("owner", "Test client", "ws")
    s.add_user("owner", "reviewer", PASSWORD)
    s.set_member("owner", w, "reviewer", "reviewer")
    s.set_policy(
        "owner",
        w,
        1,
        {
            "name": "Pilot policy",
            "instructions": "Separate contractual and service issues.",
            "required_documents": ["complaint", "policy"],
            "egress_enabled": True,
        },
    )
    right = s.add_rights(
        "owner",
        w,
        {
            "basis": "owned_test",
            "reference": "Authored software-test fixture only",
            "expires": time.time() + 86400,
            "egress": True,
        },
    )
    case = s.create_case("owner", w, CONTEXT, "case-key")
    s.add_source(
        "owner",
        case["id"],
        1,
        "complaint.txt",
        b"Customer was promised a refund.",
        "complaint",
        right,
        "upload1",
    )
    s.add_source(
        "owner",
        case["id"],
        2,
        "policy.txt",
        b"Policy requires annual premiums after a claim.",
        "policy",
        right,
        "upload2",
    )
    return s, w, case["id"]


def start(s, c, key="start"):
    preview = s.preview("owner", c)
    return s.start("owner", c, preview["binding"], key)


def test_start_is_idempotent_and_bound_to_preview(seeded):
    s, _w, c = seeded
    j = start(s, c)
    assert start(s, c) == j
    before = s.case("owner", c)
    s.update_case("owner", c, before["revision"], {**CONTEXT, "facts": "New material fact"}, "edit")
    assert s.job("owner", j["id"])["state"] == "stale"
    with pytest.raises(ValueError):
        s.start("owner", c, j["binding"], "different-key")
    assert len(s.list_jobs("owner", c)) == 1


def test_one_claim_and_replacement_fencing(seeded):
    s, _w, c = seeded
    start(s, c)
    with ThreadPoolExecutor(4) as p:
        jobs = list(p.map(lambda _: s.claim(lease=1), range(4)))
    assert sum(j is not None for j in jobs) == 1
    a = next(j for j in jobs if j)
    with s.write() as db:
        db.execute("UPDATE jobs SET lease_until=0")
    b = s.claim()
    assert b["token"] != a["token"]
    with pytest.raises(LeaseLost):
        s.checkpoint(a, "proposal:customer", {"value": 1})
    s.checkpoint(b, "proposal:customer", {"value": 2})
    assert s.checkpoints(b)["proposal:customer"] == {"value": 2}


def test_scope_revocation_and_no_idempotency_key_collision(seeded):
    s, w, c = seeded
    s.add_user("owner", "outsider", PASSWORD)
    with pytest.raises(KeyError):
        s.case("outsider", c)
    with pytest.raises(ValueError):
        s.create_case("owner", w, {**CONTEXT, "facts": "different"}, "case-key")
    s.set_member("owner", w, "reviewer", "owner")
    j = start(s, c)
    s.set_member("owner", w, "owner", "analyst")
    assert s.job("owner", j["id"])["state"] == "stale"


def test_budget_survives_restart_unknown_usage_blocks_new_calls(seeded):
    s, w, c = seeded
    start(s, c)
    j = s.claim()
    attempt = s.reserve(j, "proposal:customer", "prompt-digest", 0.1)
    assert Store(s.root).job("owner", j["id"])["calls"] == 1
    s.settle(
        attempt, {"status": "unknown", "usage": None, "elapsed_ms": 10, "tools_audited": False}
    )
    with pytest.raises(ValueError):
        s.reserve(j, "proposal:customer", "again", 0.1)
    assert s.workspace("owner", w)["hold"]


def test_rights_expiry_and_egress_policy_fail_closed(seeded):
    s, _w, c = seeded
    with s.write() as db:
        db.execute("UPDATE rights SET expires=0")
    with pytest.raises(ValueError):
        start(s, c)


def test_checkpoint_content_corruption_is_detected(seeded):
    s, _w, c = seeded
    start(s, c)
    j = s.claim()
    s.checkpoint(j, "test", {"value": 1})
    with s.write() as db:
        db.execute("UPDATE checkpoints SET body='{}'")
    with pytest.raises(ValueError):
        s.checkpoints(j)
