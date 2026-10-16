"""Actual connector reads and live secondary-provider routing with a labelled primary outage."""

import argparse
import asyncio
import json
from pathlib import Path

import httpx
from contracts.patchdesk import CapabilityRequest, InputUpload, ProjectCreate, ProjectPolicy
from dev_stack import environment
from patchdesk_api.adapters import Sources, make_result
from patchdesk_api.corpus import freeze, load_capture
from patchdesk_api.store import Store
from patchdesk_api.worker import Investigation


def validate(corpus, destination, url):
    capture = load_capture(corpus)
    target = Path(destination)
    if target.exists():
        raise ValueError("Choose a new connector validation directory")
    captured = next(p for p in capture["projects"] if p["repository"] == "postmanlabs/newman")
    env = environment()
    client = httpx.Client(base_url=url, timeout=60)
    login = client.post(
        "/v1/session",
        json={
            "username": env.get("PATCHDESK_USERNAME") or env["TENDERLENS_USERNAME"],
            "password": env.get("PATCHDESK_PASSWORD") or env["TENDERLENS_PASSWORD"],
        },
    )
    login.raise_for_status()
    client.headers["X-CSRF-Token"] = login.json()["csrf"]
    source = Sources()
    info = source.request("https://api.github.com/repos/postmanlabs/newman")
    project = client.post(
        "/v1/projects",
        json={
            "name": "Actual repository connector validation",
            "client": "Public-source acceptance",
        },
    )
    project.raise_for_status()
    pid = project.json()["id"]
    policy = client.put(
        f"/v1/projects/{pid}/policy",
        json={
            "expected_revision": 1,
            "repository": "postmanlabs/newman",
            "repository_id": info["id"],
        },
    )
    policy.raise_for_status()
    imported = client.post(
        f"/v1/projects/{pid}/repository-snapshots", json={"ref": captured["commit"]}
    )
    imported.raise_for_status()
    inventory = imported.json()["payload"]["inventory"]
    assert inventory["sha256"] == captured["inventory_hash"]
    assert inventory["entry_count"] == captured["inventory_entries"]
    client.request("DELETE", "/v1/session", json={}).raise_for_status()
    connectors = []
    for adapter, cap, args in [
        ("depsdev", "dependency.context", {"package": "lodash", "version": "4.17.20"}),
        ("epss", "threat.epss", {"package": "lodash", "cve": "CVE-2021-23337"}),
        ("kev", "threat.kev", {"package": "lodash", "cve": "CVE-2021-23337"}),
    ]:
        result = source.execute(adapter, CapabilityRequest(capability=cap, arguments=args))
        connectors.append({"adapter": adapter, "request": args, "result": result})
    # This raw freeze is separate from the isolated durable run store.
    freeze(
        str(target) + "-sources",
        {
            "kind": "actual connector reads",
            "project_id": pid,
            "repository_snapshot": {
                "commit": captured["commit"],
                "input_hash": inventory["sha256"],
                "entries": inventory["entry_count"],
            },
            "connectors": connectors,
        },
    )
    store = Store(target)
    store.add_user("audit", "local-connector-audit-password", admin=True)
    p = store.create_project(
        "audit", ProjectCreate(name="Secondary-provider audit", client="Public validation")
    )
    artifact = store.import_input(
        "audit", p["id"], InputUpload(manifest=captured["manifest"], lockfile=captured["lockfile"])
    )
    packages = artifact["payload"]["inventory"]["packages"]
    public = {row["name"] for row in packages if row["source_type"] != "private_or_unknown"}
    store.update_policy(
        "audit", p["id"], ProjectPolicy(expected_revision=1, public_packages=sorted(public))
    )
    installed = {(r["name"], r["version"]) for r in packages}
    lookup = next(
        r
        for r in capture["lookup"]["records"]
        if (r["package"], r["version"]) in installed and r["advisory_ids"]
    )

    class OutageSources:
        def execute(self, adapter, request):
            if adapter == "osv":
                return make_result(
                    adapter,
                    request.capability,
                    [],
                    None,
                    outcome="unavailable",
                    completeness="unknown",
                    error="Labelled primary-provider outage; secondary read is live",
                )
            return source.execute(adapter, request)

    run = store.enqueue("audit", p["id"], "Check scoped provider failover", "connector", {})
    investigation = Investigation(store, store.claim(), sources=OutageSources())
    asyncio.run(
        investigation.batch(
            [
                (
                    CapabilityRequest(
                        capability="advisories.detail",
                        arguments={"package": lookup["package"], "id": lookup["advisory_ids"][0]},
                    ),
                    None,
                )
            ]
        )
    )
    report = investigation.report(
        reason="Live secondary detail after labelled primary outage; not complete project coverage"
    )
    store.finish(run["id"], investigation.lease, report, "Connector-only validation")
    completed = store.run("audit", run["id"])
    result = next(iter(completed["results"].values()))
    assert result["adapter"] == "github_advisory" and result["outcome"] == "success"
    assert any(e["outcome"] == "failover" for e in completed["events"])
    summary = {
        "kind": "live connectors; primary outage explicitly injected",
        "repository_input": "passed",
        "project_id": pid,
        "fallback_adapter": result["adapter"],
        "fallback_snapshot": result["snapshot_id"],
        "optional_source_outcomes": {c["adapter"]: c["result"]["outcome"] for c in connectors},
        "external_writes": False,
    }
    (target / "report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus")
    parser.add_argument("destination")
    parser.add_argument("--url", default="http://127.0.0.1:8003")
    args = parser.parse_args()
    validate(args.corpus, args.destination, args.url)
