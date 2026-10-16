"""Large real-data audit with an independent Node semver oracle, not human gold."""

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from patchdesk_api.common import digest, now
from patchdesk_api.corpus import load_capture
from patchdesk_api.inventory import matches, osv_match, parse_inventory


def audit(corpus, destination):
    target = Path(destination)
    if target.exists():
        raise ValueError("Choose a new audit directory")
    payload = load_capture(corpus)
    target.mkdir(parents=True)
    cases = []
    expected = []
    identity_errors = []
    strata = Counter()
    inventory_rows = []
    installed = {}
    raw_entries = 0
    for project in payload["projects"]:
        inv = parse_inventory(project["manifest"], project["lockfile"])
        entries = project["lockfile"]["packages"]
        raw_entries += len(entries)
        strata["lockfile_v" + str(project["lockfile"]["lockfileVersion"])] += 1
        strata["workspace_link_entries"] += sum(bool(v.get("link")) for v in entries.values())
        strata["nested_entries"] += sum(k.count("node_modules/") > 1 for k in entries)
        strata["peer_metadata_entries"] += sum(
            bool(v.get("peerDependencies")) for v in entries.values()
        )
        strata["optional_entries"] += sum(bool(v.get("optional")) for v in entries.values())
        strata["dev_entries"] += sum(bool(v.get("dev")) for v in entries.values())
        for row in inv["packages"]:
            raw = entries[row["location"]]
            if str(raw.get("version", "")) != row["version"] or raw.get("link"):
                identity_errors.append([project["repository"], row["location"]])
            installed.setdefault(row["name"], set()).add(row["version"])
        # Check every captured edge with npm's implementation; no dependency installation.
        versions = {p["location"]: p["version"] for p in inv["packages"]}
        for edge in inv["edges"]:
            spec = edge["constraint"]
            if spec.startswith("npm:"):
                spec = spec.rsplit("@", 1)[-1]
            cases.append({"kind": "npm_constraint", "version": versions[edge["to"]], "spec": spec})
            expected.append(matches(versions[edge["to"]], spec))
        inventory_rows.append(
            {
                "repository": project["repository"],
                "commit": project["commit"],
                "split": project.get("split"),
                "entries": inv["entry_count"],
                "packages": len(inv["packages"]),
                "edges": len(inv["edges"]),
                "gaps": len(inv["gaps"]),
                "gap_categories": dict(Counter(g.split(":")[0] for g in inv["gaps"])),
            }
        )
    advisories = {}
    for value in payload["snapshots"].values():
        if (
            value["result"]["adapter"] == "osv"
            and value["request"]["capability"] == "advisories.detail"
        ):
            for record in value["result"]["records"]:
                advisories[record["id"]] = record
    for aid, record in sorted(advisories.items()):
        for affected in record.get("affected", []):
            if affected.get("package", {}).get("ecosystem") != "npm":
                continue
            name = affected["package"]["name"]
            versions = set(installed.get(name, []))
            # Explicitly labelled semantic probes, not fabricated project instances.
            probes = set()
            for span in affected.get("ranges", []):
                if span.get("type") != "SEMVER":
                    continue
                for event in span.get("events", []):
                    for version in event.values():
                        if version != "0":
                            probes.add(version)
                            match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
                            if match:
                                a, b, c = map(int, match.groups())
                                probes.add(f"{a}.{b}.{c + 1}")
                                if c:
                                    probes.add(f"{a}.{b}.{c - 1}")
            for version in sorted(versions | probes):
                cases.append(
                    {
                        "kind": "osv",
                        "advisory": aid,
                        "name": name,
                        "version": version,
                        "stratum": "real_installed_version"
                        if version in versions
                        else "boundary_probe",
                    }
                )
                expected.append(osv_match(record, name, version))
    node = subprocess.run(
        ["node", str(Path(__file__).with_name("patchdesk_semver_oracle.cjs"))],
        input=json.dumps({"cases": cases, "advisories": advisories}),
        text=True,
        capture_output=True,
        check=True,
        timeout=120,
    )
    oracle = json.loads(node.stdout)
    disagreement = []
    totals = Counter()
    for case, actual, reference in zip(cases, expected, oracle["answers"], strict=True):
        totals[case["kind"]] += 1
        totals[case.get("stratum", "constraint")] += 1
        totals[case["kind"] + "_" + str(reference)] += 1
        if actual != reference:
            disagreement.append({**case, "product": actual, "oracle": reference})
    lookup = payload.get("lookup") or {}
    queried = {(r["package"], r["version"]) for r in lookup.get("records", [])}
    found_ids = {a for r in lookup.get("records", []) for a in r["advisory_ids"]}
    report = {
        "kind": "automated independent-implementation conformance audit, not adjudicated gold",
        "created_at": now(),
        "code_hashes": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                Path(__file__),
                Path(__file__).with_name("patchdesk_semver_oracle.cjs"),
                Path("apps/patchdesk-api/src/patchdesk_api/inventory.py"),
            ]
        },
        "corpus_hash": digest(payload),
        "repositories": len({p["repository"] for p in payload["projects"]}),
        "snapshots": len(payload["projects"]),
        "distinct_input_hashes": len({p["inventory_hash"] for p in payload["projects"]}),
        "split_counts": dict(Counter(p.get("split", "unassigned") for p in payload["projects"])),
        "raw_entries": raw_entries,
        "strata": dict(strata),
        "inventory": inventory_rows,
        "raw_version_identity_errors": identity_errors,
        "oracle": {k: v for k, v in oracle.items() if k != "answers"},
        "comparisons": dict(totals),
        "distinct_decisions": {
            "npm_constraint": len(
                {(c["version"], c["spec"]) for c in cases if c["kind"] == "npm_constraint"}
            ),
            "osv": len(
                {(c["advisory"], c["name"], c["version"]) for c in cases if c["kind"] == "osv"}
            ),
        },
        "disagreements": disagreement,
        "query_identities_captured": len(queried),
        "lookup_completeness": lookup.get("completeness"),
        "queried_advisory_ids": len(found_ids),
        "captured_detail_ids": len(advisories),
        "missing_detail_ids": sorted(found_ids - set(advisories)),
        "source_outcomes": dict(
            Counter(v["result"]["outcome"] for v in payload["snapshots"].values())
        ),
        "limitations": [
            "No independent human adjudication or exploitation/compatibility labels",
            "Repo-held-out selection does not prevent shared advisory-family leakage",
            "Oracle compares semantics, not whether upstream vulnerability claims are true",
        ],
    }
    (target / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (target / "cases.json").write_text(
        json.dumps({"cases": cases, "product": expected, "oracle": oracle["answers"]}),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ["inventory", "disagreements"]}, indent=2
        )
    )
    print(f"Disagreements: {len(disagreement)}; evidence: {target / 'report.json'}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus")
    parser.add_argument("destination")
    args = parser.parse_args()
    audit(args.corpus, args.destination)
