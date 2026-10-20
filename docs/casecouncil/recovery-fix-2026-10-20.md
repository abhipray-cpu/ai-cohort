# Failure diagnostics and audited recovery — 20 October 2026

Subsequent user-approved policy: [irrecoverable incident closure](incident-closure-2026-10-20.md).
The evidence-reconciliation path below still requires a real verified receipt.
The separate incident path explicitly retains unknown usage and unverified tool
safety. Later live continuation supersedes the historical held-state description
at the end of this record; the old receipt was never reconstructed or overwritten.

Implemented after the user's explicit request to fix the failure-observability and
same-job recovery gap. This does **not** retroactively recover the missing live
receipt or turn the [incomplete real-data campaign](approved-real-data-run-2026-10-19.md)
into a pass. No additional complaint payload was sent to a model during this fix.

## What changed

`runtime.py` now retains a bounded diagnostic in the call receipt: fixed category,
exit code, error-event count, unsafe-tool-event flag and `message_retained: false`.
It inspects documented JSON failure/error events and bounded stderr in memory,
then discards their text. No raw error message, stdout, stderr, complaint narrative,
email, token or arbitrary provider key is persisted in the diagnostic. Nonzero
exits also inspect tool events; a missing completed turn does not imply safe tools.
Timeout, cancellation and stream overflow have explicit categories. Message-based
categories are hints, not proof of quota state or zero usage.

The [official CLI JSON event contract](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)
informed this implementation through the OpenAI Docs skill. Controller failures
now include the same sanitized diagnostic in validation history. The original
pre-fix error cannot be reconstructed from data that was never retained.

`recovery.py`, Store methods and `scripts/recover_casecouncil.py` add **operator-only**
inspection, evidence reconciliation and bounded resume. There is no new public
HTTP/model tool or UI “clear hold” button. The local caller must have filesystem
operator authority and name an application owner of the affected workspace.

## Invariants

1. A reconciliation is a separate, hash-bound append to SQLite and the external
   usage authority. It never overwrites the original receipt, assigns an unknown
   call zero tokens or refunds its conservative full reservation.
2. Supplemental evidence must match the attempt ID and prompt hash, contain valid
   observed usage and an explicitly verified tool audit, and have a verification
   reference. It is recorded as **operator-verified evidence**, not as an observation
   made by the original adapter. The software checks structure/binding; it cannot
   cryptographically authenticate a provider receipt or replace a trustworthy operator.
3. An acknowledgement, account-wide quota balance, healthy subsequent call or
   fabricated fixture numbers are not receipt evidence. Explicit unsafe-tool
   incidents are not cleared by this workflow.
4. Reconciliation alone never clears the hold or dispatches work. Resume is a
   separate owner action, fenced by the expected journal head, packet hash,
   current evidence/rights/policy/authority/snapshot and idempotency key.
5. Every unresolved liability in the workspace must have valid supplemental
   evidence. Possibly live invocations and other queued/running jobs block recovery.
   Integrity/restore holds, stale/cancelled/reviewed jobs and exhausted allowances
   cannot be bypassed through resume.
6. The same job retains its ID, attempts, call count, charged seconds and claim
   count. A new explicit wall window is 90–1,800 seconds; it is not a new inference
   allowance. Existing two-attempt/stage, 22-call/job and 1,800 charged-second ceilings remain.
7. Valid proposal/critic/revision/ballot checkpoints stay intact. Failed/blocked
   retryable stage placeholders and derived consensus are archived before removal
   from the current projection. The old partial packet is archived with its hash,
   recovery ID and unapproved historical label; it remains inspectable by scoped
   API readers. The controller recomputes consensus without repeating completed
   model work. Human-reviewed packets cannot be rewritten by recovery.
8. Case erasure removes packet/checkpoint history as well as current evidence;
   minimal usage/reconciliation metadata remains. Backup/restore uses the current
   external reconciliation authority, retains the original unknown receipt and
   leaves old jobs stale; it never automatically resumes an old job.
9. Journal errors roll back the database transition. A file/DB crash-window mismatch
   remains fail-closed rather than silently resetting the authority head.

