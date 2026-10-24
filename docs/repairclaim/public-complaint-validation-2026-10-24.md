# Actual public consumer-record metadata validation — 24 October 2026

**Measured result: 400/400 actual public-record metadata workflows passed through
the real API/worker; four packet flows and eight live Jev decisions validated.**
This is not a pass for full consumer-invoice E2E, complaint narrative interpretation,
independent domain accuracy, coverage confirmation, refunds, browser UI or Windows.

## What is actual, what was minimized

The official NHTSA complaints API returned real public consumer complaint records.
The initial successful schema inspection found 1,776 records for 2017 CR-V. A bounded
four-query acquisition then covered the cohorts below. The first importer run
rejected every record because it assumed `make`/`model` where the actual API uses
`productMake`/`productModel`. That run exited nonzero and remains preserved.
A regression reproduced the actual-field mismatch as a failure; the correction
passed before reacquiring the four queries into a new directory.

| Cohort | API records | Valid unique metadata | Frozen selection |
| --- | --- | --- | --- |
| Honda CR-V, 2017 | 1,776 | 1,776 | 100 |
| Honda HR-V, 2016 | 243 | 243 | 100 |
| Honda Pilot, 2016 | 1,719 | 1,719 | 100 |
| Honda Odyssey, 2018 | 1,007 | 1,007 | 100 |
| Total | 4,745 | 4,745 | 400 |

The four queries were repeated to correct the importer, not counted as 9,490 unique
records. There was also one initial schema-inspection query. All were bounded
model/year reads, not VIN enumeration or the full bulk archive. Acquired bodies
were each below 20 MiB. Query URLs, response SHA-256, byte counts, field names and
UTC acquisition times remain in the manifest. No private account or portal was used.

The frozen selection is deterministic by hashed public ODI record identifier, one
hundred per cohort, selected before product outcomes. It preserves only record ID,
public-source URL, original-record hash, model/model-year facts and explicit missing
evidence flags. Raw response bodies, VINs, narratives, contact/location fields and
incident/complaint dates were **not persisted**. No date of incident or complaint was
turned into a repair date. No repair component, mileage, payment, in-service date,
diagnosis or invoice was inferred from make/model/year or a broad complaint category.

Actual case inputs were therefore **record-derived, not authored repair facts**.
But minimization leaves only **four distinct vehicle-metadata input signatures**
across 400 distinct ODI identifiers. This is workflow repetition/volume evidence,
not 400 independent substantive case assessments, unique people or gold labels.

