# Product acceptance gates

Latest named checks: [timeout receipts and exact-context repeat-work validation](receipts-and-repeat-work-2026-10-18.md). 455 Python tests, eight frontend tests/build, repeated 400-query API/stress workflow and three live calls pass their scoped checks. Two eligible cached repeats consume no new inference, while one uncertain repeat remains unresolved. This does not satisfy the original fresh-row routing savings, independent confidence, historical settlement or deployment gates. Equivalent cache conditions are required for both sides of future quality/cost comparisons.

Status: engineering and named workflow/safety checks have executed; **full release remains blocked**. See [current hardening evidence](runtime-hardening-2026-10-18.md). A clean rerun or compact-prompt token reduction does not settle historical unknown liabilities, qualify calibration, meet the original quality-constrained routing-token target or establish Windows/browser/customer acceptance. Required evidence must be executed, not inferred from code, docs or a passing build. A pilot may ship for supervised evaluation while remaining not production accepted.

| Gate | Required evidence | Failure/blocking rule |
| --- | --- | --- |
| Documentation | Complete linked pack; no planned commands presented as available | Broken/contradictory scope blocks implementation handoff |
| TDD engineering | Failing tests captured before each behavior; unit/integration regression, lint, web tests/build | Untested or failing behavior is not done |
| Isolation | Real auth/object-scope/CSRF tests including evidence/analytics/export | Any cross-workspace disclosure fails |
| Genuine routing | At least two verified effective models; recorded choices on actual task inputs | One model with renamed profiles is blocked |
| Budget enforcement | Atomic nested reservations, cumulative retries, real enforced token cap, crash/unknown-usage tests | Advisory estimates cannot pass hard-token gate |
| Confidence exits | Held-out applicable calibration; actual economy exits without stronger dispatch; risk–coverage evidence | Self-reported model certainty is insufficient |
| Cost analytics | Exact attempt→task→batch reconciliation; unknown liabilities/price bases visible; paired baselines | Unattributed failures or invented subscription costs fail |
| Real-data semantics | Frozen volumes and thresholds from [evaluation](data-and-evaluation.md), independent adjudication | No adjudicators or shortfall leaves gate blocked |
| Full workflow | Real feed import→retrieval→route→review→export over authenticated API and browser | Mocks/HTTP alone do not prove browser acceptance |
| Recovery | Actual kill/restart and older-backup reconciliation without refunded spending/stale exports | Missing current liability/deletion state blocks dispatch |
| Target deployment | Windows limited identity, reboot/logoff/descendant cleanup, seven-product resources and protected external denial | macOS-only execution is not a Windows pass |
| Buyer value | Consenting user time/error study and paid-pilot feedback | Dataset quality alone does not establish sellability |

## Required adversarial workflows

Exercise conflicting capacity/form-factor/pack quantity/condition; missing identity fields; duplicate IDs; malformed encoding; HTML/formula/prompt injection; candidate omission and two accepted incompatible candidates; cross-tenant IDs; stale review form; source/index/policy/model changes; revoked egress; budget races and duplicate settlements; timeout after earlier successful rows; absent model identity/token telemetry; cancellation during dispatch; disk-full event rollback; process death between reservation and launch; restore from before real usage; invalid/missing current ledger.

Actual browser journeys cover separate operator/reviewer accounts, long text, empty/partial/error states, budget mode warnings, keyboard operation and export safety. Capture viewport, browser version, screenshots and assertions. No connected browser means this gate is blocked, not replaced by screenshots generated from HTML.

## Evidence report format

Each report records UTC run times, commit/worktree hashes, environment, runtime/model/profile/prompt/data/scorer versions, exact commands, volume by unique record/pair/presentation, pass/fail/blocked/not-run counts, all attempted calls/usage liabilities, semantic metrics, UI/host evidence paths and remaining limitations. Sanitized manifests must reproduce denominators and link failed cases. Tests with skips cannot be reported as “all validation complete” without naming omitted gates.

Release verdict: `accepted` only when every mandatory gate passes; otherwise `pilot_only`, `failed` or `blocked` with precise reasons. No blanket production-ready or savings claim from documentation, mocks, noisy-label agreement or a small live sample.
