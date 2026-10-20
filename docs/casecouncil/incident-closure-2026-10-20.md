# Owner-approved irrecoverable incident closure — 20 October 2026

The user explicitly approved this policy after the
[MVP readiness decision](mvp-readiness-2026-10-20.md). It is implemented and tested,
not a reconstructed provider receipt or proof that the original invocation was safe.
There is no new public HTTP/model tool, automatic closure or UI hold-clear button.

## Policy and implementation

`recovery.close_incident` and `Store.close_incident` require a workspace owner and
filesystem-operator access. A nonblocking cooperative `runtime_guard` lock fences
closure against a running `Controller.once`, and a serialized SQLite transaction
also rejects queued/running jobs or unsettled attempts. The operator must separately
attest that dispatch was stopped and the process tree inspected/isolated. The lock
does not prove orphan absence or establish the safety of the failed model call.

The closure binds the exact attempt, prompt hash, original receipt hash, actor,
hashed reason and isolation reference. The original unknown receipt, attempt count,
stage count and full reserved call/time charge remain unchanged. Unknown token
usage and any corresponding monetary cost remain **unknown**, not an invented
maximum token charge or zero. Known usage is only a lower bound on total usage.

Eligibility is deliberately narrow:

- Settled unknown usage, with no explicit unsafe-tool diagnostic; explicit unsafe
  tool activity requires separate investigation, not accepted uncertainty.
- Only the unknown-runtime/interrupted-call hold is eligible, not restore,
  journal, checkpoint or other integrity holds.
- No verified reconciliation already exists, no prior human review of that packet,
  and the original settlement matches the independent journal.
- Explicit acknowledgement that usage remains unknown and tool safety unverified,
  an expected current journal head and an idempotency key.
- **One incident closure per store-authority lifetime**, counted from the external
  journal, not per case/workspace/campaign. A second incident stops work again.

`attempt_incidents` is an additive hash-bound projection of the fsynced
`incident_closed` journal event. Closure alone neither clears the hold nor queues
a job. The existing separate `resume` action validates all store-wide liabilities,
current snapshot/rights/policy, packet hash, stage limits and remaining original
call/time/claim allowances. Completed model checkpoints are reused; historical
partial work is archived and remains labelled unapproved.

Start/reservation now check liabilities **across the whole store**, closing the
previous new-workspace bypass. No single-workspace approval resolves another
unclosed liability. A research campaign may additionally install a monotonic
store-wide call ceiling in the independent journal (`campaign_call_limit`), which
counts reservations made before the ceiling was installed. It cannot be raised
by a new grant. Restore retains incident/call-ceiling authority, including events
newer than the snapshot, and leaves old jobs stale. This is not protection against
a hostile host administrator constructing a separate installation/authority.

## Review and export

Scoped run responses expose validated incident metadata. The workbench shows an
owner-accepted incident warning alongside the unchanged unknown receipt. A resumed
packet includes `incident_notices`, an explicit limitation and a required
`runtime_incident` review resolution. The packet verifier rejects missing notices
or lost review requirements when checked against incident authority. JSON and HTML
exports retain incident notices even after independent maker/checker approval.
Human approval is not conversion of an unknown receipt into a verified one.

## Operator commands

Stop dispatch, inspect/isolate the process tree, and take a protected verified backup
first. Backups are plaintext; use encrypted storage/ACLs and approved retention.
Use `--evaluation-only` only for the isolated Irish research store.

```sh
.venv/bin/python scripts/recover_casecouncil.py \
  --data-dir /protected/casecouncil --actor OWNER \
  inspect --job JOB_ID

.venv/bin/python scripts/recover_casecouncil.py \
  --data-dir /protected/casecouncil --actor OWNER \
  close-incident --attempt ATTEMPT_ID --expected-head CURRENT_HEAD \
  --reason 'Explicit owner acceptance of this irrecoverable incident' \
  --isolation-reference 'Reference to checked stopped runtime/process tree' \
  --acknowledge-unknown --runtime-isolated --key INCIDENT_KEY
```

Inspect the new head, then use the separate bounded `resume` procedure in the
[recovery runbook](recovery-fix-2026-10-20.md). Do not auto-repeat closure when another
call fails. Neither command grants broader data rights, new cases or model spend.

`scripts/continue_casecouncil_replay.py` continues only the exact current approved
development manifest/IDs in the **original store**. It preserves original reports,
uses a new-only report directory and installs the original cumulative ceiling.
It never renews rights, closes incidents or records human/domain approval. Pending
intake uses the operator Store API, not a new HTTP/browser acceptance path.

Protocol reporting keeps three separate facts: all stage artifacts present,
fully audited protocols, and independent semantic/product acceptance. Incident
acceptance cannot turn an unaudited history into `protocol_campaign_passed=true`.

## Verification

Observed red/green failures covered missing incident closure, restore refusing
accepted incidents, a missing persistent call-limit function, acceptance of an
incident after human review, and a missing incident-aware packet verifier. Tests
cover same-stage reuse, unchanged receipts/charges, explicit acknowledgement and
owner scope, stale heads, active-runtime fencing, unsafe/known receipts, lifetime
caps, other-workspace bypass, erasure, fsync/commit crash windows, old-snapshot
restore, idempotent continuation, scope changes, gold isolation and reviewed exports.

Final monorepo regression: **681 passed, zero failed/skipped**, including 148
CaseCouncil Python tests; artifact
`var/validation/casecouncil-incident-regression-2026-10-20-v3.xml`.
Frontend logic: six passed; production build and scoped Ruff passed. Six upstream
dependency deprecation warnings remain. The Windows branch of the file lock and
actual Windows installation have not been qualified on the target laptop.

## Applied live transition

Before mutation, a verified SQLite snapshot was taken at
`var/validation/casecouncil-before-incident-2026-10-20-v1.sqlite3` with its manifest.
Original reports/packets were preserved. Process inventory found no CaseCouncil
worker/replay launcher or `codex exec` invocation; the exclusive lock was acquired.
This inventory is isolation evidence, **not** a tool audit of the old failure.

Incident `5f472344411c4d50b164e4ecc2dccde2` accepts the irrecoverable failure of
attempt `3986db68a65c448693dd33f55486940b`. Its original `usage:null`,
`tools_audited:false` receipt and 90-second reservation remain intact. Job
`eca1aee91a9d40df9a5f758f5994fc92` resumed with the same ID and completed its
three ballots and synthesis without repeating its three proposals or critic.
It now has nine attempts, one still unknown, and an explicit incident warning.

The follow-up campaign/report location is
`var/validation/casecouncil-fspo-continuation-2026-10-20-v1/`. Final measured results
are in the [continuation record](real-data-continuation-2026-10-20.md); this policy
document does not assert a clean audited campaign or MVP pass.
