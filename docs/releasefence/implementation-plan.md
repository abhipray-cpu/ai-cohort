# Dependency-ordered test-driven implementation plan

**Implementation was subsequently authorized and is present.** This remains the
dependency-ordered plan; its exit criteria are not all acceptance passes. Consult
[implementation notes](implementation-notes.md), [TDD checkpoints](tdd-checkpoints.md)
and [status](implementation-status.md) for what was actually exercised. In particular,
actual-backend, real-source, browser, target-host and commercial gates remain open.

For each behavioural slice: write focused tests, run and retain a meaningful red,
implement the smallest coherent change, rerun/refactor under green, then expand
integration evidence. Do not claim a style-only edit was TDD or a fake backend
proved an actual destination. Inject clocks, provider ports and network adapters.

| Phase | Red tests first | Exit evidence |
| --- | --- | --- |
| 0 source/authority freeze | Missing rights/license, unsupported adapter, no baseline, no control capability | Reviewed contracts, source/integration registry and finite campaign proposal |
| 1 contracts/pure functions | Bad scope/hash, nonfinite values, oversized bodies, unknown/null/zero, price categories | Bounded models, canonical identities and normalization tests |
| 2 tenant store/auth | Cross-tenant IDs, RLS pool leakage, role denial, CSRF/replay/idempotency conflicts | Real PostgreSQL integration and two-tenant API tests |
| 3 ingest/collector | Duplicate/conflicting events, late/orphan spans, pressure, redaction and sampling | Bounded durable intake and lifecycle coverage computation |
| 4 metrics | Failed-work exclusion, parent/leaf double cost, unknown prices, cached overlap, zero success | Independent aggregate-oracle agreement and honest metric API |
| 5 detectors/incidents | Legitimate polling, hard loop, human wait, missing terminal, storm/dedup | Versioned rule episodes and sustained no-data behaviour |
| 6 notification outbox | Lost response, 429/5xx, restart, replay, SSRF and dead-letter re-drive | Actual isolated receiver verification with bounded retries |
| 7 release registry/routing | Manifest mutation, incompatible baseline, turn/retry reroute, assignment imbalance | Immutable bundle and real sticky Python HTTP runtime adapter |
| 8 canary analyzer | Low n, missing data, mismatched cohorts, repeated-peeking, tail instability | Frozen/calibrated deterministic analysis with pass/fail/inconclusive tests |
| 9 control/rollback | Expired/revoked approval, competing revisions, command replay, offline/partial scope | Signed fenced compare-and-set commands and read-back/probe verification |
| 10 durability | Kill before/after every apply/commit/ack, stale worker, restore/revocation replay | Real process/partition/restart and quarantined restore tests |
| 11 trace backends | Export-only false pass, ID/schema drift, failed exporter, secrets | Actual authorized LangSmith and Phoenix ingest/query evidence; mock scope kept separate |
| 12 operator workbench | Empty/stale/null states, tenant deep link, unauthorised actuation, partial rollback | Domain tests/build and actual browser/accessibility evidence |
| 13 repo/host | Owned lifecycle, no startup side effects, absent credentials, dependency failure | Additive Make/config packaging, target-host resource/proxy/runbook evidence |
| 14 validation | Scenario oracles, leakage, source rights, finite live egress and denied side effects | Mechanical volume campaign, fresh real-source provider campaign, failed/pending denominators |
| 15 acceptance | Complete concept proof, low-volume hold, no fake SLA, customer acceptance | Gate report with explicit open UI/security/host/business criteria |
| 16 learning cadence | Evidence and link checks | Study guide/single blog after measured checkpoint, not before |

Engineering implementation precedes claimed end-to-end actual-data acceptance.
Approved source acquisition or read-only prerequisite checks can happen while
engineering proceeds, but no model/provider/production action inherits authority
from another product or a general instruction to finish.

Keep new apps independently runnable; extend shared packages additively with
compatibility tests. Do not edit real `.env`, old services/data or unrelated dirty
work. Proposed tests should include core/contracts, PostgreSQL/RLS, telemetry,
metrics, incidents/outbox, connector/routing, canary/control, real processes,
HTTP/UI, actual backends, workload/evidence and Windows/proxy acceptance.

Retain red/green commands and failure outputs, actual module map, design deviations,
JUnit/build/lint/browser artifacts, source/version/license manifests, trace backend
queries, observed durations, command/probe proof, approvals and all failed runs.
Check gating policy before execution; never tune a locked result into a pass.
