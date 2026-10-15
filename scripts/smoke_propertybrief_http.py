"""Exercise authenticated PropertyBrief HTTP, optionally a real-source AI conversation."""

import argparse
import json
import re
import time
from pathlib import Path

import httpx
from dev_stack import environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8002")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    env = environment()
    auth = (
        env.get("PROPERTYBRIEF_USERNAME") or env.get("TENDERLENS_USERNAME"),
        env.get("PROPERTYBRIEF_PASSWORD") or env.get("TENDERLENS_PASSWORD"),
    )
    client = httpx.Client(base_url=args.url, auth=auth, timeout=35)
    evidence = {"url": args.url, "live": args.live, "checks": []}

    def request(method, path, **kwargs):
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
        return response

    assert httpx.get(args.url + "/v1/cases", timeout=10).status_code == 401
    evidence["checks"].append("unauthorized case access denied")
    assert request("GET", "/health/ready").json()["product"] == "propertybrief"
    html = request("GET", "/").text
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
    assert assets
    for asset in assets:
        request("GET", asset)
    evidence["checks"].append("authenticated HTML and built assets served")
    if args.live:
        case = request(
            "POST",
            "/v1/cases",
            json={"address": "22 FRONT STAGG STREET", "borough": "Brooklyn", "bin": "3327904"},
        ).json()
        case = request("POST", f"/v1/cases/{case['id']}/resolve").json()
        assert any(value["id"] == "375411" for value in case["candidates"])
        request(
            "POST",
            f"/v1/cases/{case['id']}/identity",
            json={"candidate_id": "375411", "expected_revision": case["revision"]},
        )
        import uuid

        run = request(
            "POST", f"/v1/cases/{case['id']}/runs", headers={"Idempotency-Key": str(uuid.uuid4())}
        ).json()

        def wait(rid):
            deadline = time.monotonic() + 960
            previous = None
            while time.monotonic() < deadline:
                result = request("GET", f"/v1/runs/{rid}").json()
                progress = (result["status"], result["actions"], result["model_calls"])
                if progress != previous:
                    print("HTTP investigation:", progress, flush=True)
                    previous = progress
                if result["status"] not in ("queued", "running"):
                    return result
                time.sleep(2)
            raise TimeoutError("HTTP acceptance wait expired")

        result = wait(run["id"])
        assert result["report"], "No durable report after terminal state"
        evidence["case_id"] = case["id"]
        evidence["first_run"] = {
            key: result[key]
            for key in ("id", "status", "actions", "model_calls", "http_attempts", "stop_reason")
        }
        evidence["checks"].append(
            "actual address identity resolution and durable investigation report"
        )
        report = result["report"]
        request(
            "PATCH",
            f"/v1/reports/{report['id']}/review",
            json={
                "expected_revision": report["revision"],
                "notes": "HTTP acceptance: reviewed captured evidence and retained all gaps.",
                "acknowledge_limits": True,
            },
        )
        exported = request(
            "POST", f"/v1/reports/{report['id']}/exports", json={"format": "markdown"}
        ).text
        assert "Coverage and limitations" in exported and "SHA-256" in exported
        evidence["checks"].append("reviewed Markdown export retains coverage and source hashes")
        follow = request(
            "POST",
            f"/v1/cases/{case['id']}/messages",
            headers={"Idempotency-Key": str(uuid.uuid4())},
            json={
                "content": "Which seller documents should we request to clarify the conflicting property identifiers? Use the captured evidence."
            },
        ).json()
        second = wait(follow["id"])
        assert second["report"]
        evidence["follow_up"] = {
            key: second[key] for key in ("id", "status", "actions", "model_calls", "stop_reason")
        }
        evidence["checks"].append("persistent same-property follow-up returned a durable report")
        assert len(request("GET", f"/v1/cases/{case['id']}").json()["messages"]) == 2
    path = Path("var/propertybrief-http-smoke")
    path.mkdir(parents=True, exist_ok=True)
    filename = path / f"report-{time.time_ns()}.json"
    filename.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"HTTP acceptance evidence: {filename}")


if __name__ == "__main__":
    main()
