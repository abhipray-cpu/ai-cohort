"""Pure fixed-roster voting. Model confidence is deliberately not a voting weight."""

import hashlib
import json
from collections import Counter

from contracts.casecouncil import ROLES, Ballot, Proposal


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def registry(proposals, snapshot):
    if set(proposals) != set(ROLES):
        raise ValueError("full proposer roster required")
    candidates = {}
    for role in ROLES:
        proposal = Proposal.model_validate(proposals[role])
        for candidate in proposal.issues:
            value = candidate.model_dump()
            ident = digest(value)[:24]
            candidates.setdefault(ident, {**value, "id": ident, "roles": []})["roles"].append(role)
    value = {"snapshot": snapshot, "candidates": [candidates[k] for k in sorted(candidates)]}
    return {**value, "hash": digest(value)}


def aggregate(issues, registry, ballots, blockers):
    if registry["hash"] != digest({k: v for k, v in registry.items() if k != "hash"}):
        raise ValueError("registry integrity")
    if set(ballots) - set(ROLES):
        raise ValueError("forged voter")
    candidates = {c["id"]: c for c in registry["candidates"]}
    parsed = {}
    for role, raw in ballots.items():
        ballot = Ballot.model_validate(raw)
        if ballot.snapshot != registry["snapshot"] or ballot.registry_hash != registry["hash"]:
            raise ValueError("stale ballot")
        if sorted(c.issue_id for c in ballot.issues) != sorted(issues):
            raise ValueError("ballot must cover each issue exactly once")
        for choice in ballot.issues:
            if choice.candidate_id is not None and (
                choice.candidate_id not in candidates
                or candidates[choice.candidate_id]["issue_id"] != choice.issue_id
            ):
                raise ValueError("unknown candidate")
        parsed[role] = {c.issue_id: c for c in ballot.issues}
    result = []
    all_blockers = list(blockers)
    for issue in issues:
        choices = {role: parsed[role][issue].model_dump() for role in ROLES if role in parsed}
        missing = sorted({m for c in choices.values() for m in c["missing"]})
        local_blockers = sorted(set(blockers + missing))
        counts = Counter(c["candidate_id"] for c in choices.values() if c["candidate_id"])
        winner = max(sorted(counts), key=counts.get) if counts else None
        n = counts[winner] if winner else 0
        if winner and n >= 2:
            local_blockers = sorted(set(local_blockers + candidates[winner]["missing"]))
        status = (
            "insufficient_participation"
            if len(parsed) != 3
            else "agreement_blocked"
            if local_blockers and n >= 2
            else "unanimous_agreement"
            if n == 3
            else "majority_agreement"
            if n == 2
            else "no_consensus"
        )
        qualified = status in {"unanimous_agreement", "majority_agreement"}
        if winner and candidates[winner]["disposition"] == "undetermined":
            qualified = False
            local_blockers += candidates[winner]["missing"]
        all_blockers.extend(local_blockers)
        result.append(
            {
                "issue_id": issue,
                "status": status,
                "winner": winner if n >= 2 else None,
                "votes": dict(sorted(counts.items())),
                "denominator": 3,
                "ballots": choices,
                "blockers": sorted(set(local_blockers)),
                "qualified": qualified,
                "route": "ready_for_human_review"
                if qualified
                else "escalate"
                if status == "insufficient_participation"
                else "request_evidence"
                if local_blockers
                else "escalate",
            }
        )
    return {
        "issues": result,
        "confidence_band": "medium" if all(i["qualified"] for i in result) else "low",
        "calibration_status": "unqualified",
        "blockers": sorted(set(all_blockers)),
        "roster": list(ROLES),
        "registry_hash": registry["hash"],
    }
