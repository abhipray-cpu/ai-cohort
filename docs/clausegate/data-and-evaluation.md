# Real-data validation and release gates

Status: **engineering checks pass; semantic/release acceptance still blocked**. [Complete development evidence](development-validation-2026-10-17.md) covers 607 corpus records, 300 workflow fixtures, all 374 safe PDFs and all 61 official development NDAs (1,037 predictions). The [repair comparison](fixes-and-validation-2026-10-17.md) and [rejected build](rigorous-validation-2026-10-17.md) remain preserved. Read consistency passes; model accuracy/calibration remain inadequate. Lexical screening flags 12 high-overlap pairs across official splits. Thresholds below are proposed release criteria, not measured performance. No generated agreement or repeated inference is counted as a new real contract.

## Three independent layers of evidence

| Layer | Input/oracle | What it can establish |
| --- | --- | --- |
| Semantic interpretation/evidence | Real ContractNLI text with existing human labels and spans | Three-way classification and evidence support on those defined propositions |
| Approval-system mechanics | Versioned, clearly labelled test playbooks and controlled actor/event scenarios over real documents | Correct pause, routing, authority, decisions, revalidation and audit behavior under the fixture |
| Product/legal usefulness | Separately consenting teams, approved playbook and qualified reviewers | Whether findings/approvals are useful and appropriate for their actual work |

Never use a fixture approver's programmed “yes” as real-world approval ground truth. Our own interactive decisions exercise the mechanism; they are not independent legal certification. Source quotes can be exact while the interpretation is wrong.

## Acquisition, provenance and rights

