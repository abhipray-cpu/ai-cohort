# 850 tests passed. Our live agent campaign still failed.

*Day 11 of our 14-day, 12-product challenge: building ReleaseFence, a
production-agent observability and release-assurance workbench.*

The larger live run looked respectable from a distance: 200 real public-data
tasks, local Codex integration, two actual tracing backends and hundreds of spans.

It was not a pass.

We used 239 model-call attempts, including retries. Only 165 of the 200 tasks
produced successful literal-source outputs. Six Phoenix export records reached
dead letters after read-back mismatches. The campaign stopped at complete-export
verification, before its closed-window decision or rollback.

Meanwhile, the final monorepo regression had 850 passing tests and five unrelated
skips. Six actual browser end-to-end cases passed after accessibility fixes.

Those results are not contradictory. They answer different questions. Building
ReleaseFence made that distinction central to the product itself.

## The product is release assurance, not another trace viewer

An agent release is rarely just a new code package. A team might change its prompt,
model configuration, tool schema and retrieval index together. When behavior gets
worse, an on-call engineer needs more than a list of successful HTTP requests.

Which release is serving the session? Is it repeating tools without progress?
Are failures being excluded from the latency chart? Did cost increase, or did
usage reporting disappear? If someone requested rollback, is the previous bundle
actually handling new work?

ReleaseFence is aimed at engineering/platform teams operating customer-facing
agents. Its proposed value is to connect those questions into a scoped workflow:
observe, compare, authorize a change and verify the runtime result.

That is a commercial hypothesis, not a proven market. We have not established
customer willingness to pay, savings, production availability or superiority to
existing observability/release platforms.

## Instrument execution, but keep accounting separate

We implemented the requested concepts as distinct responsibilities: production
tracing, latency and cost dashboards, loop-failure alerts, canary analysis and
verified rollback.

On the customer side, an authenticated gateway routes sessions to registered
stable or candidate bundles. The SDK records lifecycle and usage events; a
dedicated OpenTelemetry provider emits filtered execution metadata. ReleaseFence
persists tenant-scoped state in PostgreSQL, with durable workers for observation,
exports and notification delivery.

A trace is useful for seeing how an execution unfolded. It is not automatically
the authoritative count of accepted tasks or billed attempts. A retry can create
another invocation span without creating another independent customer session.
An exporter outage must not make failed work disappear from the dashboard.

In our larger cohort, 200 agent roots plus 239 invocation spans produced **439
unique spans**. Querying each from two backends produces 878 backend observations,
not 878 model calls. Keeping those denominators separate matters more than making
the chart look busy.

## Two real backends, not two adapter labels

The original design named LangSmith and Arize Phoenix. No authorized LangSmith
project was available, so we researched alternatives and obtained approval for a
named self-hosted profile using MLflow alongside Phoenix.

This was a requirement change, not a LangSmith test pass. The legacy profile
remains separate. New OSS-profile rollouts explicitly require both selected
backends; missing proof in either destination holds qualification.

We used actual upstream servers, authenticated/scoped MLflow access and real
export/query paths. Verification checks original trace/span IDs, parent
relationships and release identity. A successful upload or HTTP status is not
enough. Customer-owned backend connections also do not grant permission to resell
third-party platforms as an unrestricted managed service.

The interesting failure came later: both retained backend databases contained all
439 spans with matching identities, yet six original Phoenix export records had
not passed read-back within the retry limits.

We replayed that retained metadata into fresh actual backends, without another
model call. All 439 spans verified in each destination.

That narrowed the investigation. It did not establish the exact original cause,
recover the original dead-letter records or turn the failed campaign green.
Later data presence is not proof of successful verification at an earlier time.

## Unknown cost must survive the dashboard

The workload invoked the installed Codex executable through a restricted adapter.
It did not add a direct model API client to the product's domain logic or change
model/authentication settings. Local CLI execution does not mean inference is
offline or that we know its per-call price.

All 239 calls in the larger campaign had unknown USD cost. Token availability did
not resolve billing identity. We kept reported, estimated and unknown categories
separate, with unavailable cost-per-success rather than an invented zero.

This is easy to get wrong. A known-cost subtotal of zero can look like free
inference if the interface hides its unknown denominator. A latency chart can look
healthier if it quietly ignores failed tasks. Observability has to make missing
evidence visible, not just display the evidence that arrived cleanly.

