"""Short-lived PDF parsing process; no links, attachments or scripts executed."""

import json
import sys


def main():
    # Darwin rejects lowering RLIMIT_AS below the already-reserved address space.
    # Windows/Darwin retain the subprocess, input/page/text and parent wall limits;
    # hard memory isolation on those hosts is a separate deployment qualification.
    if sys.platform.startswith("linux"):
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    import pymupdf

    raw = sys.stdin.buffer.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError("too large")
    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        if doc.needs_pass or doc.embfile_count() or not 0 < len(doc) <= 200:
            raise ValueError("unsupported PDF")
        parts = []
        for page in doc:
            parts.append(page.get_text())
            if sum(len(p) for p in parts) > 1_000_000:
                raise ValueError("too much text")
        print(
            json.dumps(
                {
                    "text": "\n".join(parts),
                    "pages": len(doc),
                    "partial": any(not p.strip() for p in parts),
                }
            )
        )


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 -- child never emits parser or document details
        raise SystemExit(2) from None
