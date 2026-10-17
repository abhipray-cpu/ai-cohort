"""Authorized-first batched cosine recall. No global top-k or stale vector authority."""

import re
from datetime import datetime

import numpy as np

from relaydesk_api.common import now
from relaydesk_api.embeddings import validate_vector


def index_case(store, actor, cid, encoder, check=lambda: None, limit=10000):
    store.case(actor, cid, "investigator")
    memories = store.memories(actor, cid)
    with store.connect() as db:
        existing = {
            (r[0], r[1])
            for r in db.execute(
                "SELECT DISTINCT v.memory_id,v.revision FROM vectors v JOIN memories m ON m.id=v.memory_id WHERE m.case_id=? AND v.model=?",
                (cid, encoder.fingerprint),
            )
        }
    saved = 0
    stale = 0
    for memory in memories:
        if saved >= limit:
            break
        if (memory["id"], memory["revision"]) in existing:
            continue
        check()
        store.case(actor, cid, "investigator")
        chunks = encoder.chunks(memory["body"])
        vectors = encoder.encode([c[2] for c in chunks])
        check()
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            store.case(actor, cid, "investigator")
            current = db.execute("SELECT * FROM memories WHERE id=?", (memory["id"],)).fetchone()
            source = db.execute(
                "SELECT * FROM sources WHERE id=?", (memory["source_id"],)
            ).fetchone()
            if (
                not current
                or not source
                or current["revision"] != memory["revision"]
                or current["state"] in ("erased", "suppressed", "superseded")
                or source["erased"]
                or not source["active"]
                or source["sha256"] != memory["source_hash"]
            ):
                stale += 1
                continue
            store.validate_source(source)
            for chunk, vector in zip(chunks, vectors, strict=True):
                db.execute(
                    "INSERT OR REPLACE INTO vectors VALUES(?,?,?,?,?,?)",
                    (
                        memory["id"],
                        memory["revision"],
                        chunk[0],
                        chunk[1],
                        encoder.fingerprint,
                        validate_vector(vector).tobytes(),
                    ),
                )
            saved += 1
    if saved or stale:
        store.event(
            cid,
            "vectors_published",
            {"memories": saved, "stale_skipped": stale, "model": encoder.fingerprint},
        )
    return {
        "saved": saved,
        "eligible": len(memories),
        "omitted": max(0, len(memories) - limit),
        "stale_skipped": stale,
    }


def terms(text):
    return set(re.findall(r"[a-z0-9][a-z0-9_.-]{1,}", text.lower()))


