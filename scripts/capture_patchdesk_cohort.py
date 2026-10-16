"""Acquire a larger public, repository-split evaluation cohort without executing projects."""

import argparse
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from contracts.patchdesk import CapabilityRequest
from patchdesk_api.adapters import Sources, Transport
from patchdesk_api.common import digest, now
from patchdesk_api.corpus import freeze, load_capture
from patchdesk_api.inventory import parse_inventory
from patchdesk_api.reconcile import fixed_versions

# Predeclared discovery order; exclusions/failures are retained, not silently replaced.
REPOSITORIES = [
    "expressjs/expressjs.com",
    "node-red/node-red",
    "chartjs/Chart.js",
    "markedjs/marked",
    "highlightjs/highlight.js",
    "mozilla/pdf.js",
    "videojs/video.js",
    "microsoft/TypeScript",
    "rollup/rollup",
    "acornjs/acorn",
    "eslint/eslint",
    "jquery/jquery",
    "jashkenas/underscore",
    "jashkenas/backbone",
    "caolan/async",
    "tj/commander.js",
    "expressjs/morgan",
    "expressjs/cors",
    "http-party/http-server",
    "jshttp/mime-types",
    "pugjs/pug",
    "nock/nock",
    "socketio/socket.io",
    "d3/d3",
    "SortableJS/Sortable",
    "sweetalert2/sweetalert2",
    "react-bootstrap/react-bootstrap",
    "testing-library/dom-testing-library",
    "fastify/fastify",
    "sinonjs/sinon",
    "remy/nodemon",
    "websockets/ws",
]


def split_repositories(projects):
    repos = sorted(
        {p["repository"] for p in projects}, key=lambda x: digest(["patchdesk-cohort-1", x])
    )
    return {
        repo: "development" if i < 10 else "calibration" if i < 14 else "held_out"
        for i, repo in enumerate(repos)
    }


