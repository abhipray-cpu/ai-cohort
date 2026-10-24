# ClauseGate: complete development-set validation — 17 October 2026

Verdict: **engineering/integration checks pass; semantic and full-product acceptance remain blocked**. This is the evidence for the final [study guide](study-guide.md), not a production certificate.

## What ran

The current API/UI/contracts match the frozen repaired build in [the earlier 30-document campaign](fixes-and-validation-2026-10-17.md). No product behavior, prompt, policy threshold or model configuration was changed for this expansion. Validation helpers were extended and tested to select a disjoint complement and pool scores without duplicate predictions or averaged F1.

The original fixed cohort contains 30 development NDAs. A fresh campaign evaluated the remaining **31 distinct documents**, with zero ID/text overlap against that cohort. This covers **all 61 official development documents, 61 exact-distinct texts and 1,037 document/hypothesis pairs**. Some complement documents occurred in earlier diagnostics: this is not a claim that they were never model-seen, blind or independent data. Repeated diagnostics are not additional contracts.

Complement UTC start: `2026-10-17T13:12:45.837114+00:00`; finish: `2026-10-17T13:33:23.874260+00:00`. Product hashes remain unchanged. Gold labels/spans stay evaluator-only, outside provider context. The official 123-document test split was not sent to inference. Published split/template overlap and possible model-training exposure still weaken independence claims.

## Semantic results: all attempts retained

| Metric | All 61 development NDAs |
| --- | ---: |
| Analysis stages completed | 61 / 61 |
| Reserved model calls | 61 |
| Label matches | 790 / 1,037 (76.18%) |
| Missing/unusable predictions | 0 |
| Three-way macro-F1 | 0.6995 |
| Training-only per-hypothesis majority baseline | 706 / 1,037; macro-F1 0.6325 |
| Evidence-token precision / recall | 0.5662 / 0.5105 |
| Evidence-token micro-F1 | 0.5370 |
| Evidence-character micro-F1 | 0.5452 |
| Model-marked supported subset | 475 correct / 637; **162 incorrect (25.43%)** |
| Supported-subset coverage | 61.43% of attempted pairs; uncalibrated |

The complementary 31-document batch alone matched 409/527 labels, macro-F1 0.7132; it is a different cohort, not a paired improvement over the 30-document batch. Combined metrics are recomputed from all predictions and raw evidence-overlap counts, not averaged batch F1. The exact same pinned scorer is used for both components. Token overlap uses the documented Unicode word/punctuation interval method, **not the official ContractNLI scorer or proof of semantic sufficiency**.

All completed analyses wait for human input. No actual person legally approved these agreements. “Supported” remains a model assessment, not calibrated confidence: a quarter of that subset disagrees with published annotations. Contradiction remains especially weak (63 correct detections from 95 gold examples, with many false positives). No target is lowered to create a pass. The provisional 0.85 classification / 0.80 evidence thresholds are not demonstrated, and qualified held-out/challenge review is absent.

The repaired 30-document comparison also remains relevant: overall gains partly recovered provider failures, while matches on previously usable pairs fell from 341 to 331. This full-development expansion does not erase that regression or prove a causal prompt improvement.

## Fresh workflow, intake and recovery checks

