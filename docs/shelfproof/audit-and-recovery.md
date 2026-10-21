# Durable artifacts, accounting and operational recovery

Planned from the start; no live recovery or new model authorization is performed
by this document. Preserve failed runs and uncertainty, not merely final drafts.

## State and event ownership

SQLite stores immutable source/fact/draft revisions, snapshots, version lineage,
evaluations/plans, incumbent decisions, reviews, idempotency records, leases and audit.
The separate append-only fsynced journal stores reservations, settlements, grant
changes, incident records and restore authority. A database rollback cannot erase
external invocation history; a hash chain is not protection against a hostile admin.

Persist import/freeze, authority/profile activation, batch authorization, dispatch
intent/reservation, provider receipt/fault, schema/evidence rejection, checkpoint,
selection/stop, review, edit, export, cancel/stale/erasure and recovery events. Use
minimal IDs/hashes and safe fixed codes, not raw customer content in routine logs.

## Idempotency, fencing and checkpoints

Idempotency binds actor, workspace/operation, key and canonical request hash. Same
intent returns the prior result; conflicting reuse rejects. Freeze stage IDs
(`draft:0`, `judge:0`, `reflect:1`...) and attempt sequences. A committed validated
checkpoint is reused only under identical snapshot/prompt/schema/protocol binding.

Worker claims have a random fence token, a proposed 600-second lease and 20-second
renewal. Every state write, including recording a failure, verifies ownership and
lease. Late results cannot mutate replacement work. An exclusive cooperative
runtime guard prevents two participating processes dispatching/recovering concurrently.
It does not by itself prove that an orphaned child is absent.

## Reservations and unknown liability

Reserve one invocation and its time before dispatch. Retain failed/malformed calls
and pre-crash reservations. Measured tokens may be null; unknown is not zero. Reconcile
known time/usage only from validated attempt-bound telemetry; never infer zero from
an exit code, quiet log, a healthy next call or account-wide quota information.

Stage repairs, revisions, row calls/charged seconds, worker claims and batch/campaign
allowances are separate counters. Restarts and resume do not reset any. Row caps
from [protocol](reflection-protocol.md) remain fixed. An explicitly approved campaign
expansion may append a revision with old/new ceilings, expected head and authority;
it must retain prior usage and cannot be induced by another batch or model output.
An unresolved store-wide liability blocks all workspaces, not just the failed row.

An orphan reservation is conservatively settled interrupted/unknown after runtime
isolation, preserving its full charge, never automatically repeated. Stream/timeout,
auth/quota/connection/schema/tool-audit faults have bounded sanitized diagnostics;
classification is a hint, not proof of root cause or safe execution.

## Recovery paths

Prefer independently verified supplemental provider evidence bound to the exact
attempt/prompt and original receipt hash. Append a reconciliation rather than
overwrite the original record; trusted operator evidence is labelled as such.

For irrecoverable unknown receipts, design a **separate owner/filesystem-operator
incident acceptance** path, not a pretend receipt:

- Explicit acknowledgement of unknown usage/unverified historical tool safety,
  reason, runtime/process-tree isolation evidence reference, current journal head
  and idempotency key; no active/queued work or possibly live invocation.
- No explicit unsafe-tool, integrity/restore incident, verified-known receipt or
  already human-reviewed target packet is eligible.
- Preserve original receipt, full reservation, counters and previous artifact history.
  At most one such incident per ShelfProof store-authority lifetime, counted from
  the external journal; workspace/campaign/restore changes cannot reset it.
- Closure alone never clears dispatch. Separate owner resume checks all store-wide
  liabilities, current source/policy/snapshot, selected artifact hash, row/stage/
  claim/grant ceilings and a new bounded wall window only.
- Retain warnings in run views, reviews and draft/approved export manifests. Require
  reviewer acknowledgement; accepted uncertainty never becomes observed safe usage.

This is a proposed ShelfProof policy, not reuse of another product's incident
approval. Applying it to a real ShelfProof incident requires explicit owner authority.
A second incident stops work pending investigation/new policy decision, not an
automatic closure loop. No fresh workspace/store may be created to hide a campaign hold.

## Backups, restore and crash consistency

Take new-only SQLite backups with source/artifact hashes and audit/manifest verification.
Retain current external authority independently. Restore into a new explicit root,
verify all hashes/journal linkage, revoke sessions, change authority epoch and put
old jobs in stale/quarantined state. Later external events must still constrain
liability/campaign/incident accounting even if absent from the older snapshot.

Only an explicit operator authorization can enable new runtime after reconciliation;
old jobs never auto-resume. A DB/file crash-window mismatch fails closed. Test fsync
failure, fsync-before-DB-commit, stale journal, corrupted artifact and rollback-to-
pre-incident/pre-budget-change snapshots. Refuse destructive overwrite of live roots.

## Degradation and reporting

If judge/plan/revision fails, preserve earlier copy/checks/findings with a terminal
manual state; do not call an unevaluated draft `review_ready`. A later rejected
candidate is retained without replacing a valid incumbent. Known input gaps produce
`needs_data`; cancellation/staleness retain authorized historical artifacts but no
current approval. Failed campaigns include pending products and spent/unknown calls.

Evaluation reports distinguish terminal tasks, complete artifact sets, fully audited
histories, review-ready rows and current human-approved exports. An owner incident
may permit useful bounded work while the fully audited acceptance result remains
false. Metrics must carry that distinction rather than laundering it into success.
