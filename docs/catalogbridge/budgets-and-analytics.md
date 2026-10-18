# Token budgets and cost-per-decision analytics

Implemented amendment: [durable timeout receipts and repeat-work control](receipts-and-repeat-work-2026-10-18.md). Opt-in exact-context draft hits make no reservation/attempt and record zero additional measured inference, while original usage remains charged to its original attempt. Cached drafts require review and stay out of reviewed exports. Hosting/review cost and actual account charges are not inferred as zero. Report warm-cache and fresh-row comparisons separately with equivalent baseline cache conditions; caching does not pass the unmet original fresh-row savings gate. Unknown timeout usage still holds liability; complete unambiguous runtime receipts can preserve known usage despite failure.

Status: proposed accounting contract. A desired limit is not proof the installed CLI can enforce it. Existing shared output-byte/time limits alone do not establish a hard token ceiling.

## Separate three meanings of cost

1. **Measured usage:** reported input/cached/output/reasoning token fields where available, call count, elapsed time and host resources. Record provenance and unknown fields as null, not zero.
2. **Estimated cost:** measured or estimated usage multiplied by a frozen applicable rate card, with currency, unit, source date and pricing basis. A reference API scenario is labeled hypothetical, never the subscription bill.
3. **Actual attributable charges:** reconciled billed credits/money only where an authoritative source exposes them; shared subscription fees may be allocated under a stated rule, not misrepresented as marginal per-request charges.

