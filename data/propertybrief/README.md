# PropertyBrief actual-data workflow

Official source definitions are in the [source registry](../../docs/propertybrief/research-and-sources.md#source-registry) and [source adapter](../../apps/propertybrief-api/src/propertybrief_api/sources.py). Raw public records and validation stores remain under ignored `var/`, with metadata, hashes, queries and acquisition times. They are not fabricated records or production customer uploads.

Create a new capture directory:

```bash
.venv/bin/python scripts/fetch_propertybrief_sources.py var/propertybrief-corpus/new-capture --count 12
.venv/bin/python scripts/validate_propertybrief.py --corpus var/propertybrief-corpus/new-capture --all
# Actual model invocation; consumes Codex usage:
.venv/bin/python scripts/validate_propertybrief.py --corpus var/propertybrief-corpus/new-capture --live --case 375411
```

Acquisition does not overwrite a frozen directory. `refresh_propertybrief_dob.py` creates a new revision with freshly queried DOB evidence while preserving its parents; it was used to correct the historical-parcel query regression. `resume_propertybrief_validation.py` explicitly grants one additional bounded attempt to a failed evaluation run without discarding checkpoints or resetting cumulative counters.

The development cohort is curated from public agency records and is not representative of all NYC properties. Its current source coverage includes explicit gaps. Hash integrity, correct references and functional agent behavior do not establish legal/physical condition, independent semantic accuracy, or customer value. See [evaluation plan](../../docs/propertybrief/data-and-evaluation.md).

Use is governed by [NYC Open Data terms](https://data.cityofnewyork.us/stories/s/Terms-of-Use/k9k7-3cje). Preserve source attribution; no separate permissive software license for agency records is asserted here. Do not publish tenant/owner contact collections or original property-specific records unnecessarily.
