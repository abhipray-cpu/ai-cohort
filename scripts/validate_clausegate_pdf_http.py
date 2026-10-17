"""Real original PDF uploads/downloads against the managed local service, no AI."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from clausegate_api.common import byte_hash, digest, now
from clausegate_api.intake import archive_members
from dev_stack import environment


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", default="var/validation/clausegate-corpus-v2")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    output, root = Path(args.output), Path(args.corpus)
    if output.exists():
        raise ValueError("New artifact path required")
    manifest = json.loads((root / "manifest.json").read_text())
    raw = (root / "contract-nli.zip").read_bytes()
    if byte_hash(raw) != manifest["sha256"]:
        raise ValueError("Corpus integrity failure")
    files = archive_members(raw, quarantined=[])
    names = sorted(
        (n for n in files if n.lower().endswith(".pdf")), key=lambda n: (len(files[n]), n)
    )
    selected = [names[round(i * (len(names) - 1) / 11)] for i in range(12)]
    env = environment()
    report = {
        "started_at": now(),
        "classification": "Actual original PDF HTTP journey; no inference, legal review or visual/browser certification",
        "documents": [],
        "checks": [],
    }
    with httpx.Client(base_url="http://127.0.0.1:8005", timeout=60) as client:
        response = client.post(
            "/v1/auth/session",
            json={
                "username": env.get("CLAUSEGATE_USERNAME") or env.get("TENDERLENS_USERNAME"),
                "password": env.get("CLAUSEGATE_PASSWORD") or env.get("TENDERLENS_PASSWORD"),
            },
        )
        response.raise_for_status()
        client.headers["X-CSRF-Token"] = response.json()["csrf"]
        w = client.post("/v1/workspaces", json={"name": "Original PDF validation " + now()})
        w.raise_for_status()
        wid = w.json()["id"]

        def check(name, passed):
            report["checks"].append({"name": name, "passed": bool(passed)})
            output.write_text(json.dumps(report, indent=2), encoding="utf-8")
            if not passed:
                raise AssertionError(name)

        for index, name in enumerate(selected):
            r = client.post(
                f"/v1/workspaces/{wid}/cases", json={"name": f"PDF fixture {index + 1}"}
            )
            r.raise_for_status()
            c = r.json()
            route = f"/v1/cases/{c['id']}/documents"
            params = {"expected_revision": c["revision"], "name": f"fixture-{index + 1}.pdf"}
            uploaded = client.post(
                route,
                params=params,
                content=files[name],
                headers={"Content-Type": "application/pdf"},
            )
            check(
                "bounded upload accepted or explicit input rejection",
                uploaded.status_code in {200, 409, 422},
            )
            outcome = {
                "archive_member": name,
                "bytes": len(files[name]),
                "status": uploaded.status_code,
            }
            report["documents"].append(outcome)
            if uploaded.status_code != 200:
                continue
            c = uploaded.json()
            doc = client.get(f"/v1/documents/{c['document_id']}").json()
            outcome.update(
                {"complete": doc["complete"], "gaps": doc["gaps"], "pages": len(doc["pages"])}
            )
            original = client.get(f"/v1/documents/{c['document_id']}/file")
            check(
                "original bytes round trip",
                original.status_code == 200
                and byte_hash(original.content) == byte_hash(files[name]) == doc["bytes_hash"],
            )
            check(
                "original Unicode source ranges resolve",
                digest(doc["text"]) == doc["text_hash"]
                and all(doc["text"][s["start"] : s["end"]] == s["quote"] for s in doc["spans"]),
            )
            with httpx.Client(base_url=client.base_url, timeout=30) as anonymous:
                check(
                    "anonymous source bytes denied",
                    anonymous.get(f"/v1/documents/{c['document_id']}/file").status_code == 401,
                )
            stale = client.post(
                route,
                params=params,
                content=files[name],
                headers={"Content-Type": "application/pdf"},
            )
            check("stale upload cannot replace newer revision", stale.status_code == 409)
            with ThreadPoolExecutor(max_workers=4) as pool:
                statuses = list(
                    pool.map(
                        lambda _, cid=c["id"]: client.get(f"/v1/cases/{cid}").status_code, range(8)
                    )
                )
            check("concurrent authenticated reads succeed", statuses == [200] * 8)
            print(
                "PDF HTTP", index + 1, uploaded.status_code, "complete", doc["complete"], flush=True
            )
        report["finished_at"] = now()
        report["summary"] = {
            "documents": len(report["documents"]),
            "accepted": sum(d["status"] == 200 for d in report["documents"]),
            "checks": len(report["checks"]),
            "failures": sum(not c["passed"] for c in report["checks"]),
        }
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
