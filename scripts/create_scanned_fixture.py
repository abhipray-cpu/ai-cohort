"""Create a temporary image-only test PDF from the public seed RFP's first page."""

from __future__ import annotations

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/tenderlens/raw/unicef-montenegro-lrps-2026-9202732.pdf"
OUTPUT = ROOT / "tmp/pdfs/scanned-seed.pdf"


def main():
    if not SOURCE.exists():
        raise SystemExit("Fetch the seed PDF first")
    source = pymupdf.open(SOURCE)
    page = source[0]
    raster = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    scanned = pymupdf.open()
    target = scanned.new_page(width=page.rect.width, height=page.rect.height)
    target.insert_image(target.rect, stream=raster.tobytes("png"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    scanned.save(OUTPUT)
    source.close()
    scanned.close()
    print(OUTPUT)


if __name__ == "__main__":
    main()
