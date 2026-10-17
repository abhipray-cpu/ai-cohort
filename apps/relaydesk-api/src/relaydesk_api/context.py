"""Bounded serialized, source-preserving compression; full omission ledger stays outside prompts."""

import json

from relaydesk_api.common import digest

CATEGORIES = (
    "environment",
    "attempt",
    "outcome",
    "workaround",
    "hypothesis",
    "decision",
    "commitment",
    "open_question",
    "episode",
)


def build_buffer(rows, budget=6000):
    chosen = []
    used = 0
    for row in reversed(rows):
        projected = {
            k: row[k]
            for k in ["id", "role", "body", "seq", "source_id", "output_id", "session_id"]
            if k in row
        }
        size = len(json.dumps(projected, ensure_ascii=False)) + 2
        if used + size + 100 > budget:
            break
        chosen.append(projected)
        used += size
    return {
        "messages": list(reversed(chosen)),
        "omitted": len(rows) - len(chosen),
        "characters": used,
        "budget": budget,
    }


def compress(memories, budget=6000, *, allowed_ids=None):
    groups = {kind: [] for kind in CATEGORIES}
    selected = []
    critical = {"environment", "attempt", "outcome", "commitment", "open_question", "workaround"}
    ordered = sorted(
        memories, key=lambda m: (m["kind"] not in critical, m.get("available_at", ""), m["id"])
    )
    scope_hash = digest(
        [(m["id"], m.get("revision"), m.get("source_hash"), m["state"]) for m in memories]
    )

    def result():
        selected_set = set(selected)
        omitted = [m["id"] for m in memories if m["id"] not in selected_set]
        value = {
            "groups": groups,
            "coverage": {
                "total": len(memories),
                "selected": len(selected),
                "omitted": len(omitted),
            },
            "omitted_ids": omitted[:8],
            "omission_ledger": {
                "count": len(omitted),
                "sample_count": min(8, len(omitted)),
                "sample_complete": len(omitted) <= 8,
                "sha256": digest(omitted),
                "lookup": "Authorized case memory ledger at the pinned case revision",
            },
            "status": "partial" if omitted else "complete_for_declared_scope",
            "characters": 0,
            "policy": "serialized-source-preserving-selection-2",
            "source_hash": scope_hash,
        }
        for _ in range(3):
            value["characters"] = len(json.dumps(value, ensure_ascii=False))
        return value

    # Tiny legacy unit budgets can be smaller than the fixed envelope itself.
    # The envelope stays bounded; no critical fact is claimed to be included.
    empty = result()
    if empty["characters"] > budget:
        empty["groups"] = {}
        empty["omitted_ids"] = []
        empty["omission_ledger"] = {
            "count": len(memories),
            "sha256": digest([m["id"] for m in memories]),
            "sample_complete": False,
        }
        for _ in range(3):
            empty["characters"] = len(json.dumps(empty, ensure_ascii=False))
        if empty["characters"] > budget:
            raise ValueError("Compression budget below minimum coverage envelope")
        return empty
    used = empty["characters"]
    for memory in ordered:
        if allowed_ids is not None and memory["id"] not in allowed_ids:
            continue
        item = {k: memory[k] for k in ["id", "body", "state", "source_id"]}
        item.update({k: memory[k] for k in ["author", "available_at"] if k in memory})
        if used + len(json.dumps(item, ensure_ascii=False)) + 10 > budget:
            continue
        groups[memory["kind"]].append(item)
        selected.append(memory["id"])
        candidate = result()
        if candidate["characters"] > budget:
            groups[memory["kind"]].pop()
            selected.pop()
        else:
            used = candidate["characters"]
        # Once enough room is occupied, skip overlong items but retain the full denominator.
    return result()