[Official OpenAI pricing documentation](https://learn.chatgpt.com/docs/pricing) distinguishes subscription allowances, credits and API rates. Do not infer remaining subscription allowance from prompt tokens or extrapolate reference costs into “tasks left.” Account quota state and product budgets are different controls. A purchased-credit rate card is not automatically applicable to included usage.

## Budget scope and provisional defaults

Each row and batch has immutable original allowances plus separately authorized increases. Every dispatch must fit both current scopes. Retries, repairs, escalation and routing-model calls consume the same scopes. Human review/candidate CPU costs are separate non-token metrics.

The implemented workspace runtime circuit now fences dispatch across batches after provider failure or unknown usage. Circuit status is separate from the selected batch's remaining allowance; increasing that allowance does not authorize spending through the hold. Owner retry acknowledgement refuses unknown/in-flight liabilities, journal divergence and quarantine, changes no usage, and never proves provider health. Evaluation modes share an additional campaign-wide stop guard; compare complete known-usage cohorts only. [Measured hardening results](runtime-hardening-2026-10-18.md) distinguish absolute prompt reductions from the still-unmet >=20% routing-token target.

Provisional ceilings for feasibility testing: 24,000 serialized input-token estimate and 6,000 total output/reasoning allowance per row; three total attempts; 240 seconds active row time; each call at most 90 seconds and the remaining deadline. Count all attempts cumulatively. These are initial targets to verify, not a guarantee that a three-call row fits. Per-call prompt cap is the smaller of 8,000 estimated serialized tokens and remaining allowance; the prompt includes instructions, schema, candidates and metadata. Reject oversize rather than silently remove identity evidence.

Batch creation requires an explicit token/call/time envelope calculated for its row count and approved ceilings, not unlimited multiplication of defaults. Provide a preflight estimate/range and affordable-row forecast. A monetary estimate ceiling applies only for a valid applicable rate basis; unknown rates block cost-constrained dispatch or require explicit non-monetary mode. Switching mode is an audited owner action.

## Admission is not provider-side hard enforcement

Use an exact compatible tokenizer when verified; otherwise mark conservative estimates and calibration error. Reserve prompt allowance plus an enforceable upper bound on all completion/reasoning usage and known overhead before dispatch. Verify whether cached/reasoning tokens are subsets or additional quantities for that adapter version; never double count.

If the runtime does not expose a reliable hard completion-token bound, a reservation is an **admission estimate**, not a hard bound on incurred tokens. Strict hard-token mode must refuse dispatch. An explicitly selected advisory-token mode can use call/time/output-byte bounds, reconcile actual usage, and stop further calls after overrun; its UI and report must state that a single call can exceed the estimate. Killing a process cannot undo provider usage already incurred. Hard-budget acceptance remains blocked unless real enforcement is demonstrated. This distinction applies even if all sampled calls happened to fit.

## Transactional reservation lifecycle

`prepared → reserved → dispatching → settled` or `usage_unknown`. `released` is allowed only with proof no dispatch occurred or an authoritative zero-charge outcome. Reserve row and batch accounts in the same short transaction with attempt identity and event; competing workers cannot independently spend the same remainder. Use fixed-point integers/decimals, no float money arithmetic.

Implemented v2 preflight prepares the complete installed-adapter prompt/schema and refuses its >24,000-byte envelope before reservation. This is a byte-envelope guard, not a hard token cap. Preflight refusal has zero dispatched attempts; provider exceptions after reservation retain unknown liability. A later escalation failing its budget/provider checks preserves an existing review draft and all previous usage. The 12,000-token per-call reserve remains advisory; observed overruns must be recorded in full, never clipped or described as an enforced ceiling.

Persist dispatch intent before launching. Marking intent and executing an external process cannot be atomic: a crash in that gap is conservatively unknown until reconciled. Unknown in-flight usage holds its liability and blocks unsafe automatic retry. A provider error is not proof of zero usage. Store reported usage from malformed, nonzero-exit, timed-out or cancelled attempts whenever available; preserve maximum liability when it is not.

Settle exactly once by attempt ID, independent of duplicate event delivery. Duplicate differing telemetry is a reconciliation conflict, not a second charge or overwrite. Actual usage above reservation is recorded in full with an overrun event; no clipping to make the budget look compliant. Fence new dispatch until reconciled/top-up. Lease loss prevents publication but not recording an incurred usage event. No DB lock during inference.

Available allowance = authorized allowance − settled consumption − outstanding reservation/liability. On settlement, replace the reservation with actual consumption; do not subtract both. Sum task accounts to batch ledger, and batch attempts to the analytics denominator. A rate-card update creates a new version; original estimates remain reproducible.

## Cost formula and reporting

For an adapter where cached input is a subset of total input and reasoning is already included in billed output:

`estimated_cost = ((input - cached) × input_rate + cached × cache_rate + output × output_rate) / rate_unit`.

This is conditional, not a universal billing formula. Unknown usage/rate yields unknown cost or a labeled interval. Keep original currency/credits; conversion requires a dated explicit conversion basis. Record discounts/minimums only when applicable and verified.

Required analytics:

- Whole-batch totals: all input rows, matched/review/unresolved/failed/cancelled counts, measured/estimated/unknown tokens, latency and outstanding liabilities.
- Per route/model/task/pair/attempt: dispatch reason, usage source, price version, early-exit stage, retries and validation failures.
- Cost per input row, model-decided row, reviewed accepted mapping, and independently correct decision, each with explicit denominator. Correctness is available only in evaluation/adjudicated samples; customer acceptance is not gold truth.
- Quality-adjusted comparisons: match precision/recall, automation coverage, reviewer minutes and cost on the **same frozen rows**, including failures.

Zero denominator produces `not_available`, not zero/infinite “savings.” Cache savings and early-exit savings require a measured comparable baseline; avoided hypothetical calls are labeled estimates, not observed billed savings. Operator time is measured separately and included in an explicitly labeled total workflow-cost scenario.

## Crash, restore and audit

Append usage/reservation events with batch, task, attempt, worker lease, request digest, profile, revision and restore epoch. Restore cannot erase real provider spending: hold a current usage high-watermark/dispatch-liability journal outside the restorable product snapshot. Restoring an older DB requires reconciliation against that journal/provider evidence before any dispatch. The journal is an accounting safeguard, not an immutable defense against a privileged host administrator.

Cancellation keeps costs; resume keeps counters; imported historical reports cannot fund new tasks. Logs must not contain feed bodies or credentials. Required tests cover rounding, cached/reasoning semantics, duplicate/out-of-order events, concurrency, crash windows, rate drift, missing telemetry, restore rollback and aggregate reconciliation.
