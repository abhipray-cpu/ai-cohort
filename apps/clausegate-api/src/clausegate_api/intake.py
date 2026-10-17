"""Bounded source intake; annotation labels are evaluator-only, never model input."""

import io
import re
import zipfile
from pathlib import PurePosixPath

from clausegate_api.common import byte_hash, digest


def resolve_evidence(spans, finding):
    lookup = {s["id"]: s for s in spans}
    quotes = {q["span_id"]: q["quote"] for q in finding.get("evidence_quotes", [])}
    result = []
    for sid in finding["evidence_ids"]:
        if sid not in lookup:
            raise ValueError("Unknown source evidence")
        span = dict(lookup[sid])
        if sid in quotes:
            quote = quotes[sid]
            at = span["quote"].find(quote)
            if not quote.strip() or at < 0 or span["quote"].find(quote, at + 1) >= 0:
                raise ValueError("Quote must be a unique exact original-source substring")
            span.update(start=span["start"] + at, end=span["start"] + at + len(quote), quote=quote)
        result.append(span)
    return result


def archive_members(raw, max_bytes=512 * 1024**2, *, quarantined=None):
    if len(raw) > 256 * 1024**2:
        raise ValueError("Archive compressed limit")
    result = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if len(infos) > 10000 or sum(i.file_size for i in infos) > max_bytes:
            raise ValueError("Archive expansion limit")
        for info in infos:
            path = PurePosixPath(info.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in info.filename
                or ":" in info.filename
                or (info.external_attr >> 16) & 0o170000 == 0o120000
            ):
                if quarantined is None:
                    raise ValueError("Unsafe archive path")
                quarantined.append(info.filename)
                continue
            if info.is_dir():
                continue
            if info.filename in result:
                raise ValueError("Duplicate archive entry")
            result[info.filename] = archive.read(info)
    return result


def text_document(text, name, *, complete=True, gaps=None, raw_hash=None, pages=None):
    if not text.strip() or len(text) > 500000 or len(text.encode()) > 20 * 1024**2:
        raise ValueError("Empty or oversized extracted document")
    spans = []
    # Stable original Unicode offsets. Whitespace is preserved, not re-normalized.
    for block in re.finditer(r"[^\n]+(?:\n|$)", text):
        for start in range(block.start(), block.end(), 1200):
            end = min(start + 1200, block.end())
            spans.append(
                {"id": f"s{len(spans)}", "start": start, "end": end, "quote": text[start:end]}
            )
    if len(spans) > 10000:
        raise ValueError("Document span limit")
    return {
        "name": name,
        "text": text,
        "text_hash": digest(text),
        "bytes_hash": raw_hash or byte_hash(text.encode()),
        "spans": spans,
        "complete": complete,
        "gaps": gaps or [],
        "pages": pages or [],
        "extraction_version": "original-unicode-lines-1",
    }


def pdf_document(raw, name):
    import pymupdf

    if len(raw) > 20 * 1024**2:
        raise ValueError("PDF size limit")
    try:
        with pymupdf.open(stream=raw, filetype="pdf") as pdf:
            if pdf.is_encrypted or not 1 <= len(pdf) <= 150:
                raise ValueError("Encrypted or unsupported page count")
            pages, gaps, texts, position = [], [], [], 0
            for number, page in enumerate(pdf):
                body = page.get_text("text")
                if page.get_images(full=True):
                    gaps.append(
                        f"Page {number + 1} contains image objects; OCR/visual completeness is unverified (including possible logos)"
                    )
                if not body.strip():
                    gaps.append(f"Page {number + 1} has no readable text; OCR unavailable")
                texts.append(body + "\n")
                pages.append({"page": number + 1, "start": position, "end": position + len(body)})
                position += len(body) + 1
                if position > 500000:
                    raise ValueError("Extracted text limit")
            return text_document(
                "".join(texts),
                name,
                complete=not gaps,
                gaps=gaps,
                raw_hash=byte_hash(raw),
                pages=pages,
            )
    except (RuntimeError, pymupdf.FileDataError) as error:
        raise ValueError("Unreadable PDF") from error


def normalize_dataset(raw, split):
    if not raw.get("documents") or not raw.get("labels"):
        raise ValueError("Dataset schema missing records or labels")
    result, seen = [], set()
    for row in raw["documents"]:
        if row["id"] in seen or len(row.get("annotation_sets", [])) != 1:
            raise ValueError("Duplicate ID or missing/ambiguous annotations")
        seen.add(row["id"])
        text = row["text"]
        for start, end in row["spans"]:
            if not 0 <= start < end <= len(text):
                raise ValueError("Invalid dataset evidence span")
        gold = row["annotation_sets"][0]["annotations"]
        if set(gold) != set(raw["labels"]):
            raise ValueError("Missing hypothesis annotations")
        for value in gold.values():
            if value["choice"] not in {"Entailment", "Contradiction", "NotMentioned"}:
                raise ValueError("Unknown gold class")
            if any(not 0 <= i < len(row["spans"]) for i in value["spans"]):
                raise ValueError("Unknown gold evidence index")
        result.append(
            {
                "id": row["id"],
                "split": split,
                "source_url": row.get("url"),
                "document": text_document(text, row.get("file_name", f"{row['id']}.txt")),
                "hypotheses": raw["labels"],
                "gold": gold,
                "gold_spans": row["spans"],
            }
        )
    return result
