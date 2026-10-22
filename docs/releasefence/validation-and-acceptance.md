# Validation gates and honest acceptance

Engineering tests now exist and have been run against real isolated PostgreSQL,
HTTP processes, a customer gateway and a notification receiver. This is not a
complete product acceptance. The [latest OSS validation](oss-validation-2026-10-22.md)
includes the real-source/model pipeline and actual MLflow/Phoenix, but not the
target Windows/browser deployment. Legacy LangSmith remains unqualified, not a
requirement of the user-approved alternate profile. See [measured status](implementation-status.md).
A generated dashboard, mock backend, uploaded trace or provider log alone cannot
establish the requested production-observability workflow.

Latest [follow-up](followup-acceptance-2026-10-22.md): bounded browser checks now
pass, but the larger actual cohort failed. Older successful smoke checks do not
override that result or qualify an uninterrupted statistical promotion window.

| Gate | Required evidence | Current state |
| --- | --- | --- |
| G0 source/authority | Frozen workloads, exact rights/egress/control grant, backend licenses and accounts | Original grant 24/24 spent; separately approved 200-product/240-call grant 239 spent. Neither ledger may be reset; no new full campaign authority |
| G1 deterministic contracts/logic | Red/green contracts, metrics, detectors, routing, policy and no-data tests | Implemented, focused engineering tests pass; broad statistical calibration remains open |
| G2 durable processes | Real PostgreSQL/HTTP/worker/connector, restart/partition/unknown command tests | Tested API restart, worker kill/restart, retry, lost acknowledgement, rollback/drain and quarantine restore; exhaustive kill/partition matrix not claimed |
| G3 actual tracing | Both selected profile backends: export/query, cross-backend identity, redaction and failure handling | Bounded dual-backend checks pass. Larger campaign had six Phoenix read-back dead letters; separate replay of all 439 retained spans passes both backends, not original state recovery. Sustained/host qualification open |
| G4 metrics/alerting | Independent aggregate comparison, loop episodes, verified receiver delivery and lost-telemetry holds | 1,000-source/12,000-event campaign and 150 controlled cases pass; three live HMAC deliveries/rollback drills; not customer/SLA evidence |
| G5 canary/rollback | Actual sticky routing, policy decisions, authenticated read-back/probes, partial/incompatible cases | Actual Codex-backed HTTP candidate then stable serving, three verified rollbacks; partial/offline/incompatible controls pass; live statistical promotion remains open |
| G6 real workload/provider | Fresh authorized source-backed runs with bounded calls and both-backend evidence | New 200-product cohort failed: 165 successful outputs, 239 attempts; unknown USD costs and clock discontinuities. Representative live statistical promotion and independent review open |
| G7 browser/security/host | Actual UI/two-tenant isolation, independent security review, Windows/tunnel/restore/resource tests | Six actual Chrome browser cases, automated seven-view accessibility and four domain tests/build pass. Independent review/assistive-technology testing open; target host unavailable |
| G8 commercial | Qualified pilot, agreed success comparison, actual buyer acceptance/payment | Hypothesis only |

Engineering completion requires G1–G2 plus implemented UI/integrations and explicit
pending gates; supervised pilot acceptance needs G0–G7 for its declared scope.
Commercial willingness-to-pay requires G8. A bounded live smoke is named as such,
not broad statistical promotion or complete product acceptance.

## Required adversarial acceptance tests

- A request returning 200 while exhausting tools must not look like task success.
- No data, missing terminals, stale heartbeat or unavailable cost cannot promote.
- A partial exporter failure remains visible while healthy export is not double counted.
- Different code/prompt/tool schema creates a different release; unknown aliases are flagged.
- Sessions/retries stay pinned; controlled routing weights cannot leak across tenants.
- A rollout conflict, expired approval or revoked connector prevents command execution.
- Duplicate/replayed command is idempotent; lost acknowledgement is reconciled by ID.
- Changing a pointer without runtime read-back cannot report verified rollback.
- Offline/incompatible runtime and in-flight exposure remain partial/blocked.
- Optional AI explanation failure never disables metrics, alerts or safe state transitions.
- Restore does not resurrect completed commands, revoked authority or erased payloads.
- Alert retries/dead letters persist across process restart and receiver dedup works.

## Measurement targets, not claims

Zero cross-tenant disclosures/unauthorized actuations are required in the test
matrix. Deterministic aggregate results must match an independent oracle within
declared precision; unknowns/exclusions must match exactly. Every serving runtime
in the declared verification scope must be accounted for. Never lower these gates
to make a demonstration green.

Notification p95 <=60 seconds and healthy scoped rollback <=120 seconds are lab
targets from the rule/rollback specs. Report all misses and conditions; neither is
a customer SLA. Mechanical and live volumes are defined in data-and-evaluation.md.
Report process-test skips, unavailable browser/accounts and incomplete host testing
as unpassed, not as successes hidden behind unit-test totals.

Every report binds code/dependency/image/policy/metric versions, source manifests,
approval, workload split, randomization, raw measured denominators, independent
expectations, receipts, backend query proofs, notification receiver logs and actual
runtime verification. Gate summaries must derive from evidence, not manual “pass”
flags. Retain original failed reports and new-version successors without resets.
