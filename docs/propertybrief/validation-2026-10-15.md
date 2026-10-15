# Implementation and actual-data validation — 15 October 2026

Verdict: locally runnable, functionally tested pilot; **not production-ready**. Actual records validate acquisition, identity handling, provenance and bounded agent behavior. They do not supply independent finding-quality labels or establish current building condition. Failed/partial model runs remain part of the evidence.

## 1. Implementation verification

Environment: macOS 15.7.3 ARM64, Python 3.12, Node 24; installed authenticated Codex CLI, with public source/model network access. Code is uncommitted workspace implementation, so model evaluation sessions pin file SHA-256 hashes as well as the base commit. Files loaded before a later patch are not claimed to contain that patch.

| Check | Measured result |
| --- | --- |
| Full repository `pytest -q` | **153 passed**, six dependency deprecation warnings |
| PropertyBrief collection | 59 tests, including 14 frozen-actual-data cases/checks |
| Frontend `npm ... test` | **4 passed** |
| TypeScript/Vite production build | Pass; approximately 251 kB JavaScript / 78 kB gzip, 19.4 kB CSS / 5.1 kB gzip |
| `ruff check .` | Pass |
| Local managed up/down/status | API and worker started/stopped independently of earlier products; final processes running |
| Final authenticated HTTP/assets smoke | Pass after worker reload; `var/propertybrief-http-smoke/report-1792042527488243000.json` |
| Actual browser interaction/visual QA | **Not run successfully**: supported browser runtime returned no available browser; no substitute browser or screenshot pass claimed |

`pytest` includes regression tests for earlier products after additive shared-provider changes. Actual-data tests skip if the ignored corpus is absent; this validation machine had the corpus and ran them. New checkout test passes without that corpus do not imply actual-data validation.

## 2. Real data acquired

Frozen corpus: `var/propertybrief-corpus/20261014-final/manifest.json`, created **2026-10-14T16:50:59.786233+00:00**. All ten official dataset metadata captures, case payloads and raw source hashes verify through `load_corpus`. Earlier `20261014-first` and `20261014-v2` artifacts are preserved rather than overwritten after query corrections.

- **12 actual buildings**, borough distribution Manhattan 3, Bronx 3, Brooklyn 2, Queens 2, Staten Island 2.
- **3,346 raw/normalized source records** across eight required sources.
- **96 source checks**: 91 `complete_for_query`, five `unknown`.
- Unknown checks: building `375411` HPD complaints and DOB violations; `44538` HPD complaints and underlying conditions; `44539` HPD complaints.
- Gaps reflect identifier conflicts or actual transport/metadata failures. Neither an unknown result nor an outage is a zero-result pass.
- Feasibility cohort curated from source records; not representative sampling, independently adjudicated gold or a held-out set. Building `44540` contributes 2,046 records, so totals are not balanced quality denominators.

