"""Actual loopback HTTP read/write stress on a new real-source fixture case."""

import argparse
import json
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from clausegate_api.common import byte_hash, now
from dev_stack import environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="var/validation/clausegate-corpus-v2")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output, root = Path(args.output), Path(args.corpus)
    if output.exists():
        raise ValueError("New evidence path required")
    raw = root / "evaluator-only.json"
    manifest = json.loads((root / "manifest.json").read_text())
    if byte_hash(raw.read_bytes()) != manifest["normalized_sha256"]:
        raise ValueError("Corpus integrity mismatch")
    row = next(r for r in json.loads(raw.read_text()) if r["split"] == "train")
    env = environment()
    client = httpx.Client(base_url="http://127.0.0.1:8005", timeout=30)
    report = {
        "started_at": now(),
        "source_id": row["id"],
        "classification": "Actual authenticated loopback HTTP; new public-source fixture; 100 legitimate context updates and 600 concurrent case reads, no model or legal approvals",
    }
    try:
        login = client.post(
            "/v1/auth/session",
            json={
                "username": env.get("CLAUSEGATE_USERNAME") or env.get("TENDERLENS_USERNAME"),
                "password": env.get("CLAUSEGATE_PASSWORD") or env.get("TENDERLENS_PASSWORD"),
            },
        )
        login.raise_for_status()
        client.headers["X-CSRF-Token"] = login.json()["csrf"]
        workspace = client.post(
            "/v1/workspaces", json={"name": "Network concurrency fixture " + now()}
        )
        workspace.raise_for_status()
        created = client.post(
            f"/v1/workspaces/{workspace.json()['id']}/cases",
            json={"name": "Real NDA concurrency validation"},
        )
        created.raise_for_status()
        c = created.json()
        imported = client.post(
            f"/v1/cases/{c['id']}/imports",
            json={
                "expected_revision": c["revision"],
                "text": row["document"]["text"],
                "name": row["document"]["name"],
            },
        )
        imported.raise_for_status()
        c = imported.json()
        cid, barrier = c["id"], threading.Barrier(5)

        def writer():
            revision = c["revision"]
            barrier.wait()
            for i in range(100):
                result = client.put(
                    f"/v1/cases/{cid}/context",
                    json={
                        "expected_revision": revision,
                        "side": "recipient",
                        "purpose": f"Explicit concurrency fixture {i}",
                    },
                )
                result.raise_for_status()
                revision = result.json()["revision"]
            return revision

        def reader(_):
            barrier.wait()
            counts = Counter()
            for _ in range(150):
                response = client.get(f"/v1/cases/{cid}")
                counts[str(response.status_code)] += 1
            return counts

        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=5) as pool:
            write = pool.submit(writer)
            reads = [pool.submit(reader, i) for i in range(4)]
            counts = sum((r.result() for r in reads), Counter())
            revision = write.result()
        audit = client.get(f"/v1/cases/{cid}/audit")
        audit.raise_for_status()
        verification = audit.json()["verification"]
        report.update(
            case_id=cid,
            read_statuses=dict(counts),
            writes=100,
            final_revision=revision,
            seconds=time.monotonic() - started,
            final_audit=verification,
            passed=counts == {"200": 600} and verification["valid"],
        )
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0 if report["passed"] else 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
