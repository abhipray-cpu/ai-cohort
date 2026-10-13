"""Run the checked-in source manifest's local PDF through the live Codex worker."""

from __future__ import annotations

import hashlib
import json
import tempfile
import time
from pathlib import Path

from agent_core.codex_local import LocalCodexProvider
from tenderlens_api.store import Store
from tenderlens_api.worker import run_once

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/tenderlens/raw/unicef-montenegro-lrps-2026-9202732.pdf"
EXPECTED_SHA256 = "f64e41551ec6bd0287373ca0d1d3fef7edd1ff2da10e660c3be18b60069a8e2d"


def main():
    if not SOURCE.exists():
        raise SystemExit(
            "Download the seed PDF listed in data/tenderlens/manifests/seed-sources.json"
        )
    data = SOURCE.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise SystemExit("Seed PDF checksum mismatch")
    with tempfile.TemporaryDirectory(prefix="tenderlens-seed-") as temporary:

        class DiagnosticProvider:
            def __init__(self):
                self.inner = LocalCodexProvider()

            def generate(self, *, prompt, schema):
                result = self.inner.generate(prompt=prompt, schema=schema)
                if result.exit_code:
                    print(
                        json.dumps(
                            {"codex_exit": result.exit_code, "stderr_tail": result.stderr[-1000:]}
                        )
                    )
                return result

        store = Store(Path(temporary))
        opportunity = store.create_opportunity("UNICEF Montenegro graphic design")
        store.add_document(opportunity["id"], SOURCE.name, data)
        run_id = store.create_run(opportunity["id"])["id"]
        started = time.monotonic()
        run_once(store, DiagnosticProvider())
        elapsed = round(time.monotonic() - started, 1)
        result = store.run(run_id)
        claims = result["brief"]["claims"] if result["brief"] else []
        values = " ".join(claim["value"].lower() for claim in claims)
        report = {
            "source_sha256": EXPECTED_SHA256,
            "status": result["status"],
            "error": result["error"],
            "elapsed_seconds": elapsed,
            "claim_count": len(claims),
            "validation_failure_count": len(result["events"]),
            "contains_70_point_criterion": "70" in values,
            "contains_2_references": "2 reference" in values or "two reference" in values,
            "kinds": sorted({claim["kind"] for claim in claims}),
        }
        print(json.dumps(report, indent=2))
        if result["status"] != "draft":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
