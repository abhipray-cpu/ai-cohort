# Audit, durable execution and recovery

Target behaviour for all requirements. A restart must not lose completed evidence,
repeat consumer actions or resurrect deleted records. Single-host failure is a real
availability limitation; independent backup/restore evidence is a release gate.

Current implementation: scoped durable jobs/leases/checkpoints, validation events,
nullable usage holds, separate erasure ledger, per-case key deletion and encrypted
quarantined restore. Temporary backup/restore, account-resurrection and erasure-race
regressions pass. See [module map](implementation-notes.md) and [TDD](tdd-checkpoints.md).
The exhaustive kill-at-every-stage, disk-full, Windows crash and operational
retention matrix below remains acceptance work. Audit rows are not hash-chained,
administrator-proof legal evidence, or proof of external delivery.

## Event and job records

Record actor/system identity, household/case, event ID, source/fact/artifact revisions,
correlation/idempotency key, wall-clock UTC time, monotonic elapsed duration where
available, safe result/error code and previous event link. Do not log document text,
complete VIN, raw prompts, bank details or credentials. Display user-reported events
as such. Store validation failures and timeout/tool/permission failures explicitly,
not only schema errors. Append-only application audit is not tamper-proof against
a host administrator; do not market it as immutable legal evidence.

Persist intent/checkpoint/outbox transactionally with compare-and-set case revision,
household deletion epoch and worker lease fence. Worker results with expired
authority or stale leases are rejected even if their provider call succeeded.
Keep useful validated earlier artifacts if a later stage fails, labelled partial.

## Bounded retries and unknown receipts

Classify errors as retryable transport/rate limit, malformed output, nonretryable
scope/schema/safety or unknown execution. Backoff with jitter and retry-after within
persisted attempt/time limits. Parse retry has at most one correction attempt and
still consumes the investigation allowance. An external timeout may have consumed
usage: store unknown rather than zero and hold further paid work until reconciled
or an owner explicitly accepts the uncertainty with a new bounded allowance.
Record failed and cancelled attempts in denominators. Receipt absence never means free.

Public GET source capture is retryable with hashes/validators. Draft attempts may
yield different content; they never overwrite an accepted checkpoint. First-release
manual external submission has no automatic retry because the application did not
send it. Downloads/idempotent outcomes/inbox items use stable identities.

## Failure matrix

| Interruption | Required recovery |
| --- | --- |
| Upload before metadata commit | Orphan quarantine sweeper deletes after bounded grace; no case attachment assumed |
| Fact commit before extraction job ack | Resume original job identity; preserve correction revision |
| Provider called before receipt persisted | Unknown-cost hold; retain accepted earlier stages, never unbounded retry |
| New source captured before interpretation | Pending registry review; affected old results stale if materially uncertain |
| Invalidation committed before rematch | Keep stale approvals blocked; resume rematch once with fresh consent |
| Rematch written before notification | Transactional outbox materializes one inbox item |
| Consent revoked during provider call | Fence late result, suppress alert; do not reuse context for another purpose |
| Packet approved before content changes | Old approval remains historical; download denied against changed dependencies |
| File written but DB commit fails | Hash-addressed private orphan cleanup; no public link |
| Payment recorded then corrected | Attributed reversal/amendment, not hidden overwrite or duplicate savings |
| Host sleeps / clock jumps | Bound catch-up, flag deadline uncertainty; no stale scheduled action |
| Backup restored | Quarantined start, reconcile deletion/revocation ledger, revoke sessions, audit before serving |

## Restore and deletion evidence

Back up a consistent database/blob manifest pair with source versions and encryption
metadata; private DB and files cannot be recovered independently and called valid.
Test restore to a separate restricted directory/account. Disable scheduler/provider
egress, reconcile tombstones/consents/grants, revoke old sessions/approvals as
appropriate, verify hashes and run isolation probes before operator activation.
Never overwrite the live store to test restore. Logs and evaluation artifacts have
their own retention; deletion must include private corpus copies where applicable.

Required tests kill real workers before/after commit, lease renewal, provider response,
packet render and outbox materialization; test disk-full/read-only stores and old
worker completion. Mock-only crash tests do not qualify process recovery.
