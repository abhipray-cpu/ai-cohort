# ClauseGate rigorous real-data validation — 17 October 2026

Historical rejected build. The later [fixes and fresh validation](fixes-and-validation-2026-10-17.md) correct the read-boundary defect and retain this run unchanged for comparison. These earlier results must not be presented as the repaired build's measurements.

Verdict: **release rejected: concurrent reads can falsely report audit corruption**. Model-quality evaluation is separate from workflow correctness. This report extends, and does not overwrite, the [earlier implementation baseline](implementation-validation-2026-10-17.md).

## Scope and provenance

Same verified official ContractNLI acquisition: 607 IDs, 606 distinct exact text hashes, 10,319 annotated pairs. SHA-256 of the retained 65,362,913-byte archive is `e03fc77bbf8b53e2976a250e81d8a294bc3d5e5fb014521e477dee9340d6287b`. One unsafe member name remains quarantined, never extracted. No new customer data, consent bypass, external publication or outreach.

Public benchmark documents are real data. Company policies and automated approval responses in this campaign are explicit fixtures, **not actual organizational approvals or qualified legal review**. Annotation labels are evaluator-only and not sent to the model. The official test split remains sealed from inference; this is development validation, not a blind held-out score.

Product API/UI/contracts are unchanged during this campaign, verified by the campaign's SHA-256 manifest. Validation harnesses were expanded; passing helper tests and the final acceptance run are retained separately. No product fix is smuggled into the frozen evaluation.

## Measured workflow and input checks

| Exercise | Result |
| --- | --- |
| Whole-corpus source, span and schema integrity | 607 records / 10,319 labelled pairs checked |
| Revisioned approval-workflow fixtures on real texts | 300 cases on 300 distinct text hashes: 100 clarification, 100 exception, 100 hard block |
| Mechanical assertions across corpus/workflows | 3,314 passed, zero failed |
| Original PDF intake | All 374 safely named original PDFs attempted; 212 no detected gaps, 162 conservatively partial, zero parser rejection |
| Actual PDF HTTP upload/download | 12 documents selected across byte-length range, all accepted; 72 checks passed, including original-byte hashes, source offsets, anonymous denial, stale replacement and concurrent reads |
| Sequential authenticated HTTP approval journey | 21 checks passed |
| Natural-model authenticated HTTP journey | 23 checks passed; one real model proposal, automated reviewer/exception/final-review fixtures, actual background-worker resume and reviewed export |
| Actual isolated worker kill/restart | Seven checks passed; waiting survives termination, response persists with worker down, one continuation and zero inference calls on resume |

The single natural HTTP job reuses development document 456 with one configured hypothesis. It is not an additional distinct document and is not pooled into the 30-document / all-17-hypothesis semantic score.

The PDF partial rule is deliberately conservative: any image object can trigger it, including a logo. No detected gap is not proven visual/text completeness. Three first pages spanning the HTTP PDF size sample were rendered and inspected under the PDF skill; this is a small layout sanity check, not a complete page-by-page extraction assessment or browser test.

## Reproduced failure: read/write snapshot race

`scripts/validate_clausegate_read_race.py` creates an isolated case with real training NDA 34, then runs one writer performing 100 legitimate business-context updates and four concurrent readers, each making 150 case reads.

Two separate retained runs each observed **510 successful reads and 90 false integrity errors out of 600 reads (15%)**. Both final audits verify successfully at sequence 102. Neither test modifies source or audit tables directly. These are two reproductions of one scenario, not independent legal-data samples or a production error-rate estimate.

Cause: `Store.case()` and `Store._verify()` execute multiple SELECTs without one explicit read transaction. Events can be read before a legitimate write commits, and current case payload after that commit. The audit-head state hash comparison then treats two valid but different snapshots as corruption. Mutations already use `BEGIN IMMEDIATE`; the read path does not have the same snapshot boundary.

Authenticated in-process ASGI HTTP reproduction then returned **491 successful reads and 109 false HTTP 409 integrity conflicts out of 600 requests**, again with a valid final audit. This uses the actual API route and authentication, not browser interaction or network transport. Its artifact is `clausegate-read-race-http-rigorous-v1/report.json`.

