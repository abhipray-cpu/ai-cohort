# Observed test-first checkpoints

21–22 October 2026. These are observations from the implementation session, not
fabricated historical CI runs. Focused tests were run red before their behavior was
added/fixed, then rerun green. Not every scaffold, formatting edit or documentation
line is claimed to have been developed by TDD. Live-backend and actual-data gates
are not represented by stub success.

| Slice | Observed red | Green coverage |
| --- | --- | --- |
| Contracts/metrics/routing | New modules/contracts absent | Content addressing, bounded inputs, sticky assignment, dedup, unknown/zero/estimated cost |
| Tenant/control plane | Missing store/operation behavior | Actual PostgreSQL FORCE RLS, scoped roles, independent approvals, idempotency |
| OTLP boundary | Valid nested JSON returned 422 | Valid JSON accepted; bounded/privacy-filtered payload |
| Protobuf status | ERROR normalized to `unset` | Official protobuf enum decoding preserves error without exception text |
| Backend integration | `backends` module absent | Identity/parent/release read-back; a 200 empty body is not verification |
| Durable backend configuration | `Store.backend` absent | Encrypted credentials, tenant isolation, finite export retries |
| Customer event SDK | `sdk` module absent | Durable spool, capacity, dedup, finite retries/dead-letter replay |
| Spool concurrency | Late sender changed delivered state back to retry | Fenced local lease cannot overwrite newer sender |
| Task/session counters | `attest(window=...)` unsupported | Exact signed event-time window excludes later production traffic |
| Multiple runtimes | Same local event/task IDs collapsed two tasks into one | Runtime namespaces preserve independent observations |
| Expired control recovery | `recover` absent | Fresh post-expiry reconciliation and new independent rollback approval |
| Approver removal | Demoted approver still authorized rollback | Dispatch/execution recheck current membership |
| Lost acknowledgement | Connector attempted new authorization after an already applied command expired | Committed command read-back without new expired execution |
| Loaded bundle adapter | `gateway` module absent | Real dispatch/probe contract, payload isolation, wrong bundle rejected |
| Long inference deadline | Task dispatch had no separate deadline | Finite task timeout distinct from short health/control requests |
| Usage ID collision | Declared two model calls became one | Declared independent count preserves unknown attempts |
| Key/restore operations | `operations` module absent; backup lacked schema scope | Exclusive private key file, actual pg_dump/pg_restore to new quarantine database |
| Incident closure | `resolve` absent | Acknowledgement alone cannot resolve unmitigated critical episode |
| Retry after crash | Sixth notification delivery attempted despite five crashed attempts | Unknown attempts consume retry budget; dead letter retained |
| Trace replay | `replay_trace` absent | One owner-only replay and destination disable |
| Required tracing gate | `trace_gate` absent | Both vendors, both arms, matching environment/window, fresh read-back required |
| Signed proof replay | Old reconciled proof accepted after verified rollback | Observed revision/command scope cannot regress |
| Candidate-session resurrection | Closed old candidate could run again after rollback; duplicate completion could clear retirement during a later canary | Retired sessions require a new ID; task admission and routing serialized; completion is idempotent and cannot clear retirement |
| Worker health | `cycle` absent | Failed cycles do not publish successful observer readiness |
| Ingest quota | Over-capacity new evidence was accepted in reduced-capacity test | New evidence rejected, committed duplicate retries acknowledged |
| Privacy fingerprints | Persistent keyed fingerprint absent | Per-customer HMAC survives restart; no raw tool arguments |
| Contradictory success | Exhausted terminal accepted as success | Contract rejects it; runtime/gateway conservatively record failure |
| Independent hard-failure guard | A synthetic aggregate-pass state and approval could still dispatch promotion after a critical candidate failure | Expansion is independently denied; hard failures cannot be averaged into a statistical pass |
| Actual Phoenix project | New export-project assertion failed: header absent | `x-project-name` targets the same project used for read-back |
| Actual Phoenix protocol | Real server returned 415; new protobuf content-type/decoded-ID assertion failed | OTLP protobuf preserves trace/span bytes and actual backend parent/release read-back passes |
| Source acceptance guards | New validation module absent; relabelled brand test failed | Hash/GTIN/literal-source/package checks, persistent finite grant, no synthetic fallback |
| Acceptance summary | New summary function absent; earlier live report could hide degraded backend under a scoped pass | Named live checks reject failed Phoenix qualification even when model answers succeed |
| Exported runtime signatures | New independent-audit test failed because `proof_envelope` was absent | Original signed command receipts/heartbeat/window envelopes retained; verification audit includes envelope hash; live harness independently verifies exported signatures |
| Explicit OSS policy profile | New `trace_profile` rejected by policy contract | Finite named profiles; legacy default retained; both selected vendors/releases and backlog checks still required |
| MLflow enrollment and read-back | New backend rejected as unsupported | Encrypted scoped basic auth, numeric experiment IDs, actual protobuf-JSON identity/parent/release/experiment checks |
| OSS acceptance summary | Phoenix-only receipt incorrectly satisfied new-profile checks | MLflow, measured trace gate and privacy proofs required; integration mode requires zero model calls |
| UI profile selection | New profile helper export absent | Explicit validated profile submitted with rollout; unknown profile rejected |

The new profile then passed [actual dual-backend/source/live checks](oss-validation-2026-10-22.md).
This is additional test-first behavior plus real process validation, not a claim
that every lab-helper line was written after a failing unit test.

Subsequent [browser/cohort follow-up](followup-acceptance-2026-10-22.md) added:

- Actual browser axe failures before contrast fixes; rules were not disabled.
- Missing `duration` export before rounded latency/missing-value presentation.
- Rejected 240-call new grant before the bounded ledger extension; old grant cap
  and identity remain immutable.
- Missing cohort summary helper before fail-closed provider/export/clock checks.
- Missing source-archive helper before absolute-runner-path normalization.
  The prior cohort's missing runner self-copy is a retained provenance gap, not
  retrospectively reconstructed evidence.

Controlled tests also establish that minimum admission counts do not guarantee
statistical power. The singular Phoenix REST filter was confirmed against upstream
source; an initial plural-wire hypothesis was rejected without changing the adapter.

The process test starts isolated API/worker subprocesses and an actual local HTTP
receiver/fixture-bundle service. It checks actual candidate dispatch, loop event,
preauthorized rollback, stable dispatch, HMAC retry identity, worker kill/restart
and API restart. Its agent responses and usage values are **deterministic engineering
fixtures**, not live model output, real-world task labels or actual incurred cost.
The shipped development launcher is also exercised from an isolated temporary root:
actual up/status/down, duplicate-start refusal, and owned-process cleanup. This
does not start or stop the real workspace's existing product stacks.

Run `make releasefence-test` for current behavior. Retain new, separately named JUnit
artifacts for subsequent validation; never rewrite a failed live campaign into a pass.
