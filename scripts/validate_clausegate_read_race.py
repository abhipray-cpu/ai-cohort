"""Concurrent legitimate writes and reads on an isolated real-source case."""

import argparse
import json
import secrets
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from clausegate_api.common import byte_hash, now
from clausegate_api.store import Store


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", default="var/validation/clausegate-corpus-v2")
    p.add_argument("--output", required=True)
    p.add_argument(
        "--http-readers",
        action="store_true",
        help="Exercise the actual ASGI GET route with an authenticated test client; writer still uses the domain service",
    )
    args = p.parse_args()
    root, corpus = Path(args.output), Path(args.corpus)
    root.mkdir(exist_ok=False)
    raw = corpus / "evaluator-only.json"
    manifest = json.loads((corpus / "manifest.json").read_text())
    if byte_hash(raw.read_bytes()) != manifest["normalized_sha256"]:
        raise ValueError("Source integrity mismatch")
    row = next(r for r in json.loads(raw.read_text()) if r["split"] == "train")
    store = Store(root / "store", ledger_dir=root / "authority")
    password = secrets.token_urlsafe(24)
    store.add_user("requester", password)
    w = store.create_workspace("requester", "Concurrent real-source diagnostic")
    c = store.create_case("requester", w["id"], "Read/write consistency fixture")
    c = store.import_document("requester", c["id"], c["revision"], row["document"])
    cid, barrier = c["id"], threading.Barrier(5)
    client = None
    if args.http_readers:
        from clausegate_api.api import create_app
        from fastapi.testclient import TestClient

        client = TestClient(create_app(store=store))
        client.__enter__()
        login = client.post(
            "/v1/auth/session", json={"username": "requester", "password": password}
        )
        login.raise_for_status()

    def writer():
        barrier.wait()
        for i in range(100):
            current = store.case("requester", cid)
            store.set_context(
                "requester", cid, current["revision"], "recipient", f"Explicit test purpose {i}"
            )
        return {"writes": 100}

    def reader(_):
        barrier.wait()
        outcomes = Counter()
        for _ in range(150):
            try:
                if client is None:
                    store.case("requester", cid)
                    outcomes["consistent_read"] += 1
                else:
                    response = client.get(f"/v1/cases/{cid}")
                    outcomes[
                        "consistent_read"
                        if response.status_code == 200
                        else "HTTP "
                        + str(response.status_code)
                        + ": "
                        + response.json().get("detail", "unknown")
                    ] += 1
            except (ValueError, RuntimeError, PermissionError) as error:
                outcomes[type(error).__name__ + ": " + str(error)] += 1
        return dict(outcomes)

    try:
        with ThreadPoolExecutor(max_workers=5) as pool:
            write = pool.submit(writer)
            readers = [pool.submit(reader, i) for i in range(4)]
            outcomes = [r.result() for r in readers]
            writes = write.result()
    finally:
        if client is not None:
            client.__exit__(None, None, None)
    totals = sum((Counter(r) for r in outcomes), Counter())
    result = {
        "finished_at": now(),
        "source_id": row["id"],
        "classification": "Isolated legitimate context writes against real NDA source; no source/audit tampering injected",
        "read_surface": "authenticated in-process ASGI HTTP; not a browser or network transport"
        if args.http_readers
        else "domain service",
        "writes": writes,
        "read_outcomes": dict(totals),
        "final_audit": store.verify_audit("requester", cid),
        "passed": totals["consistent_read"] == 600,
    }
    (root / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
