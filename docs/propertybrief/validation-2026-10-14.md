# Source feasibility observations — 14 October 2026

Scope: read-only public-source checks while preparing the documentation. No product evaluation or implementation test was run. These checks did not create a frozen corpus, raw-data files, application database, or service. Observations below were transcribed from returned records; future acquisition must preserve and hash original payloads before treating them as reproducible fixtures.

## Method and access

The sandboxed shell request failed DNS resolution. The same public one-row GET succeeded using approved network access. Browser access to a query URL was also unreliable, whereas the unparameterized endpoint could be read. These are tool/environment observations, not evidence that the source service was down.

For each dataset ID in the table, the command was:

```bash
curl --fail --silent --show-error --max-time 25 \
  'https://data.cityofnewyork.us/resource/DATASET_ID.json?$limit=1'
```

Replace `DATASET_ID` with the ID below. The command is a diagnostic example, not a PropertyBrief implementation command. No app token was supplied. `$limit=1` provides a connectivity/schema sample; it is not an ordered or representative sample, and the first row may change.

## Observed sample results

| Dataset | HTTP/command outcome | Observed sample identity / relevant values |
| --- | --- | --- |
| HPD buildings `kj4p-ruqc` | Success, JSON array, exit 0 | Building `859129`; zero block/lot/address fields; `recordstatus=Inactive` |
| HPD violations `wvxf-dwi5` | Success, JSON array, exit 0 | Violation `10081311`; building `375411`; class `C`; `violationstatus=Close`; `currentstatus=VIOLATION CLOSED` |
| HPD complaints `ygpa-z7cr` | Success, JSON array, exit 0 | Complaint `8852631`; problem `18168892`; building `374378`; both statuses `CLOSE` |
| Vacate orders `tb8q-a3ar` | Success, JSON array, exit 0 | Order `260021`; building `574773`; effective `2025-10-15`; rescind `2025-01-07` |
| Underlying conditions `xpbf-ithr` | Success, JSON array, exit 0 | Building `119028`; `current_status=Discharged` |
| AEP `hcir-3275` | Success, JSON array, exit 0 | Building `324094`; `current_status=AEP Discharged`; discharge `2011-11-02` |
| Registrations `tesw-yqqr` | Success, JSON array, exit 0 | Registration `825850`; building `271859`; registration end `2026-09-01` |
| DOB complaints `eabe-havv` | Success, JSON array, exit 0 | Complaint `1450858`; BIN `1012271`; `status=CLOSED` |
| DOB violations `3h2n-5cm9` | Success, JSON array, exit 0 | Row `24174`; house/street `TEST` / `RECORD`; category active; disposition explicitly marks test-record deletion |
| DOB ECB `6bgk-3dad` | Success, JSON array, exit 0 | Row `191496`; violation `38200385N`; `ecb_violation_status=RESOLVE`; `certification_status=CURE ACCEPTED` |

Ten distinct endpoints were sampled successfully. An additional GET checked the building corresponding to the housing-violation sample:

```bash
curl --fail --silent --show-error --max-time 25 \
  'https://data.cityofnewyork.us/resource/kj4p-ruqc.json?buildingid=375411&$limit=2'
```

It returned one building record: building ID `375411`, BIN `3327904`, borough `3`, block `3031`, lot `15`, registration `306067`, `recordstatus=Active`. These matched the violation's building/registration and borough/block/lot fields. The derived BBL is `3030310015`. The returned house number used the unusual value `22 FRONT`; preserve it rather than claiming full address normalization has been proved.

Total successful shell requests: eleven. No complete address-to-candidate resolution, BIN-to-DOB join, pagination, metadata capture, or multi-source investigation was tested.

## Design implications from actual records

1. Inactive/zero-valued building rows require identity validation.
2. Historical closed violations must not become current-condition claims.
3. Complaint and problem IDs/statuses are separate concepts.
4. Vacate effective/rescind dates can conflict; preserve uncertainty rather than choosing a current legal interpretation.
5. Program membership can be discharged; historical inclusion is not active participation.
6. DOB data can include test/deletion descriptions even when a category appears active. A blanket category-only status rule is insufficient.
7. Mixed field names and date formats require adapter-specific normalization and source dictionaries.

These observations influenced the [contracts](contracts-and-evidence.md), [agent loop](agent-loop.md), [evaluation scenarios](data-and-evaluation.md), and [TDD plan](implementation-plan.md). They are examples, not prevalence estimates.

## Remaining validation

Acquire complete scoped records and metadata, validate keys and status dictionaries, freeze original payloads/hashes, independently label real cases, implement/test the application, run actual Codex investigations, and complete browser and target Windows acceptance. No accuracy, commercial value, product completion, or production-ready result is claimed.
