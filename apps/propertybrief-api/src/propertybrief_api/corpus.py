"""Hash-verified replay of captured actual public records, never fabricated results."""

import json
from pathlib import Path

from propertybrief_api.evidence import normalize_record
from propertybrief_api.sources import DEFINITIONS, REQUIRED, digest


def load_corpus(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for key, definition in DEFINITIONS.items():
        metadata = json.loads((root / f"metadata-{key}.json").read_text(encoding="utf-8"))
        entry = manifest["sources"][key]
        if entry["dataset"] != definition.dataset or digest(metadata) != entry["metadata_sha256"]:
            raise ValueError("Source metadata hash or dataset identity mismatch")
    cases = []
    for item in manifest["cases"]:
        path = (root / item["file"]).resolve()
        if path.parent != root.resolve():
            raise ValueError("Invalid corpus path")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if digest(payload) != item["sha256"]:
            raise ValueError("Corpus hash mismatch")
        for source, observation in payload["observations"].items():
            if source not in REQUIRED or digest(observation["raw"]) != observation["sha256"]:
                raise ValueError("Source hash mismatch")
        cases.append(payload)
    return manifest, cases


class FrozenSources:
    def __init__(self, case):
        self.case = case

    def fetch(self, source, identity):
        if identity["building_id"] != self.case["identity"]["building_id"]:
            raise ValueError("Frozen corpus identity mismatch")
        original = self.case["observations"][source]
        result = {**original, "records": [], "flags": list(original["flags"])}
        for raw in original["raw"]:
            try:
                row = normalize_record(source, raw, identity)
                result["records"].append(row)
                if "identity_conflict" in row["flags"]:
                    result["flags"].append("identity_conflict")
            except ValueError:
                result["flags"].append("identity_conflict")
        if source == "dob_violations" and "$where" not in original["query"]:
            result["flags"].append("adapter_query_changed")
        if "identity_conflict" in result["flags"] or "adapter_query_changed" in result["flags"]:
            result["completeness"] = "unknown"
            result["outcome"] = "partial"
        result["count"] = len(result["records"])
        result["flags"] = sorted(set(result["flags"]))
        return result
