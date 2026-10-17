# ClauseGate: read-boundary fixes and model rerun — 17 October 2026

Historical repair/30-document comparison. The later [complete 61-document development evaluation](development-validation-2026-10-17.md) and refreshed study/blog are the current learning handoff. The paired measurements here remain unchanged; the larger cohort is not a new paired before/after experiment.

**Read-snapshot defect corrected; completion and grounding improve, but semantic reliability remains unresolved. Full release is not accepted.** The [rejected baseline](rigorous-validation-2026-10-17.md), raw proposals and failing stress artifacts are preserved. This is a new build/campaign, not a rewritten pass for the earlier build.

## Corrections implemented with failing regressions first

1. `Store.coherent_read()` explicitly acquires `BEGIN IMMEDIATE` for short case, audit, verification, source, worker-check and export reads. `anchor()` takes the same domain fence before publishing an external head. Domain state cannot advance between audit and case SELECTs, and ordinary anchor publication cannot overtake that read.
2. `backup()` validates sources/audits and copies the database under that fence. SQLite backup uses a **separate source connection**, not the connection holding the write reservation; otherwise SQLite can wait on its own transaction. The backup path had its own reproduced interleaving failure before correction.
3. Original-byte download authorizes, verifies the source and reads bytes in one fence through `Store.original()`, rather than authorizing in one connection and fetching bytes in another.
4. An independently recorded erasure denies content reads before local cleanup completes. Erasure reconciliation now starts an explicit transaction before reading the case it will update. An erased non-content receipt remains readable by authorized users after reconciliation.
5. Interpretation requests retain the complete document when the **actual serialized prompt and schema** fit the 48,000-character ceiling. Only oversized requests split into source-bound groups. This avoids unnecessary separation of a provision from qualifications elsewhere. No source truncation, larger context allowance or infinite retry was introduced.
6. Optional `Finding.evidence_quotes` contains one unique verbatim substring per cited `span_id`. The server finds the exact substring within the original span and derives original Unicode character offsets. Invented, ambiguous, duplicate or uncited quotations are rejected. Legacy/manual ID-only citations still resolve to complete original spans; exact string matching does not establish semantic sufficiency.
7. Prompt instructions distinguish express/necessary support, incompatible text and silence; quantify “some/all/only” and permission versus obligation; request material qualifiers and exact source excerpts. No per-document label exceptions or gold annotations enter model context.
8. Provider failures retain exit code, tool-audit flag, stderr presence/digest and safe fixed reason codes where known. Raw stderr is not logged, and unknown failures remain unknown. Repair receives structural error locations or safe boundary messages; repair context is checked against the same serialized ceiling.
9. `ANALYSIS_VERSION = clausegate-2-full-context-exact-quotes` participates in the analysis input hash and audit metadata. Old partial chunk cursors cannot be reused under a different pipeline version. Two-grant/four-call-per-grant, active deadline, permission, source and final-review fences remain in place.

The interleaving regression coordinates a legitimate writer between audit-event and case-state reads, rather than relying on random timing. It covers case, audit, verification and backup surfaces. It fails on the original case/backup paths and passes after their fixes. Existing corruption/rollback checks remain mandatory: the correction does not suppress integrity errors or turn them into success responses.

## Serialization tradeoff

`BEGIN IMMEDIATE` reserves the domain writer even for these reads. This is intentionally conservative and **serializes these short operations**, reducing read/write throughput. It is not a general claim that SQLite WAL reads require a write lock. A plain deferred read transaction would fix the local snapshot but still needs a design for a separately advancing anchor/authority store.

No inference, PDF parsing, remote calls or waiting for human input runs inside the fence. Backup does hold it during disk copying and should be scheduled with that write-blocking cost in mind. SQLite's existing ten-second busy timeout remains. The measured small loopback stress run does not certify sustained load, starvation freedom, power-loss behavior or performance on the older Windows host.

## Verified engineering retests

