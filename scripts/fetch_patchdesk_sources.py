"""Capture real public npm project snapshots and official advisory/release data; never execute them."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from contracts.patchdesk import CapabilityRequest
from patchdesk_api.adapters import Sources, Transport
from patchdesk_api.common import digest, now
from patchdesk_api.corpus import freeze, load_capture
from patchdesk_api.inventory import parse_inventory

SEEDS = [
    ("npm/cli", "v10.8.2"),
    ("npm/cli", "v10.9.0"),
    ("axios/axios", "v1.7.9"),
    ("axios/axios", "v1.8.2"),
    ("npm/node-semver", "v7.6.3"),
    ("npm/node-semver", "v7.7.2"),
    ("npm/npm-package-arg", "v11.0.3"),
    ("npm/npm-package-arg", "v12.0.2"),
    ("npm/pacote", "v18.0.6"),
    ("npm/pacote", "v19.0.1"),
    ("typicode/json-server", "v0.17.4"),
    ("postmanlabs/newman", "v6.2.1"),
    ("hakimel/reveal.js", "5.1.0"),
    ("hakimel/reveal.js", "5.2.1"),
    ("postmanlabs/newman", "v6.1.2"),
    ("typicode/json-server", "v0.17.3"),
]


def acquire(destination, count=10, parent=None):
    if Path(destination).exists():
        raise ValueError("Use a new corpus directory")
    transport = Transport(deadline=__import__("time").monotonic() + 1800)
    source = Sources(transport=transport)
    previous = load_capture(parent) if parent else {}
    projects, failures = list(previous.get("projects", [])), list(previous.get("failures", []))
    for repo, ref in SEEDS:
        if len(projects) >= count:
            break
        if any(p["repository"] == repo and p["ref"] == ref for p in projects) or any(
            p["repository"] == repo and p["ref"] == ref for p in failures
        ):
            continue
        try:
            commit = transport.request(f"https://api.github.com/repos/{repo}/commits/{ref}")["sha"]
            values = {
                name: transport.request(f"https://raw.githubusercontent.com/{repo}/{commit}/{name}")
                for name in ("package.json", "package-lock.json")
            }
            inventory = parse_inventory(values["package.json"], values["package-lock.json"])
            projects.append(
                {
                    "repository": repo,
                    "ref": ref,
                    "commit": commit,
                    "manifest": values["package.json"],
                    "lockfile": values["package-lock.json"],
                    "inventory_hash": inventory["sha256"],
                    "inventory_entries": inventory["entry_count"],
                    "parser_gaps": inventory["gaps"],
                }
            )
            print(f"Captured {repo}@{ref}: {inventory['entry_count']} entries", flush=True)
        except (OSError, ValueError, KeyError) as error:
            failures.append({"repository": repo, "ref": ref, "error": type(error).__name__})
            print(f"Capture unavailable: {repo}@{ref}: {type(error).__name__}", flush=True)
    queries = sorted(
        {
            (p["name"], p["version"])
            for project in projects
            for p in parse_inventory(project["manifest"], project["lockfile"])["packages"]
            if p["source_type"] != "private_or_unknown"
        }
    )
    lookup = (
        source.execute(
            "osv",
            CapabilityRequest(
                capability="advisories.lookup",
                arguments={
                    "packages": [
                        {"name": name, "version": version} for name, version in queries[:2000]
                    ]
                },
            ),
        )
        if queries
        else None
    )
    snapshots = {}

    def capture(adapter, capability, arguments):
        req = CapabilityRequest(capability=capability, arguments=arguments)
        key = digest([adapter, req.model_dump()])
        return key, {"request": req.model_dump(), "result": source.execute(adapter, req)}

    aids = sorted(
        {aid for row in (lookup or {}).get("records", []) for aid in row["advisory_ids"]}
    )[:60]
    jobs = [
        (
            "osv",
            "advisories.detail",
            {
                "id": aid,
                "package": next(
                    row["package"] for row in lookup["records"] if aid in row["advisory_ids"]
                ),
            },
        )
        for aid in aids
    ]
    seed = "GHSA-jr5f-v2jv-69x6"
    jobs.extend(
        (adapter, "advisories.detail", {"id": seed, "package": "axios"})
        for adapter in ("osv", "github_advisory", "github_publisher")
    )
    jobs.extend(
        ("npm", "releases.lookup", {"package": "axios", "version": version})
        for version in ("1.7.9", "1.8.1", "1.8.2")
    )
    jobs.append(("epss", "threat.epss", {"package": "axios", "cve": "CVE-2025-27152"}))
    with ThreadPoolExecutor(max_workers=4) as executor:
        for key, value in executor.map(lambda job: capture(*job), jobs):
            snapshots[key] = value
    payload = {
        "created_at": now(),
        "kind": "actual-public-data",
        "projects": projects,
        "failures": failures,
        "lookup": lookup,
        "snapshots": snapshots,
        "query_count": len(queries),
        "query_cap": 2000,
        "advisory_detail_cap": 60,
        "terms": [
            "Repository file licenses apply; raw capture remains ignored",
            "Upstream OSV/GitHub/npm/FIRST terms and attribution apply",
        ],
    }
    freeze(destination, payload)
    print(
        f"Frozen {len(projects)} snapshots / {len({p['repository'] for p in projects})} repositories at {destination}"
    )
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    parser.add_argument("--count", type=int, default=10, choices=range(1, 11))
    parser.add_argument("--parent")
    args = parser.parse_args()
    acquire(args.destination, args.count, args.parent)