These are public agency records, not model-created fixtures. [NYC Open Data terms](https://data.cityofnewyork.us/stories/s/Terms-of-Use/k9k7-3cje) apply; raw captures stay ignored rather than asserting unrestricted redistribution. Dataset IDs and attribution are in [research and sources](research-and-sources.md).

### Bugs discovered with real records and fixed through regression tests

| Discovery | Fix and evidence |
| --- | --- |
| DOB query padding differs from BBL | DOB block and lot use five digits; BBL embeds lot in four. Query regression test checks official filter values. |
| Current-parcel-only DOB filtering dropped old records | Query confirmed BIN regardless of historical lot; parcel fallback only for missing-BIN rows. Actual row `285232` matches BIN `3327904` but historical lot 1 rather than current lot 15; preserved with `parcel_identifier_differs`. |
| HPD complaint building ID may disagree with its BIN/BBL | Preserve matching-building row, mark `identity_conflict`, set status/affected coverage unknown. Frozen replay tests prove it is not silently discarded. |
| Metadata can fail after rows arrive | Keep rows but downgrade completeness unknown; no false complete source. |
| Model invented source/field aliases | Literal source keys and dynamic per-source row/field JSON Schema, plus independent exact-value validation. `identity` is not a citation source; `buildings` is. ECB uses `ecb_violation_status`, not generic `status`. |
| Confirmed identity itself needs provenance | Create a citable `buildings` snapshot, include it in report/export manifests and backfill older recovered runs. |
| A valid complaint warning was rejected | Negation-aware guard allows “not a verified violation” while still rejecting the positive claim. This is a conservative pattern check, not full entailment. |
| An inspected row remained omitted from planning context | Inspected source gets priority and explicit omitted-row accounting. Empty sources no longer consume row-text allowance. Both new tests failed before the fixes and passed afterward. |
| Critic sampled unrelated rows / mistook prompt omissions for source gaps | Critique context prioritizes actual cited rows; omitted cited rows force insufficient. Explicit context-scope metadata/instruction distinguishes prompt sampling from source acquisition. Exhaustive recall is not assessed by this critic. |

TDD was used for core contracts/store/source/agent behavior and the real-data regressions: add a failing expectation, implement the bounded change, rerun the affected tests, then the complete suite. Additional tests audit native-tool rejection and successful tool-free provider completion. Tests are not a retrospective claim that every discovered issue was anticipated.

## 3. Actual Codex evaluation, including failures

All sessions below used official frozen records with actual installed Codex generation, not the scripted test provider. Each report's structural citations were independently checked against its source rows. That verifies exact references, not general semantic accuracy or material finding recall. Session directories are below `var/propertybrief-evaluation/` and ignored locally; keep them when reproducing failures.

| Session | Building | Status | Actions / calls | Seconds | Findings / references | Critique / result |
| --- | --- | --- | --- | --- | --- | --- |
| `20261014T163553106611` | 375411 | partial | 4 / 5 | 45.15 | 4 / 4 | not assessed; provider unavailable |
| `20261014T164012050671` | 375411 | partial | 11 / 11 | 147.04 | 11 / 11 | not assessed; unknown inspection IDs |
| `20261014T164421902226` | 375411 | partial | 10 / 12 | 183.50 | 11 / 11 | not assessed; repair exhausted |
| same | 1 | partial | 10 / 14 | 302.06 | 16 / 16 | not assessed; repair exhausted |
| `20261014T165432933810` | 375411 | partial | 12 / 15 | 320.89 | 14 / 14 | not assessed; report validation failed |
| same | 1 | partial | 9 / 11 | 242.06 | 20 / 20 | not assessed; provider timeout |
| `20261015T051923975939` | 375411 | partial | 14 / 18 | 236.20 | 2 / 13 | revise; unsupported findings removed |
| same | 44538 | partial | 10 / 17 | 318.73 | 4 / 25 | revise; citation/coverage objections |
| `20261015T052503182679` | 44538 | partial | 11 / 16 | 294.06 | 5 / 36 | revise; per-source field schema worked, source gaps retained |
| `20261015T052619124458` | 399115 | partial | 10 / 15 | 226.38 | 3 / 21 | revise; exposed context allocation bug |
| `20261015T053621081020` | 706227 | **completed** | **8 / 11** | **181.32** | **4 / 23** | **pass**; all eight sources complete-for-query |

The first ten initial investigations produced **zero completed reports**; the eleventh, after the context/schema fixes, completed. Across this development series: **one completed, ten partial**, spanning five unique buildings. This is not a controlled model failure-rate benchmark: corpus revisions, code revisions and repeated properties differ. Do not market partial outputs as successful complete narratives, or one successful sparse case as proof of reliability on full, conflict-heavy packs.

The final case, building 706227, used the finished context/schema code. It distinguished a historical electrical complaint from a verified violation, preserved occupant-reported closure as a source statement, and proposed seller documentation, current inspection and authorized-use verification. Seven query-specific empty datasets did not become property clearance. Independent exact-reference validation passed for all 23 finding references. Its same-model critique passed; independent human accuracy/recall is still unmeasured. This is frozen-source/actual-model evidence, not another live-source/browser journey.

### Recovery evidence

- `20261014T165432933810/recovery-20261015T051249537871.json`: buildings 375411 and 1 reused earlier observations, reached advisory critique, remained partial with revise outcomes.
- `20261015T052503182679/recovery-20261015T053024859915.json`: building 44538 reused eight checkpoints; zero new source actions, two additional calls, provider timeout. All evidence retained, critique not assessed on the new fallback revision.
- `20261015T052619124458/recovery-20261015T053313338983.json`: building 399115 reused eight checkpoints. The planner explicitly observed both HPD rows and `inspection_rows_omitted=0`, demonstrating context delivery after the fix. Later generation timed out; prior report remains available and the new partial fallback preserves evidence.

Recovery is an explicit second budget grant, not a reset. These runs cannot receive unlimited grants. Old reports are preserved even if a later fallback becomes the latest revision. Code hashes in recovery files distinguish the tested fixes; the final critique prompt-scope clarification was added after the 399115 recovery started and is not attributed to that run.

## 4. Live source → HTTP → reviewed export → follow-up

Evidence: `var/propertybrief-http-smoke/report-1792042420885969000.json`; actual app database `var/propertybrief/propertybrief.sqlite3`.

The automated HTTP client verified unauthenticated case access gets 401, authenticated HTML/assets load, BIN/address resolves official building 375411, identity is explicitly confirmed, a worker acquires current official records, a durable report is reviewable, and Markdown export retains coverage/limitations and SHA-256 source manifests. A follow-up remains in the same case/conversation and returns another durable report.

- Initial run: **partial**, 12 actions, 16 calls, 24 HTTP attempts; all eight sources attempted, self-critique requested revision.
- Follow-up: **partial**, zero new source actions, four calls; pinned evidence reused, critique requested revision.
- Case has two persisted user messages. Export required explicit review/partial acknowledgment.
- Earlier HTTP attempt `report-1791997279670863000.json` is preserved and had report-validation failures; not counted as a narrative success.

This verifies the HTTP workflow, not browser interaction or expert report quality. The service was reloaded after context changes and final auth/assets smoke passed; that final smoke does not rerun the model workflow.

## 5. Required Day 3 concepts

| Concept | Implementation / observed evidence |
| --- | --- |
| Observe | Typed source results saved as snapshots with counts, quality flags and coverage; actual 96-check frozen corpus and live acquisition |
| Think | Structured next-action selection; actual traces choose source order and record inspection based on prior results |
| Act | Python dispatches read-only registry queries/inspections/comparisons; actual HTTP attempt counts; no model-owned shell/source URLs |
| Reflect | `think_reflect` events explain effects of previous results; 399115 recovery explicitly recognizes recovered rows and preserves historical/current uncertainty |
| Max iteration limit | Fixed 16 actions / 24 calls per grant, 48 HTTP attempts, deadline/repeat limits and cumulative ceilings; deterministic exhaustion test proves reserved finalization. Do not claim every boundary was reached in live runs. |
| Self-critique | Separate real critique calls produce unsupported IDs/issues; safe removal/revision, same-model advisory status, unresolved issues remain partial |
| Graceful degradation | Real provider failures/timeouts preserve source previews, snapshots and prior report revisions; stage events accompany stop reasons; partial reviewed export retains gaps |

All requested behaviors exist. Their implementation does not establish that every actual investigation completes or that the product is production-ready.

## 6. Backup and deployment evidence

Online SQLite backup and restore succeeded into new directories:

```text
var/backups/propertybrief-20261015-validation/
var/propertybrief-restore-20261015-validation/
```

Original/restored counts matched: cases 2/2, runs 4/4, snapshots 18/18, reports 4/4, exports 2/2. The helper verified SQLite integrity and raw evidence hashes; tests separately reject tampered backups and existing destinations. This is macOS restoration evidence, not a Windows reboot drill.

## 7. Remaining release gates

Reliable complete narratives on dense/conflict-heavy cases and independent quality review remain open. A sparse-case complete run does not close those gates. No 60-case labelled cohort, precision/recall score, calibrated critique score, paired manual baseline, paid customer validation or measured time saving exists. Current facts do not justify financial/legal/safety advice or blanket property clearance.

Browser tool availability prevented actual keyboard/viewport/screenshot journeys; premium visual quality/accessibility has no recorded acceptance. Windows service-account auth, task restart/reboot/sign-out, descendant cleanup, old-laptop resources, disk-full handling and protected Cloudflare tunnel policy remain untested on the target host.

Reproduction commands are in [operations](operations.md) and [data instructions](../../data/propertybrief/README.md). New live public data can change counts/statuses; never overwrite this frozen evidence or replace an unknown source with a favourable fabricated fixture.
