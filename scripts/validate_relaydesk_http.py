"""Authenticated loopback service journey with captured real public data; own isolated test case."""

import argparse
import json
import secrets
import time
from pathlib import Path

import httpx
from dev_stack import environment
from relaydesk_api.common import now
from relaydesk_api.ingest import GithubSources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--port", type=int, default=8004)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError("Refusing to overwrite validation evidence")
    env = environment()
    username = env.get("RELAYDESK_USERNAME") or env.get("TENDERLENS_USERNAME")
    password = env.get("RELAYDESK_PASSWORD") or env.get("TENDERLENS_PASSWORD")
    capture = Path(args.capture)
    rows = json.loads((capture / "manifest.json").read_text())
    from relaydesk_api.common import file_hash

    def request(url):
        row = next(r for r in rows if r["url"] == url)
        path = capture / row["path"]
        assert file_hash(path) == row["sha256"]
        return json.loads(path.read_text())

    batch = GithubSources(request=request).fetch("elastic/elasticsearch", 90216)
    base = f"http://127.0.0.1:{args.port}"
    a, b, outsider = [httpx.Client(base_url=base, timeout=30) for _ in range(3)]
    report = {
        "started_at": now(),
        "scope": "Real HTTP engineering journey; not browser acceptance",
        "checks": [],
    }

    def check(name, condition):
        assert condition, name
        report["checks"].append(name)

    check("static UI served", a.get("/").status_code == 200)
    check("unauthenticated cases rejected", a.get("/v1/cases").status_code == 401)
    for client in [a, b]:
        response = client.post(
            "/v1/auth/session", json={"username": username, "password": password}
        )
        response.raise_for_status()
        client.headers["X-CSRF-Token"] = response.json()["csrf"]
    check(
        "two independent authenticated sessions",
        a.headers["X-CSRF-Token"] != b.headers["X-CSRF-Token"],
    )
    account = a.post(
        "/v1/accounts", json={"name": "RelayDesk HTTP real-data validation " + now()}
    ).json()
    case = a.post(
        f"/v1/accounts/{account['id']}/cases", json={"name": "Elasticsearch #90216 · real evidence"}
    ).json()
    cid = case["id"]
    report["case_id"] = cid
    result = a.post(f"/v1/cases/{cid}/imports", json=batch.model_dump()).json()
    check("10 real messages imported", result["inserted"] == 10)
    check(
        "reimport deduplicated",
        a.post(f"/v1/cases/{cid}/imports", json=batch.model_dump()).json()["inserted"] == 0,
    )
    check(
        "cross-origin mutation rejected",
        a.post(
            "/v1/accounts", json={"name": "bad"}, headers={"Origin": "https://attacker.invalid"}
        ).status_code
        == 403,
    )
    check(
        "missing CSRF rejected",
        httpx.post(base + "/v1/accounts", json={"name": "bad"}, cookies=a.cookies).status_code
        == 403,
    )
    for _ in range(30):
        readiness = b.get(f"/v1/cases/{cid}/readiness").json()
        if readiness["semantic_ready"]:
            break
        time.sleep(1)
    check(
        "asynchronous genuine semantic indexing ready",
        readiness["indexed"] == 10 and readiness["semantic_ready"],
    )
    conversation = a.post(f"/v1/cases/{cid}/conversations", json={}).json()
    new_session = b.post(f"/v1/conversations/{conversation['id']}/sessions", json={}).json()
    check(
        "new interactive session has distinct ID",
        new_session["id"] != conversation["session"]["id"],
    )
    job = b.post(
        f"/v1/conversations/{conversation['id']}/messages",
        json={
            "session_id": new_session["id"],
            "content": "What failure and attempted workaround were reported?",
        },
        headers={"Idempotency-Key": "http-real-data"},
    ).json()
    for _ in range(30):
        result = a.get("/v1/jobs/" + job["id"]).json()
        if result["status"] not in ["queued", "running"]:
            break
        time.sleep(1)
    check(
        "fresh-session recall returns partial evidence when egress denied",
        result["status"] == "partial"
        and result["output"]["payload"]["recall"]["mode"] == "semantic_hybrid"
        and result["model_calls"] == 0,
    )
    oid = result["output_id"]
    check(
        "unreviewed export blocked",
        a.post(f"/v1/handovers/{oid}/exports", json={}).status_code == 409,
    )
    check(
        "review acknowledged partial limitations",
        a.post(f"/v1/handovers/{oid}/reviews", json={"acknowledge_limits": True}).status_code
        == 200,
    )
    exported = a.post(f"/v1/handovers/{oid}/exports", json={})
    check(
        "reviewed Markdown retains limitations",
        exported.status_code == 200 and "Limits" in exported.text,
    )
    memories = a.get(f"/v1/cases/{cid}/memories").json()["items"]
    memory = memories[0]
    correction = {
        "expected_revision": memory["revision"],
        "text": "Reported only: source review remains necessary.",
        "kind": "open_question",
        "state": "proposed",
        "reason": "HTTP validation correction",
    }
    check(
        "revision-bound correction accepted",
        a.post(f"/v1/memories/{memory['id']}/corrections", json=correction).status_code == 200,
    )
    check(
        "stale concurrent edit rejected",
        b.post(f"/v1/memories/{memory['id']}/corrections", json=correction).status_code == 409,
    )
    check(
        "second session sees latest revision",
        b.get(f"/v1/cases/{cid}").json()["revision"] > case["revision"],
    )
    check(
        "old reviewed export invalidated",
        a.post(f"/v1/handovers/{oid}/exports", json={}).status_code == 409,
    )
    actor = "http-outsider-" + secrets.token_hex(4)
    actor_password = secrets.token_urlsafe(24)
    check(
        "separate test actor provisioned",
        a.post("/v1/users", json={"username": actor, "password": actor_password}).status_code
        == 200,
    )
    outsider.post("/v1/auth/session", json={"username": actor, "password": actor_password})
    check(
        "other actor denied source/case access",
        outsider.get(f"/v1/cases/{cid}").status_code == 403
        and outsider.get("/v1/sources/" + memory["source_id"]).status_code == 403,
    )
    report["readiness"] = readiness
    report["finished_at"] = now()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    for client in [a, b, outsider]:
        client.close()


if __name__ == "__main__":
    main()