Impact observed: spurious integrity failures during legitimate concurrent activity and a disruptive review experience. **No actual audit corruption, unauthorized approval or data loss was demonstrated** by this test. It remains a release blocker because a collaborative approval product must not falsely report corruption under ordinary updates.

Next correction needs a consistent read/snapshot strategy across case, evidence, roles and audit checks, with explicit consideration of independently advancing authority/anchor state. Add a deterministic interleaving regression and repeat the real-data concurrency test. This testing request does not silently change product behavior; the defect remains open in this frozen build.

## Dataset quality: lexical/template overlap

`screen_clausegate_corpus.py` compares all 183,921 document pairs using lowercase ASCII-alphanumeric tokens, unique contiguous five-token shingles, 128-bit SHA-256 fingerprints and exact Jaccard similarity ≥0.70. All parameters and pair IDs are retained.

It flags **28 high-overlap pairs, including 12 across official splits**, despite zero exact raw-text-hash overlap between splits. Examples include train/test similarities above 0.99 and one identical normalized shingle set. This is evidence of substantial lexical/template overlap, not proof of identical legal meaning. No document is silently removed, split reassigned or threshold tuned against the model answers. No model-training provenance or semantic-template independence is established.

None of the 30 selected live documents occurs in a flagged pair at this threshold. That is a lexical diagnostic, not a guarantee of independence or absence of model-training exposure.

Any future held-out claim must disclose affected clusters and provide official plus clean-cluster diagnostics; a high benchmark score alone would not establish generalization to new contract families.

## Live-model cohort and scoring

The campaign preselects 30 distinct development documents at evenly spaced ranks across source-text length, including shortest and longest. Selection uses no labels. Text lengths range 2,270–32,359 characters, with 1–3 serialized source chunks. All 17 hypotheses are configured per document. Selection method, IDs and original job outcomes are retained under `var/validation/clausegate-rigorous-v1/`.

The source spans, hypotheses and company-context fixture are the only model task data. Model output cannot approve or execute tools; installed-adapter audit and strict schema/source checks remain enforced. No labels are changed or corrected before scoring. Provider failures/partial results remain in denominators as missing, not correct guessed `NotMentioned` answers.

Final primary campaign: **30 attempted, 26 completed analysis, four partial**, all 30 preserved in scoring. The 26 complete cases wait for human input, not automatic approval. Four partial cases (610, 13, 595, 7) retain degraded findings and cannot be counted as completed analysis. Document 610 retains one completed chunk; the other three have no completed chunk. Their audit records report `stage_unavailable: RuntimeError`. Original provider stderr/exit details were not retained by the worker, so the specific underlying causes are **unknown**, not invented as timeouts or rate limits. Subsequent successful analysis of document 64 does not retroactively explain the failures.

| Primary diagnostic | Result |
| --- | ---: |
| Label matches, all attempted pairs | 341 / 510 (66.86%) |
| Missing/unusable predictions from partial stages | 68 / 510 |
| Label matches, completed stages only | 341 / 442 (77.15%); not the all-attempt success rate |
| Three-class macro-F1, all attempts | 0.6656 |
| Training-only per-hypothesis majority baseline | 342 / 510; macro-F1 0.6195 |
| Model-marked supported subset | 290 pairs; 232 correct, **58 wrong (20%)** |
| Supported-subset coverage | 56.86% of attempted pairs; uncalibrated |
| Evidence character-overlap micro-F1 | 0.4241 |
| Evidence token-overlap micro-F1 | 0.4213 |

The model has higher macro-F1 than this simple baseline but **does not exceed its overall label-match count** once partial failures remain in the denominator. Development macro-F1 and evidence overlap do not demonstrate the provisional 0.85/0.80 held-out quality targets. Even among supported proposals, substantial errors remain. Mandatory review stays essential; no safe autonomous clearance rate is established.

`scores.json` retains per-class/per-hypothesis metrics, confusion matrices and all 510 gold/predicted pairs. The pinned token metric uses Unicode-regex word/punctuation tokens and source interval overlap; it is **not the official ContractNLI scorer or proof that all material exceptions were cited**. Correlated hypotheses within documents are not 510 independent contracts. Gold annotation ambiguity remains possible; no independent legal adjudication occurred.

