"""Integrity/provenance audit, not an AI accuracy benchmark or native webhook corpus."""

import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree


def audit_capture(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    for artifact in manifest["artifacts"]:
        path = PurePosixPath(artifact["file"])
        if path.is_absolute() or len(path.parts) != 1:
            raise ValueError("unsafe manifest path")
        if hashlib.sha256((root / artifact["file"]).read_bytes()).hexdigest() != artifact["sha256"]:
            raise ValueError("capture hash mismatch")
    with zipfile.ZipFile(root / "logchunks.zip") as z:
        names = [
            n for n in z.namelist() if "__MACOSX" not in n and ".." not in PurePosixPath(n).parts
        ]
        logs = {n for n in names if n.startswith("LogChunks/logs/") and n.endswith(".log")}
        xmls = [
            n
            for n in names
            if n.startswith("LogChunks/build-failure-reason/") and n.endswith(".xml")
        ]
        references, missing, empty, languages, repos = [], [], [], set(), set()
        for name in xmls:
            info = z.getinfo(name)
            if info.file_size > 2000000:
                raise ValueError("oversized annotation")
            for example in ElementTree.fromstring(z.read(name)).findall("Example"):
                relative = (example.findtext("Log") or "").strip()
                references.append(relative)
                if "LogChunks/logs/" + relative not in logs:
                    missing.append(relative)
                if not (example.findtext("Chunk") or "").strip():
                    empty.append(relative)
                parts = PurePosixPath(relative).parts
                if len(parts) >= 2:
                    languages.add(parts[0])
                    repos.add(parts[1])
    return {
        "logs": len(logs),
        "annotations": len(references),
        "annotation_files": len(xmls),
        "repositories": len(repos),
        "languages": len(languages),
        "missing_log_references": missing,
        "empty_gold_chunks": empty,
        "unique_referenced_logs": len(set(references)),
        "ai_semantic_validation": "not_run",
        "native_webhook_traffic": False,
        "notes": "Gold chunks locate failure evidence; structural categories are not BuildRelay failure classes.",
    }