The additive tables are `attempt_reconciliations`, `checkpoint_history` and
`packet_history`; existing store schema/receipt shapes remain readable. Old
software cannot be used to bypass current journal/recovery gates. Backups are
still plaintext and require protected encrypted storage and ACLs.

## Operator procedure

Stop dispatch and take a verified protected backup before recovering a live store.
Use a dedicated operator session; do not place secrets or case text in reasons.
The CLI never invokes a model. `--evaluation-only` is only for the isolated Irish
research store and does not enable IE in the normal UK service.

```sh
.venv/bin/python scripts/recover_casecouncil.py \
  --data-dir /protected/casecouncil --actor owner \
  inspect --job JOB_ID
```

Inspection prints counts, binding/hash, receipts, reconciliation metadata and the
current journal head, not historical packet bodies. Inspect actual provider
evidence independently. The bounded evidence JSON has exactly:

| Field | Required meaning |
| --- | --- |
| `attempt_id` | Exact failed invocation ID |
| `prompt_hash` | Exact stored invocation prompt hash |
| `receipt.status` | `returned`, backed by independently verified provider evidence |
| `receipt.tools_audited` | `true`, independently verified; not a guess from no observed tool |
| `receipt.usage` | Observed integer input/output/cached counts; cached cannot exceed input |
| `receipt.elapsed_ms` | Observed nonnegative bounded elapsed milliseconds |
| `receipt.diagnostic` | Optional fixed-label diagnostic; unsafe evidence is rejected |

Do not copy the numbers from engineering fixtures, infer zero from a failed process,
or use another call's receipt. Keep the original supporting evidence protected;
the ledger stores normalized evidence and reference hashes, not raw message logs.

```sh
.venv/bin/python scripts/recover_casecouncil.py \
  --data-dir /protected/casecouncil --actor owner \
  reconcile --attempt ATTEMPT_ID --expected-head CURRENT_HEAD \
  --evidence /protected/verified-receipt.json \
  --reference 'Reference to independently checked provider evidence' \
  --key RECONCILIATION_KEY --verified-provider-evidence
```

Reinspect for the new journal head, then authorize a bounded same-job retry:

```sh
.venv/bin/python scripts/recover_casecouncil.py \
  --data-dir /protected/casecouncil --actor owner \
  resume --job JOB_ID --packet-hash CURRENT_PARTIAL_PACKET_HASH \
  --expected-head NEW_CURRENT_HEAD --wall-seconds 600 \
  --reason 'Verified evidence, current context and remaining original allowance' \
  --key RESUME_KEY
```

Start the existing worker only after successful authorization. Reuse the same key
and identical arguments for an uncertain command retry; a conflicting request
fails. This procedure does not itself grant a new campaign or source-egress budget.

## Verification and actual-live status

Red/green cases reproduced missing diagnostics, missing recovery methods,
message-only JSON error classification, exit-zero without a completed audited turn,
unavailable archived packet retrieval and
restore ignoring supplemental evidence. Focused tests exercise successful reuse,
privacy, idempotent retries, forged/stale evidence, revocation/currentness,
exhausted allowances, erasure, journal failure and restore. The fixture recovery
requires only four new provider calls—three ballots and synthesis—not reexecution
of proposals/critic. These are authored test-provider calls, not new real-case inference.

Final focused recovery/runtime/restore checks: **23 passed**, artifact
`var/validation/casecouncil-recovery-2026-10-20-focused-v2.xml`. Frontend logic checks:
**5 passed**. Ruff and `git diff --check` passed. Full monorepo regression:
**643 passed, zero skipped or failed**, including **110 CaseCouncil tests**. Report:
`var/validation/casecouncil-recovery-2026-10-20-regression-v2.xml`; this uses actual
local HTTP/NATS fixture tests, not new complaint-model calls.

The original actual-data store has **not** been modified, migrated, reconciled,
cleared or resumed by these tests: it still has 21 attempts, 20 known receipts,
two complete packets, one manual packet and `unknown usage or unsafe runtime` hold.
Its missing receipt has no independently verified supplemental evidence available.
Therefore the remaining three cases stay pending; the fix is not a live-campaign pass.
