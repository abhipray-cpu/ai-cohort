# Context compression and cross-session consistency

Status: implemented pilot plus broader acceptance targets. Compression is source-preserving selection, not recursive/abstractive model summarization. Sync uses revisions/events/restore epoch and two-second polling. [Implementation differences](implementation-and-operations.md). A concise summary is not lossless memory; a shared database alone is not sufficient sync.

Corrective implementation, 17 October: the full serialized compression result is budgeted, including coverage metadata. `omitted_ids` contains at most eight samples; `omission_ledger` carries the full count/hash and authorized pinned-revision ledger lookup, never a claim the sample is exhaustive. The interactive summary selects only evidence that can actually be cited. The recent buffer projects turn fields and excludes nested prior output payloads. Schema-2 restore validates the store's independent-ledger identity/binding before copying data and rotates the sync epoch. [Measured corrective results](corrective-validation-2026-10-17.md).

## Compression contract

A summary is a versioned derived view over explicitly bounded source/message revisions. Store the included source range/IDs, content hash, prior summary dependency, policy/prompt/model version, processed/unprocessed counts and resulting memory references. Do not recursively summarize only the previous summary forever: retain access to original sources and periodically rebuild from attributable evidence.

Required structured fields: current reported environments; attempts linked to outcomes; active and superseded workarounds; hypotheses with unresolved evidence; decisions/commitments with explicit attribution; owners/dates only where stated; open questions; conflicts; coverage and omissions. Every material entry has source or memory links that resolve to original sources.

Compression invariants:

- Preserve negation, uncertainty, speaker attribution, version qualifiers and event/observed times.
- “Suggested,” “attempted,” “reported successful” and “verified” are distinct states.
- A source-backed unresolved commitment/open item cannot disappear merely because it is old or low similarity.
- Contradictions survive compression; a summary cannot settle them by confident wording.
- Source corrections/deletions invalidate dependent summaries/answers. Rebuilding cannot recover erased content from an old summary.
- Coverage counts refer to the full declared source range, not only selected input snippets. Caps create explicit partial ranges/continuations.

Model-generated summary validation has two layers: strict shape/reference/ownership checks, then semantic-preservation tests and human labels. Exact citations are necessary but not proof of entailment. Selected unsafe-phrase checks cannot replace meaningful quality review.

Compression is triggered near a context watermark or after a bounded ingestion chunk—not for every keystroke. At most one active compression per case revision. If the model times out/returns invalid output, retain the last valid summary as stale plus original new turns, publish safe deterministic state/coverage, and record the stage failure. Do not replace a good summary with an empty one.

Long open-item lists remain separately queryable. A concise top-level brief may link to a complete ledger; it must state omissions and cannot be reviewed/exported as an exhaustive handover unless required fields/coverage pass.

## Revision-aware memory writes

Use immutable memory revisions and optimistic expected revisions. New source evidence can create a proposal, not overwrite an approved state silently. A source edit creates a new source revision; it does not mutate citations attached to an old historical answer.

Deterministic reduction proposes supersession only when subject, case, environment and explicit correction/effective timing support it. Different reporters/environments may both be valid. When meaning is ambiguous, mark disputed and request review rather than resolving by arrival order, vector similarity or “latest message wins.”

Atomic transaction: append memory/source change → increment relevant case/account-memory revision → invalidate derived readiness → enqueue embedding/compression work → append safe change event. Compute expensive work outside the transaction. On completion, verify source hash, memory revision, model revision and lease/fencing token before publishing; stale jobs are skipped/requeued, never resurrected.

## Session synchronization protocol

Proposed client context token: case revision, explicitly visible account-memory revision, policy revision and restore epoch. Each authorized event stream has an ordered cursor. Serve only authorized case/account-promoted events; do not leak hidden case names/IDs through event lists, cursors or notifications.

Initial transport: bounded polling, approximately two-second active-session interval as a proposed target, not a measured guarantee. Responses include current revision, index watermark, `has_more`, next cursor and a scoped reset marker when history is compacted or restore changes epoch. Slow/disconnected clients refetch an authorized snapshot rather than assume missing events never happened.

Two-session flow:

1. Session A submits an edit with expected revision and idempotency key.
2. Server checks live permissions and commits once; concurrent stale edits receive a conflict, not last-writer-wins acceptance.
3. Session B receives a scoped invalidation and rebuilds its buffer/summary/recall cache from the new revision.
4. If vectors lag, B sees pending semantic recall and current authoritative state. It may wait within a bound or use explicitly degraded lexical/source mode.
5. Before returning a generated reply, server rechecks source dependencies, revision and policy. A correction may mark the draft stale; a deletion/revocation requires discarding inaccessible derived content. Regeneration is bounded, not an infinite catch-up loop.

Use a minimum revision/read-your-writes parameter for immediate follow-up after a correction. Prevent duplicate browser retries from duplicating turns/memories. API/worker restart retains revisions/events/jobs; a fresh session sees the same latest authorized state after catch-up.

Case memory and approved account memory have separate revision/read permissions. Do not expose another case's raw conversation merely because an account-level item was promoted. Promotion must establish allowable evidence visibility or a properly reviewed/redacted account-level source.

## Forgetting versus correcting

Expose two distinct operations:

- **Suppress from recall:** prevent an item being selected as memory; preserve authorized historical evidence/audit according to policy. It must be labelled reversible suppression, not total erasure.
- **Erase selected source and derived content:** apply an authorized dependency-aware deletion to source bodies, memories, vectors, summaries, cached contexts, generated answers and export availability. Show affected artifacts and backup limitations before confirmation.

Tombstones exclude erased rows immediately at query time, even while index jobs are pending. Log only non-content erasure metadata. Invalidate all derived outputs whose context dependencies included erased material; uncertain lineage should invalidate conservatively. Previously downloaded exports or already read browser text cannot be remotely un-read.

Deletion from live SQLite is not certified secure wiping of SSD/WAL/backups. Define retention/checkpoint/compaction and protected backup disposal operationally. Maintain a protected erasure ledger outside ordinary restorable backups; restore fails closed until later erasures are reconciled. Restore also creates a new sync epoch, expires sessions and quarantines ingestion/index jobs until consistency is verified.

## Acceptance matrix

| Scenario | Expected result |
| --- | --- |
| Two browsers edit the same memory | One expected revision wins; stale edit returns explicit conflict |
| Source corrected while reply is generating | No old claim labelled current; bounded stale/retry path |
| Source erased during encoding | Late vector commit fenced out; recall remains excluded |
| Permission revoked during recall | No new prompt/answer/export containing unauthorized evidence |
| Client reconnects after event retention | Scoped reset and latest snapshot, no guessed synchronization |
| Worker restart after memory commit | Outbox replay finishes pending work without duplicate facts |
| Old backup restored | Erasure reconciliation, new epoch and session invalidation before serving |
| Compression later times out | Original evidence/valid summary retained; explicit stale/partial state |

Test real histories for semantics and labelled controlled races for concurrency. Report these as different evidence types in [evaluation](data-and-evaluation.md).