- **3,314 mechanical assertions passed** in the complement campaign: whole-corpus integrity plus **300 workflow fixtures on 300 distinct real texts**, with 100 clarification, 100 exception and 100 hard-block cases. Repeating the same fixtures is not 600 independent contracts or actual customer approval history.
- Retained official corpus: **607 IDs, 606 distinct text hashes, 10,319 annotated pairs and 27,439 source spans**, with archive/normalized hashes verified. One unsafe archive member remains quarantined. The previous lexical screen flags 28 high-overlap pairs, 12 across published splits.
- **374 safely named original PDFs** checked again: 212 without detected gaps and 162 conservatively partial because image content/OCR completeness cannot be assessed. No source parser rejection in this batch. No detected gap is not visual completeness.
- **12 original-PDF HTTP journeys / 72 checks passed**, including original-byte round trips, Unicode source ranges, anonymous denial, stale upload and concurrent reads.
- **21 authenticated fixture HTTP checks passed**. The fresh **natural-model HTTP journey passes 24 checks**, including an uncertain interpretation response before exception approval, actual worker continuation and exact final-review/export fixtures. The count differs from the prior 23-check supported branch. These reviewer responses are automated fixtures, not real human/legal review. Its reused one-hypothesis document is not pooled into semantic scoring.
- Actual managed-service stress: **100 legitimate updates and 600/600 HTTP 200 reads**, valid audit. This small Mac loopback workload is not a Windows/load/SLA certificate.
- **Seven actual isolated worker restart checks** and **11 real-source concurrent backup/later-erasure/quarantine/fresh-authority recovery checks passed**. Only own public-source fixtures were logically erased; snapshots/public originals remain. No customer source was removed.
- Fresh unmasked monorepo regression: **346 Python tests, zero failed/skipped**; four frontend tests, production TypeScript/Vite build and Ruff pass. This includes the validation-helper safeguards, not 346 independent semantic cases.

## Acceptance boundary

Fresh assessment: **six gates passed, four blocked**, `verdict=blocked`, `full_acceptance_completed=false`. Its nonzero exit is intentional. Passed engineering gates do not override weak semantic results.

Still unavailable: independent qualified/held-out quality and calibrated risk, actual two-person browser/keyboard/responsive/accessibility acceptance, actual old-Windows/protected-Cloudflare/all-products resource acceptance, and consenting-customer usefulness. Browser skill setup/discovery was retried and returned no available browser. No substitute browser screenshots or passes were invented. No tunnel, Windows task or external publication was changed.

The host is macOS, not the target Windows laptop. Inference uses the installed isolated Codex adapter and may be remote; CLI version does not pin the remote model revision. Synthetic policy/approver fixtures cannot establish legal or commercial correctness.

## Retained artifacts

Under `var/validation/`:

- `clausegate-development-complement-v1/report.json`: fresh 31-document run, corpus/PDF/workflow checks and frozen product manifest.
- `clausegate-development-complement-v1/scores.json`: its original-proposal score; `complete-development.json`: guarded 61-document aggregation, all 1,037 predictions, source hashes and pooled counts.
- `clausegate-fixed-validation-v2/scores-complete-development-scorer.json`: retained 30-document component rescored by the same scorer, without rerunning or correcting model predictions.
- `clausegate-development-complement-v1/acceptance/`: final gate report, JUnit and regression/frontend/build/Ruff logs.
- Fresh `clausegate-*-cadence-v1` HTTP, PDF, network, worker recovery and backup artifacts. Earlier rejected/interrupted campaigns remain intact.

## Reproduce without overwriting evidence

From the repository root; choose new output paths. The complement command requires the retained parent campaign to match the current product/corpus hashes. After a product change, start a new declared campaign rather than silently mixing builds.

```sh
.venv/bin/python scripts/validate_clausegate.py --corpus var/validation/clausegate-corpus-v2 --output var/validation/clausegate-complement-NEW --workflow-cases 300 --live-jobs 31 --sample length-spread --pdf-limit 1000 --exclude-evidence var/validation/clausegate-fixed-validation-v2/report.json
.venv/bin/python scripts/score_clausegate.py --corpus var/validation/clausegate-corpus-v2 --evidence var/validation/clausegate-complement-NEW --output var/validation/clausegate-complement-NEW/scores.json
.venv/bin/python scripts/aggregate_clausegate_development.py --score var/validation/clausegate-fixed-validation-v2/scores-complete-development-scorer.json --score var/validation/clausegate-complement-NEW/scores.json --output var/validation/clausegate-complement-NEW/complete-development.json
```

Do not open/tune against official test labels through inference and then call the corrected rerun blind. A larger development evaluation is useful evidence, but it is not independent acceptance.