Observed runtime: codex-cli 0.160.0, Python 3.12.14, Node v24.10.0, Pydantic 2.14.1, FastAPI 0.143.0, PyMuPDF 1.28.2, HTTPX 0.28.1 and pytest 9.1.1, on macOS ARM64. The exact remote inference model revision was not retained; CLI version alone does not pin model weights or guarantee deterministic reproduction.

## Five-concept coverage

| Concept | Exercised behavior and result |
| --- | --- |
| Uncertainty detection | Natural uncertain/partial findings produce review or degraded status; supported flags still have 20% label error and are not calibrated |
| Pause | Durable request/checkpoint survives Store reopen and actual worker termination; no inference while waiting |
| Request human input | Typed scoped clarification, interpretation and exception fixtures; own-request, CSRF, scope and stale-input rejection |
| Resume with validated context | Actual HTTP worker continuation, exact packet review and source-change invalidation pass sequentially; concurrent read consistency fails |
| Full audit trail | Source-to-decision-to-resume verification and tamper/recovery tests pass; concurrent reads can falsely reject a valid audit, so collaborative acceptance fails |

## Remaining unavailable acceptance

Final `clausegate-rigorous-v1/acceptance/report.json` records **four passed, one failed, five blocked**; verdict **rejected**, `full_acceptance_completed=false`. Fresh unmasked monorepo regression: **331 Python tests passed, zero failed/skipped, 38.596 seconds**; four frontend tests, production TS/Vite build and Ruff pass. Separate stress evidence is a failed gate, not hidden as a passing pytest result. The 30-completed-live-documents gate is still blocked because only 26 analysis stages completed. Acceptance intentionally exits nonzero.

Browser skill discovery again returned no browsers; actual visual, keyboard, responsive/accessibility and two-person browser acceptance remains **blocked**. HTTP clients, React state tests, production builds and PDF renders do not substitute for it.

Actual old-Windows service identity/reboot, protected Cloudflare route, all-products resource contention, independent qualified review and consenting-customer usefulness remain unrun. No tunnel or Windows task was installed. Natural semantic accuracy and mechanical safety do not replace those gates.

## Reproduction

Run from the repository root, choosing **new** output paths. Retained results are not overwritten:

```bash
.venv/bin/python scripts/validate_clausegate.py --corpus var/validation/clausegate-corpus-v2 --output var/validation/clausegate-rigorous-NEW --workflow-cases 300 --live-jobs 30 --sample length-spread --pdf-limit 1000
.venv/bin/python scripts/score_clausegate.py --corpus var/validation/clausegate-corpus-v2 --evidence var/validation/clausegate-rigorous-NEW --output var/validation/clausegate-rigorous-NEW/scores.json
.venv/bin/python scripts/screen_clausegate_corpus.py --corpus var/validation/clausegate-corpus-v2 --output var/validation/clausegate-screen-NEW.json
.venv/bin/python scripts/validate_clausegate_http.py --output var/validation/clausegate-http-NEW.json
.venv/bin/python scripts/validate_clausegate_http.py --natural-ai --output var/validation/clausegate-natural-http-NEW.json
.venv/bin/python scripts/validate_clausegate_pdf_http.py --output var/validation/clausegate-pdf-http-NEW.json
.venv/bin/python scripts/validate_clausegate_recovery.py --output var/validation/clausegate-recovery-NEW
.venv/bin/python scripts/validate_clausegate_read_race.py --output var/validation/clausegate-read-race-NEW
.venv/bin/python scripts/validate_clausegate_read_race.py --http-readers --output var/validation/clausegate-read-race-http-NEW
.venv/bin/python scripts/accept_clausegate.py --evidence var/validation/clausegate-rigorous-NEW/report.json --output var/validation/clausegate-rigorous-NEW/acceptance --run-tests --read-race-evidence var/validation/clausegate-read-race-http-NEW/report.json
```

The read-race command intentionally exits nonzero when the defect reproduces. Acceptance must reject the build when that evidence fails, even if unit tests, the UI build and sequential HTTP journeys pass. Existing local fixture workspaces created by HTTP validation are retained for inspection; earlier products were not stopped.
