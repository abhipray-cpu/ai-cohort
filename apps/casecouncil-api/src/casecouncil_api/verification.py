"""Read-only packet rechecks; mechanical evidence is not independent semantic accuracy."""

from contracts.casecouncil import Citation

from .consensus import aggregate, registry
from .evidence import validate_citations


def verify_packet(packet, snapshot, incidents=None):
    if packet["binding"] != snapshot["binding"]:
        raise ValueError("packet snapshot binding mismatch")
    proposals = packet["proposals"]
    expected = registry(proposals, snapshot["binding"])
    if expected != packet["registry"]:
        raise ValueError("frozen registry mismatch")
    blockers = list(snapshot["blockers"])
    findings = (packet.get("critique") or {}).get("findings", [])
    blockers += [
        "Critic " + f["id"] + ": " + f["reason"]
        for f in findings
        if f["severity"] in {"material", "critical"}
    ]
    blockers += ["Unassessed issue: " + i for p in proposals.values() for i in p["new_issues"]]
    # Controller computes consensus before a subsequent synthesis failure.
    blockers += [
        "Stage unavailable: " + s for s in packet.get("unavailable", []) if s != "synthesis"
    ]
    computed = aggregate(
        [i["id"] for i in snapshot["context"]["issues"]], expected, packet["ballots"], blockers
    )
    if computed != packet["consensus"]:
        raise ValueError("consensus recomputation mismatch")
    cited = [i for p in proposals.values() for i in p["issues"]] + findings
    cited += (packet.get("synthesis") or {}).get("observations", [])
    count = 0
    for item in cited:
        citations = [Citation.model_validate(c) for c in item.get("citations", [])]
        validate_citations(citations, snapshot["evidence"])
        count += len(citations)
    requirements = set(packet["review_requirements"])
    notices = packet.get("incident_notices", [])
    if incidents is not None and notices != incidents:
        raise ValueError("runtime incident notices differ from operator authority")
    if notices and "runtime_incident" not in requirements:
        raise ValueError("runtime incident lost from human review requirements")
    if not {f["id"] for f in findings if f["severity"] in {"material", "critical"}} <= requirements:
        raise ValueError("critic findings lost from review")
    if snapshot["blockers"] and any(i["qualified"] for i in computed["issues"]):
        raise ValueError("evidence blocker overridden")
    if packet.get("approved") is not False:
        raise ValueError("AI packet claims approval")
    return {
        "exact_citations_rechecked": count,
        "consensus_recomputed": True,
        "critic_findings_retained": True,
        "independent_semantic_accuracy": "not_measured",
    }
