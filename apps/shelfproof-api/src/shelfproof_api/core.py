"""Pure intake, deterministic checks and nonregression policy (protocol v1)."""

import csv
import hashlib
import io
import json
import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from contracts.shelfproof import (
    DIMENSIONS,
    RESTRICTED,
    CheckFinding,
    Contract,
    Draft,
    FactPack,
    JudgeEvaluation,
    SelectionDecision,
)
from pydantic import Field, ValidationError


def canonical(value):
    if isinstance(value, Contract):
        value = value.model_dump(mode="json")
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def digest(value):
    payload = value if isinstance(value, bytes) else canonical(value).encode()
    return hashlib.sha256(payload).hexdigest()


@lru_cache(maxsize=1)
def code_fingerprint():
    files = sorted(Path(__file__).parent.glob("*.py"))
    files.append(Path(__import__("contracts.shelfproof", fromlist=["__file__"]).__file__))
    return digest({str(p.name): digest(p.read_bytes()) for p in files})


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def bounded_json(text):
    quoted, escaped, depth = False, False, 0
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 8:
                raise ValueError("JSON nesting exceeds eight")
        elif char in "]}":
            depth -= 1
    return json.loads(
        text,
        object_pairs_hook=unique_object,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")),
    )


class FrozenImport(Contract):
    raw_hash: str
    fact_hash: str
    mapping: dict[str, str]
    facts: list[FactPack] = Field(max_length=1000)


class ImportValidationError(ValueError):
    def __init__(self, issues):
        super().__init__("Source row validation failed")
        self.issues = issues


def freeze_import(raw: bytes, format: str, mapping: dict[str, str]) -> FrozenImport:
    if not isinstance(mapping, dict) or any(
        not isinstance(k, str) or not isinstance(v, str) or len(v) > 128 for k, v in mapping.items()
    ):
        raise ValueError("explicit literal column mapping required")
    if len(raw) > 25 * 1024 * 1024:
        raise ValueError("import exceeds 25 MiB")
    text = raw.decode("utf-8-sig", errors="strict")
    if format == "json":
        rows = bounded_json(text)
    elif format == "csv":
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("duplicate or missing CSV headers")
        rows = []
        for row in reader:
            if len(rows) >= 1000:
                raise ValueError("import exceeds 1000 rows")
            rows.append(row)
    else:
        raise ValueError("only csv/json supported")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
        raise ValueError("require 1..1000 rows")
    required = set(FactPack.model_fields)
    if set(mapping) != required or len(set(mapping.values())) != len(mapping):
        raise ValueError("explicit unambiguous mapping of all required fields required")
    facts = []
    for row_index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or len(row) > 64 or len(canonical(row).encode()) > 65536:
            raise ValueError("row exceeds limits")
        if any(
            not isinstance(k, str) or not isinstance(v, (str, type(None))) for k, v in row.items()
        ):
            raise ValueError("flat literal text fields required, including GTIN/quantities")
        if not set(mapping.values()) <= row.keys():
            raise ValueError("mapped column missing")
        try:
            facts.append(
                FactPack.model_validate({key: row[column] for key, column in mapping.items()})
            )
        except ValidationError as exc:
            raise ImportValidationError(
                [
                    {
                        "row": row_index,
                        "field": ".".join(str(x) for x in issue["loc"]),
                        "code": issue["type"],
                    }
                    for issue in exc.errors()[:20]
                ]
            ) from None
    if len({f.product_id for f in facts}) != len(facts):
        raise ValueError("duplicate product identity")
    return FrozenImport(
        raw_hash=digest(raw),
        fact_hash=digest([f.model_dump(mode="json") for f in facts]),
        mapping=mapping,
        facts=facts,
    )


def preview_import(raw: bytes, format: str):
    """Unapproved structural preview. Never guesses or activates a source mapping."""
    if len(raw) > 25 * 1024 * 1024:
        raise ValueError("import exceeds 25 MiB")
    text = raw.decode("utf-8-sig", errors="strict")
    if format == "json":
        rows = bounded_json(text)
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            raise ValueError("flat JSON row array required")
        columns = list(rows[0])
    else:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        columns = reader.fieldnames or []
        rows = []
        for row in reader:
            if len(rows) >= 1000:
                raise ValueError("import exceeds 1000 rows")
            rows.append(row)
    if not 1 <= len(rows) <= 1000 or len(columns) > 64 or len(columns) != len(set(columns)):
        raise ValueError("duplicate columns or invalid row/column count")
    return {
        "status": "UNAPPROVED_MAPPING_REQUIRED",
        "columns": columns,
        "row_count": len(rows),
        "sample": rows[:3],
        "raw_hash": digest(raw),
    }


