"""Day 9 deterministic requirements: written before the product modules."""

import itertools

import pytest
from casecouncil_api.consensus import aggregate, digest, registry
from contracts.casecouncil import ROLES, Ballot, Candidate, Citation, Proposal


def option(remedy="Review the disputed premium", disposition="partial_uphold"):
    return Candidate(
        issue_id="premium",
        disposition=disposition,
        remedy=remedy,
        conditions=[],
        rationale="Policy and service handling require separate consideration.",
        counterargument="The service evidence may support a different resolution.",
        citations=[Citation(source_id="s", start=0, end=6, quote="Policy")],
        missing=[],
    )


def proposals():
    return [Proposal(issues=[option()], new_issues=[], critique_responses=[]) for _ in ROLES]


def vote(candidate, binding="snapshot", registry_hash="registry"):
    return Ballot(
        snapshot=binding,
        registry_hash=registry_hash,
        issues=[
            {
                "issue_id": "premium",
                "candidate_id": candidate,
                "reason": "Supported by the policy evidence",
                "missing": [],
            }
        ],
    )


def test_registry_merges_only_exact_candidates_and_keeps_lineage():
    p = proposals()
    p[2].issues[0].remedy = "Request a different material remedy"
    r = registry(dict(zip(ROLES, p)), "snapshot")
    assert len(r["candidates"]) == 2
    assert sorted(len(c["roles"]) for c in r["candidates"]) == [1, 2]
    assert r == registry(dict(reversed(list(zip(ROLES, p)))), "snapshot")


@pytest.mark.parametrize("choices", list(itertools.product(("A", "B", None), repeat=3)))
def test_fixed_denominator_and_order_independence(choices):
    candidates = {k: {**option().model_dump(), "id": k, "roles": list(ROLES)} for k in ("A", "B")}
    r = {"snapshot": "snapshot", "hash": "registry", "candidates": list(candidates.values())}
    r["hash"] = digest({k: v for k, v in r.items() if k != "hash"})
    ballots = {role: vote(c, registry_hash=r["hash"]) for role, c in zip(ROLES, choices)}
    a = aggregate(["premium"], r, ballots, [])
    assert a == aggregate(["premium"], r, dict(reversed(list(ballots.items()))), [])
    result = a["issues"][0]
    assert result["denominator"] == 3
    count = max(choices.count("A"), choices.count("B"))
    assert result["status"] == (
        "unanimous_agreement"
        if count == 3
        else "majority_agreement"
        if count == 2
        else "no_consensus"
    )


def test_unavailable_role_and_critical_blocker_cannot_be_outvoted():
    r = registry(dict(zip(ROLES, proposals())), "snapshot")
    cid = r["candidates"][0]["id"]
    ballots = {role: vote(cid, registry_hash=r["hash"]) for role in ROLES}
    missing = aggregate(["premium"], r, {k: v for k, v in ballots.items() if k != ROLES[2]}, [])
    assert missing["issues"][0]["status"] == "insufficient_participation"
    blocked = aggregate(["premium"], r, ballots, ["Missing decisive policy"])
    assert blocked["issues"][0]["status"] == "agreement_blocked"
    assert blocked["confidence_band"] == "low"


def test_unknown_stale_and_extra_role_ballots_rejected():
    r = registry(dict(zip(ROLES, proposals())), "snapshot")
    cid = r["candidates"][0]["id"]
    for ballots in (
        {ROLES[0]: vote("forged", registry_hash=r["hash"])},
        {ROLES[0]: vote(cid, binding="old", registry_hash=r["hash"])},
        {"critic": vote(cid, registry_hash=r["hash"])},
    ):
        with pytest.raises(ValueError):
            aggregate(["premium"], r, ballots, [])


def test_strict_contract_has_no_model_vote_weight_or_probability():
    with pytest.raises(ValueError):
        vote("A").model_copy().model_validate({**vote("A").model_dump(), "weight": 99})
    with pytest.raises(ValueError):
        option().model_validate({**option().model_dump(), "confidence": float("nan")})


def test_candidate_missing_evidence_cannot_disappear_in_the_ballot():
    p = proposals()
    for proposal in p:
        proposal.issues[0].missing = ["Decisive original communication missing"]
    r = registry(dict(zip(ROLES, p)), "snapshot")
    ballots = {role: vote(r["candidates"][0]["id"], registry_hash=r["hash"]) for role in ROLES}
    result = aggregate(["premium"], r, ballots, [])
    assert result["issues"][0]["status"] == "agreement_blocked"
