"""Safe offline public-benchmark normalization and transparent scoring."""

import re
from pathlib import PurePosixPath

from contracts.catalogbridge import Product


def safe_members(archive):
    infos = archive.infolist()
    if len(infos) > 10000 or sum(i.file_size for i in infos) > 512 * 1024 * 1024:
        raise ValueError("archive exceeds expanded limits")
    seen = set()
    for info in infos:
        name = info.filename.replace("\\", "/")
        path = PurePosixPath(name)
        if path.is_absolute() or any(
            part in {".", ".."}
            or part.endswith((" ", "."))
            or ":" in part
            or re.match(r"(?i)^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\.|$)", part)
            for part in path.parts
        ):
            raise ValueError("unsafe archive member")
        if name.casefold() in seen or (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError("archive collision or symlink")
        seen.add(name.casefold())
    return infos


def normalize_pair(row):
    products = []
    for side in ("left", "right"):
        value = {"id": str(row[f"id_{side}"])}
        for field in ("title", "description", "brand", "price"):
            raw = row.get(field + "_" + side)
            value[field] = "" if raw is None else str(raw)
        value["currency"] = str(row.get("priceCurrency_" + side) or "")
        products.append(Product.model_validate(value).model_dump())
    if type(row["label"]) is not int or row["label"] not in (0, 1):
        raise ValueError("invalid gold label")
    return {"input": {"supplier": products[0], "master": products[1]}, "gold": row["label"]}


def score_pairs(gold, predictions):
    if len(gold) != len(predictions) or not gold:
        raise ValueError("invalid evaluation denominator")
    tp = sum(g == 1 and p == 1 for g, p in zip(gold, predictions, strict=True))
    fp = sum(g == 0 and p == 1 for g, p in zip(gold, predictions, strict=True))
    fn = sum(g == 1 and p != 1 for g, p in zip(gold, predictions, strict=True))
    resolved = sum(p is not None for p in predictions)
    correct = sum(g == p for g, p in zip(gold, predictions, strict=True))
    return {
        "total": len(gold),
        "resolved": resolved,
        "correct": correct,
        "coverage": resolved / len(gold),
        "accuracy_all_rows": correct / len(gold),
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }
