# ShelfProof actual-data validation log

21 October 2026. Validation began **after** the implementation gate passed:
770 repository tests including 89 ShelfProof tests, no skips/failures; frontend
build/four domain tests/lint and owned-fixture up/status/down also passed.
This log is not a production-readiness or independent factual-quality claim.

Latest checkpoint: following the failed run, the user explicitly approved fixed-code
revalidation. **All six USDA products reached `review_ready`; all five concepts
were observed; 23 new calls were audited, with zero new unknowns.** Campaign spend
is 34/96 calls, retaining the original unknown charge/history. The bounded live-agent
gate passed; independent quality, browser, Windows/tunnel and production acceptance
remain unpassed. Earlier failed checkpoints below are preserved as history.

## Source acquisition and discrepancies found

- Official archive: `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_json_2026-04-30.zip`.
- Downloaded size: **204,270,542 bytes**. SHA-256:
  `57b0f122e61cf2840f03c11e9520275d0d2018dc036e16273fcd3cd370db2256`.
- Actual archive directory: one JSON member,
  `FoodData_Central_branded_food_json_2026-04-30.json`, expanded **3,315,545,449 bytes**.
- **No field dictionary is bundled in this actual archive**, despite the download
  page's general statement. The initial acquisition stopped mapping rather than
  inventing a guide or silently accepting a guessed field mapping.
- The official external `Download_Field_Descriptions_Oct2020.pdf` was downloaded,
  hashed, text-inspected and visually checked on its branded-food definitions page.
  Hash: `e21d658d4d3fa583aceaa78e23efd4e64dbf9010fd0210a87b94edbcfb56928a`.
  It is explicitly labelled an external official fallback, **not a bundled 2026
  dictionary**. The older guide is not claimed to fully specify newer JSON fields.
- Initial native DNS resolution of `fdc.nal.usda.gov` failed in Python, curl and
  Node. Public DNS verified CNAME `agw-ars-shared-03.nal.usda.gov` and address
  `52.245.234.40`; the same archive then returned HTTPS 200 with its original
  hostname/SNI/certificate verification. Only a process-local resolver override
  was used; system DNS, application auth and model configuration were unchanged.
- One bounded official API diagnostic request using the documented public
  `DEMO_KEY` also succeeded. It was not substituted into the corpus or counted as
  an acquired test cohort. No demo-key bulk collection or quota bypass occurred.

Acquisition artifacts are under gitignored
`var/validation/shelfproof-usda-20261021-resolved/`; `acquisition.json` records
source URL, release, hashes, dictionary provenance and mapping-pending state.
The failed native-DNS attempt directory is retained separately. No private data,
customer account or live catalog was used.

## Mapping audit

The inspected guide distinguishes brand owner, GTIN revisions, ingredient text,
serving quantity/unit and household serving description. The first five actual
archive records contain `brandOwner` and serving quantities but lack `brandName`
and `packageWeight`. Those are **not** eligible merely because other numerical
fields exist. Brand owner is not substituted for brand; serving weight is not
substituted for package quantity. Missing/ambiguous/out-of-scope records must be
counted as exclusions, not silently fixed or cloned into a larger positive cohort.

The mapping remains conservative: a supplied literal `brandName`, complete ordered
ingredients and a single explicit `packageWeight` quantity/unit. Dual-unit,
multipack, missing or ambiguous package strings are excluded; no density/unit
conversion is performed. These are reported source facts, not independent proof
of current package truth or a regulatory net-weight certification.

An authored regression test reproduced the missing-bundled-dictionary condition;
the pinned official fallback and completed-download hash resume were implemented
and the corpus test family passed (nine tests at that checkpoint). No model budget
was spent on this acquisition correction.

## Measured corpus / engineering / actual-model results

### Corpus

The official ZIP contained 204,270,542 bytes (expanded JSON 3,315,545,449 bytes).
SHA-256: `57b0f122e61cf2840f03c11e9520275d0d2018dc036e16273fcd3cd370db2256`.
It contained no bundled dictionary. The official external dictionary PDF hash is
`e21d658d4d3fa583aceaa78e23efd4e64dbf9010fd0210a87b94edbcfb56928a`.

Curation scanned 50,031 records and retained 1,000 distinct-GTIN candidate packs.
Exclusions: missing literal brand name 16,682; missing/ambiguous package 32,199;
category 91; contract validation 36; discontinued 22; duplicate GTIN 1.
These counts describe a bounded scan, not the complete release or verified labels.

The original brand/category grouping had 756 heuristic groups (615 development,
215 calibration, 170 locked rows). Before any model calls, an audit identified
shared-owner brand aliases. A new immutable derivative groups conservatively by
normalized published owner across categories: **533 heuristic owner groups**, with
605 development, 209 calibration and 186 locked rows. These are not expert-confirmed
product families. Neither source nor locked results were rewritten after model use.

The derivative is `var/validation/shelfproof-usda-grouped-20261021/`:

- Records SHA-256: `86690b369cac989d01a77fabd95a9438cbe1a2edb61cf6df4281e7cbf4ce8bcc`.
- Canonical manifest hash: `de93c819f26507339cdc402f414d306e83e41bbc41ab8565f4a14a9cbf59ad9b`.
- Parent source manifest: `5768532320c65ad4fd6b438690299deceb49eaa336912ef9780b9464a812ba49`.

### Source-backed controlled engineering workload

`var/validation/shelfproof-usda-engineering-20261021/report.json` records:
**1,000 terminal tasks, 2,131 controlled-provider calls, zero actual model calls**;
869 `review_ready` under the fixture rubric and 131 `needs_data`. All 131 retained
restricted-claim blockers in required literal source ingredients rather than
silently deleting them. No human approvals or quality labels were fabricated.

The provider copies source facts and supplies controlled rubric responses; this
workload exercises intake, persistence and gating against real records, **not LLM
quality or real-model self-improvement**. It does not demonstrate regeneration;
`all_concepts_observed=false` is preserved. Unit/process tests cover the full loop
separately. This workload used the original inventory, not a locked comparison.

### Actual installed-Codex campaign: failed and held

The actual runner used the HTTP API, worker and installed Codex 0.160.0, with the
approved six development records, distinct published owners and deterministic
source preflight before model outputs. GTINs: `00954174`, `854410003041`,
`028800274315`, `639713992335`, `041380291022`, `041497128129`.
Three were generation tasks; three contained explicitly injected quantity faults,
not authentic customer mistakes. No calibration/locked records were sent.

Only the first `draft:0` invocation occurred. It returned no auditable completion
or usage receipt. Tokens and elapsed receipt fields remain null, not verified zero.
The original reservation (one call / 90 seconds) remains charged against the same
96-call grant. No explicit unsafe tool event was observed; absence of such an event
does not verify historical safety. The exact original failure cause is not known:
the runtime retained a generic failure category, not raw provider stderr. Read-only
feature/login diagnostics confirmed the CLI and existing login, not successful inference.

After worker shutdown: **one `manual_required`, five `queued`, no running tasks**.
There is no validated generated draft, judge result, correction plan or regeneration
from this campaign. The three supplied faulty originals are retained. No human
approval, publication, retry, incident acceptance or grant reset occurred. The
approval registry prevents silently creating a fresh store to reuse this authority.
Integrity verification passed; the usage hold remains active and both services
are stopped. Actual-model acceptance has **not passed**.

Evidence root: `var/validation/shelfproof-usda-smoke-20261021/`. The original
`report.json` captured the worker before its terminal transition and is preserved.
The read-only, new-file finalizer recorded stopped-worker state in
`report-final.json`, with the original report hash and no grant/liability change.
Code fingerprint: `a3d240d682d87a3328032b133326bdf7b7feeb7f48d4dc9880a657b12f9e4b95`.
Journal head: `d73531059bab871af3d582cee6d6fc10adcd73e0a52588cf42fe382fd3a4a0b8`.

The acceptance utility correctly exited 2: actual-provider gate failed; independent
quality, browser, Windows/tunnel and commercial gates not run; production accepted
false. Evidence: `var/validation/shelfproof-acceptance-20261021/gates.json`.

### Final engineering regression and next authority boundary

The final repository run passed **774 tests, zero skipped, zero failures**, including
93 ShelfProof Python tests and real child/HTTP process checks. JUnit:
`var/validation/shelfproof-final-handoff-regression.xml`. Four frontend domain tests,
TypeScript/Vite production build and focused Ruff checks passed. No available
in-app browser was discovered; visual/browser acceptance is not claimed. Target
Windows/tunnel deployment and independent human quality review remain unperformed.

At that initial failed checkpoint, further dispatch required a verified supplemental receipt or an explicitly
authorized owner recovery decision under the documented one-time unknown-incident
procedure. Unknown spend/safety uncertainty must remain visible; recovery cannot
reset the six-product/96-call cumulative ceiling. Recovery was not yet authorized;
the subsequent explicit decision and results are recorded below.

The model grant remains six distinct development products / 96 cumulative calls.
Unknown usage/unsafe tools stop dispatch; there is no automatic incident closure.
Browser, human-labelled quality/baselines, actual Windows/tunnel deployment and
customer utility remain separate unpassed gates.

## Explicitly authorized one-time recovery: completed, acceptance still failed

After the user explicitly answered yes to the documented recovery question, a
new-only pre-recovery backup was made. The exact five untouched queued tasks were
parked with owner attribution, current-head/integrity checks and the stopped
runtime lock, without cancelling/recreating them or changing counters. An authored
regression first failed without the operator helper, then passed after implementation.
The same original incident task and parked tasks were separately resumed through
the existing bounded-resume operation. No grant was created or amended.

Incident: `dde5e9f80aa5afb38f6c62eb2a60c547ee8efcc13178aa4513df13d24180eeee`.
Its original unknown receipt and charge remain unchanged. This consumes the store's
one-time incident allowance; it is not authority for another unknown-incident loop.

The unchanged product fingerprint `a3d240d682d87a3328032b133326bdf7b7feeb7f48d4dc9880a657b12f9e4b95`
was exercised through the actual installed-Codex adapter and production worker/store.
This recovery driver did not repeat authenticated HTTP/browser acceptance. It added
bounded redacted process categories only; all **10 new calls** completed with audited
receipts. No auth, model selection, CLI configuration file or real `.env` was changed.

Measured outcome:

| Measure | Result |
| --- | --- |
| Products / terminal / pending | 6 / 6 / 0 |
| Product states | 6 `manual_required`; none approved or published |
| Cumulative grant spend | 11 of original 96 calls, including the retained unknown |
| Known successful process receipts | 10 new audited calls; no additional unknowns |
| Known input/output token lower bounds | 94,088 / 4,661; excludes unknown usage |
| Unassessable judgments | 5 products, channel dimension null |
| Parse exhaustion | 1 product, two judge parse failures after its generated draft |
| Reflection/regeneration/improvement demonstration | Not observed in this actual run |
| Recovery worker-driver duration | 141.551 seconds, not total wall time since original run |

The five unassessable judges explicitly reported that channel requirements were
not supplied. Inspection confirmed that producer/planner contexts carried the
channel profile but independent-judge context omitted it. That is a product defect,
not evidence that those records lack usable source data. The remaining product's
exact parse failure detail was not retained by the privacy-minimal validation log;
do not invent a more precise cause or claim it fixed by the context change.

The first post-recovery report accidentally inherited two pre-recovery metadata
fields (short elapsed time and unchanged liability). It is preserved as
`report-recovery.json`. A new-only derivative, `report-recovery-reviewed.json`, pins
its hash, corrects those fields, and leaves all measured counts/outcomes and the
evaluated fingerprint unchanged. The grant ceiling did not change; incident
acceptance did change liability handling. A regression verifies original-report
preservation and the metadata correction.

Evidence remains under `var/validation/shelfproof-usda-smoke-20261021/`: backup,
recovery authority, process-category JSONL, reports, DB, append-only journal and
owner audit events. Final integrity: 19 artifacts, journal head
`9ef2b44008db7685941446a2d48eec3ab1df1f71882a08bc9c81206a776fbb2d`.
No queue/running tasks or model processes remain. Usage hold is false after explicit
acceptance; unknown history is still visible and must be acknowledged by any reviewer.
The acceptance utility again correctly exited 2; evidence is under
`var/validation/shelfproof-acceptance-recovery-20261021/`.

## TDD fix after the frozen-code run (historical checkpoint)

`test_independent_judge_receives_same_channel_constraints_without_producer_history`
first failed with `KeyError: profile`. A single shared `CHANNEL_PROFILE` constant
now supplies the same immutable channel constraints to producer/regenerator and
independent judge, without passing prior scores, desired scores or producer reasoning.
The focused workflow/recovery suite passed 36 tests after this fix. A pre-fix full
regression passed 778 tests. The post-fix full regression passed **780 tests, zero
skipped, zero failures**, including 99 ShelfProof tests, with six dependency
deprecation warnings. JUnit: `var/validation/shelfproof-post-recovery-fix-regression.xml`.
Focused Ruff check/format and `git diff --check` also passed.

Current fixed-code fingerprint:
`08b859d77551caa73618d9820060dd8dd20809e93c298a2a2159e711b097dae3`.
It differs from the code actually evaluated above. The old campaign snapshots were
not silently rewritten or rebound, so the fixed code cannot resume them. A future
fixed-code campaign decision must explicitly preserve the same six products,
existing grant's cumulative spend (11 already charged, at most 85 remaining), row
budgets/lineage and unknown-history warning. At this checkpoint no fixed-code model
calls had occurred; the next section records the later explicit approval and run.

## User-approved fixed-code live validation: passed within its declared scope

The user then approved making the live run pass and updating the docs. New-only
evidence is under the original root at `fixed-code-round1/`. Its authority records
the original six product IDs, source-manifest binding, parent report hash, expected
11 charged calls/current journal head and changed-code fingerprint. A backup was
taken before creating linked successors. No original snapshots, attempts, failed
reports, grant ceiling or facts were rewritten. Per-product calls/claims were
inherited rather than reset; imported fault cases stayed explicitly injected.

Additional red/green work before freezing this run:

- A successor edit lost its accepted-unknown parent warning. Recursive lineage
  lookup now retains that warning and mandatory review acknowledgement; the first
  live successor visibly retained the historical warning.
- A malformed judge span was retried without actionable context. A failing test
  now verifies allowlisted repair feedback, unchanged constraints and no rejected
  raw output/private text in the replacement prompt. Optional evidence remains
  all-null or an exact Unicode-codepoint slice; invalid responses are not accepted.
- A terminal run with manual rows could pass a loose aggregate gate. The live gate
  now also requires all six rows to be `review_ready`, in addition to audited calls,
  zero current-pass unknowns and the full observed concept loop.
- Successor creation was tested for exact spend/head, changed code, idempotency,
  preserved originals/counters and rejection of an unmodified-code rerun.

Evaluated/current product fingerprint:
`65637edd886996fb5a9a80e1028ed87e483d551e04c38675a511769b02d62299`.
It matches all six successor snapshots and the current-pass authority/report.

| GTIN | Current-pass calls | Cumulative product calls | Outcome | Critique/regeneration | Judge score before → selected |
| --- | ---: | ---: | --- | --- | --- |
| 00954174 | 2 | 5 | review-ready | Early exit; no revision needed | No before/after comparison |
| 854410003041 | 2 | 4 | review-ready | Early exit; no revision needed | No before/after comparison |
| 028800274315 | 5 | 8 | review-ready | One adopted revision | 100 → 100; four deterministic blockers resolved |
| 639713992335 | 4 | 5 | review-ready | One adopted revision; injected quantity fault | 58.75 → 100 |
| 041380291022 | 5 | 6 | review-ready | One adopted revision; injected quantity fault; one repaired judge parse failure | 58.75 → 100 |
| 041497128129 | 5 | 6 | review-ready | One adopted revision; injected quantity fault; one repaired judge parse failure | 58.75 → 96.25 |

All four adopted revisions recorded four resolved blocker findings and zero
introduced findings. These are finding counts, not 16 independent factual errors:
the generated HANOVER draft's blockers were reference annotations despite a judge
score of 100. The unchanged score is evidence that LLM scores alone do not enforce
the deterministic gate, not a score improvement. The three deliberate quantity
faults each closed the missing-required coverage gap. These are not authentic
customer-error rates or independent human quality judgments.

Current-pass results: **6/6 terminal review-ready, zero pending/manual rows, all five
concepts observed, 23 audited actual calls, zero controlled calls, zero new unknowns**.
Two malformed judge responses were followed by validated successful replacements
within the existing two-attempt stage limits. Known usage for this pass is 217,856
input and 7,786 output tokens; the original unknown usage remains unquantified.
The driver took 329.729 seconds. Campaign accounting is **34/96 calls**, exactly
matching the grant and 34 attempt rows. All rows stayed within 16 cumulative calls
and four claims; no stage exceeded two attempts in its new context.

Post-run selected-artifact checks passed 6/6: current fingerprint, immutable frozen
source fact hash, selected revision identity, deterministic eligibility and no
remaining source/draft checks. All new receipts are audited and have no unsafe-tool
event. Integrity passed with 68 artifacts and journal head
`78cc39d53278244e6672b7da47dd65870a3caeea4e253114329b0c58246f9c0b`.
There are zero human reviews, zero export patches, no queued/running tasks and no
further model calls after completion. Review-ready does not mean approved/published.

`scripts/accept_shelfproof.py` on `fixed-code-round1/report.json` now records
`actual_provider=pass`; evidence is under
`var/validation/shelfproof-acceptance-fixed-live-20261021/`. It still correctly exits
2 because independent quality, browser, Windows/tunnel and commercial gates remain
`not_run`, and `production_accepted=false`. The actual run exercised the production
worker/store/installed-Codex path; authenticated UI/HTTP intake acceptance was not
repeated by this successor driver. The original API intake and separate process/API
regressions are distinct evidence, not a claim of complete visual E2E acceptance.

The same frozen implementation passed **785 repository tests, 104 ShelfProof tests,
zero skipped, zero failures** (six dependency deprecation warnings), including real
child/HTTP process checks. JUnit: `var/validation/shelfproof-fixed-live-regression.xml`.
Four frontend tests, TypeScript/Vite production build, focused Ruff and diff checks
passed. Browser discovery was retried using the Browser skill and returned no
available browsers; there was no substitute visual test or fabricated browser pass.