Primary: [ContractNLI](https://stanfordnlp.github.io/contract-nli/) publishes 607 NDAs and 17 hypotheses, labels/evidence, original URLs and source types. Secondary: [CUAD](https://www.atticusprojectai.org/cuad/) publishes 510 mixed contracts and clause annotations. Record license/use notices/attribution and any access prerequisites; if terms require new account consent or a material agreement, report that prerequisite rather than bypassing it. No credentials discovery, gated-term acceptance or customer upload is part of this stage.

Acquisition must use explicit trusted publisher URLs, bounded HTTPS reads and archive path/size checks, not URLs extracted from an NDA. Freeze raw archive bytes, extracted files and manifests. Record requested/final URL, observation time, status, size, SHA-256, upstream version/commit if available, license, source record ID and parser version. Do not execute downloaded scripts or untrusted archive content.

Store raw data outside source control unless redistribution is explicitly reviewed. Suggested runtime roots: `var/validation/clausegate-<campaign>/raw`, `normalized`, `results`; tracked manifests/schema/annotation instructions may live under `data/clausegate/`. Preserve failures and partial coverage. Missing original PDFs do not invalidate text-only semantic evaluation, but block claims about original PDF/OCR performance.

## Volume and quality targets

1. Acquire/verify the entire declared 607-record primary corpus. Count actual distinct IDs, text hashes, template/near-duplicate clusters, complete/partial/unreadable records, source types and span integrity; reconcile against publisher counts rather than assume them.
2. Run deterministic ingestion, canonical integrity, exact offsets, dedup replay and coverage checks over all acquired primary records. Published 607 × 17 yields 10,319 potential document/hypothesis pairs; actual observed labels and evaluated predictions determine denominators.
3. Evaluate the published semantic train/development/test split without moving failures into development. Observe actual split counts after acquisition; no invented 423/61/123 counts in reports before checking artifacts.
4. Freeze ≥60 real-document workflow cases: 20 clarification, 20 waivable-exception and 20 hard-block/no-authority cases under fixture playbooks. Include both semantic positive/negative examples, missing facts, distributed exceptions and conflicting interpretations. Repeated scenario variants do not increase unique contract counts.
5. Exercise original PDF/text intake on ≥30 distinct real documents when original artifacts and rights permit, stratified by length/source type. JSON text replay alone does not satisfy this gate. If native source artifacts cannot be acquired, report the blocked gate; corrupted/scanned variants are labelled mutations, not new natural scans.
6. CUAD optional secondary target: ≥50 distinct contracts across ≥5 agreement types for extraction/OOD behavior, kept separate from primary NDA metrics. It is not mandatory to broaden product scope in order to claim a larger number.

Do not discard ambiguous, long, contradictory or provider-failed cases to improve metrics. Report discovered/acquired/eligible/supported/analyzed/complete/uncertain/reviewed/exported counts separately. Label out-of-scope negatives, exact/near duplicates and split overlap; no unreviewed subset called a fully screened cohort.

## Split, labels and leakage

Use official training material for development only. Split development deterministically into policy-tuning and calibration subsets, keeping duplicate/template clusters together and recording seed/IDs before scoring. Keep official test sealed from prompts, examples, policy tuning and source selection. Inspect cross-split duplicates using exact hashes and a documented near-duplicate method; flag contaminated clusters and publish official plus clean-cluster diagnostics. If contamination makes the generalization claim untenable, acquire a genuinely new independently labelled challenge cohort instead of silently redefining test.

Gold labels/spans live in evaluator-only storage, never inside model scratch context or provider-accessible files. Evaluate model output before human corrections. Do not compare corrected final answers with gold and call them model accuracy. The same model generating labels and answers cannot supply independence. ContractNLI documentation describes one annotation set per document; potential annotation ambiguity is a reported limitation, not a claim of two-reviewer adjudication.

For a separate ≥60-document challenge sample and practical policy findings, two independent qualified reviewers annotate the relevant checks/evidence/critical omissions before seeing model output; adjudicate disagreements, record agreement and remaining ambiguity. Requester/user workflow exercise cannot substitute if qualified reviewers are unavailable. No model replaces this gate. Human reviewers must not review their own prior annotation as independent evidence.

## Baselines and measurements

Baselines: majority-class; documented lexical/rule heuristic; same installed model/evidence context without uncertainty routing; conservative all-manual review. Compare AI-only and AI-plus-human outcomes separately. Provider versions/prompts, artifact hashes, machine/runtime versions and policy thresholds must be frozen at run start and verified unchanged at end. Never tune on a test failure and call the same corrected test blind again.

Semantic metrics: class/per-hypothesis precision/recall/F1, macro-F1, confusion matrices, exact evidence validation, evidence span/token F1 with a pinned scorer, all-required-evidence coverage and critical exception misses. Log partial/incomplete/abstained/provider-failed separately; `NotMentioned` is a prediction class, not abstention. If the model emits a subset of hypotheses, missing predictions are unevaluated/failures, not silently absent from denominators.

Uncertainty metrics: risk–coverage curve, accepted-finding error, false-clearance rate for fixture policy, precision/recall of escalation reasons, unnecessary-review rate and reviewer workload. Initial uncertainty is uncalibrated; do not infer probabilities from model prose, rank or repeated agreement.

Workflow metrics: request correctness, per-rule routing, outstanding blocker counts, time actively working versus time waiting, duplicate effective decisions/continuations, stale/unauthorized attempts rejected, audit event coverage, decision-to-resume latency and grant usage. All-human deferral can be safe yet commercially useless; show automation/review coverage beside error rates.

Provisional quality thresholds: held-out macro-F1 ≥0.85; evidence token/span F1 ≥0.80; all published citations resolve exactly; zero observed critical falsely cleared cases in the adjudicated set. If allowing low-risk machine findings without per-finding review, require ≥25% selective coverage and a one-sided 95% exact-binomial upper bound ≤2% for accepted-finding error. With zero observed errors this needs at least 149 accepted independent pairs; correlated pairs/templates weaken independence, so also report cluster-level uncertainty and qualified review. If evidence is insufficient, keep per-finding human review mandatory and mark the automation-quality gate unmet—not a fake percentage. Final packet review stays mandatory regardless.

## End-to-end real-data scenarios

| Scenario | Required result |
| --- | --- |
| Clear supported clause, no policy exception | Finding recorded with evidence; final human review still required |
| Negation/exception elsewhere in NDA | All material spans considered or explicit uncertainty, not confident partial reading |
| Missing required business fact | Targeted clarification; no invented company side/purpose |
| Waivable deviation | Correct role request, durable pause, explicit rationale and bounded acceptance |
| Hard block | Ordinary reviewer cannot waive it or force resume |
| Human interpretation correction | New finding revision, deterministic reevaluation and fresh affected requests |
| Two concurrent reviewers/forms | No lost update; same checkpoint/quorum rules and explicit conflict |
| New upload/same filename or playbook change | Previous form/approval rejected as stale |
| Revocation/withdrawal/expiry while worker runs | Egress/publication final fence blocks readiness |
| Provider parse error or later timeout | Bounded repair, separate history event and retained source/checkpoint/decision |
| Process crash while waiting or after decision | Restart persistence, no repeated calls or duplicate effective continuation |
| Erase then restore old snapshot | Current ledger applied; restored approvals unusable; fresh authority required |
| Poisoned source or reviewer comment | No tool execution, hidden approval, scope change or policy overwrite |
| Actual two-browser workflow | Both people see current revision, explicit conflict and invalidated exports |

## Gate matrix

| Gate | Evidence required | Current state |
| --- | --- | --- |
| G01 build/contracts/regression | Fresh full monorepo Python suite without masked failures, frontend tests/build, exact code manifest | Engineering pass: 346 Python tests, four frontend tests/build and frozen API/UI/contract hashes |
| G02 corpus/rights/integrity | Verified primary capture, license attribution, schema/spans/denominators and original-artifact intake sample | 607 IDs/606 texts; 374 PDFs attempted, 162 conservatively partial; lexical screening flags 28 high-overlap pairs, 12 across splits; full visual coverage open |
| G03 semantic/uncertainty quality | Frozen held-out classification/evidence/risk–coverage and qualified challenge review | Blocked: all-development macro-F1 0.6995, evidence-token F1 0.5370, 162/637 supported labels wrong; no qualified/held-out/calibrated sign-off; historical conditional regression preserved |
| G04 pause/input/resume | ≥60 real-document fixture workflows plus actual separate-person browser journeys | 300 fixtures, 21 fixture HTTP and 24 fresh natural-model HTTP checks pass; actual separate-person browser journey open |
| G05 authority/currentness | Race, revocation, CSRF, separation-of-duties, stale and corruption tests | Corrected read fence and authority regressions pass; actual HTTP 600/600 successful reads during 100 updates; not penetration-certified |
| G06 audit/recovery/privacy | Atomic event lineage, tamper/anchor/restore/erasure drills, zero duplicate effects | Valid audit under corrected concurrent reads; seven process-recovery and 11 real-source backup/erase/restore checks pass; host assurance open |
| G07 live provider | Preselected ≥30 distinct NDAs through installed adapter, natural/partial/failure counts; no mocked success | Integration pass: all 61 development NDAs complete in 61 calls, 790/1,037 labels match; not semantic/production acceptance |
| G08 browser/premium UI | Keyboard, responsive, accessible source/decision workflow with two sessions | Blocked: no connected browser; build/state/HTTP passes do not substitute |
| G09 Windows/edge/resources | Actual service identity/reboot, protected edge, all-six-product measurements | Unrun on actual target host; packaging/example route only |
| G10 usefulness | Authorized paired customer tasks and no increased critical misses | Unrun; no outreach or customer data collection performed |

A future acceptance runner must fail or block when any mandatory gate lacks evidence, not infer acceptance from a unit test exit code. ≥30 live documents is the workflow integration minimum, not a substitute for complete declared held-out semantic evaluation. Provider-limited batches checkpoint safely; unrun evaluation remains unrun.

## Reporting cadence

Before inference: freeze manifests/splits/thresholds and record original code/model/policy hashes. After each batch: checkpoint attempted/completed/partial/failed counts, safe stage reasons and cumulative usage. At end: verify hashes unchanged, retain raw authorized evidence separately, produce metrics with denominators and failed cases, assess every gate. Repeat corrections in a new labelled campaign, preserving the old failure.

Only after implementation and this honest validation handoff: write the study guide correlating concepts to code/tests, and one blog based on measured data and limitations. Do not prewrite a fictitious success story or externally publish without permission.