The campaign also contained large wall-clock discontinuities whose exact host
cause remains unestablished. We retained those timestamps, but did not use them
to claim representative latency, a stable-host soak or an SLA.

## A canary percentage is not statistical confidence

Sessions stay pinned to their assigned bundle. The router hashes scope, session
and a rollout seed, so turns and retries do not randomly jump between releases.

For the larger run, we used unfiltered session IDs and the normal 5% candidate
stage. The result was 189 stable sessions and 11 candidate sessions.

Two hundred total tasks did not become 100 observations per arm. Nor would the
minimum admission count alone guarantee enough power to show non-inferiority.
Controlled tests demonstrate that even perfect, known-cost samples can remain
inconclusive under the conservative default bounds.

The analyzer combines closed event-time windows, lifecycle coverage, runtime
freshness, signed counters, selected-backend evidence and cost completeness with
versioned fixed-look analysis. Critical failures independently block expansion.
Repeatedly checking until a convenient result appears is not the intended method.

The larger live campaign never reached its decision stage. We therefore do not
describe its outcome as a demonstrated live statistical hold or promotion pass.
The implementation and controlled tests establish those guards; this campaign
established a failed acceptance result.

## Alert delivery and rollback need their own evidence

Loop detection is deterministic: repeated actions without progress, iteration
exhaustion, deadline/schema exhaustion and missing terminal work are operational
signals. Legitimate polling and bounded human waits need different treatment.

Findings become durable incidents and notification work. Delivery uses signed
webhooks, stable deduplication identity, finite retries and visible dead letters.
At-least-once delivery is not exactly-once behavior at an external receiver.

Control is a separate authority path. An independent approver grants a bounded
scope; signed commands carry expiry, expected revision and fencing information.
The customer connector applies an eligible command idempotently, then returns
signed state and fresh loaded-bundle probe evidence.

An acknowledgement is not verified rollback. Offline runtimes and unresolved
in-flight candidate exposure cannot simply be omitted to get a green result.
Routing back to stable also does not undo an email, payment or database write.

Earlier bounded live drills and the final zero-inference process campaign did
exercise signed/probed rollback. That evidence belongs to those campaigns—not to
the larger live run that failed before reaching rollback.

## Test-first development helped us catch the reporting mistakes too

We used observed red/green slices for behavior such as approval boundaries,
unknown-cost accounting, backend contracts, signed runtime receipts and bounded
campaign ledgers. Not every scaffold or documentation line was test-first.

Browser testing found real contrast failures. We fixed text, badges, notices and
audit timestamps rather than disabling the accessibility rules. Screenshot review
also caught ugly floating-point latency output; a focused domain test now rounds
presentation without converting missing measurements into zero.

One less glamorous failure involved provenance. An absolute runner path escaped
the evidence-directory join, leaving the failed cohort's runner self-copy missing.
Twenty-three archived files still match their recorded hashes. We added a test and
fixed future snapshots, but did not reconstruct a supposedly original source file
after the fact.

We also added fail-closed cohort summaries. Provider failures, incomplete exports,
missing decisions and discontinuous timing must not disappear behind a manually
written “all passed” flag.

## What we can honestly claim

At this checkpoint, the implementation has real engineering evidence: 850 passing
monorepo tests, five unrelated skips kept visible, six actual Chrome browser cases,
four frontend domain tests, a production build and source-backed process campaigns
against real services. The mechanical source campaign covers 1,000 USDA products
and 12,000 lifecycle/tool events; it is not 12,000 model calls or customer traffic.

The larger live campaign still failed. Provider failures, original-run trace
recovery, valid timing, billing completeness and sufficiently powered actual
traffic remain open. The old Windows laptop and protected Cloudflare deployment
are not yet available for target-host qualification. Independent review and
customer pilot acceptance are also outstanding.

We did not finish with a claim of a 100% accepted MVP. We finished with a clearer
boundary between implementation, bounded evidence and unresolved acceptance.

For a product intended to tell other teams whether an agent release is safe to
expand, that boundary is part of the product—not a disclaimer to add afterward.

---

Implementation/evidence checkpoint: 22 October 2026. Read the
[study guide](study-guide.md), [architecture](architecture.md),
[TDD checkpoints](tdd-checkpoints.md) and
[full validation follow-up](followup-acceptance-2026-10-22.md).
This is a build retrospective, not a customer case study or launch announcement.
