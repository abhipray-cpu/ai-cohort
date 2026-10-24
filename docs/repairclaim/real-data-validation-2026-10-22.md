# Public-source validation checkpoint — 22 October 2026

**Result: bounded public-source integration passed after one packet-presentation
fix. Full consumer/product acceptance remains open.** This checkpoint followed the
implementation gate, not the reverse. It does not claim real customer invoices,
independent accuracy labels, live-provider quality, UI interaction or a refund.

## Implementation gate and isolation

Before acquisition, `make repairclaim-test repairclaim-lint` passed: 157 Python
tests, three frontend tests, build and lint; three opt-in process tests skipped in
that invocation had separate prior passing evidence. Historical full regression
was 1,010 passed / five existing optional skips. No previous product's inference
approval was reused.

The campaign used a new private validation directory, two temporary households,
free loopback ports and actual API/worker child processes. Existing product data,
accounts, authentication and model settings were not changed. Source refresh and
Codex were disabled for replay; downloaded official bytes were frozen beforehand.
All owned API/worker children stopped afterward. No claim or email was submitted.

## Actual source acquisition

Frozen discovery plan: [public-source-validation-plan.json](public-source-validation-plan.json).
URLs point to the official NHTSA archive, not invented fixtures. The manifest saves
final URL, acquisition time, SHA-256, bytes, parse result and errors. Raw PDFs remain
ignored local validation artifacts; redistribution rights are not cleared.

| Measure | Observed |
| --- | --- |
| Official PDFs downloaded | 12 |
| Parsed distinct PDFs | 11 |
| Parsed pages | 68 |
| Quarantined | 1: 2019 MC-10161640, `active_content_denied` |
| Download/accounted bytes | 9,394,193 |
| Programme interpretations used in case replay | 6, assistant-authored and not independently reviewed |
| Actual customer records / provider calls | 0 / 0 |

The restricted production parser handled actual bytes. The rejected PDF was not
stripped, reclassified as passing or silently omitted. One parsed motorcycle notice
is outside the passenger-car product scope and was not activated as coverage. Eleven
parsed documents are not eleven independently reviewed programme families.

First acquisition `public-20261022-a` retained two `source_too_large` exclusions due
to the harness's initial 2 MiB bound. The harness was corrected to the product's
20 MiB bound; the second run retained the genuine active-content exclusion. Both
reports remain; this is not twelve successful parses.

Six exploratory configurations concern Accord Hybrid condenser, Clarity condenser,
HR-V CVT, CR-V powertrain, Odyssey injectors and Pilot idle-stop. Their conditions
have literal page/hash anchors. Factory-defect, configuration, VIN, prior-software,
diagnostic and other manufacturer-specific checks remain confirmation-required.
Normalized component names and date interpretation are supplied assumptions, not
measured autonomous extraction or specialist-reviewed coverage advice.

## Actual HTTP workflow with mixed data

Two campaigns ran, before and after the presentation correction. Each passed:

- 48/48 authored boundary cases: six configurations times eight variants, including
  model/component mismatch, age anniversary and next day, missing in-service date,
  mileage boundary/overrun or explicitly unlimited mileage.
- Six real uploads of frozen official PDFs, classified `other` rather than invoices;
  actual durable worker and restricted parsing, hash and cross-household denial.
- Six queued packet-render flows, sanitized official-document attachments,
  preapproval download refusal, exact-byte approval, CSRF-protected ZIP download,
  PDF/manifest hash checks, and refusal after revocation.
- Genuine 2023-to-2025 source-term evolution applied to an authored Pilot scenario:
  outside conditions to potentially applicable, one consented notification,
  monitoring revocation and owner access denied after case erasure.

The evolution check compares the earlier official announcement with the later
bulletin, not an unparsed historical full bulletin. Its future repair date is a
labelled authored boundary, not an observed consumer repair.

Interpretations and scenarios were frozen before execution. The same author built
rules and expectations, so 48/48 is a deterministic integration result, **not an
independent accuracy estimate**. Repeated runs are not additional unique cases.
No model was invoked; no model-based extraction/ranking improvement is established.
The final replay took 24.31 seconds, not a production load/performance benchmark.

## Defect found and TDD correction

PDF inspection exposed a misleading heading: every assessed programme was called
potential, including ruled-out programmes. Three parameterized regressions failed
for missing-evidence, potentially-applicable and outside-condition states. Packet
headings now state each actual assessment; all three regressions passed, followed
by another complete actual HTTP replay. Conditions and manufacturer-confirmation
warnings remain visible; rejected assessments are not silently deleted.

Two actual source first pages were previewed through the restricted parser. Generated
packet pages were rendered and visually inspected using the PDF skill, leading to
this correction. Sampling is not visual inspection of all 68 source pages or all
packet pages. Fontconfig reported unavailable cache directories during Poppler
rendering; PNG output was still produced and inspected.

Post-fix scoped verification: **162 Python passed / three optional process skips**,
three frontend tests, production build and scoped lint passed. The new acquisition
contract tests observed an initial missing-module failure before implementation;
they check official/bounded plans and honest report flags, not network accuracy.

The final full-repository regression, with RepairClaim's actual process tests
enabled, passed **1,015 tests / five existing optional skips**, six upstream warnings,
113.20 seconds. JUnit: `var/repairclaim-public-validation-regression-junit.xml`.
PostgreSQL used an owned short temporary runtime; no database assertions were mocked.

## Reproduction and artifacts

```bash
make repairclaim-test repairclaim-lint
# Explicit network/native-parser operation; use a new output directory each time.
.venv/bin/python scripts/validate_repairclaim.py acquire \
  --plan docs/repairclaim/public-source-validation-plan.json \
  --out var/repairclaim-validation/new-source-run
# Starts an isolated actual API and worker; no model calls or submissions.
.venv/bin/python scripts/repairclaim_public_e2e.py \
  --corpus var/repairclaim-validation/new-source-run \
  --out var/repairclaim-validation/new-http-run
```

An acquisition exit code of one preserves exclusions; inspect the report rather
than bypassing parser policy. The replay requires the six referenced sources to
have parsed. Native macOS sandbox or configured local isolated parser is required.

Local retained evidence under `var/repairclaim-validation/`:

- `public-20261022-a/acquisition.json`: first, bounded-limit failure report.
- `public-20261022-b/acquisition.json`: final frozen sources, hashes and exclusion.
- `e2e-20261022-a/`: pre-correction scenarios, interpretations, report and PDFs.
- `e2e-20261022-b/`: final report, same unique scenarios and actual downloaded packets.

Credentials are random and not printed. Test cases are deleted after exercising
them. Frozen public sources and local test audit state remain for reproducibility;
no private consumer records were acquired.

## Acceptance shortfall — unchanged targets

The target remains 100 distinct PDFs across 20 reviewed families, 300 independently
reviewed pairs including 100 negatives and 60 holdout pairs, browser interactions
at 360/768/1440 widths, ten consented cases/five actual replies, specialist review,
provider-quality evaluation if selected, and Windows/tunnel deployment drills.
This run has only 11 parsed PDFs, six exploratory configurations, 48 authored
cases, no independent labels, no available browser and no private cases/outcomes.
Do not lower these targets retroactively or call the product 100% accepted.

Public acquisition can be expanded separately; it cannot supply consented private
invoices, vehicle-specific manufacturer confirmation or actual correspondence.
Browser discovery returned an empty list after documented troubleshooting, so no
UI pass is claimed. Windows hardware/hostname are unavailable. Jev's advertised
free-access options are assessed [separately](jev-free-access-research.md), not used
as evidence of a live provider test.
