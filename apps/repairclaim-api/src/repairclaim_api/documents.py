"""Document primitives. Untrusted bytes must be processed by the restricted runner."""

import hashlib
import re
import struct

import pymupdf

from repairclaim_api.errors import DomainError

MAX_BYTES = 20 * 1024 * 1024


def _open(data: bytes, filename: str):
    if not data or len(data) > MAX_BYTES:
        raise DomainError("document_size", 413)
    suffix = filename.rsplit(".", 1)[-1].lower()
    if suffix not in {"pdf", "jpg", "jpeg", "png"}:
        raise DomainError("unsupported_document", 415)
    if suffix == "pdf" and not data.lstrip().startswith(b"%PDF-"):
        raise DomainError("invalid_document", 422)
    if suffix != "pdf":
        try:
            width, height = _image_dimensions(data, suffix)
            if not width or not height or width * height > 30_000_000:
                raise DomainError("image_size", 413)
        except (ValueError, RuntimeError) as error:
            raise DomainError("invalid_document", 422) from error
    try:
        document = pymupdf.open(stream=data, filetype=suffix)
        if document.is_encrypted:
            document.close()
            raise DomainError("encrypted_document", 422)
        if not document.is_pdf:
            converted = document.convert_to_pdf()
            document.close()
            document = pymupdf.open(stream=converted, filetype="pdf")
        if len(document) > 100 or document.xref_length() > 50000:
            document.close()
            raise DomainError("document_complexity", 413)
        if document.embfile_count():
            document.close()
            raise DomainError("embedded_content_denied", 422)
        for index in range(1, document.xref_length()):
            obj = document.xref_object(index, compressed=True)
            if any(tag in obj for tag in ("/JavaScript", "/Launch", "/RichMedia", "/EmbeddedFile")):
                document.close()
                raise DomainError("active_content_denied", 422)
        return document
    except (ValueError, RuntimeError) as error:
        raise DomainError("invalid_document", 422) from error


def _image_dimensions(data, suffix):
    if suffix == "png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 24:
            raise DomainError("invalid_document", 422)
        return struct.unpack(">II", data[16:24])
    if not data.startswith(b"\xff\xd8"):
        raise DomainError("invalid_document", 422)
    index = 2
    while index + 4 <= len(data):
        if data[index] != 255:
            raise DomainError("invalid_document", 422)
        marker = data[index + 1]
        index += 2
        if marker == 255:
            index -= 1
            continue
        length = int.from_bytes(data[index : index + 2], "big")
        if length < 2 or index + length > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            return int.from_bytes(data[index + 5 : index + 7], "big"), int.from_bytes(
                data[index + 3 : index + 5], "big"
            )
        index += length
    raise DomainError("invalid_document", 422)


def _text(page, ocr):
    text = page.get_text()
    if text.strip() or not ocr:
        return text
    try:
        return page.get_text(textpage=page.get_textpage_ocr(language="eng", dpi=150, full=True))
    except (RuntimeError, ValueError) as error:
        raise DomainError("ocr_unavailable", 503) from error


def parse_document(data: bytes, filename: str, *, ocr=True):
    with _open(data, filename) as document:
        pages, proposals = [], []
        for number, page in enumerate(document, 1):
            text = _text(page, ocr)
            if len(text) > 64000:
                raise DomainError("page_text_limit", 413)
            pages.append({"page": number, "text": text})
            patterns = [
                (
                    "repair_mileage",
                    r"(?:repair mileage|mileage at repair)\s*[:=]?\s*([0-9,]+(?:\.[0-9]+)?)\s*(mi|miles|km)",
                ),
                (
                    "current_mileage",
                    r"current mileage\s*[:=]?\s*([0-9,]+(?:\.[0-9]+)?)\s*(mi|miles|km)",
                ),
                (
                    "diagnostic_code",
                    r"(?:diagnostic code|\bDTC(?:\s+code)?)\s*[:=]?[\s|]{0,40}([PBCU][0-9A-F]{4})\b",
                ),
                ("repair_date", r"repair date\s*[:=]?\s*(\d{4}-\d{2}-\d{2})"),
                (
                    "paid_amount",
                    r"(?:paid amount|amount paid)\s*[:=]?\s*(USD|EUR|GBP)\s*([0-9,]+\.[0-9]{2})",
                ),
                ("invoice_total", r"invoice total\s*[:=]?\s*(USD|EUR|GBP)\s*([0-9,]+\.[0-9]{2})"),
                ("component", r"(?:repair component|component)\s*[:=]\s*([^\n]{1,150})"),
                ("diagnosis", r"diagnosis\s*[:=]\s*([^\n]{1,150})"),
            ]
            for field, pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    unit = None
                    value = match.group(1).replace(",", "")
                    if field == "diagnostic_code":
                        value = value.upper()
                    if field.endswith("mileage"):
                        unit = "km" if match.group(2).lower() == "km" else "mi"
                    if field in {"paid_amount", "invoice_total"}:
                        unit, value = match.group(1).upper(), match.group(2).replace(",", "")
                    proposals.append(
                        {
                            "field": field,
                            "value": value,
                            "unit": unit,
                            "status": "extracted",
                            "page": number,
                            "quote": match.group(0),
                        }
                    )
            for match in re.finditer(r"\b[A-HJ-NPR-Z0-9]{17}\b", text, re.IGNORECASE):
                proposals.append(
                    {
                        "field": "vin",
                        "value": match.group(0).upper(),
                        "unit": None,
                        "status": "extracted",
                        "page": number,
                        "quote": match.group(0),
                    }
                )
        if len(proposals) > 100:
            raise DomainError("proposal_limit", 413)
        return {
            "sha256": hashlib.sha256(data).hexdigest(),
            "pages": pages,
            "page_count": len(pages),
            "proposals": proposals,
            "needs_ocr": any(not page["text"].strip() for page in pages),
        }


