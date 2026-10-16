"""Session/CSRF HTTP acceptance; opt-in real public-source/model maintenance journey."""

import argparse
import hashlib
import json
import re
import time
import uuid
from pathlib import Path

import httpx
from dev_stack import environment
from patchdesk_api.corpus import load_capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8003")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--corpus", default="var/patchdesk-corpus/20261015-expanded")
    parser.add_argument("--repository", default="postmanlabs/newman")
    args = parser.parse_args()
    env = environment()
    client = httpx.Client(base_url=args.url, timeout=40)
    login = client.post(
        "/v1/session",
        json={
            "username": env.get("PATCHDESK_USERNAME") or env.get("TENDERLENS_USERNAME"),
            "password": env.get("PATCHDESK_PASSWORD") or env.get("TENDERLENS_PASSWORD"),
        },
    )
    login.raise_for_status()
    csrf = login.json()["csrf"]
    client.headers.update({"X-CSRF-Token": csrf})

    def request(method, path, **kwargs):
        if method != "GET" and "json" not in kwargs:
            kwargs["json"] = {}
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
        return response

    assert httpx.get(args.url + "/v1/projects").status_code == 401
    assert (
        client.post(
            "/v1/projects",
            headers={"X-CSRF-Token": "wrong"},
            json={"name": "Must deny", "client": "Testing"},
        ).status_code
        == 403
    )
    assert request("GET", "/health/ready").json()["product"] == "patchdesk"
    html = request("GET", "/").text
    for asset in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html):
        request("GET", asset)
    root = Path(__file__).resolve().parents[1]
    evidence = {
        "code_hashes": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.glob("apps/patchdesk-api/src/**/*.py")
        },
        "live": args.live,
        "checks": [
            "unauthenticated project access denied",
            "invalid CSRF denied",
            "session-authenticated assets served",
        ],
    }
    if args.live:
        capture = load_capture(args.corpus)
        project = request(
            "POST",
            "/v1/projects",
            json={"name": args.repository + " validation", "client": "Public-source acceptance"},
        ).json()
        captured = next(p for p in capture["projects"] if p["repository"] == args.repository)
        artifact = request(
            "POST",
            f"/v1/projects/{project['id']}/inputs",
            json={
                "manifest": captured["manifest"],
                "lockfile": captured["lockfile"],
                "origin": captured["repository"],
                "commit": captured["commit"],
            },
        ).json()
        names = sorted(
            {
                p["name"]
                for p in artifact["payload"]["inventory"]["packages"]
                if p["source_type"] != "private_or_unknown"
            }
        )
        request(
            "PUT",
            f"/v1/projects/{project['id']}/policy",
            json={"expected_revision": 1, "public_packages": names, "model_egress": True},
        )
        run = request(
            "POST",
            f"/v1/projects/{project['id']}/runs",
            json={
                "content": "Prepare a concise maintenance plan grounded in captured advisories. Preserve conflicts, source gaps and unperformed verification."
            },
            headers={"Idempotency-Key": uuid.uuid4().hex},
        ).json()

        def wait(rid):
            deadline = time.monotonic() + 960
            last = None
            while time.monotonic() < deadline:
                value = request("GET", f"/v1/runs/{rid}").json()
                progress = (
                    value["status"],
                    value["actions"],
                    value["model_calls"],
                    value["http_attempts"],
                )
                if progress != last:
                    print("HTTP investigation:", progress, flush=True)
                    last = progress
                if value["status"] not in ("running", "queued"):
                    return value
                time.sleep(2)
            raise TimeoutError("Acceptance wait expired")

        value = wait(run["id"])
        assert value["report"]
        report = value["report"]
        request(
            "POST",
            f"/v1/reports/{report['id']}/reviews",
            json={
                "expected_revision": report["revision"],
                "notes": "HTTP acceptance: source limitations retained; no application security guarantee.",
                "acknowledge_limits": True,
            },
        )
        exported = request("POST", f"/v1/reports/{report['id']}/exports").text
        assert "Coverage and limitations" in exported and "SHA-256" in exported
        json_export = request("POST", f"/v1/reports/{report['id']}/exports?format=json").json()
        assert json_export["report"]["payload"]["gaps"] == report["payload"]["gaps"]
        follow = request(
            "POST",
            f"/v1/projects/{project['id']}/messages",
            json={
                "content": "What verification should an engineer perform before proposing these changes to the client? Use pinned evidence."
            },
            headers={"Idempotency-Key": uuid.uuid4().hex},
        ).json()
        second = wait(follow["id"])
        assert second["report"]
        evidence.update(
            project_id=project["id"],
            first_run={
                k: value[k]
                for k in ("id", "status", "actions", "model_calls", "http_attempts", "stop_reason")
            },
            follow_up={
                k: second[k]
                for k in ("id", "status", "actions", "model_calls", "http_attempts", "stop_reason")
            },
        )
        evidence["checks"] += [
            "real project imported and public/model egress explicitly granted",
            "live source orchestration returned durable report",
            "reviewed Markdown/JSON exports retain gaps/hashes",
            "persistent scoped follow-up returned durable report",
        ]
    directory = Path("var/patchdesk-http-smoke")
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / f"report-{time.time_ns()}.json"
    output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Evidence: {output}")


if __name__ == "__main__":
    main()
