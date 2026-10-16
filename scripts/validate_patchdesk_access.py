"""Live multi-actor authorization against an actual-data validation project; no remote writes."""

import argparse
import json
import secrets
import time
from pathlib import Path

import httpx
from dev_stack import environment


def validate(smoke, url):
    evidence = json.loads(Path(smoke).read_text())
    pid = evidence["project_id"]
    env = environment()
    owner = httpx.Client(base_url=url, timeout=40)
    login = owner.post(
        "/v1/session",
        json={
            "username": env.get("PATCHDESK_USERNAME") or env["TENDERLENS_USERNAME"],
            "password": env.get("PATCHDESK_PASSWORD") or env["TENDERLENS_PASSWORD"],
        },
    )
    login.raise_for_status()
    owner.headers["X-CSRF-Token"] = login.json()["csrf"]
    username = "audit-" + secrets.token_hex(6)
    password = secrets.token_urlsafe(32)
    owner.post("/v1/users", json={"username": username, "password": password}).raise_for_status()
    outsider = httpx.Client(base_url=url, timeout=40)
    signed = outsider.post("/v1/session", json={"username": username, "password": password})
    signed.raise_for_status()
    outsider.headers["X-CSRF-Token"] = signed.json()["csrf"]
    run = owner.get("/v1/runs/" + evidence["first_run"]["id"]).json()
    rid = run["id"]
    oid = run["report"]["id"]
    snapshot = next(v["snapshot_id"] for v in run["results"].values() if v.get("snapshot_id"))
    checks = []

    def check(client, method, path, status, **kwargs):
        response = client.request(method, path, **kwargs)
        assert response.status_code == status, (
            method,
            path,
            response.status_code,
            response.text[:200],
        )
        checks.append(
            {"method": method, "route": path, "expected": status, "observed": response.status_code}
        )
        return response

    assert check(outsider, "GET", "/v1/projects", 200).json() == []
    for path in [
        f"/v1/projects/{pid}",
        f"/v1/runs/{rid}",
        f"/v1/reports/{oid}",
        f"/v1/snapshots/{snapshot}",
    ]:
        check(outsider, "GET", path, 403)
    check(outsider, "POST", f"/v1/reports/{oid}/exports", 403, json={})
    check(
        owner,
        "PUT",
        f"/v1/projects/{pid}/members",
        200,
        json={"username": username, "roles": ["reviewer"]},
    )
    check(outsider, "GET", f"/v1/projects/{pid}", 200)
    check(outsider, "GET", f"/v1/snapshots/{snapshot}", 200)
    check(
        outsider,
        "POST",
        f"/v1/projects/{pid}/runs",
        403,
        json={"content": "Should not investigate"},
        headers={"Idempotency-Key": secrets.token_hex(12)},
    )
    check(
        outsider,
        "POST",
        f"/v1/reports/{oid}/publication-drafts",
        403,
        json={"title": "Must not publish"},
    )
    check(
        outsider,
        "POST",
        "/v1/users",
        403,
        json={"username": "must-not-create", "password": "must-not-create-password"},
    )
    check(outsider, "PUT", "/v1/admin/registry", 403, json={"adapter": "osv", "enabled": False})
    export = check(outsider, "POST", f"/v1/reports/{oid}/exports?format=json", 200, json={}).json()
    assert export["report"]["payload"]["gaps"]
    check(
        owner, "PUT", f"/v1/projects/{pid}/members", 200, json={"username": username, "roles": []}
    )
    assert check(outsider, "GET", "/v1/projects", 200).json() == []
    check(outsider, "GET", f"/v1/reports/{oid}", 403)
    check(outsider, "GET", "/v1/exports/" + export["id"], 403)
    check(outsider, "DELETE", "/v1/session", 200, json={})
    check(outsider, "GET", "/v1/me", 401)
    owner.request("DELETE", "/v1/session", json={}).raise_for_status()
    target = Path("var/patchdesk-access-validation")
    target.mkdir(parents=True, exist_ok=True)
    output = target / f"report-{time.time_ns()}.json"
    output.write_text(
        json.dumps(
            {
                "kind": "live actual-data project authorization",
                "project_id": pid,
                "checks": checks,
                "external_writes": False,
                "cleanup": "test actor logged out, all project roles revoked; audit account retained, random password not stored",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Passed {len(checks)} live access checks; evidence: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("smoke_report")
    parser.add_argument("--url", default="http://127.0.0.1:8003")
    args = parser.parse_args()
    validate(args.smoke_report, args.url)
