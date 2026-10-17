"""Extractive factual boundary, not a claim of automatic paraphrase entailment.

Only original quoted source text is published as a factual finding. Model planning
prose is not a source and is never published as a factual summary. Human review
still assesses relevance, contradiction, context and completeness.
"""


def quote_span(source, requested):
    start = source.find(requested)
    if start >= 0:
        return start, start + len(requested)
    # Models may render CRLF as LF. Resolve back to exact ORIGINAL offsets;
    # no other whitespace/case/Unicode equivalence is silently accepted.
    normalized = []
    positions = []
    for i, char in enumerate(source):
        if char == "\r" and i + 1 < len(source) and source[i + 1] == "\n":
            continue
        normalized.append(char)
        positions.append(i)
    needle = requested.replace("\r\n", "\n")
    start = "".join(normalized).find(needle)
    if start < 0 or not needle:
        raise ValueError("Claim is not an exact cited source quote")
    left = positions[start]
    right = positions[start + len(needle) - 1] + 1
    if source[left : left + 1] == "\n" and left > 0 and source[left - 1] == "\r":
        left -= 1
    return left, right


def validate_claims(reply, hits):
    lookup = {h["id"]: h for h in hits}
    for claim in reply.claims:
        if len(claim.memory_ids) != 1 or claim.memory_ids[0] not in lookup:
            raise ValueError("Unknown memory reference")
        hit = lookup[claim.memory_ids[0]]
        quote_span(hit["evidence"]["quote"], claim.text)


def publish_reply(reply, hits):
    validate_claims(reply, hits)
    lookup = {h["id"]: h for h in hits}
    claims = []
    for claim in reply.claims:
        hit = lookup[claim.memory_ids[0]]
        e = hit["evidence"]
        left, right = quote_span(e["quote"], claim.text)
        claims.append(
            {
                "text": e["quote"][left:right],
                "memory_ids": claim.memory_ids,
                "attribution": {
                    "author": hit["author"],
                    "state": hit["state"],
                    "available_at": hit["available_at"],
                    "source_type": hit.get("source_type", "source_record"),
                },
                "citations": [
                    {
                        "source_id": e["source_id"],
                        "source_revision": e["source_revision"],
                        "sha256": e["sha256"],
                        "start": e["start"] + left,
                        "end": e["start"] + right,
                        "quote": e["quote"][left:right],
                    }
                ],
            }
        )
    return {
        "summary": f"{len(claims)} source-linked participant quotation(s). Reports and proposals are not independent technical verification."
        if claims
        else "No source-supported answer was extracted. Review the evidence and clarify the question.",
        "claims": claims,
        "questions": reply.questions,
        "limitations": reply.limitations,
        "answer_state": "quoted_evidence" if claims else "abstained",
        "grounding_policy": "exact-attributed-source-quotes-2",
        "semantic_paraphrase_verified": False,
    }