class RecallEngine:
    def __init__(self, store, encoder=None):
        self.store, self.encoder = store, encoder

    def search(self, actor, cid, request):
        scope = self.store.case(actor, cid)
        if scope["revision"] < request.minimum_revision:
            raise ValueError("Requested revision is not available")
        memories = self.store.memories(
            actor, cid, as_of=request.as_of, history=request.history, account=True
        )
        # Current intent is already supplied separately; it cannot support itself.
        excluded = [
            m
            for m in memories
            if m.get("source_key", "").startswith("turn:")
            and m["body"].strip() == request.question.strip()
        ]
        excluded_ids = {m["id"] for m in excluded}
        memories = [m for m in memories if m["id"] not in excluded_ids]
        eligible = len(memories)
        memories = memories[-10000:]
        lookup = {m["id"]: m for m in memories}
        best = {}
        if self.encoder and memories:
            query = self.encoder.query(request.question)
            # Temporary authorization relation contains only the already-scoped,
            # current/eligible memory revisions. Unauthorized rows are never scored.
            with self.store.connect() as db:
                db.execute(
                    "CREATE TEMP TABLE authorized_recall(id TEXT PRIMARY KEY,revision INTEGER)"
                )
                db.executemany(
                    "INSERT INTO authorized_recall VALUES(?,?)",
                    [(m["id"], m["revision"]) for m in memories],
                )
                rows = db.execute(
                    "SELECT v.* FROM vectors v JOIN authorized_recall a ON a.id=v.memory_id AND a.revision=v.revision WHERE v.model=?",
                    (self.encoder.fingerprint,),
                ).fetchall()
            if rows:
                if any(len(r["value"]) != 384 * 4 for r in rows):
                    raise ValueError("Invalid vector byte size")
                matrix = np.stack([np.frombuffer(r["value"], dtype=np.float32) for r in rows])
                if not np.isfinite(matrix).all() or not np.allclose(
                    np.linalg.norm(matrix, axis=1), 1, atol=0.002
                ):
                    raise ValueError("Invalid normalized vector batch")
                scores = np.clip(matrix @ query, -1, 1)
                for row, score in zip(rows, scores, strict=True):
                    m = lookup[row["memory_id"]]
                    if not 0 <= row["start"] < row["end"] <= len(m["body"]):
                        raise ValueError("Invalid vector chunk span")
                    value = (float(score), row["start"], row["end"])
                    if m["id"] not in best or value > best[m["id"]]:
                        best[m["id"]] = value
        query_terms = terms(request.question)
        cutoff = datetime.fromisoformat(request.as_of or now())
        ranked = []
        tokens = {}
        for m in memories:
            # Call-local deduplication avoids repeated tokenization without keeping
            # erased plaintext in a process-global cache.
            key = (m["source_hash"], m["body"])
            if key not in tokens:
                tokens[key] = terms(m["body"])
            lexical = len(query_terms & tokens[key]) / max(1, len(query_terms))
            semantic = best.get(m["id"], (0, 0, 0))[0]
            if semantic < 0.25 and lexical < 0.15:
                continue
            age = max(
                0, (cutoff - datetime.fromisoformat(m["available_at"])).total_seconds() / 86400
            )
            recency = 1 / (1 + age / 90)
            status = 1 if m["state"] == "reported" else 0.5 if m["state"] == "proposed" else 0.25
            score = 0.65 * max(0, semantic) + 0.28 * lexical + 0.04 * recency + 0.03 * status
            ranked.append(
                (
                    score,
                    m["id"],
                    m,
                    {
                        "semantic": round(semantic, 4),
                        "lexical": round(lexical, 4),
                        "recency": round(recency, 4),
                        "status": status,
                        "rank": round(score, 4),
                    },
                )
            )
        ranked.sort(key=lambda row: (-row[0], row[1]))
        hits = []
        for _, mid, m, scores in ranked[: request.limit]:
            start, end = m["start"], m["end"]
            full_length = end - start
            chunk = best.get(mid)
            # Raw episodes have identical body/source coordinates. Proposals use
            # their original quoted source span, never offsets into model prose.
            if chunk and m["body"] == m["source_body"][start:end]:
                start += chunk[1]
                end = m["start"] + chunk[2]
            end = min(end, start + 2500)
            quote = m["source_body"][start:end]
            if not quote:
                raise ValueError("Empty source evidence span")
            hits.append(
                {
                    "id": mid,
                    "revision": m["revision"],
                    "kind": m["kind"],
                    "state": m["state"],
                    "body": quote,
                    "available_at": m["available_at"],
                    "author": m["author"],
                    "case_id": m["case_id"],
                    "source_type": "conversation"
                    if m.get("source_key", "").startswith("turn:")
                    else "source_record",
                    "scores": scores,
                    "evidence": {
                        "source_id": m["source_id"],
                        "source_revision": m["source_revision"],
                        "start": start,
                        "end": end,
                        "quote": quote,
                        "sha256": m["source_hash"],
                        "full_memory_span_characters": full_length,
                        "excerpted": end - start < full_length,
                    },
                }
            )
        latest = self.store.case(actor, cid)
        if (
            latest["revision"] != scope["revision"]
            or latest["account_revision"] != scope["account_revision"]
        ):
            raise ValueError("Case changed during recall; retry latest revision")
        for origin in {h["case_id"] for h in hits}:
            self.store.case(actor, origin)
        mode = (
            "semantic_hybrid"
            if self.encoder and len(best) == len(memories)
            else "semantic_partial"
            if self.encoder and best
            else "lexical_only"
        )
        return {
            "hits": hits,
            "mode": mode,
            "revision": scope["revision"],
            "account_revision": scope["account_revision"],
            "epoch": self.store.setting("epoch"),
            "policy": "hybrid-initial-2-uncalibrated",
            "as_of": request.as_of,
            "coverage": {
                "eligible": eligible,
                "indexed": len(best),
                "candidates": len(ranked),
                "selected": len(hits),
                "omitted": max(0, eligible - len(hits)),
                "current_intent_excluded": len(excluded),
            },
            "limitations": [
                "Rank scores are not correctness probabilities.",
                "Participant reports and model proposals are not technical verification.",
            ]
            + (
                ["Semantic recall unavailable or not fully indexed"]
                if mode != "semantic_hybrid"
                else []
            )
            + (["Eligible vector scope capped at 10000"] if eligible > 10000 else [])
            + (
                ["Selected evidence uses exact excerpts; full source records remain available."]
                if any(h["evidence"]["excerpted"] for h in hits)
                else []
            ),
        }
