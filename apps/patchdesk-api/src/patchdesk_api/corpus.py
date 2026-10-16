"""Immutable capture/replay; raw data remains in ignored local storage."""

import json
from copy import deepcopy
from pathlib import Path

from patchdesk_api.adapters import make_result
from patchdesk_api.common import digest, now


def freeze(directory, payload):
    root = Path(directory)
    if root.exists():
        raise ValueError("Use a new capture directory")
    root.mkdir(parents=True)
    (root / "payload.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "created_at": now(),
                "sha256": digest(payload),
                "kind": "source-capture",
                "file": "payload.json",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def load_capture(directory):
    root = Path(directory)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest["file"] != "payload.json":
        raise ValueError("Invalid capture path")
    payload = json.loads((root / "payload.json").read_text(encoding="utf-8"))
    if digest(payload) != manifest["sha256"]:
        raise ValueError("Capture hash mismatch")
    return payload


class FrozenSources:
    """Replay captured upstream payloads; missing capture is unknown, never invented data."""

    def __init__(self, payload):
        self.payload = payload
        self.lookups = {
            (r["package"], r["version"]): r
            for r in (payload.get("lookup") or {}).get("records", [])
        }

    def execute(self, adapter, request):
        if adapter == "osv" and request.capability == "advisories.lookup":
            records, missing = [], []
            for item in request.arguments["packages"]:
                pair = (item["name"], item["version"])
                if pair in self.lookups:
                    records.append(self.lookups[pair])
                else:
                    missing.append(pair)
            return make_result(
                adapter,
                request.capability,
                records,
                {"captured_records": records, "missing_query_identities": missing},
                completeness="unknown"
                if missing
                else (self.payload.get("lookup") or {}).get("completeness", "unknown"),
            )
        for value in self.payload["snapshots"].values():
            original = value["request"]
            if (
                value["result"]["adapter"] != adapter
                or original["capability"] != request.capability
            ):
                continue
            args = request.arguments
            identity_fields = (
                ("id",)
                if request.capability == "advisories.detail"
                else ("package", "version")
                if request.capability in ("releases.lookup", "dependency.context")
                else ("cve",)
            )
            if all(original["arguments"].get(k) == args.get(k) for k in identity_fields):
                return deepcopy(value["result"])
        return make_result(
            adapter,
            request.capability,
            [],
            None,
            completeness="unknown",
            outcome="unavailable",
            error="Not captured; no synthetic substitute",
        )
