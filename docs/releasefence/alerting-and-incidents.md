# Loop-failure alerting and incident lifecycle

Detection is deterministic/versioned. An optional AI summary explains already
recorded evidence; it cannot change severity, silence a page or authorize action.

## First rule families

| Rule | Evidence | Important distinction |
| --- | --- | --- |
| Iteration exhaustion | Runtime reports enforced iteration cap and stop reason | Not an inferred semantic loop |
| Repeated action without progress | Bounded repeated tool/argument/outcome fingerprint and unchanged progress marker | Allow declared polling/retries; expose heuristic uncertainty |
| Deadline exceeded | Accepted task and elapsed deadline/heartbeat evidence | Distinguish queued, running and declared human wait |
| Missing terminal | Accepted task remains unclosed beyond lateness/deadline policy | Missing telemetry is not proof the agent failed |
| Schema repair storm | Repair attempts/failures exceed approved per-task/rate limit | Parse retries are charged work, not successful completions |
| Canary outcome regression | Versioned metric window fails approved policy | Needs correct cohort and coverage denominator |
| Telemetry/control degradation | Connector stale, export loss, queue overflow, worker lag or delivery failure | Monitor the observer, not only the customer agent |

A customer pins iteration/deadline/polling limits in its manifest/policy. Initial
lab defaults may use repeated-action count 3 and max iterations 8; these are
fixture settings, not universal production limits or an automatic kill permission.

## Durable episodes

Incident states: open -> acknowledged -> mitigating -> resolved, with reopened
episodes linked to prior evidence. Acknowledgement is not resolution. Store rule
revision, event/window hashes, tenant/app/environment/release and dedup episode key.
Repeated delivery of one event must not page repeatedly or create multiple incidents.
Resolve only after configured recovery evidence, not after a webhook returns 200.

Initial notification path is an allowlisted signed HTTPS webhook with a built-in
isolated test receiver. Separate connector-command and notification outboxes.
Suggested initial delivery schedule: immediate, 5s, 30s, 120s and 600s, bounded by
incident expiry/attempt policy. Persist each attempt, response class and next due
time. A dead-letter record is visible and replayable only through scoped audited
operator action. Do not leak receiver bodies, credentials or raw prompts.

Treat network/receiver outcomes as accepted, rejected or unknown. A lost response
can follow a successfully accepted request, so receivers get a stable delivery ID
and must dedup; no exactly-once external delivery guarantee. Verify webhook HMAC,
timestamp/replay handling and delivery at the receiver, not merely queue insertion.

## Severity and action

Warn on suspicious repetition; page on approved hard exhaustion/deadline rules or
sustained regression. Proposed lab notification target: receiver acceptance p95
within 60 seconds of durable incident creation with a healthy network. It is a
test target, not an end-to-end detection SLA; report detection and delivery delays
separately, plus p99/max and failure count. Simulated-clock unit tests do not prove
wall-clock delivery behaviour.

Alerts never imply automatic rollback authority. An owner may preauthorize exact
hard rules for a registered manifest pair/environment within a finite window.
Other cases require an exact-target human approval. Low-volume/no-data windows
block expansion and can page telemetry health without guessing agent quality.
