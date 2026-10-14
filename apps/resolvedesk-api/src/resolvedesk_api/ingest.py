"""Deterministic HTML/text ingestion preserving code and section context."""

import re
from html.parser import HTMLParser


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0
        self.headings = []
        self.heading = None
        self.anchor = ""

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if not self.skip and attributes.get("id"):
            self.anchor = attributes["id"]
        if not self.skip and tag in ("h1", "h2", "h3", "h4"):
            self.heading = {"anchor": self.anchor, "parts": []}
        if tag in ("script", "style", "nav", "header", "footer"):
            self.skip += 1
        if not self.skip and tag in ("p", "pre", "li", "div", "br", "h1", "h2", "h3", "h4", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3", "h4") and self.heading is not None:
            self.headings.append(
                {"anchor": self.heading["anchor"], "heading": "".join(self.heading["parts"])}
            )
            self.heading = None
        if tag in ("script", "style", "nav", "header", "footer") and self.skip:
            self.skip -= 1
        if not self.skip and tag in ("p", "pre", "li", "div", "h1", "h2", "h3", "h4", "tr"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self.heading is not None:
                self.heading["parts"].append(data)


def normalize(text):
    return "\n".join(re.sub(r"[\t \r]+", " ", line).strip() for line in text.splitlines()).strip()


def parse_document(html):
    return parse_document_details(html)[0]


def parse_document_details(html):
    # PostgreSQL's docContent excludes the site's chrome; generic imports can use main.
    content = re.search(
        r'<div\b[^>]*\bid=["\']docContent["\'][^>]*>(.*)', html, re.DOTALL | re.IGNORECASE
    )
    if content:
        html = content.group(1)
    else:
        main = re.search(r"<main\b[^>]*>(.*?)</main>", html, re.DOTALL | re.IGNORECASE)
        if main:
            html = main.group(1)
    parser = DocumentParser()
    parser.feed(html)
    text = re.sub(r"\n{3,}", "\n\n", normalize("".join(parser.parts)))
    sections = []
    cursor = 0
    for heading in parser.headings:
        title = normalize(heading["heading"])
        start = text.find(title, cursor) if title else -1
        if start >= 0:
            sections.append({"start": start, "heading": title, "anchor": heading["anchor"]})
            cursor = start + len(title)
    return text, sections


def passages(text, size=3500):
    """Return exact normalized spans, preferring paragraph/line boundaries."""
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + size // 2, end)
            if boundary > start:
                end = boundary
        while start < end and text[start].isspace():
            start += 1
        trimmed = end
        while trimmed > start and text[trimmed - 1].isspace():
            trimmed -= 1
        if trimmed > start:
            yield start, trimmed, text[start:trimmed]
        start = end
