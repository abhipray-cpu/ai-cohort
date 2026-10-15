"""Freeze a small cohort of actual public NYC building records for evaluation."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/propertybrief-api/src"))

from propertybrief_api.sources import DEFINITIONS, REQUIRED, SourceClient, candidate, digest, now


def acquire(destination, count=12):
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Use a new corpus directory; frozen sessions are never overwritten")
    destination.mkdir(parents=True)
    client = SourceClient()
    manifest = {"created_at": now(), "kind": "actual-public-records", "cases": [], "sources": {}}
    for key, definition in DEFINITIONS.items():
        metadata = client.get(
            f"https://data.cityofnewyork.us/api/views/{definition.dataset}.json", {}
        )
        path = destination / f"metadata-{key}.json"
        path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        manifest["sources"][key] = {
            "dataset": definition.dataset,
            "metadata_sha256": digest(metadata),
        }
    identities = []
    seed = client.get(DEFINITIONS["buildings"].url, {"buildingid": "375411", "$limit": 1})
    if seed:
        identities.append(candidate(seed[0]))
    for borough in range(1, 6):
        rows = client.get(
            DEFINITIONS["buildings"].url,
            {
                "boroid": str(borough),
                "recordstatus": "Active",
                "$limit": 6,
                "$where": "bin IS NOT NULL AND block != '0' AND lot != '0'",
                "$order": "buildingid",
            },
        )
        for row in rows:
            try:
                identity = candidate(row)
            except ValueError:
                continue
            if identity["id"] not in {value["id"] for value in identities}:
                identities.append(identity)
            if sum(value["bbl"][0] == str(borough) for value in identities) >= (
                3 if borough <= 2 else 2
            ):
                break
    for identity in identities[:count]:
        # Per-building HTTP and byte accounting; raw API metadata is also retained above.
        client = SourceClient()
        observations = {source: client.fetch(source, identity) for source in REQUIRED}
        payload = {"identity": identity, "observations": observations}
        filename = f"building-{identity['id']}.json"
        (destination / filename).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        manifest["cases"].append(
            {
                "building_id": identity["id"],
                "bbl": identity["bbl"],
                "file": filename,
                "sha256": digest(payload),
                "coverage": {key: value["completeness"] for key, value in observations.items()},
                "counts": {key: value["count"] for key, value in observations.items()},
            }
        )
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(
            f"Frozen building {identity['id']}: {sum(v['count'] for v in observations.values())} records",
            flush=True,
        )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    parser.add_argument("--count", type=int, default=12, choices=range(1, 13))
    arguments = parser.parse_args()
    result = acquire(arguments.destination, arguments.count)
    print(f"Frozen {len(result['cases'])} actual buildings. Review completeness before evaluation.")