| Exercise | Rejected baseline | Fixed build |
| --- | --- | --- |
| Authenticated in-process API, 100 writes / 600 reads | 109 false HTTP 409 integrity conflicts | 600 successful reads, zero false conflicts; valid final audit |
| Domain-service stress, same shape | 90 false integrity failures / 600 reads in each of two reproductions | 600 successful reads, zero false failures; valid final audit |
| Actual managed service over loopback HTTP | No paired old-build network measurement claimed | 100 successful updates / 600 HTTP 200 reads; valid audit; approximately 0.994 seconds on this Mac |
| Backup/restore on real sources | Backup interleaving regression failed | 11 checks passed: concurrent writer, verified snapshot, later erasure, quarantine, non-resurrection and fresh authority |
| Sequential HTTP fixture journey | 21 passed | 21 passed |
| Natural-model HTTP → pause → fixture reviewer → worker resume → final-review fixture → export | 23 passed | 23 passed |
| Original PDF upload/download journeys | 12 sources / 72 checks passed | 12 sources / 72 checks passed |
| Actual isolated worker kill/restart | Seven checks passed | Seven checks passed |

These are controlled test workloads over real public documents. Reviewer responses and organization policies remain **automated fixtures**, not actual people or legal sign-off. The natural HTTP job reuses document 456 and one hypothesis; it is not another independent document or part of the all-17-check semantic cohort.

The two-document backup drill actually removes its own fixture's live source after taking a snapshot, then verifies restore applies the later independent erasure. This is logical deletion, not secure wiping: the preserved snapshot still holds earlier bytes, and the public corpus retains the original document. Nothing from a user/customer case was deleted.

## Natural-model development evaluation

Final campaign: `var/validation/clausegate-fixed-validation-v2/`. It reruns the **same preselected 30 distinct development NDAs** and 17 hypotheses as the rejected baseline, retaining all attempts. All 607 corpus records, 300 distinct-text workflow fixtures and all 374 safely named original PDFs are rechecked. Gold annotations remain evaluator-only; the official test split stays sealed from inference.

Final frozen campaign started UTC `2026-10-17T12:44:32.077579+00:00` and finished `2026-10-17T13:02:58.477134+00:00`. Product API/UI/contract hashes match at completion and final assessment. All 30 analyses complete and wait for human input; no real legal approval occurred. All 607 records, 300 distinct-text workflow fixtures and 374 PDF attempts were rechecked: **3,314 mechanical assertions pass**, 212 PDFs have no detected gaps and 162 remain conservatively partial. No OCR/complete visual-coverage claim.

| Same-cohort development metric | Rejected baseline | Fixed candidate |
| --- | ---: | ---: |
| Completed analysis stages | 26 / 30 | 30 / 30 |
| Reserved model calls | 36 | 30 |
| Label matches, all 510 attempted pairs | 341 / 510 | 381 / 510 (74.71%) |
| Missing/unusable predictions | 68 | 0 |
| Three-class macro-F1 | 0.6656 | 0.6849 |
| Evidence-token precision | 0.3226 | 0.5669 |
| Evidence-token recall | 0.6072 | 0.4847 |
| Evidence-token F1 | 0.4213 | 0.5226 |
| Model-marked supported subset | 58 wrong / 290 (20%) | **78 wrong / 289 (26.99%)** |

The new proposals supply **436 validated exact quotes across 290 findings**; all 436 returned evidence ranges resolve to those quotations. Provenance improved; semantic sufficiency is not established. Narrower excerpts improve measured precision but reduce recall, potentially missing relevant qualifiers. Evidence F1 remains far below the provisional 0.80 target.

`comparison.json` separates availability from semantic changes: 68 previously missing pairs now have predictions, 50 of which match. On the **442 previously usable pairs**, correct answers fall from **341 to 331** (13 corrected, 23 regressed). Thus the net +40 matches is **50 recovered matches minus ten lost matches** on previously usable material. It is misleading to call this an unqualified classification improvement. The model's supported flag becomes less reliable in this rerun, despite similar selective coverage. No confidence threshold is lowered or result reclassified to manufacture a pass.

The fixed candidate beats the training-only majority baseline's 342/510 matches and macro-F1 0.6195, but does not demonstrate the provisional 0.85 held-out target. Classification and calibration quality remain open. Human review is mandatory; this build is not cleared for autonomous interpretation/approval. A qualified challenge/adjudication cohort and independent held-out evidence are needed before broader confidence claims, not further tuning to the same 30 answers.

