# Dependency-ordered TDD implementation plan

Status: supervised pilot implemented after documentation completeness check; broader design/external gates remain incomplete. [Evidence](implementation-validation-2026-10-17.md) records observed red/green steps; [runbook](implementation-and-operations.md) maps actual delivery/deviations. Every phase follows **red → green → refactor → regression**. A test added after implementation is regression coverage, not evidence of TDD.

## Phase 0 — feasibility and frozen inputs

First failing tests: absent effective model identity/usage; missing hard token control; unsafe archive/path; wrong hash; split/gold fields reaching runtime; noisy/duplicate labels. Inspect actual CLI capability/event schemas without printing secrets. Build additive typed model/usage boundary with old-provider compatibility tests. Acquire authorized data with manifests only when rights/allowance are resolved. If hard tokens are unsupported, expose strict-mode refusal and advisory mode honestly; do not halt safe implementation of other features or claim strict acceptance.

Gate: reproducible source acquisition and explicit capability matrix. Existing products continue to pass unchanged.

## Phase 1 — contracts, auth and immutable store

Failing tests: schema bounds, forged actor, cross-workspace list/detail/export, CSRF, immutable revision, duplicate IDs/idempotency, event rollback and optimistic conflicts. Implement independent API/store, scoped sessions/grants and bounded CSV/JSON intake. Proposed paths follow [architecture](architecture.md). No product-to-product controllers or stores.

## Phase 2 — retrieval and deterministic identity checks

Failing tests: unit normalization, missing/contradictory variants, price similarity false link, label leakage, missing positive candidate, candidate-list bounds, two incompatible accepted candidates and stale index. Implement versioned lexical candidates and literal evidence checks. Preserve missing fields. Gate: real query/gallery evaluation separate from pair classification.

## Phase 3 — budget ledger and durable worker

Failing tests: nested concurrent reservations, repair/escalation counting, duplicate/out-of-order settlement, unknown usage after crash, usage above reservation, cancel/lease races, resume budget reset, float rounding and restoring an older snapshot. Implement atomic reservation/dispatch-intent/accounting events, bounded jobs/checkpoints and independent current liability journal. Gate: no new dispatch with unreconciled liability or stale restore state; no model call inside DB lock.

## Phase 4 — actual model routing and confidence

Failing tests: two configured aliases resolve to same model; unavailable profile; unexpected tool event; invalid quote/candidate; self-confidence bypass; sparse calibration; low confidence escalation; budget exhaustion; later timeout erasing earlier results. Implement deterministic/economy/strong/manual policy with actual selected identities and validated typed output. Freeze development-only calibration, prompt and policy versions. Gate: live installed-provider traces establish real model choices and early exit; fixtures alone cannot pass.

## Phase 5 — review, export and analytics

Failing tests: stale review, unauthorized correction/top-up, unreviewed default export, CSV formulas, changed source/policy invalidation, unknown-cost hidden as zero, division by zero and ledger/report discrepancy. Implement explicit review and version-bound exports, fixed-point costs and full-denominator analytics. Gate: one coherent snapshot supports totals, task details and exported coverage.

## Phase 6 — premium UI and actual workflow

Frontend red tests cover every critical state in [UI](reviewer-ui.md); implement workbench, import, budget preflight, review and analytics. Run authenticated API journeys on real records, then actual browser journeys at all viewports and separate identities. Gate: captured keyboard/responsive/partial/stale/error evidence, not just build output. If browser is unavailable, preserve blocked gate.

## Phase 7 — rigorous actual-data validation

Freeze all code/data/model/calibration/scorer hashes. Run mechanical full corpus, live pair cohort, same-cohort model baselines, query/gallery end-to-end and independent challenge truth per [evaluation](data-and-evaluation.md). Capture every failure and liability; keep original failed reports on corrective runs. Gate: all semantic/economic thresholds met or explicitly failed/blocked. No threshold tuning on held-out results disguised as a pass.

## Phase 8 — operations, integration and handoff

Add product-only launcher/Make/settings/Windows task support; verify existing six products. Test actual process kill/restart, backup/restore, disk pressure, bounded descendants, scoped shutdown, and old Windows limited-account/reboot/Cloudflare protection before deployment acceptance. No external account changes without deployment authority.

After implementation and validation, write `study-guide.md` mapping all four concepts to actual code/tests/results and one `blog.md` grounded in observations, including unresolved gates. Neither learning document should claim measured results before they exist. Update status/catalog with actual commands, limits and evidence, preserving original targets.

## Completion criteria

Implemented means all scoped behavior has tests, runnable app/UI and documented limitations. Validated means the named executed gate passed with evidence. Production accepted additionally requires independent semantic truth, actual target-host/edge/browser and buyer acceptance. Report these separately; do not stop implementation merely because an external acceptance gate needs a person/host, and do not invent a pass for it.
