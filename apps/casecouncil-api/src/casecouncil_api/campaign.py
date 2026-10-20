"""Mechanical replay completion, explicitly separate from product acceptance."""

from contracts.casecouncil import ROLES


def limit_store_calls(store, actor, workspace, ceiling, reference):
    """Operator-only monotonic store-wide ceiling, including pre-grant attempts."""
    from . import journal
    from .consensus import digest

    if type(ceiling) is not int or not 1 <= ceiling <= 132 or len(reference) < 20:
        raise ValueError("bounded explicit research-call ceiling required")
    with store.write() as db:
        store._access(db, actor, workspace, {"owner"})
        events = journal.assert_current(db, store.journal_path)
        limits = [e["max_calls"] for e in events if e["kind"] == "campaign_call_limit"]
        if limits and ceiling > min(limits):
            raise ValueError("cumulative ceiling cannot be raised or reset")
        if ceiling < sum(e["kind"] == "reserved" for e in events):
            raise ValueError("ceiling cannot understate already charged attempts")
        if limits and ceiling == min(limits):
            return
        journal.append(
            db,
            store.journal_path,
            {
                "kind": "campaign_call_limit",
                "max_calls": ceiling,
                "actor": actor,
                "reference_hash": digest(reference),
                "includes_preexisting_attempts": True,
            },
        )
        store.record(db, actor, "campaign_call_limit", workspace, detail={"max_calls": ceiling})


def summarize_replay(selected_ids, results):
    selected = list(selected_ids)
    ids = [r["id"] for r in results]
    if len(set(selected)) != len(selected) or len(set(ids)) != len(ids) or set(ids) - set(selected):
        raise ValueError("unique selected cases and at most one result per selected case required")
    full = 0
    artifacts = 0
    unknown = 0
    for result in results:
        calls, known = result["calls"], result["usage_known"]
        if type(calls) is not int or type(known) is not int or not 0 <= known <= calls <= 22:
            raise ValueError("invalid observed call accounting")
        unknown += calls - known
        complete = bool(
            result["state"] == "draft_ready"
            and calls > 0
            and sorted(result["proposers"]) == sorted(ROLES)
            and result["critic_available"] is True
            and sorted(result["ballots"]) == sorted(ROLES)
            and result["synthesis_available"] is True
            and not result["unavailable"]
        )
        artifacts += complete
        full += bool(complete and known == calls and result["all_tools_audited"] is True)
    return {
        "selected": len(selected),
        "terminal_packets": len(results),
        "full_protocols": full,
        "protocol_artifacts_present": artifacts,
        "all_protocol_artifacts_present": bool(selected) and artifacts == len(selected),
        "partial_or_failed": len(results) - full,
        "pending_ids": [i for i in selected if i not in ids],
        "unknown_usage_calls": unknown,
        "protocol_campaign_passed": bool(selected) and full == len(selected),
        "independent_semantic_accuracy": "not_measured",
        "full_product_accepted": False,
    }
