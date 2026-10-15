# Research and source registry

Research checked 14 October 2026. The current evidence supports a buildable public-record workflow; customer demand remains untested. Read the [source feasibility record](validation-2026-10-14.md) before treating source discovery as application validation.

## Technical and commercial basis

[ReAct](https://arxiv.org/abs/2210.03629) describes interleaving reasoning with actions and external observations. PropertyBrief applies this to selecting record checks based on findings. [Reflexion](https://arxiv.org/abs/2303.11366) explores using verbal feedback to guide subsequent attempts. Our planned within-run reflection and critique are inspired by that mechanism; the design does not claim to reproduce its experiments or implement model training.

[PropertyShark](https://www.propertyshark.com/property-data/ownership-and-legal) offers property research including NYC violations and recorded documents. This is evidence of a competing product category. It does not establish demand for PropertyBrief. The proposed differentiation is a case-specific investigation, traceable decisions, and a follow-up checklist whose unresolved items remain visible through review and export. Validate the advantage against both manual official-site research and a general-purpose chatbot supplied with the same evidence.

Primary agency catalogs: [HPD open data](https://www.nyc.gov/site/hpd/about/open-data.page), [DOB complaints and violations](https://www.nyc.gov/site/buildings/dob/complaints-violations.page). HPD distinguishes public complaints, verified violations, and current recorded status. This motivates separate evidence types and conservative interpretation in our contracts.

## Source registry

All ten JSON endpoints below returned one public sample row on the research date. Sample access establishes neither complete property coverage nor reliable pagination. Dataset IDs are registry configuration, not model-generated values. Catalog URLs use the stable dataset identifier rather than relying on display-title slugs.

| Source / catalog | Dataset ID | Initial role | Observed fields relevant to mapping |
| --- | --- | --- | --- |
| [HPD buildings](https://data.cityofnewyork.us/d/kj4p-ruqc) | `kj4p-ruqc` | Identity resolution | `buildingid`, `bin`, `boroid`, `block`, `lot`, `recordstatus` |
| [HPD violations](https://data.cityofnewyork.us/d/wvxf-dwi5) | `wvxf-dwi5` | Required coverage | `violationid`, `buildingid`, `class`, `violationstatus`, `currentstatus`, `novdescription` |
| [HPD complaints and problems](https://data.cityofnewyork.us/d/ygpa-z7cr) | `ygpa-z7cr` | Required coverage | `problem_id`, `complaint_id`, `building_id`, complaint/problem statuses, `bin`, `bbl` |
| [Repair/vacate orders](https://data.cityofnewyork.us/d/tb8q-a3ar) | `tb8q-a3ar` | Required coverage | `building_id`, `vacate_order_number`, effective/rescind dates, `bin`, `bbl` |
| [Underlying Conditions Program](https://data.cityofnewyork.us/d/xpbf-ithr) | `xpbf-ithr` | Required coverage | `building_id`, `order_issue_date`, `current_status`, `bin`, `bbl` |
| [Alternative Enforcement Program](https://data.cityofnewyork.us/d/hcir-3275) | `hcir-3275` | Required coverage | `building_id`, `aep_start_date`, `current_status`, `discharge_date`, `bin`, `bbl` |
| [Multiple dwelling registrations](https://data.cityofnewyork.us/d/tesw-yqqr) | `tesw-yqqr` | Identity assistance | `registrationid`, `buildingid`, `bin`, `lastregistrationdate`, `registrationenddate` |
| [DOB complaints](https://data.cityofnewyork.us/d/eabe-havv) | `eabe-havv` | Required coverage | `complaint_number`, `bin`, `status`, `date_entered`, `disposition_code` |
| [DOB violations](https://data.cityofnewyork.us/d/3h2n-5cm9) | `3h2n-5cm9` | Required coverage | `isn_dob_bis_viol`, optional `bin`, `boro`, `block`, `lot`, `violation_category`, `disposition_comments` |
| [DOB ECB violations](https://data.cityofnewyork.us/d/6bgk-3dad) | `6bgk-3dad` | Required coverage | `isn_dob_bis_extract`, `ecb_violation_number`, `bin`, status, certification/hearing fields |

Endpoint form: `https://data.cityofnewyork.us/resource/{dataset_id}.json`. Schema metadata is captured from `https://data.cityofnewyork.us/api/views/{dataset_id}.json` during acquisition; all ten definitions were captured and hash-verified for the 12-building corpus. Source adapters use stable row-key ordering and metadata before/after acquisition. This is schema/functional evidence, not independent adjudication of every status meaning. See [implementation validation](validation-2026-10-15.md).

The current HPD complaints catalog links to `ygpa-z7cr`. An older reference used `uwyv-629c`; do not silently substitute schemas or merge these datasets. Record any migration in the source registry and label set.

## Actual feasibility observations

Eleven bounded GET requests checked ten distinct datasets and one additional identity lookup. The joined example was HPD violation `10081311`, building `375411`, BIN `3327904`, derived BBL `3030310015`. The building endpoint confirmed the same borough/block/lot. This example contains a closed historical violation and an unusual house-number representation; it is useful for normalization tests, not a complete investigation.

The building sample included zero-valued identity fields and an inactive record. The DOB sample included an explicitly marked test record. A vacate sample had a rescind date earlier than its effective date. These observations require invalid-identity, placeholder-record, and temporal-conflict handling. They do not establish how frequent those issues are.

## Acquisition and use constraints

Implementation acquisition exposed two additional identifier pitfalls. DOB violation block and lot query fields are both five-digit padded strings, unlike the four-digit BBL lot component. A current-parcel-only filter also missed historical DOB rows with the same BIN but an old lot. The corrected query uses confirmed BIN, with parcel fallback only for missing-BIN rows; differing parcel identifiers remain flagged rather than discarded. HPD complaint rows can match building ID while disagreeing in BIN/BBL; preserve and flag those rows, setting affected completeness unknown. These findings are documented with actual source snapshots and regression tests in [15 October validation](validation-2026-10-15.md).

[NYC Open Data terms](https://data.cityofnewyork.us/stories/s/Terms-of-Use/k9k7-3cje) govern reuse and state limitations on the data. Do not invent a permissive software license for the records. Preserve agency attribution, source URLs, terms references, and retrieval times. Review redistribution requirements before committing source snapshots or publishing building-specific examples; keep raw acquisition data in ignored storage initially.

[Socrata paging](https://dev.socrata.com/docs/paging.html) documents limits, offsets, and ordering. Use stable source-specific order keys and bounded property filters; ordering does not make a mutable dataset an atomic historical snapshot. Capture metadata before/after acquisition and flag possible drift. [Application tokens](https://dev.socrata.com/docs/app-tokens) support application-level throttling. We observed anonymous sample access, but sustained access and current quotas require testing; no throughput guarantee is assumed.

[ACRIS](https://www.nyc.gov/site/finance/property/acris.page) supports recorded property documents for four boroughs. Automated document retrieval and interpretation are deferred. No ACRIS API or image access check was run in this task.

## Questions to resolve before release

Can we obtain complete property-scoped results without source caps? Which DOB rows lack a valid BIN, and how should parcel-level results be represented for multi-building lots? Are source dictionaries sufficient to map statuses without overstating correction? How often do source changes alter a report during a run? Does the adaptive investigation materially improve completeness or reviewer effort over simpler baselines? Can the Windows laptop meet resource limits while the earlier products run?

See [data and evaluation](data-and-evaluation.md) for experiments answering these questions. Current evidence supports proceeding to source freeze and TDD, with release gates still open.