Source/method reference: [NHTSA datasets and complaint API](https://www.nhtsa.gov/nhtsa-datasets-and-apis),
[API use policy](https://api.nhtsa.gov/).

## Scoped inventory and honest expectations

The campaign used the previously frozen official PDF corpus and one exploratory
CR-V powertrain programme interpretation, anchored to the actual 2024 bulletin.
Eleven parsed official documents were captured locally; the active programme used
only its own cited source pages. It is not a complete Honda programme inventory.

The contract checks were deliberately narrow:

- 100 CR-V records: `missing_evidence`, because the supported model/year alone
  cannot establish component, repair date or in-service history.
- 300 records from the other three models: `appears_outside_conditions` **for this
  specific CR-V programme**, not ineligible for every programme or manufacturer remedy.
- No product-generated entitlement, verified payment or reimbursement-success claim.

These expectations are identity/presence assertions, not specialist-reviewed
eligibility annotations. Other public metadata was not smuggled into expected
repair facts. No source narrative or alleged incident was evaluated for truth.

## Actual execution and observed results

Every selected record created a scoped vehicle/case via authenticated socket HTTP,
posted only the record-derived vehicle facts, queued an investigation and waited
for the actual durable worker. Cases were deleted after each scenario so no case
limit was bypassed. The campaign used fresh isolated state and owned loopback
processes; existing application accounts, data and credentials were not changed.

| Check | Observed |
| --- | --- |
| Public record workflows | 400 passed / 0 failed |
| Rules-only cases | 396 primary investigations |
| Live-model representatives | Four actual ODI records, one per cohort |
| Actual native model calls | Eight: before and after PDF upload for each representative |
| Live response validation | Eight valid Choice/Noul/version/usage/balance receipts; zero unknown/invalid calls |
| Jev-versus-rule disagreement | Zero on these eight calls; only four unique minimized inputs, not an accuracy estimate |
| Programme PDF attachment flows | Four: actual 21-page bulletin upload and sandbox parsing; classified `other`, never invoice |
| Packet control flows | Four real queued renders, sanitized attachments, approval-required refusal, exact-byte approval, ZIP/PDF manifest hashes, download and refusal after revocation |
| Cross-household attachment access | Denied in all four packet flows |
| Campaign duration | 130.68 seconds; sequential workflow, not a load benchmark |

The attached source PDF was a programme document, **not the consumer's complaint or
repair invoice**. No fabricated consumer PDFs were substituted. Packet creation
used the actual case state after upload/re-investigation. Outputs stayed local;
no dealer, manufacturer, regulator or claimant received a submission.

All eight live representative jobs routed to manual review rather than authorizing
coverage. All 400 record cases completed their asserted scoped outcome and deletion.
Owned API/worker children shut down after the run. Earlier monitoring revision
checks belong to prior explicitly authored campaigns and are not relabelled as
consumer-record tests here.

## External-data and cost controls

Only non-identifying vehicle make/model/year and official programme excerpts were
approved for jevmodel.org. ODI IDs, response/record hashes, narratives, VINs, locations,
case/household identifiers and contact details were not sent to the model. Exact
destination/model preview fingerprints were approved for each live investigation.

The service's documented `jev-latest` route returned `jev-1.14.0`; this remains a
proxy-reported version, not independent verification of its underlying model.
Direct versioned access had previously required payment. The campaign used only
the documented route authorized by the user, with no vendor or model fallback.

The new journal was initialized with a **50,000-token cap**, below the previously
observed 59,206 remaining. Tests verify that reopening a lower-limit journal cannot
raise it back to 90,000. Existing per-attempt reservations, 16-attempt hard bound,
unknown-usage holds and no-automatic-retry policy remain. No grant-farming accounts,
credit purchase, subscription, refill or billing changes occurred.

| Token measure | Observed |
| --- | --- |
| This campaign | 25,834 input tokens |
| Prior probe + authored smoke | 40,794 input tokens |
| Cumulative successful proxy usage | 66,628 input tokens |
| Remaining proxy allowance | 33,372 tokens |
| USD cost/reservation receipt from proxy | None: represented as null, not fabricated as $0 |

No payment was made. The earlier Vercel attempts' $0.02 conservative unknown-use
reservations remain historical holds; the user's cumulative $2 ceiling was not
renewed or increased by creating this journal.

## TDD, artifacts and reproduction

The initial acquisition test collection failed because the new acquisition script
did not exist. Actual field-name incompatibility subsequently caused zero records
to be retained and a nonzero exit. A focused actual-schema test failed before the
correction. Current tests also reject duplicate records, accidental introduction
of repair-date facts, absent/mismatched product identity and quota increases on
reopen. These are unit contract tests, not independent factual labels.

Scoped verification: **185 Python passed / three optional process skips**, three
frontend tests passed, production web build and lint passed.

Full repository regression with actual RepairClaim process checks enabled:
**1,038 passed / five existing optional skips**, six upstream warnings, 115.37
seconds. JUnit: `var/repairclaim-public-complaints-regression-20261024.xml`.
Owned temporary PostgreSQL, native restricted parsing and actual API/worker checks
ran; database assertions were not mocked away.

Retained local evidence:

- `var/repairclaim-validation/public-complaints-20261024-a/`: failed schema/import run.
- `var/repairclaim-validation/public-complaints-20261024-b/`: final source manifests
  and 400 minimized public records. Raw identity/narrative payloads were not saved.
- `var/repairclaim-validation/public-complaints-e2e-20261024-a/`: frozen records,
  scenarios, interpretation, actual report and native receipts, durable budget DB,
  owned-process log, four actual downloaded packet PDFs/manifests.

```bash
make repairclaim-test repairclaim-lint
# Explicit official-source reads, no model calls:
.venv/bin/python scripts/repairclaim_complaints.py \
  --out var/repairclaim-validation/NEW-SOURCE-DIRECTORY
# Use only with confirmed remaining allowance: current balance is below the
# original 50,000-token cap, so do NOT blindly rerun this live command.
.venv/bin/python scripts/repairclaim_public_e2e.py \
  --corpus var/repairclaim-validation/public-20261022-b \
  --out var/repairclaim-validation/NEW-UNUSED-DIRECTORY \
  --jev --jev-route jevmodel --families 1 --programme-index 3 \
  --public-records var/repairclaim-validation/NEW-SOURCE-DIRECTORY/records.json
```

## Still not validated

Private invoice parsing/grounding, narrative understanding, actual repair chronology,
paid amounts, configuration/VIN applicability, specialist-labelled programme rules,
manufacturer replies and consumer outcomes remain unvalidated with real private
records. Public complaint metadata cannot replace those records or consent.
The original independent-label, corpus breadth, browser, pilot and Windows/tunnel
acceptance gates remain unchanged. Do not call this full consumer E2E or a 100%
accepted MVP merely because 400 workflow assertions passed.