def acquire(destination, parent, target=40):
    if Path(destination).exists():
        raise ValueError("Use a new capture directory")
    base = load_capture(parent)
    projects = list(base["projects"])
    failures = list(base.get("failures", []))
    attempts = Counter()

    def reserve(counter, amount):
        attempts[counter] += amount
        if attempts["http_attempts"] > 2500 or attempts["acquired_bytes"] > 256 * 1024**2:
            raise ValueError("Evaluation acquisition allowance exceeded")

    transport = Transport(reserve=reserve, deadline=time.monotonic() + 3600)
    # Individual transports retain the 64 MiB ceiling; use distinct stages below.
    for repo in REPOSITORIES:
        if len(projects) >= target:
            break
        try:
            commits = transport.request(
                f"https://api.github.com/repos/{repo}/commits?path=package-lock.json&per_page=2"
            )
            if not isinstance(commits, list) or len(commits) < 2:
                raise ValueError("Two root-lockfile commits unavailable")
            pair = []
            for entry in commits:
                commit = entry["sha"]
                manifest = transport.request(
                    f"https://raw.githubusercontent.com/{repo}/{commit}/package.json"
                )
                lock = transport.request(
                    f"https://raw.githubusercontent.com/{repo}/{commit}/package-lock.json"
                )
                inventory = parse_inventory(manifest, lock)
                pair.append(
                    {
                        "repository": repo,
                        "ref": commit,
                        "commit": commit,
                        "manifest": manifest,
                        "lockfile": lock,
                        "inventory_entries": inventory["entry_count"],
                        "inventory_hash": inventory["sha256"],
                        "parser_gaps": inventory["gaps"],
                        "selection": "two latest commits touching the root lockfile at acquisition",
                    }
                )
            projects.extend(pair)
            print(f"Captured {repo}: {[p['inventory_entries'] for p in pair]}", flush=True)
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append(
                {
                    "repository": repo,
                    "ref": "latest-two-lockfile-commits",
                    "error": str(error)[:180],
                }
            )
            print(f"Excluded {repo}: {str(error)[:100]}", flush=True)
    splits = split_repositories(projects)
    for project in projects:
        project["split"] = splits[project["repository"]]
    # Save acquisition independently before collecting source evidence.
    inputs = {
        "kind": "actual-public-data",
        "created_at": now(),
        "projects": projects,
        "failures": failures,
        "lookup": None,
        "snapshots": {},
        "selection_order": REPOSITORIES,
        "split_policy": "stable repository hash: 10 development / 4 calibration / remainder held out",
    }
    freeze(str(destination) + "-inputs", inputs)
    sources = Sources(transport=Transport(reserve=reserve, deadline=time.monotonic() + 3600))
    inventories = [parse_inventory(p["manifest"], p["lockfile"]) for p in projects]
    pairs = sorted(
        {
            (p["name"], p["version"])
            for inv in inventories
            for p in inv["packages"]
            if p["source_type"] != "private_or_unknown"
        }
    )
    lookups = []
    for start in range(0, len(pairs), 2000):
        request = CapabilityRequest(
            capability="advisories.lookup",
            arguments={
                "packages": [{"name": n, "version": v} for n, v in pairs[start : start + 2000]]
            },
        )
        lookups.append(sources.execute("osv", request))
        freeze(str(destination) + f"-lookup-{start:05d}", lookups[-1])
        print(
            f"Queried {min(start + 2000, len(pairs))}/{len(pairs)} public version pairs", flush=True
        )
    lookup_records = [row for lookup in lookups for row in lookup["records"]]
    # Evaluation index, NOT a single dispatched ToolResult. Each original bounded
    # batch is independently typed/hash-validated and preserved in lookup_batches.
    lookup = {
        "records": lookup_records,
        "raw": [l["raw"] for l in lookups],
        "completeness": "complete_for_query"
        if all(l["completeness"] == "complete_for_query" for l in lookups)
        else "truncated",
    }
    aids = {}
    for row in lookup_records:
        for aid in row["advisory_ids"]:
            aids.setdefault(aid, set()).add(row["package"])
    snapshots = {}

    def capture(job):
        adapter, cap, args = job
        request = CapabilityRequest(capability=cap, arguments=args)
        return digest([adapter, request.model_dump()]), {
            "request": request.model_dump(),
            "result": sources.execute(adapter, request),
        }

    def batch(jobs):
        with ThreadPoolExecutor(max_workers=2) as pool:
            for key, value in pool.map(capture, jobs):
                snapshots[key] = value

    batch(
        [
            ("osv", "advisories.detail", {"id": aid, "package": min(names)})
            for aid, names in sorted(aids.items())[:1000]
        ]
    )
    print(f"Captured {len(snapshots)} advisory details", flush=True)
    details = {
        v["request"]["arguments"]["id"]: v["result"]["records"][0]
        for v in snapshots.values()
        if v["result"]["records"]
    }
    query_map = {(r["package"], r["version"]): r["advisory_ids"] for r in lookup_records}
    release_pairs = set()
    cvemap = {}
    for inv in inventories:
        installed = sorted(
            {
                (p["name"], p["version"])
                for p in inv["packages"]
                if p["source_type"] != "private_or_unknown"
            }
        )
        release_pairs.update(installed[:12])
        versions = {}
        selected = sorted({a for pair in installed[:2000] for a in query_map.get(pair, [])})[:60]
        for aid in selected:
            record = details.get(aid, {})
            for name in {n for n, _ in installed}:
                versions.setdefault(name, set()).update(fixed_versions(record, name))
            for alias in record.get("aliases", []):
                if alias.startswith("CVE-"):
                    cvemap.setdefault(alias, min(aids.get(aid, {"axios"})))
        targets = [
            (n, v)
            for n, values in sorted(versions.items())
            for v in sorted(values)
            if (n, v) not in installed
        ][:16]
        release_pairs.update(targets)
    batch(
        [
            ("npm", "releases.lookup", {"package": n, "version": v})
            for n, v in sorted(release_pairs)[:1000]
        ]
    )
    # Target-version advisory lookup is essential; a fix for one CVE can introduce another match.
    target_pairs = sorted(release_pairs - set(pairs))
    for start in range(0, len(target_pairs), 2000):
        req = CapabilityRequest(
            capability="advisories.lookup",
            arguments={
                "packages": [
                    {"name": n, "version": v} for n, v in target_pairs[start : start + 2000]
                ]
            },
        )
        result = sources.execute("osv", req)
        lookup["records"].extend(result["records"])
        lookup["raw"].append(result["raw"])
        if result["completeness"] != "complete_for_query":
            lookup["completeness"] = "truncated"
            lookup["outcome"] = "partial"
    lookup["sha256"] = digest(lookup["raw"])
    batch(
        [
            ("epss", "threat.epss", {"package": name, "cve": cve})
            for cve, name in sorted(cvemap.items())[:100]
        ]
    )
    batch(
        [
            (
                "github_advisory",
                "advisories.detail",
                {"package": "axios", "id": "GHSA-jr5f-v2jv-69x6"},
            ),
            (
                "github_publisher",
                "advisories.detail",
                {"package": "axios", "id": "GHSA-jr5f-v2jv-69x6"},
            ),
        ]
    )
    payload = {
        **inputs,
        "lookup": lookup,
        "lookup_batches": lookups,
        "snapshots": snapshots,
        "query_count": len(pairs),
        "target_queries": len(target_pairs),
        "detail_count": len(aids),
        "detail_cap": 1000,
        "release_count": len(release_pairs),
        "release_cap": 1000,
        "epss_cap": 100,
        "acquisition_counters": dict(attempts),
        "terms": base.get("terms", []),
    }
    freeze(destination, payload)
    print(
        json.dumps(
            {
                "directory": destination,
                "projects": len(projects),
                "repositories": len(splits),
                "entries": sum(p["inventory_entries"] for p in projects),
                "queries": len(pairs),
                "snapshots": len(snapshots),
                "outcomes": dict(Counter(v["result"]["outcome"] for v in snapshots.values())),
                "attempts": dict(attempts),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    parser.add_argument("--parent", default="var/patchdesk-corpus/20261015-expanded")
    parser.add_argument("--count", type=int, default=40, choices=range(12, 61, 2))
    args = parser.parse_args()
    acquire(args.destination, args.parent, args.count)
