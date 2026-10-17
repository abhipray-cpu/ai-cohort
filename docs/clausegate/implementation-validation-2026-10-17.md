# ClauseGate implementation validation — 17 October 2026

Historical implementation-v4 baseline. The later [rigorous campaign](rigorous-validation-2026-10-17.md) expands to 300 workflow cases, all 374 safe PDFs and 30 natural model attempts, and **rejects release after reproducing a concurrent-read defect**. The measurements below are retained, not the current acceptance verdict.

Verdict: **implemented pilot; engineering baseline passed; release acceptance blocked**. This is not a legal-quality certificate, complete held-out evaluation or production launch.

## Test-first evidence

Tests were added before intake/domain/worker/API/UI behavior, with initial missing-package failures followed by behavioral red tests during hardening. Actual failed assertions caught domain-state tampering not detected by the audit, blank rationale acceptance, confirmation changing an interpretation, expired manual-review authority, auditor content exposure, expired actors blocking queue cleanup, clarification reusing old interpretation, in-flight authority expiry leaving cleanup incomplete, and mixed image/text PDFs labelled complete. Corrections now pass as mandatory regressions, not expected failures.

Final acceptance-v4 unmasked run: **326 monorepo Python tests passed**, zero failed/skipped, 39.66 seconds; **43 ClauseGate tests**, **four frontend state tests**, TypeScript/Vite production build and repository Ruff checks pass. Earlier 315/321/325-test runs are intermediate, not the final count.

## Frozen real inputs

Official ContractNLI archive acquired read-only into `var/validation/clausegate-corpus-v2/`; publisher attribution/use notices retained in manifest/archive. Archive bytes: 65,362,913; SHA-256 `e03fc77bbf8b53e2976a250e81d8a294bc3d5e5fb014521e477dee9340d6287b`.

Observed: **607 record IDs, 606 distinct text hashes, 10,319 labelled document/hypothesis pairs, 27,439 product source spans**. Published split verified: train 423/7,191 pairs, development 61/1,037, test 123/2,091. Exact cross-split text overlap is zero; near-duplicate/template screening is not performed. One repeated text remains disclosed, not counted as independent data.

Archive contains one unsafe Windows-style member name, quarantined rather than extracted. Original v1 acquisition stopped on it; the raw archive was preserved and reused safely for v2 normalization. This was not a malicious file we executed. Dataset annotations remain in evaluator-only storage, absent from product/model imports and isolated provider context.

## Final campaign v4

`var/validation/clausegate-implementation-v4/report.json`: UTC start `2026-10-17T11:48:52.509357+00:00`, finish `2026-10-17T11:49:53.428290+00:00`. Product API/UI/contract hashes were frozen before the campaign and verified unchanged at completion and acceptance. These are macOS results, not Windows measurements.

- **1,634 mechanical assertions**, zero failures: full-primary source/span/schema checks plus workflow invariants. This is not 1,634 independent semantic questions.
- **60 workflow cases over 60 distinct real document texts**: 20 clarification, 20 exception and 20 hard-block cases. Playbooks and responses were explicitly synthetic fixtures; published labels seed the mechanical findings. They are not real organizational approvals or human legal review.
- **30 original PDF intake attempts**. After conservative mixed-image checks, 15 had no detected text/image gaps and 15 were flagged partial because image content could not be assessed. Logos can trigger this deliberately conservative flag. Earlier v1–v3 “30 complete” counts are superseded by this corrected PDF interpretation. No OCR or visual text-coverage accuracy claim.
- One acquired original PDF first page was rendered and inspected as an intake sanity check; it does not validate all PDF layouts, pages or the browser UI.

Workflow tests exercise durable waiting across Store reopen, typed clarification, independent scoped exception response, idempotency, non-waivable block, validated worker continuation, exact final review, export invalidation and outsider denial. Original source/evidence and diagnostic classes remain inspectable.

## Natural live-model diagnostic, not a release pass

Final v4 ran the installed isolated Codex adapter on the three shortest development records (IDs 456, 71, 488), with all 17 hypotheses each. Each used one model call, each completed the analysis stage, and each ended `waiting_human`. No human legal approval occurred.

| Record | Proposed labels matching published annotations |
| --- | ---: |
| 456 | 14 / 17 |
| 71 | 12 / 17 |
| 488 | 14 / 17 |
| Total | **40 / 51** |

Diagnostic macro-F1: **0.6860**; character-overlap evidence micro-F1: **0.4252**. Character overlap is not the planned token/span benchmark. The three-document class distribution is highly imbalanced (only one Contradiction example) and not representative. Nineteen findings were model-marked supported; **four of those nineteen had incorrect labels**. That flag is not calibrated confidence or permission to skip review.

Most label misses were Entailment predicted as NotMentioned, illustrating why exact source IDs and complete chunk processing do not establish semantic correctness. Required review/exception rules and independent final review remain essential. Quality release targets are not demonstrated; no held-out or qualified-review score is claimed.

Intermediate campaigns v1–v3 and their original responses/results are retained. They reran the same three documents during implementation and are **not nine additional distinct natural contracts or independent trials**. Final scoring uses untouched original model proposals, not human-corrected answers.

## Live service and real process recovery

`clausegate-http-v2.json`: **21 HTTP checks passed** against the managed final build on port 8005. Real NDA text, separate authenticated identities, explicit fixture policy/decisions, CSRF/origin protection, self-approval denial, deduplication, actual background-worker resume, unreviewed-export denial, exact final review, retained limitations and stale-source/form/export rejection. HTTP clients are not visual/browser acceptance.

`clausegate-recovery-v1/report.json`: **seven real process checks passed**. An isolated worker was actually killed while a human request was pending; the checkpoint survived, waiting consumed no model work, a decision committed with worker stopped, and restart completed one effective continuation with zero inference calls. Test processes were cleaned up; managed ClauseGate/earlier product processes were not killed by this drill.

Wrong independent authority, later erasures, quarantined restore, audit tamper/rollback and stale lease behavior are covered by tests. No actual Windows reboot/power-loss or five/six-product resource acceptance was performed.

Browser skill selection failed; read-only discovery returned `[]`. Actual visual/two-browser/keyboard/responsive/accessibility checks remain blocked. No substitute screenshots or browser pass were invented.

## Acceptance assessment

`clausegate-implementation-v4/acceptance/report.json`: **blocked**, `full_acceptance_completed=false`. Four engineering gates pass; five remain blocked: ≥30 distinct live-document workflows, full held-out/qualified quality review, actual two-person browser, Windows/protected edge/resources, and customer usefulness. The command intentionally exits nonzero. Pipeline completion does not imply that the quality sample is good enough.

## Artifacts retained locally

Under `var/validation/`: corpus-v1 raw stopped capture, corpus-v2 manifest/archive/evaluator-only data; implementation-v1/v2/v3/v4 reports/stores; final `scores.json`; final acceptance JUnit and Python/frontend/Ruff logs; HTTP-v1/v2; recovery-v1 worker log/report; one PDF intake preview. No sensitive source corpus is committed or redistributed. `docs/clausegate/` describes the current implementation and unresolved gates, not a replacement for those measured artifacts.
