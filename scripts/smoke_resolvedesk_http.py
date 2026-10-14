"""Check the actual loopback API, built UI, worker, and clarification export."""

import argparse
import base64
import json
import re
import time
import urllib.request
from urllib.parse import urlsplit

from dev_stack import environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8001")
    args = parser.parse_args()
    parts = urlsplit(args.url)
    if parts.scheme != "http" or parts.hostname not in ("127.0.0.1", "localhost"):
        raise SystemExit("This smoke script sends credentials only to loopback HTTP")
    config = environment()
    username = config.get("RESOLVEDESK_USERNAME") or config.get("TENDERLENS_USERNAME")
    password = config.get("RESOLVEDESK_PASSWORD") or config.get("TENDERLENS_PASSWORD")
    if not username or not password:
        raise SystemExit("Configure local application credentials first")
    token = base64.b64encode(f"{username}:{password}".encode()).decode()

    def request(path, method="GET", value=None, headers=None):
        data = json.dumps(value).encode() if value is not None else None
        req = urllib.request.Request(
            args.url + path,
            data=data,
            method=method,
            headers={
                "Authorization": "Basic " + token,
                "Content-Type": "application/json",
                **(headers or {}),
            },
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode()
            return (
                json.loads(body)
                if "application/json" in response.headers.get("Content-Type", "")
                else body
            )

    html = request("/")
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
    if not assets:
        raise SystemExit("Built UI asset references are missing")
    for asset in assets:
        request(asset)
    case = request(
        "/v1/cases",
        "POST",
        {
            "title": "Smoke check: missing client version",
            "question": "pg_dump reports a version mismatch; which version details should I provide?",
            "server_version": "17",
            "client_version": None,
            "os": "Windows",
        },
    )
    run = request(f"/v1/cases/{case['id']}/runs", "POST", headers={"Idempotency-Key": "http-smoke"})
    deadline = time.monotonic() + 30
    while run["status"] in ("queued", "running") and time.monotonic() < deadline:
        time.sleep(1)
        run = request(f"/v1/runs/{run['id']}")
    if run["status"] != "needs_clarification":
        raise SystemExit(f"Expected a clarification result, received {run['status']}")
    exported = request(
        f"/v1/answers/{run['answer']['id']}/exports", "POST", {"format": "json", "escalation": True}
    )
    assert exported["kind"] == "escalation" and exported["questions"]
    print(
        json.dumps(
            {
                "ui_assets": len(assets),
                "case_id": case["id"],
                "run_id": run["id"],
                "status": run["status"],
                "escalation_export": "passed",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
