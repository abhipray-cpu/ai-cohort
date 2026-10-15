"""Create a NEW corpus revision with corrected, freshly queried DOB evidence."""

import argparse
import json
from pathlib import Path

from propertybrief_api.corpus import FrozenSources, load_corpus
from propertybrief_api.sources import DEFINITIONS, REQUIRED, SourceClient, digest, now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parents", nargs="+")
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    target = Path(args.destination)
    if target.exists():
        raise SystemExit("Use a new corpus destination")
    cohort, parents = {}, []
    for parent in args.parents:
        manifest, cases = load_corpus(parent)
        parents.append({"path": str(Path(parent).resolve()), "manifest_sha256": digest(manifest)})
        for payload in cases:
            cohort[payload["identity"]["id"]] = payload
    target.mkdir(parents=True)
    manifest = {
        "created_at": now(),
        "kind": "actual-public-records",
        "parents": parents,
        "sources": {},
        "cases": [],
    }
    for key in DEFINITIONS:
        original = Path(args.parents[-1]) / f"metadata-{key}.json"
        metadata = json.loads(original.read_text(encoding="utf-8"))
        (target / original.name).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        manifest["sources"][key] = {
            "dataset": DEFINITIONS[key].dataset,
            "metadata_sha256": digest(metadata),
        }
    for bid, payload in cohort.items():
        identity = payload["identity"]
        replay = FrozenSources(payload)
        observations = {key: replay.fetch(key, identity) for key in REQUIRED}
        observations["dob_violations"] = SourceClient().fetch("dob_violations", identity)
        revised = {"identity": identity, "observations": observations}
        filename = f"building-{bid}.json"
        (target / filename).write_text(json.dumps(revised, indent=2), encoding="utf-8")
        manifest["cases"].append(
            {
                "building_id": bid,
                "bbl": identity["bbl"],
                "file": filename,
                "sha256": digest(revised),
                "coverage": {key: value["completeness"] for key, value in observations.items()},
                "counts": {key: value["count"] for key, value in observations.items()},
            }
        )
        temporary = target / "manifest.pending.json"
        temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        temporary.replace(target / "manifest.json")
        print(
            f"Revised actual building {bid}: {observations['dob_violations']['count']} DOB rows; {observations['dob_violations']['completeness']}",
            flush=True,
        )
    print(f"Saved {len(cohort)} cases at {target}")


if __name__ == "__main__":
    main()
