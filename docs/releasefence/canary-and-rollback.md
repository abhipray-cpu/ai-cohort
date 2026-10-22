# Canary analysis, scoped control and verified rollback

This file is the normative decision boundary. Proposed defaults require calibration
and owner approval; they are not measured business-risk tolerances.

## Immutable whole-agent release

Manifest binds code/package digest, prompt digest, model configuration, tool schema,
policy revision and compatible index snapshot where used. Baseline must be healthy,
addressable and deployable before starting a canary. The runtime must report the
resolved manifest, not merely the requested label. Mutable model aliases and
external knowledge changes are explicit reproducibility limitations.

One active rollout per application/environment. Start pins baseline, candidate,
policy, enrolled runtime set, authority expiry, outcome contract and configuration
revision. Compare-and-set transitions/fencing prevent competing controllers.

## Routing and session correctness

Proposed stages: 5%, 25%, 100% candidate assignment, with a fixed baseline/control
holdout retained until the final promotion decision. The final 100% state follows
evidence evaluation, not a comparison with an empty control. Stage durations and
sampling plan are frozen before traffic. Session assignment hashes a stable
tenant/app/environment/session key plus rollout seed; retries and turns stay on
their original bundle. Do not route each turn independently.

Pin in-flight sessions until their approved stop/drain boundary. Repeated turns
do not inflate independent sample counts. Shadow execution is permitted only for
explicit read-only/sandboxed tools; never duplicate customer writes to obtain a
paired comparison. Replay timing is not a real user-latency claim.

## Proposed analysis policy

Separate immediate hard-failure rules from sampled quality/performance gates.
An enforced critical loop/deadline event can abort under an approved hard rule
without waiting for statistical sample floors. It does not demonstrate a measured
population regression rate.

For ordinary promotion, initial defaults require at least 100 independent completed
sessions per arm, a closed event-time window, at least 99% lifecycle coverage and
no unexplained model/cost/assignment gaps. These are minimums, not adequate power
for every metric. Insufficient evidence yields `inconclusive` and holds expansion.

Initial non-inferiority policy candidates: candidate failure rate at most +2
percentage points, task p95 latency at most +20%, and cost/success at most +20%
relative to baseline. Owners must explicitly accept these margins or choose safer
ones. Unknown/zero-denominator cost blocks that gate. Semantic judge scores alone
do not trigger autonomous control in the first product.

Implement a versioned fixed-look analyzer: predeclare stages/looks and gating
metrics; family error budget 0.05 distributed conservatively across comparisons
(including component intervals where used). Use conservative binomial interval
differences for outcome rates and reproducible session/cluster-level resampling
for latency/cost ratios where assumptions are satisfied. Report interval, count,
method/seed and composition. Unstable p95/tail estimates, poor coverage or unequal
cohort applicability remain inconclusive. Do not repeatedly peek at nominal 95%
intervals until they pass. Freeze/calibrate the exact method in TDD before live use.

`pass` requires every gating metric to meet its non-inferiority bound; `fail`
requires a hard breach or sufficient evidence of a policy violation; otherwise
`inconclusive`. Missing evidence cannot count as a pass or be hidden by averaging.

## Rollout states

Draft -> preflight -> ready -> canary_running -> analyzing -> paused_inconclusive
or promotion_pending -> promoted. Failures can lead to rollback_pending ->
rollback_dispatched -> verifying -> rollback_verified, partial or blocked.
Abort/cancel/expired authority are explicit, audited states, not deletion.

Promotion and rollback each recheck exact authority, current policy/manifests,
connector capability, expiry and expected routing revision at dispatch and runtime.
An LLM can propose neither an arbitrary target nor an unregistered command.

## What rollback means

The first adapter changes future session routing to a registered compatible stable
bundle. Signed commands carry unique ID, expiry, expected revision and fencing
epoch. Runtime execution is idempotent and read-back reports the actual new revision.
A timeout after possible execution is `unknown`, not a safe reason to issue a
different command blindly. Reconcile the same command ID by reading runtime state.

Verification requires fresh authenticated attestations from every serving runtime
in scope, or independently evidenced removal/draining from service, plus fresh
session probes through the real router showing the expected stable digest.
An acknowledgement, changed database pointer, stale heartbeat, mock response or
single healthy runtime is insufficient. Report disconnected/partial runtimes.

Track in-flight candidate sessions separately. If they still have unaccounted
exposure, show stable future routing with unresolved work, not fully recovered.
Cancellation requires a distinct supported capability; it cannot undo prior tool
effects. Database/index incompatibility or unavailable predecessor blocks rollback
and calls for operator mitigation. Never claim an email/refund has been reversed.

Initial lab target: scoped routing rollback verified within 120 seconds under
declared healthy-adapter conditions, with observed propagation/in-flight limits.
This is a target to measure, not a SaaS SLA. Offline runtime and incompatible-state
tests must produce visible partial/blocked results even when that fails the target.