def sanitized_attachment(data: bytes, filename: str, redactions: list[str]):
    if len(redactions) > 40 or any(not value.strip() or len(value) > 200 for value in redactions):
        raise DomainError("invalid_redactions", 422)
    found = set()
    output = pymupdf.open()
    try:
        with _open(data, filename) as document:
            for page in document:
                textpage = page.get_textpage()
                if redactions and not page.get_text().strip():
                    try:
                        textpage = page.get_textpage_ocr(language="eng", dpi=150, full=True)
                    except RuntimeError as error:
                        raise DomainError("redaction_ocr_required", 422) from error
                for term in redactions:
                    boxes = page.search_for(term, textpage=textpage)
                    if boxes:
                        found.add(term)
                    for box in boxes:
                        page.draw_rect(
                            box + (-2, -2, 2, 2), color=(0, 0, 0), fill=(0, 0, 0), overlay=True
                        )
                if page.rect.width * page.rect.height * 2.25 > 30_000_000:
                    raise DomainError("page_render_limit", 413)
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
                clean = output.new_page(width=page.rect.width, height=page.rect.height)
                clean.insert_image(clean.rect, pixmap=pixmap)
            if set(redactions) != found:
                raise DomainError("redaction_not_found", 422)
            output.set_metadata({})
            result = output.tobytes(garbage=4, deflate=True)
            if len(result) > MAX_BYTES:
                raise DomainError("derivative_size", 413)
            return result
    finally:
        output.close()


def render_packet(*, title: str, paragraphs: list[str], manifest_hash: str, approved=False):
    if len(paragraphs) > 200 or sum(map(len, paragraphs)) > 100000 or len(title) > 200:
        raise DomainError("packet_size", 413)
    font = pymupdf.Font("cjk")
    document = pymupdf.open()
    page, y = None, 0

    def new_page():
        nonlocal page, y
        page = document.new_page(width=612, height=792)
        page.insert_font(fontname="RC", fontbuffer=font.buffer)
        page.insert_text(
            (48, 32),
            "REPAIRCLAIM  /  " + ("REVIEW COPY" if approved else "UNAPPROVED"),
            fontsize=9,
            color=(0.35, 0.35, 0.35),
        )
        page.insert_text((48, 763), f"Page {len(document)} | {manifest_hash[:16]}", fontsize=8)
        y = 65

    try:
        for paragraph in [title, *paragraphs]:
            if any(not font.has_glyph(ord(char)) for char in paragraph if not char.isspace()):
                raise DomainError("unsupported_packet_glyph", 422)
            size = 17 if page is None else 10.5
            lines, line = [], ""
            for word in paragraph.replace("\n", " ").split(" "):
                candidate = f"{line} {word}".strip()
                if font.text_length(candidate, fontsize=size) <= 510:
                    line = candidate
                    continue
                if line:
                    lines.append(line)
                line = ""
                for character in word:
                    if font.text_length(line + character, fontsize=size) > 510:
                        lines.append(line)
                        line = ""
                    line += character
            lines.append(line)
            for line in lines:
                if page is None or y > 724:
                    new_page()
                page.insert_text((48, y), line, fontname="RC", fontsize=size)
                y += 23 if size == 17 else 16
            y += 8
        return document.tobytes(garbage=4, deflate=True)
    finally:
        document.close()
