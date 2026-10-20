# A webhook is not a workflow: building BuildRelay, an event-triggered AI response desk

*Day 8 of our 14-day, 12-product challenge.*

A client build fails. GitHub sends a notification. An engineer sees it later,
opens several job logs, works out what is worth investigating, assigns someone and
tries to explain the situation to the client.

That is a real operating workflow, not just a summarization problem. For an agency
maintaining many repositories, the product opportunity is a response desk that
turns noisy CI failures into owned, evidence-backed handoffs.

We called it **BuildRelay**. It listens to signed GitHub webhooks and an authenticated
queue, captures evidence, proposes a structured triage, and records an incident
with an owner and an unapproved client-update draft. GitHub issue synchronization
is optional. Automatic code changes and client-message sending are out of scope.

The interesting part was not connecting a webhook to a model. It was deciding
what should happen when the same event arrives again—or the process disappears
halfway through handling it.

## First, make acceptance durable

The tempting implementation is one request handler that downloads logs, calls the
model and creates an issue. That ties fast event delivery to several slower,
failure-prone dependencies. It also makes a timeout ambiguous: was nothing done,
or did the last action succeed before the connection broke?

BuildRelay separates acceptance from execution. Both transports converge on a
transactional inbox in local SQLite. A worker subsequently claims accepted work
and advances it through evidence capture, validated triage, an internal incident
and optional external delivery.

For queue ingress, ACK happens **after inbox commit**, not after model analysis.
If the consumer dies before commit, redelivery can recover the message. If it
dies after commit but before ACK, redelivery encounters the same canonical event
instead of creating another one.

An HTTP `202` therefore means “accepted durably,” not “the AI finished” or “the
diagnosis is correct.” Clear semantics beat an optimistic success banner.

## Idempotency needs a business identity

Delivery IDs identify transport attempts. They are not enough when the same source
event can arrive by webhook and queue with unrelated delivery IDs.

Our event identity includes the configured repository, source run, source attempt,
conclusion and workflow-version value. Incident identity groups the attempts of
one run. Database uniqueness enforces convergence across process restarts and
concurrent acceptance; an in-memory “already seen” set would not.

This also forces a distinction between duplication and ordering. A later successful
attempt should recover the incident. An older failure arriving afterwards must
not reopen it. “Received most recently” is not the same as “latest source state.”

## Retry is a policy, not a loop

A temporary upstream outage may recover. A malformed queue envelope will not fix
itself on its hundredth delivery. An expired log archive may require a person.

BuildRelay distinguishes these outcomes. Transient workflow failures use persisted
backoff with jitter and relevant rate-limit delays. Four attempts, including expired
claims, bound crash loops. Permanent or exhausted failures become visible dead
letters. Authorized replay requires investigation and a reason; completed evidence
and triage checkpoints are retained.

Malformed queue messages take a different path: record a digest and rejection
guidance, without storing a potentially secret raw payload, then terminate delivery.
If rejection auditing cannot be persisted, do not ACK away the evidence of failure.

The broker's pending messages and the application's dead workflows are separate
operational concerns. A workflow can become dead after its source message was
correctly ACKed, because durable acceptance transferred responsibility to the app.

## The bug was inside the error handler

The worker uses expiring lease tokens to fence state changes. A stale worker cannot
checkpoint or finish an event after its lease expires or another worker takes over.

Our real-data fault testing found a subtle failure. A source request failed after
the lease expired. The workflow caught the network failure and tried to record it.
The database correctly rejected that write because the lease was stale—but the
second exception escaped the error handler and crashed the worker loop.

The fix was not to weaken fencing. It was to introduce typed lease loss and handle
it around **both processing and failure recording**. The stale worker appends an
audit event without modifying the event or its replacement's token. Lease loss
inside analysis auditing also must not masquerade as a JSON-parse error and cause
another model call.

This is a useful testing lesson: verify the path where writing the failure itself
fails. A happy-path lease test would never have exposed this bug.

## Exactly-once is especially slippery across an external API

Consider an issue POST that GitHub accepts just before the connection breaks.
Repeating the POST can create a duplicate. Local deduplication alone cannot make
the remote action transactional with SQLite.

BuildRelay records `sending` before the POST and includes a stable incident marker
in the issue body. An ambiguous result requires reconciliation against the source.
If creation cannot be established, it stops for review instead of blindly issuing
another create. Internal ownership is already durable, so the handoff survives a
failed optional external delivery.

