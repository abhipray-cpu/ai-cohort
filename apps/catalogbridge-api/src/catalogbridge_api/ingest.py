"""Bounded text intake; hidden evaluation fields never reach runtime."""

import csv
import io
import json

from contracts.catalogbridge import Product


def parse_feed(data: bytes, format: str) -> list[Product]:
    if len(data) > 20 * 1024 * 1024:
        raise ValueError("feed too large")
    text = data.decode("utf-8-sig", errors="strict")
    if format == "csv":
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError("duplicate columns")
        rows = list(reader)
    elif format == "json":
        rows = json.loads(text)
    else:
        raise ValueError("unsupported format")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 25000:
        raise ValueError("feed must contain 1..25000 rows")
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) - set(Product.model_fields):
            raise ValueError("forbidden or unknown fields")
        product = Product.model_validate(row)
        if product.id in seen:
            raise ValueError("duplicate product id")
        seen.add(product.id)
        result.append(product)
    return result
