"""Frozen public-data evaluation helpers. Gold labels never enter generation prompts."""

import hashlib
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

from .corpus import audit_capture
from .github import select_archive
from .workflow import Failure, redact


def normalized(text):
    # XML cannot preserve ESC; this corpus sometimes retains visible SGR fragments.
    # Score gold/predictions symmetrically. Never alter the actual generation evidence.
    text = re.sub(r"\[(?:\d{1,3};)*\d{1,3}m", "", redact(text))
    return re.sub(r"\s+", " ", text).strip()


def overlap(triage, gold):
    quotes = [normalized(c["quote"]) for c in triage.get("citations", [])]
    lines = [normalized(line) for line in gold.splitlines() if len(normalized(line)) >= 12]
    return any(q in line or line in q for q in quotes if len(q) >= 12 for line in lines)


def prepare_logchunks(capture, output):
    capture, output = Path(capture), Path(output)
    selector_path = Path(select_archive.__code__.co_filename)
    selector_hash = hashlib.sha256(selector_path.read_bytes()).hexdigest()
    audit = audit_capture(capture)
    if audit["missing_log_references"] or audit["empty_gold_chunks"]:
        raise ValueError("invalid corpus references")
    output.mkdir(parents=True, exist_ok=False)
    records = []
    with zipfile.ZipFile(capture / "logchunks.zip") as archive:
        annotations = sorted(
            n
            for n in archive.namelist()
            if n.startswith("LogChunks/build-failure-reason/")
            and n.endswith(".xml")
            and "__MACOSX" not in n
        )
        for name in annotations:
            for example in ElementTree.fromstring(archive.read(name)).findall("Example"):
                relative = example.findtext("Log").strip()
                gold = example.findtext("Chunk") or ""
                raw = archive.read("LogChunks/logs/" + relative)
                parts = relative.split("/")
                ident = hashlib.sha256(relative.encode()).hexdigest()[:20]
                case = output / ident
                case.mkdir()
                context = {
                    "provider": "Travis CI",
                    "dataset": "LogChunks",
                    "repository": parts[1].replace("@", "/"),
                    "language": parts[0],
                    "build_id": Path(relative).stem,
                    "original_log_path": relative,
                }
                record = {
                    "id": ident,
                    "context": context,
                    "log_sha256": hashlib.sha256(raw).hexdigest(),
                    "gold_sha256": hashlib.sha256(gold.encode()).hexdigest(),
                    "raw_bytes": len(raw),
                }
                packed = io.BytesIO()
                with zipfile.ZipFile(packed, "w", compression=zipfile.ZIP_DEFLATED) as z:
                    z.writestr(Path(relative).name, raw)
                try:
                    evidence = select_archive(
                        packed.getvalue(), "https://zenodo.org/records/3632351#" + ident
                    )
                    anchor = next(
                        (
                            normalized(line)
                            for line in gold.splitlines()
                            if len(normalized(line)) >= 12
                        ),
                        "",
                    )
                    full = normalized(raw.decode("utf-8", errors="replace"))
                    selected = normalized(evidence["text"])
                    record.update(
                        status="selected",
                        truncated=evidence["truncated"],
                        anchor_in_full=bool(anchor and anchor in full),
                        anchor_in_selected=bool(anchor and anchor in selected),
                    )
                    (case / "evidence.json").write_text(json.dumps(evidence))
                except Failure as exc:
                    record.update(status="selector_failure", error=exc.code)
                (case / "context.json").write_text(json.dumps(context))
                (case / "gold.txt").write_text(gold)
                records.append(record)
    # One case per repository, selected by source-path hash, not by quality/outcome/gold.
    by_repo = {}
    for record in sorted(records, key=lambda r: r["id"]):
        by_repo.setdefault(record["context"]["repository"], record)
    sample = list(by_repo.values())
    scorable = [r for r in records if r.get("anchor_in_full")]
    report = {
        "kind": "all_corpus_production_selector_evaluation",
        "selector_module_sha256": selector_hash,
        "records": records,
        "sample_ids": [r["id"] for r in sample],
        "total": len(records),
        "repositories": len(by_repo),
        "languages": len({r["context"]["language"] for r in records}),
        "statuses": dict(Counter(r["status"] for r in records)),
        "scorable_anchors": len(scorable),
        "retained_anchors": sum(r["anchor_in_selected"] for r in scorable),
        "gold_anchor_retention": sum(r["anchor_in_selected"] for r in scorable) / len(scorable)
        if scorable
        else None,
        "sample_unique_gold_chunks": len({r["gold_sha256"] for r in sample}),
        "ai_calls": 0,
        "gold_in_generation_prompt": False,
        "gate": "retain >=90% of literal scorable annotated failure anchors; diagnostic target, not causal accuracy",
    }
    if hashlib.sha256(selector_path.read_bytes()).hexdigest() != selector_hash:
        raise ValueError("selector changed during preparation; discard this derived run")
    (output / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