That is a bounded recovery strategy, not a universal exactly-once guarantee. Our
crash tests exercise it with a controlled external-effect stand-in. Live GitHub
write acceptance remains a separate gate requiring an authorized repository.

## Grounded quotes can still be the wrong evidence

The other important failure came from evidence selection.

Our original selector took short file tails in alphabetical order. It was bounded
and easy to reason about, but initiating errors can occur long before cleanup
output. Successful early files could also consume the allowance before a later
failed job was considered.

The model could then return valid JSON and quote the supplied text exactly—while
the useful failed assertion had never reached it.

We compared selector revisions against 797 real LogChunks logs spanning 80
repositories and 29 languages. Using the same normalized literal-anchor scorer,
the old selector retained 450 of 765 scorable annotated failure anchors, or 58.82%.
Generic diagnostic windows improved that, but the tested 32,000-character versions
still did not reach our pre-existing 90% target.

The final revision keeps complete small archives, otherwise prioritizes early
diagnostics, terminal summaries and recent diagnostic windows across files. It
deduplicates overlapping lines and uses an explicit 64,000-character evidence
allowance. Retention reached **690/765, or 90.20%**—a narrow development-gate pass,
not complete coverage. Seventy-five scorable anchors are still omitted.

The larger allowance is a resource tradeoff, not a token-saving claim. This corpus
was used during development, so the comparison is not independent held-out proof.
Incomplete evidence still caps confidence below the manual-review threshold.

Most importantly, anchor retention, exact quote validity, lexical citation relevance
and causal diagnosis accuracy are different measurements. Passing one must not
be marketed as passing the others.

## Validate the system and the proposal separately

The corrective implementation passed **533 Python tests with no skips**, plus four
frontend domain tests and a production frontend build. Dedicated fault tests use
actual child-process exits and real broker redelivery, with controlled proposer and
external-effect stand-ins. They do not simulate every physical infrastructure failure.

We also replayed 36 actual captured GitHub records through real local HTTP, NATS
and the installed Codex adapter. The transport workload included 536 signed HTTP
requests, 10,000 queue envelopes and 25 malformed messages. It converged on 36
canonical events with no remaining ACK backlog. Thirty-four workflows completed;
two genuine unavailable sources became visible dead letters. All 22 available
failed-run analyses completed, exports remained draft-labelled and the tested
cross-client access checks passed.

Those were reconstructed deliveries from frozen source records, not native live
GitHub webhook traffic. Ten thousand duplicates are a transport stress workload,
not ten thousand independent AI-quality examples. The separate fixed 80-case
real-model benchmark completed all 80 cases: all produced valid grounded structures,
and **73/80 (91.25%)** had lexical citation overlap with the annotated failure chunk,
up from 57/80 (71.25%) in the failed baseline. One bounded repair brought the new
campaign to 81 model calls. Seven lexical misses remain. This is not an independently
verified root-cause accuracy figure. The [corrective report](fixes-and-validation-2026-10-19.md)
preserves the failures, denominators and remaining acceptance gates.

Running the service on an old Windows laptop is a deployment choice, not an
offline-inference claim. The installed Codex adapter can depend on an authenticated
remote model service. Quota, connectivity and unknown outcomes remain operational
concerns even without a direct LLM API integration in the product.

## What we can honestly claim

BuildRelay implements all five Day 8 concepts: dual event ingress, triggered
workflow execution, idempotent handling, dead letters and retries. The observed
lease-handler crash is fixed and the development selection-retention target now
passes. The evidence does not justify calling the entire product production-ready.

Browser interaction remains untested because no browser connection was available.
Actual Windows sleep/reboot behavior, Cloudflare deployment, authorized live issue
writes and independent causal/next-step review also remain open. The full quality
gate status belongs in the validation report, not hidden behind a green unit suite.

The bigger lesson is that an automation agent is a durable state machine with a
model inside it. The model proposes. The system authenticates, validates, commits,
deduplicates, fences, retries, reconciles and knows when to hand control to a person.

That is the foundation for a response desk a customer might eventually trust.

---

Implementation references: [architecture](architecture.md),
[study guide with concept-to-code mapping](study-guide.md),
[failed baseline](real-data-validation-2026-10-18.md), and
[corrective validation](fixes-and-validation-2026-10-19.md).
Public corpus attribution/provenance: [data and evaluation](data-and-evaluation.md)
and [LogChunks, Brandt/Panichella/Beller](https://zenodo.org/records/3632351).
