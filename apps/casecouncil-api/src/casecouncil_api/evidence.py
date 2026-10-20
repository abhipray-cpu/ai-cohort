"""Bounded extraction and exact redacted-Unicode evidence, never executable content."""

import hashlib
import json
import re
import subprocess
import sys


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def redact(text):
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    text = re.sub(r"(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)", "[REDACTED]", text)
    text = re.sub(
        r"(?i)((?:password|token|secret|authorization|api[_-]?key)\s*[:=]\s*)([^\s,;]+)",
        r"\1[REDACTED]",
        text,
    )
    text = re.sub(
        r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----",
        "[REDACTED PRIVATE KEY]",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED EMAIL]", text)
    return "".join(c for c in text if c in "\n\t" or ord(c) >= 32)


def extract(ident, name, raw):
    if not name or len(name) > 150 or any(c in name for c in "/\\\r\n\x00"):
        raise ValueError("unsafe filename")
    if name.lower().endswith(".pdf"):
        if len(raw) > 10 * 1024 * 1024 or not raw.startswith(b"%PDF"):
            raise ValueError("invalid PDF input")
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "casecouncil_api.pdf_worker"],
                input=raw,
                capture_output=True,
                timeout=20,
                check=False,
            )
            if completed.returncode or len(completed.stdout) > 8_000_000:
                raise ValueError("PDF extraction failed")
            result = json.loads(completed.stdout)
            text = result["text"]
            pages = result["pages"]
            partial = result["partial"]
        except (subprocess.TimeoutExpired, OSError, ValueError, KeyError) as exc:
            raise ValueError("PDF extraction unavailable or unsupported") from exc
    elif name.lower().endswith(".txt") and len(raw) <= 1024 * 1024:
        text = raw.decode("utf-8", errors="strict")
        pages = 0
        partial = False
    else:
        raise ValueError("supported formats: text PDF and UTF-8 txt")
    if not text.strip() or len(text) > 1_000_000:
        raise ValueError("empty or excessive extracted text")
    clean = redact(text)
    return {
        "id": ident,
        "name": name,
        "original_hash": sha(raw),
        "text_hash": sha(clean.encode()),
        "text": clean,
        "pages": pages,
        "partial": partial,
        "bytes": len(raw),
        "mapping": "redacted canonical Unicode offsets; not raw PDF offsets",
    }


def evidence_for(sources):
    spans = []
    partial = not sources
    budget = 64000 // max(1, len(sources))
    for s in sources:
        text = s["text"]
        if sha(text.encode()) != s["text_hash"]:
            raise ValueError("source integrity failure")
        partial |= s["partial"] or len(text) > budget
        # Equal per-document selection prevents one document crowding out the rest.
        # Long sources retain head and tail, with explicit omitted coverage.
        ranges = (
            [(0, len(text))]
            if len(text) <= budget
            else [(0, budget // 2), (len(text) - (budget - budget // 2), len(text))]
        )
        for lo, hi in ranges:
            for start in range(lo, hi, 800):
                end = min(start + 800, hi)
                spans.append(
                    {"source_id": s["id"], "start": start, "end": end, "text": text[start:end]}
                )
    return {
        "sources": sources,
        "spans": spans,
        "partial": bool(partial),
        "selected_chars": sum(len(s["text"]) for s in spans),
        "total_chars": sum(len(s["text"]) for s in sources),
    }


def validate_citations(citations, evidence):
    sources = {s["id"]: s for s in evidence["sources"]}
    for source in sources.values():
        if sha(source["text"].encode()) != source["text_hash"]:
            raise ValueError("corrupt source")
    for c in citations:
        source = sources.get(c.source_id)
        if not source or source["text"][c.start : c.end] != c.quote:
            raise ValueError("citation is not exact")
        if not any(
            s["source_id"] == c.source_id and s["start"] <= c.start < c.end <= s["end"]
            for s in evidence["spans"]
        ):
            raise ValueError("citation outside permitted context")