def check_draft(facts: FactPack, draft: Draft) -> list[CheckFinding]:
    findings = []

    def add(rule, family, severity, field, explanation, **kwargs):
        findings.append(
            CheckFinding(
                rule=rule,
                family=family,
                severity=severity,
                field=field,
                explanation=explanation,
                **kwargs,
            )
        )

    for field in ("title", "description"):
        text = getattr(draft, field)
        approved_words = set(
            re.findall(
                r"[^\W\d_]+",
                " ".join(
                    (
                        facts.brand,
                        facts.name,
                        facts.ingredients,
                        str(facts.net_quantity),
                        facts.net_unit,
                    )
                ).casefold(),
            )
        )
        connective = {
            "ingredients",
            "net",
            "weight",
            "contents",
            "package",
            "size",
            "and",
            "of",
            "with",
            "the",
            "a",
            "in",
        }
        unknown = next(
            (
                m
                for m in re.finditer(r"[^\W\d_]+", text, re.UNICODE)
                if m.group().casefold() not in approved_words | connective
            ),
            None,
        )
        if unknown:
            add(
                "unmapped_text",
                "reference",
                "material",
                field,
                "Text includes a term outside approved literal facts/connectives; semantic support unassessed",
                start=unknown.start(),
                end=unknown.end(),
                quote=unknown.group(),
            )
        for match in RESTRICTED.finditer(text):
            add(
                "restricted_claim",
                "restricted_claim",
                "critical",
                field,
                "Claim category is outside v1 scope",
                start=match.start(),
                end=match.end(),
                quote=match.group(),
            )
        # No conversions or serving/nutrition values are authorized by this fact schema.
        allowed = {
            Decimal(n)
            for n in re.findall(r"\d+(?:\.\d+)?", f"{facts.name} {facts.brand} {facts.ingredients}")
        } | {facts.net_quantity}
        for match in re.finditer(r"\d+(?:\.\d+)?", text):
            if Decimal(match.group()) not in allowed:
                add(
                    "unsupported_number",
                    "numeric",
                    "material",
                    field,
                    "Number is not present in approved facts",
                    start=match.start(),
                    end=match.end(),
                    quote=match.group(),
                )
        for match in re.finditer(
            r"(\d+(?:\.\d+)?)\s*(fl oz|kg|ml|oz|lb|g|l)\b", text, re.IGNORECASE
        ):
            if field == "description" and any(
                m.start() <= match.start() and match.end() <= m.end()
                for m in re.finditer(re.escape(facts.ingredients), text)
            ):
                continue  # Literal ingredient evidence retains its own measurement basis.
            if Decimal(match[1]) != facts.net_quantity or match[2] != facts.net_unit:
                add(
                    "quantity_basis",
                    "numeric",
                    "material",
                    field,
                    "Quantity/unit does not match net package basis",
                    start=match.start(),
                    end=match.end(),
                    quote=match.group(),
                )
    for path, field in (("brand", "title"), ("name", "title"), ("ingredients", "description")):
        value = getattr(facts, path)
        # Literal ingredient order/casing retained. Identity remains case-insensitive.
        text = getattr(draft, field)
        found = value in text if path == "ingredients" else value.casefold() in text.casefold()
        if not found:
            add(
                f"required:{path}",
                "coverage",
                "material",
                field,
                f"Missing literal required {path}",
                refs=[path],
            )
    quantity = re.compile(
        rf"(?<![\d.]){re.escape(format(facts.net_quantity, 'f'))}"
        rf"\s*{re.escape(facts.net_unit)}(?!\w)"
    )
    if not quantity.search(draft.title):
        add(
            "required:net_quantity",
            "coverage",
            "material",
            "title",
            "Required net package quantity and unit missing",
            refs=["net_quantity", "net_unit"],
        )
    for claim in draft.claims:
        text = getattr(draft, claim.field)
        if claim.end <= claim.start or text[claim.start : claim.end] != claim.quote:
            add(
                "claim_span",
                "reference",
                "material",
                claim.field,
                "Claim quote does not match canonical Unicode offsets",
            )
        elif not all(
            str(getattr(facts, path)).casefold() in claim.quote.casefold() for path in claim.refs
        ):
            add(
                "claim_support",
                "reference",
                "material",
                claim.field,
                "Claim is not literal supported evidence; semantic support unassessed",
            )
    return findings


def weighted_score(evaluation: JudgeEvaluation | None):
    if evaluation is None or any(r.value is None for r in evaluation.ratings.values()):
        return None
    return sum(DIMENSIONS[key] * rating.value / 4 for key, rating in evaluation.ratings.items())


def blockers(checks, evaluation):
    return [
        f
        for f in [*checks, *(evaluation.findings if evaluation else [])]
        if f.severity in ("critical", "material") or f.missing_source
    ]


def ready(checks, evaluation):
    score = weighted_score(evaluation)
    return score is not None and score >= 80 and not blockers(checks, evaluation)


def select_version(old_checks, old_eval, new_checks, new_eval):
    old = blockers(old_checks, old_eval)
    new = blockers(new_checks, new_eval)
    if weighted_score(new_eval) is None:
        return SelectionDecision(adopt=False, reason="unassessable")
    if {f.family for f in new} - {f.family for f in old}:
        return SelectionDecision(adopt=False, reason="new_blocking_defect")
    old_missing = {f.rule for f in old_checks if f.family == "coverage"}
    new_missing = {f.rule for f in new_checks if f.family == "coverage"}
    if new_missing - old_missing:
        return SelectionDecision(adopt=False, reason="reduced_coverage")
    old_counts = tuple(sum(f.severity == s for f in old) for s in ("critical", "material"))
    new_counts = tuple(sum(f.severity == s for f in new) for s in ("critical", "material"))
    if new_counts != old_counts:
        return SelectionDecision(adopt=new_counts < old_counts, reason="blocking_defect_count")
    if len(new_missing) < len(old_missing):
        return SelectionDecision(adopt=True, reason="coverage_improved")
    old_score = weighted_score(old_eval)
    gain = old_score is not None and weighted_score(new_eval) - old_score >= 5
    return SelectionDecision(adopt=gain, reason="score_gain" if gain else "keep_incumbent")
