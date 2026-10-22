# Premium operator workbench and browser acceptance

Target: a calm release operations desk, not animated success counters. React and
TypeScript, accessible contrast/keyboard navigation, consistent spacing, responsive
tables and meaningful empty/error/loading/stale states. No fabricated customers,
traffic, graphs, latency savings or successful rollback illustrations in live views.

## Screens

1. Organization/project switcher with current role and tenant scope always visible.
2. Integration setup: observe-only/controlled mode, redaction preview, scoped endpoint
   configuration, key rotation, connector freshness and independently tested backend status.
3. Release registry: whole-agent bundle diff, immutable digests, compatibility and baseline health.
4. Rollout creation: exact target/policy, allowed actions/expiry, cohort and evidence-floor preview.
5. Canary desk: session assignment, baseline/candidate counts, outcome/latency/cost
   comparisons, intervals, coverage, data freshness and pass/fail/inconclusive reason.
6. Incident desk: affected release/cohort, loop trajectory/progress, first/last event,
   acknowledgement, delivery attempts/dead letters and linked redacted traces.
7. Rollback detail: requested/dispatched/unknown/acknowledged/verifying/partial/verified,
   expected and observed versions, per-runtime proof, fresh probes and in-flight exposure.
8. Audit/evidence: actor approvals, policy revisions, trace/window lineage and bounded export.

Show known dollars, estimates and unknown cost separately. Null is not a zero bar.
Expose current cohort counts and confidence/assumption limits beside comparisons.
A model explanation must be labelled advisory, with evidence links and unavailable
state; do not present a root-cause guess as a confirmed diagnosis.

Destructive/control actions require target/digest/environment confirmation, exact
authority and server revalidation. Disable rollback in observe-only mode, but also
enforce the denial server-side. An acknowledgement is visually distinct from
verified serving state. Never green the whole environment because one probe passed.

## Browser scenarios after implementation

Actual signed-in two-tenant sessions; unauthorized deep-link/trace access; setup
with missing keys; real backend status; genuine canary data; low-volume/no-data
hold; alert receiver failure; approval conflict; response-lost command; partial
and completed rollback; keyboard-only navigation; narrow viewport; chart/table
agreement and export redaction. Preserve screenshots and accessibility findings.

Frontend domain tests and a successful build are not browser acceptance. If a
browser is unavailable, say so and keep this gate open rather than substitute a
mocked UI snapshot or assume premium usability from source code.