The original proposals are rescored with the exact same pinned scorer at `clausegate-rigorous-v1/scores-rechecked-v2-scorer.json`. Its original 341/510 label matches, macro-F1 0.6656 and token-overlap F1 0.4213 are unchanged. Character/token overlap is a source-provenance diagnostic, not proof of complete legal support or the official ContractNLI scorer.

This is development iteration, **not independent or blind validation**. Same-document repeats, stochastic inference, simultaneous prompt/planning/quote changes and unavailable remote model-version pinning prevent a causal ablation or generalization claim. Dataset lexical/template overlap remains disclosed in the earlier screening artifact. Passing exact quotations cannot resolve disputed interpretations; qualified adjudication remains necessary.

## Intermediate campaigns retained

Final `clausegate-fixed-validation-v2/acceptance/report.json`: **six passed, four blocked, zero failed engineering gates**; verdict `blocked`, `full_acceptance_completed=false`. Fresh unmasked regression: **343 Python tests passed, zero skipped/failed, 40.663 seconds**, including **60 ClauseGate tests**. Four frontend tests, TypeScript/Vite build and Ruff pass. Semantic/qualified review, actual two-person browser, Windows/protected edge/resources and customer usefulness remain blocked. The acceptance command intentionally exits nonzero; it does not declare model quality passed from stage completion.

- `clausegate-fix-candidate-v1`: three length-spread development documents (456, 440, 64), 43/51 matches. Not the baseline's same three shortest documents; do not compare their aggregate scores as a paired improvement.
- `clausegate-fixed-validation-v1`: deliberately interrupted after eight completed natural attempts while the ninth ran, after a backup read-boundary defect was reproduced. Adapter interruption cleaned up its model child. `INTERRUPTED.md` and the original checkpoint remain; this is not a finished campaign or eight additional independent contracts.
- `clausegate-fixed-validation-v2`: final campaign frozen after the backup correction. Product hashes must match at its end and final assessment.

## Artifacts and reproduction

Under `var/validation/`: `clausegate-read-race-fixed-final-v1`, `clausegate-read-race-fixed-domain-v1`, `clausegate-network-race-fixed-v1.json`, `clausegate-backup-recovery-fixed-v1`, `clausegate-http-fixed-v1.json`, `clausegate-natural-http-fixed-v1.json`, `clausegate-pdf-http-fixed-v1.json`, `clausegate-recovery-fixed-v1`, and the final campaign. Earlier failed runs remain intact.

```sh
# Choose NEW destinations; do not overwrite the retained evidence.
.venv/bin/python scripts/validate_clausegate_read_race.py --http-readers --output var/validation/clausegate-read-fix-NEW
.venv/bin/python scripts/validate_clausegate_network_race.py --output var/validation/clausegate-network-fix-NEW.json
.venv/bin/python scripts/validate_clausegate_backup_recovery.py --output var/validation/clausegate-backup-fix-NEW
.venv/bin/python scripts/validate_clausegate.py --corpus var/validation/clausegate-corpus-v2 --output var/validation/clausegate-fixed-NEW --workflow-cases 300 --live-jobs 30 --sample length-spread --pdf-limit 1000
.venv/bin/python scripts/score_clausegate.py --corpus var/validation/clausegate-corpus-v2 --evidence var/validation/clausegate-fixed-NEW --output var/validation/clausegate-fixed-NEW/scores.json
.venv/bin/python scripts/accept_clausegate.py --evidence var/validation/clausegate-fixed-NEW/report.json --output var/validation/clausegate-fixed-NEW/acceptance --run-tests --read-race-evidence var/validation/clausegate-read-fix-NEW/report.json
```

Browser/accessibility/two-person interaction, qualified held-out quality, actual Windows/protected-edge/all-products resource checks and customer usefulness remain separate gates. No credentials, external approvals, direct model API, Windows task or tunnel setting was changed. Only ClauseGate's managed service was restarted; earlier products were not stopped.
