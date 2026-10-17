"""Authenticated live HTTP journey on real NDA text with labelled fixture decisions."""

import argparse
import json
import secrets
import time
from pathlib import Path

import httpx
from clausegate_api.common import byte_hash, now
from dev_stack import environment


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", default="var/validation/clausegate-corpus-v2")
    p.add_argument("--output", required=True)
    p.add_argument(
        "--natural-ai",
        action="store_true",
        help="Use one actual model analysis rather than gold-seeded manual findings; subsequent responses remain explicit automated human-input fixtures",
    )
    args = p.parse_args()
    target = Path(args.output)
    if target.exists():
        raise ValueError("New output path required")
    corpus = Path(args.corpus)
    manifest = json.loads((corpus / "manifest.json").read_text())
    path = corpus / "evaluator-only.json"
    if byte_hash(path.read_bytes()) != manifest["normalized_sha256"]:
        raise ValueError("Corpus integrity failure")
    rows = json.loads(path.read_text())
    row = (
        min((r for r in rows if r["split"] == "dev"), key=lambda r: len(r["document"]["text"]))
        if args.natural_ai
        else next(r for r in rows if r["split"] == "train")
    )
    env = environment()
    username = env.get("CLAUSEGATE_USERNAME") or env.get("TENDERLENS_USERNAME")
    password = env.get("CLAUSEGATE_PASSWORD") or env.get("TENDERLENS_PASSWORD")
    client = httpx.Client(base_url="http://127.0.0.1:8005", timeout=30)
    reviewer = httpx.Client(base_url=client.base_url, timeout=30)
    report = {
        "started_at": now(),
        "classification": "Real source; gold-derived manual/approval fixtures, not legal review or AI quality",
        "checks": [],
    }

    def check(name, passed):
        report["checks"].append({"name": name, "passed": bool(passed)})
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if not passed:
            raise AssertionError(name)

    check("static web UI served", client.get("/").status_code == 200)
    check("anonymous cases denied", client.get("/v1/cases").status_code == 401)
    login = client.post("/v1/auth/session", json={"username": username, "password": password})
    login.raise_for_status()
    client.headers["X-CSRF-Token"] = login.json()["csrf"]
    name, secret = "http-reviewer-" + secrets.token_hex(4), secrets.token_urlsafe(24)
    check(
        "separate reviewer provisioned",
        client.post("/v1/users", json={"username": name, "password": secret}).status_code == 200,
    )
    auth = reviewer.post("/v1/auth/session", json={"username": name, "password": secret})
    auth.raise_for_status()
    reviewer.headers["X-CSRF-Token"] = auth.json()["csrf"]
    wid = client.post(
        "/v1/workspaces", json={"name": "HTTP implementation validation " + now()}
    ).json()["id"]
    c = client.post(
        f"/v1/workspaces/{wid}/cases", json={"name": "Real ContractNLI HTTP approval fixture"}
    ).json()
    cid = c["id"]
    report["case_id"], report["source_id"] = cid, row["id"]
    check("ungranted separate identity denied", reviewer.get(f"/v1/cases/{cid}").status_code == 403)
    grant = client.put(
        f"/v1/workspaces/{wid}/members",
        json={
            "username": name,
            "roles": ["reviewer", "approver", "final_reviewer"],
            "case_ids": [cid],
        },
    )
    check("case-scoped capabilities granted", grant.status_code == 200)
    c = client.get(f"/v1/cases/{cid}").json()
    h = next(iter(row["hypotheses"]))
    c = client.put(
        f"/v1/cases/{cid}/playbook",
        json={
            "expected_revision": c["revision"],
            "playbook": {
                "name": "Explicit HTTP policy fixture, not legal advice",
                "rules": [
                    {
                        "id": h,
                        "hypothesis": row["hypotheses"][h]["hypothesis"],
                        "action": "require_exception",
                    }
                ],
            },
        },
    ).json()
    c = client.put(
        f"/v1/cases/{cid}/context",
        json={
            "expected_revision": c["revision"],
            "side": "recipient",
            "purpose": "Controlled public-source HTTP workflow",
        },
    ).json()
    c = client.post(
        f"/v1/cases/{cid}/imports",
        json={
            "expected_revision": c["revision"],
            "name": row["document"]["name"],
            "text": row["document"]["text"],
        },
    ).json()
    check("actual NDA text imported", bool(c.get("document_id")))
    doc = reviewer.get(f"/v1/documents/{c['document_id']}").json()
    check("original source hash preserved", doc["text_hash"] == row["document"]["text_hash"])
    gold = row["gold"][h]
    ranges = [row["gold_spans"][i] for i in gold["spans"]]
    ids = [
        s["id"]
        for s in doc["spans"]
        if any(s["start"] < end and s["end"] > start for start, end in ranges)
    ]
    if args.natural_ai:
        c = client.put(
            f"/v1/cases/{cid}/egress", json={"expected_revision": c["revision"], "allowed": True}
        ).json()
        queued = client.post(
            f"/v1/cases/{cid}/analyses",
            json={"expected_revision": c["revision"], "key": "natural-http"},
        )
        check("natural provider job queued through HTTP", queued.status_code == 200)
        for _ in range(150):
            c = client.get(f"/v1/cases/{cid}").json()
            if c["state"] in {"waiting_human", "partial"}:
                break
            time.sleep(1)
        report["natural_model_proposal"] = c["findings"]
        report["source_id"] = row["id"]
        report["classification"] = (
            "Real public NDA and natural installed-model proposal through HTTP; automated reviewer/approval/final-review fixtures, NOT real people or legal approval"
        )
        check("natural provider reaches durable pause", c["state"] == "waiting_human")
        pending = next(r for r in c["requests"] if r["state"] == "pending")
        if pending["kind"] == "interpretation":
            confirmed = reviewer.post(
                f"/v1/approval-requests/{pending['id']}/decisions",
                json={
                    "expected_revision": pending["revision"],
                    "binding": pending["binding"],
                    "kind": "confirm_interpretation",
                    "rationale": "Automated transition fixture only; NOT qualified review of the natural model answer",
                    "key": "natural-confirm",
                },
            )
            check("typed interpretation response accepted", confirmed.status_code == 200)
            c = client.get(f"/v1/cases/{cid}").json()
    else:
        c = reviewer.post(
            f"/v1/cases/{cid}/findings",
            json={
                "expected_revision": c["revision"],
                "findings": [
                    {
                        "check_id": h,
                        "label": gold["choice"],
                        "evidence_ids": ids[:30],
                        "assessment": "supported",
                        "rationale": "Gold-derived HTTP fixture, not natural AI output",
                    }
                ],
                "rationale": "Explicit controlled fixture review",
            },
        ).json()
    check("durable human pause", c["state"] == "waiting_human")
    r = next(r for r in c["requests"] if r["state"] == "pending")
    decision = {
        "expected_revision": r["revision"],
        "binding": r["binding"],
        "kind": "approve_exception",
        "rationale": "Explicit fixture approval for mechanical validation",
        "key": "decision",
    }
    check(
        "requester self-approval denied",
        client.post(f"/v1/approval-requests/{r['id']}/decisions", json=decision).status_code == 403,
    )
    check(
        "cross-origin mutation denied",
        reviewer.post(
            f"/v1/approval-requests/{r['id']}/decisions",
            headers={"Origin": "https://attacker.example"},
            json=decision,
        ).status_code
        == 403,
    )
    csrf = reviewer.headers.pop("X-CSRF-Token")
    check(
        "missing CSRF denied",
        reviewer.post(f"/v1/approval-requests/{r['id']}/decisions", json=decision).status_code
        == 403,
    )
    reviewer.headers["X-CSRF-Token"] = csrf
    saved = reviewer.post(f"/v1/approval-requests/{r['id']}/decisions", json=decision)
    check("scoped typed reviewer response committed", saved.status_code == 200)
    replay = reviewer.post(f"/v1/approval-requests/{r['id']}/decisions", json=decision)
    check(
        "duplicate decision idempotent",
        replay.status_code == 200 and replay.json()["id"] == saved.json()["id"],
    )
    until = time.monotonic() + 15
    while time.monotonic() < until:
        c = client.get(f"/v1/cases/{cid}").json()
        if c["state"] == "review_ready":
            break
        time.sleep(0.2)
    check("real worker resumes with validated context", c["state"] == "review_ready")
    check("unreviewed export blocked", client.get(f"/v1/cases/{cid}/export").status_code == 409)
    response = reviewer.post(
        f"/v1/cases/{cid}/reviews",
        json={
            "expected_revision": c["revision"],
            "packet_hash": c["packet"]["sha256"],
            "rationale": "Fixture final packet reviewed",
            "acknowledge_limits": True,
        },
    )
    check("final exact-packet review", response.status_code == 200)
    c = response.json()
    exported = client.get(f"/v1/cases/{cid}/export?format=markdown")
    check(
        "reviewed export preserves limits",
        exported.status_code == 200 and "not legal advice" in exported.text.lower(),
    )
    audit = client.get(f"/v1/cases/{cid}/audit").json()
    check(
        "audit verifies input-to-resume lineage",
        audit["verification"]["valid"]
        and any(e["kind"] == "resume_completed" for e in audit["items"]),
    )
    corrected = client.post(
        f"/v1/cases/{cid}/imports",
        json={
            "expected_revision": c["revision"],
            "name": "same-name.txt",
            "text": "A new agreement revision.",
        },
    )
    check("changed source accepted as new revision", corrected.status_code == 200)
    check(
        "old reviewed packet invalidated", client.get(f"/v1/cases/{cid}/export").status_code == 409
    )
    check(
        "old decision form rejected",
        reviewer.post(
            f"/v1/approval-requests/{r['id']}/decisions",
            json={**decision, "key": "stale-new-action"},
        ).status_code
        == 409,
    )
    report["finished_at"] = now()
    report["summary"] = {
        "checks": len(report["checks"]),
        "failed": [c for c in report["checks"] if not c["passed"]],
        "browser_acceptance": "NOT PERFORMED",
    }
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
