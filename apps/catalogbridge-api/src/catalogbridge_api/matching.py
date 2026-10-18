"""Conservative retrieval and source-level constraints; no gold-aware features."""

import hashlib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from contracts.catalogbridge import Product, Proposal

POLICY_VERSION = "catalogbridge-v3-runtime"
PROMPT_VERSION = "catalogbridge-pair-v3-instruction-profiles"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


@lru_cache(maxsize=20000)
def words(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    tokens = set(re.findall(r"[^\W_]+", text))
    # Preserve a compact identifier alongside components (AB-123 / AB123).
    tokens.update(re.sub(r"[\W_]+", "", x) for x in re.findall(r"\w+(?:[-./]\w+)+", text))
    return frozenset(tokens)


def attributes(row: Product):
    text = row.title.casefold()
    result = {}
    for key, pattern in {
        "capacity": r"\b\d+(?:\.\d+)?\s*(?:gb|tb|mb)\b",
        "form_factor": r"\b(?:sodimm|udimm|rdimm)\b",
        "pack": r"\b\d+\s*(?:pack|pk)\b",
        "condition": r"\b(?:refurbished|renewed|used|new)\b",
    }.items():
        matches = re.findall(pattern, text)
        # Title identifies the SKU; descriptions often enumerate the entire
        # range. Only fall back when the title supplies no such attribute.
        if not matches and key != "condition":
            matches = re.findall(pattern, row.description.casefold())
        found = sorted({re.sub(r"\s+", "", x) for x in matches})
        if found:
            result[key] = found
    if row.brand:
        result["brand"] = [
            re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", row.brand).casefold())
        ]
    if row.model:
        result["model"] = [row.model.casefold()]
    return result


def conflicts(left: Product, right: Product):
    a, b = attributes(left), attributes(right)
    return sorted(k for k in a.keys() & b.keys() if a[k] != b[k])


def candidates(query: Product, gallery: list[Product], limit=10):
    if limit <= 0:
        return []
    # Retrieval is assessment, never identity acceptance. A sole master record
    # must remain assessable even across languages with no shared title words.
    if len(gallery) == 1:
        return list(gallery)
    terms = words(query.title + " " + query.brand + " " + query.model)
    ranked = []
    for row in gallery:
        other = words(row.title + " " + row.brand + " " + row.model)
        score = len(terms & other) / max(1, len(terms | other))
        if query.gtin and query.gtin == row.gtin:
            score += 2
        if score > 0:
            ranked.append((score, row))
    return [row for _, row in sorted(ranked, key=lambda x: (-x[0], x[1].id))[:limit]]


def validate_proposal(proposal: Proposal, supplier: Product, gallery: list[Product]):
    candidate = next((r for r in gallery if r.id == proposal.candidate_id), None)
    if candidate is None:
        raise ValueError("foreign candidate")
    sides = set()
    for cite in proposal.evidence:
        record = supplier if cite.side == "supplier" else candidate
        if cite.quote not in getattr(record, cite.field):
            raise ValueError("evidence quote mismatch")
        sides.add(cite.side)
    if sides != {"supplier", "candidate"}:
        raise ValueError("both evidence sides required")
    if proposal.outcome == "same_product" and conflicts(supplier, candidate):
        raise ValueError("conflicting variant attributes")
    return candidate


def draft_key(spec, supplier, master_hash, selected):
    return digest(
        {
            "version": "exact-review-draft-v1",
            "binding": binding(spec),
            "supplier": supplier.model_dump(),
            "master_hash": master_hash,
            "selected": [row.model_dump() for row in selected],
        }
    )


def binding(spec):
    return digest(
        {
            "models": [spec.economy_model, spec.strong_model],
            "instruction_profile": spec.instruction_profile,
            "routing_policy": spec.routing_policy,
            "local_router_sha256": spec.local_router_sha256,
            "classifier_instructions_sha256": hashlib.sha256(
                Path(__file__).with_name("classifier_instructions.txt").read_bytes()
            ).hexdigest(),
            "policy": POLICY_VERSION,
            "prompt": PROMPT_VERSION,
            "retrieval": "normalized-lexical-v2-k10",
            "code_hashes": {
                name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                for name in (
                    "matching.py",
                    "model_boundary.py",
                    "worker.py",
                    "runtime.py",
                    "store.py",
                    "local_router.py",
                )
            },
        }
    )
