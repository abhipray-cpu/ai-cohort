# Latency, cost, outcomes and observable uncertainty

Metrics are versioned computations over immutable deduped events, not LLM answers.
The dashboard must expose window, denominator, cohort, source, freshness and coverage.

## Latency

Separate end-to-end task latency, queue time, tool/model duration, retries and
verification latency. Measure local durations using monotonic clocks; do not
subtract wall clocks on different hosts as a precise duration. Cross-host spans
need clock-skew qualification. Show p50/p95 with sample counts; null for no samples.

Timed-out tasks and missing terminals remain visible in separate completion,
timeout and in-flight measures; do not improve p95 by dropping failed work.
Predeclare how censored durations affect a canary gate. Show stable/candidate and
cohort composition side by side rather than only an aggregate average.

## Outcomes

Customer declares `success`, `failure`, `abstained`, `manual_required` or `unknown`
under a versioned outcome contract. HTTP 200, a completed model response or a high
judge score is not automatically successful task completion. An LLM-derived score
is labelled uncalibrated and cannot authorize rollback on its own initially.

Core views: assigned/accepted/terminal counts, success/failure rates, timeout and
iteration exhaustion, repeated-action episodes, schema repairs, coverage, oldest
unclosed task, connector freshness and actual serving release distribution.
Missing-outcome rate uses accepted tasks, not only received traces, as denominator.

## Cost

Keep known token/cost receipts, price-based estimates and unknown usage separate.
Use Decimal minor-unit/precision rules, nonnegative finite quantities and a currency.
Pin provider/model pricing revision and source; do not invent a per-token dollar
rate for a subscription-based CLI or an unrecognized model alias. Such runs can
show tokens/calls/latency with dollar cost unavailable.

Avoid double counting cached token categories, parent-inclusive versus leaf costs,
retries, duplicate exporter copies and evaluation traffic. Evaluator/summary spend
is separately tagged and included in total platform-assisted workload accounting.
Customer-reported cost is labelled reported, not a reconciled invoice.

Show known spend, estimated spend and unknown-call count separately; a combined
number is explicitly an estimate/lower bound where applicable. Cost per successful
task includes the cohort's failed/retried work in its numerator and successful
outcomes in its denominator, using compatible cost coverage. With zero successes
or inadequate cost coverage it is unavailable, not zero or infinity in a chart.

## Decisions and analytics safety

Store metric definition, price revision, outcome contract, sample exclusions,
event-time windows, baseline/candidate assignment and coverage checks with each
decision. Unknown cost must hold a cost-based promotion gate; other independent
hard safety rules can still fail the canary. Never let missing data vote “healthy.”

No PII/session IDs in unbounded metric labels. Limit cardinality and query range;
scope tenant aggregation at the database/query boundary, not just a frontend filter.
Data-quality and ReleaseFence collector/worker health get their own dashboard.
