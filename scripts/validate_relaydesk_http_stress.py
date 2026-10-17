"""Bounded authenticated HTTP stress/negative journeys; only a dedicated validation case.

At most eight simultaneous local requests; no stress against public services.
"""

import argparse
import json
import secrets
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from dev_stack import environment
from relaydesk_api.common import file_hash, now
from relaydesk_api.ingest import GithubSources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--capture", default="var/validation/relaydesk-2026-10-16-implementation/raw"
    )
    args = parser.parse_args()
    path = Path(args.output)
    if path.exists():
        raise ValueError("Use a new evidence path")
    report = {"started_at": now(), "checks": [], "load": []}
    env = environment()
    username = env.get("RELAYDESK_USERNAME") or env.get("TENDERLENS_USERNAME")
    password = env.get("RELAYDESK_PASSWORD") or env.get("TENDERLENS_PASSWORD")
    capture = Path(args.capture)
    rows = json.loads((capture / "manifest.json").read_text())

    def source_request(url):
        row = next(r for r in rows if r["url"] == url)
        raw = capture / row["path"]
        if file_hash(raw) != row["sha256"]:
            raise ValueError("Capture hash failure")
        return json.loads(raw.read_text())

    batch = GithubSources(request=source_request).fetch("elastic/elasticsearch", 90216)
    base = "http://127.0.0.1:8004"
    owner = httpx.Client(base_url=base, timeout=30)
    login = owner.post("/v1/auth/session", json={"username": username, "password": password})
    login.raise_for_status()
    owner.headers["X-CSRF-Token"] = login.json()["csrf"]

    def check(name, condition, detail=None):
        report["checks"].append({"name": name, "passed": bool(condition), "detail": detail})
        if not condition:
            print("FAIL", name, flush=True)

    account = owner.post("/v1/accounts", json={"name": "HTTP stress isolated " + now()}).json()
    case = owner.post(
        f"/v1/accounts/{account['id']}/cases", json={"name": "HTTP stress · captured Elasticsearch"}
    ).json()
    cid = case["id"]
    report["case_id"] = cid
    imported = owner.post(f"/v1/cases/{cid}/imports", json=batch.model_dump())
    check("actual source import", imported.status_code == 200)
    actor = "stress-" + secrets.token_hex(4)
    actor_password = secrets.token_urlsafe(24)
    provisioned = owner.post("/v1/users", json={"username": actor, "password": actor_password})
    check("isolated actor provisioned", provisioned.status_code == 200)
    other = httpx.Client(base_url=base, timeout=30)
    response = other.post("/v1/auth/session", json={"username": actor, "password": actor_password})
    response.raise_for_status()
    other.headers["X-CSRF-Token"] = response.json()["csrf"]
    check("ungranted actor denied", other.get(f"/v1/cases/{cid}").status_code == 403)
    grant = owner.put(f"/v1/cases/{cid}/members", json={"username": actor, "roles": ["reviewer"]})
    check("reviewer grant", grant.status_code == 200)
    check(
        "reviewer may inspect but cannot import",
        other.get(f"/v1/cases/{cid}/memories").status_code == 200
        and other.post(f"/v1/cases/{cid}/imports", json=batch.model_dump()).status_code == 403,
    )
    check(
        "reviewer cannot change owner policy",
        other.put(
            f"/v1/cases/{cid}/policy", json={"expected_revision": 1, "model_egress": True}
        ).status_code
        == 403,
    )
    owner.put(f"/v1/cases/{cid}/members", json={"username": actor, "roles": ["investigator"]})
    check(
        "investigator cannot correct memory",
        other.post(
            "/v1/memories/"
            + owner.get(f"/v1/cases/{cid}/memories").json()["items"][0]["id"]
            + "/corrections",
            json={
                "expected_revision": 1,
                "text": "Injected",
                "kind": "episode",
                "state": "reported",
                "reason": "role test",
            },
        ).status_code
        == 403,
    )
    # Eight concurrent workers, 160 read requests over four scoped views.
    cookies = dict(owner.cookies)
    owner.headers["X-CSRF-Token"]

    def read(i):
        routes = [
            f"/v1/cases/{cid}",
            f"/v1/cases/{cid}/memories",
            f"/v1/cases/{cid}/readiness",
            f"/v1/cases/{cid}/changes",
        ]
        started = time.perf_counter()
        try:
            with httpx.Client(base_url=base, cookies=cookies, timeout=30) as client:
                r = client.get(routes[i % 4])
            return {
                "status": r.status_code,
                "milliseconds": (time.perf_counter() - started) * 1000,
                "route": i % 4,
            }
        except httpx.HTTPError as error:
            return {
                "status": 0,
                "category": type(error).__name__,
                "milliseconds": (time.perf_counter() - started) * 1000,
            }

    with ThreadPoolExecutor(max_workers=8) as pool:
        report["load"] = list(pool.map(read, range(160)))
    check(
        "160 bounded concurrent reads avoid errors", all(r["status"] == 200 for r in report["load"])
    )
    owner.put(f"/v1/cases/{cid}/members", json={"username": actor, "roles": []})
    check(
        "revocation blocks cached authenticated session",
        other.get(f"/v1/cases/{cid}/memories").status_code == 403
        and other.get(f"/v1/cases/{cid}/changes").status_code == 403,
    )
    check(
        "cross-origin mutation denied",
        owner.post(
            "/v1/accounts", headers={"Origin": "https://attacker.invalid"}, json={"name": "bad"}
        ).status_code
        == 403,
    )
    check(
        "invalid CSRF denied",
        owner.post(
            "/v1/accounts", headers={"X-CSRF-Token": "bad"}, json={"name": "bad"}
        ).status_code
        == 403,
    )
    check(
        "non-JSON mutation rejected",
        owner.post(
            "/v1/accounts",
            content="name=bad",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ).status_code
        == 415,
    )
    check(
        "malformed JSON rejected",
        owner.post(
            "/v1/accounts", content="{bad", headers={"Content-Type": "application/json"}
        ).status_code
        == 422,
    )
    check(
        "unknown contract fields rejected",
        owner.post("/v1/accounts", json={"name": "bad", "privileged": True}).status_code == 422,
    )
    check(
        "oversized body rejected at gateway",
        owner.post(
            "/v1/accounts",
            content=b" " * (20 * 1024**2 + 1),
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413,
    )
    check(
        "invalid memory pagination rejected",
        owner.get(f"/v1/cases/{cid}/memories?limit=201").status_code == 422,
    )
    traversal = owner.get("/assets/%2e%2e/%2e%2e/.env")
    check("static traversal rejected", traversal.status_code == 404)
    conv = owner.post(f"/v1/cases/{cid}/conversations", json={}).json()
    check(
        "interactive session ownership enforced",
        other.post(
            f"/v1/conversations/{conv['id']}/messages",
            headers={"Idempotency-Key": "foreign"},
            json={"content": "test", "session_id": conv["session"]["id"]},
        ).status_code
        == 403,
    )
    check(
        "missing idempotency key rejected",
        owner.post(
            f"/v1/conversations/{conv['id']}/messages",
            json={"content": "test", "session_id": conv["session"]["id"]},
        ).status_code
        == 422,
    )
    check(
        "logout invalidates authenticated session",
        other.delete("/v1/auth/session").status_code == 200
        and other.get("/v1/me").status_code == 401,
    )
    durations = sorted(r["milliseconds"] for r in report["load"])
    report["summary"] = {
        "checks": len(report["checks"]),
        "failed": [r for r in report["checks"] if not r["passed"]],
        "requests": len(report["load"]),
        "concurrency": 8,
        "p50_ms": statistics.median(durations),
        "p95_ms": durations[int(0.95 * (len(durations) - 1))],
        "measurement_note": "includes fresh HTTP client setup per request; macOS, not Windows SLO acceptance",
    }
    report["finished_at"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    owner.close()
    other.close()
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
