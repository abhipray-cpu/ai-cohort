# Full audit trail, integrity and recovery

Status: transactional events/state-head checks, independent authority/anchors, erasure and quarantined restore implemented; [actual scope](implementation-and-operations.md), [validation](implementation-validation-2026-10-17.md). “Full” means complete business-event lineage for supported workflows, not hidden model chain-of-thought, a legal compliance certification or immunity from a privileged host administrator.

## Event coverage

Record import acceptance/rejection and source revisions; parser/coverage results; playbook activation/context edits; scoped grants/delegations/revocations; analysis grants/reservations/stage outcomes; validation failures/repair/timeouts; findings and policy result; checkpoint/pause; request/assignment/expiry; human corrections/decisions/withdrawal/rejection; resume scheduling/revalidation failures; packet creation/final review/export; cancellation; erasure; backup/restore/epoch; audit verification and anchor gaps.

Each event has schema version, scoped monotonic sequence, unique event/correlation/job/attempt IDs as relevant, actor or service identity, UTC time, action/object/version references, outcome/reason, relevant before/after digests and predecessor hash. Time is not the sole ordering key. Store typed safe metadata; authorized source/decision detail lives separately. Routine logs must not contain raw contract text or credentials.

Use one transaction for a consequential state transition, event append and durable continuation/outbox intent. If audit append fails, the decision/state change rolls back. Rejected requests cannot be audited by committing the rejected business mutation; safe denial events need an independent controlled path without leaking foreign identifiers. Tests cover full-disk/transaction failure behavior.

## What integrity means

Application APIs append events rather than editing/deleting them, subject to approved erasure/redaction policy. Canonical event hashing with predecessor/sequence detects alteration, gaps or reordering relative to a trusted head. Separate per-scope streams avoid exposing global activity through unrelated-case sequences.

A chain stored only in the same writable database cannot prove it was not fully rewritten or truncated. For stronger assurance, export periodic chain-head manifests to operator-controlled storage outside the ordinary DB/backup rollback boundary, optionally authenticated with a separately protected key. Version keys, record rotation and verify against the latest independently retained checkpoint. No key in the database or source repository. Missing anchor means explicitly reduced assurance, not “immutable audit.”

Decisions and packet provenance must remain inspectable even if generation fails. Record model/prompt/schema/policy versions and minimized input-manifest hashes, not private reasoning traces. A recorded successful provider call is not a successful legal interpretation or customer outcome.

## Backups and restore

Use SQLite online consistent backup plus immutable upload/text files and manifests; never copy only the live main `.sqlite3` file and ignore WAL. Include schema/product version, store identity, document/text hashes, audit head, required external-ledger binding and restore instructions. Verify canonical source integrity and stored lineage, not only file hashes/`PRAGMA integrity_check`.

Keep the authoritative independent erasure ledger outside ordinary restorable snapshots. Bind it to a stable ledger identity and per-store registration; reject missing/unrelated authority **before exposing restored data**. Later erasures apply transitively to restored derived content. Explicit migration is needed for future old unbound formats; never silently enroll an arbitrary restored snapshot. Identity cannot prove freshness of a stale same-identity clone: operator protection/current checkpoints remain necessary.

Restore only to a new directory with services stopped or explicit isolation. Verify manifests/source/audit chain, reconcile current erasures and trusted external anchors, rotate restore epoch, expire sessions/leases, cancel in-flight jobs and invalidate every restored decision/final review/packet readiness. No restored approval automatically becomes usable, even if its document hash still matches.

Because a snapshot may contain revoked memberships, restored grants are not live authorization evidence. Quarantine serving/mutations until an authenticated operator explicitly reprovisions current authorized identities/memberships and activates the recovered store. Do not allow snapshot owners to self-certify authority from the old DB. Fresh decisions and packet review are required in the new epoch. A manually inspected recovery bundle may be read offline under operator control, not publicly served.

## Failure drills

Post-validation correction: audit/case reads and anchor publication now share `Store.coherent_read()`'s short domain write reservation. This prevents combining an old event set with a new case payload or ordinarily advancing an external head beyond the read. Backup verification and database copying hold the same fence; the SQLite backup API uses a separate source connection to avoid waiting on its own write transaction. Independent erasure receipts deny content reads before local cleanup, and reconciliation acquires its transaction before reading the case. Deterministic interleavings, 600-read/100-write stress, actual loopback HTTP and a real-source backup/erase/restore drill are documented in [the repair report](fixes-and-validation-2026-10-17.md). These serialized reads trade throughput for consistency; actual Windows load/power-loss acceptance remains open.

| Drill | Expected invariant |
| --- | --- |
| Kill after pause transaction | Exactly one durable request set; waiting consumes no model calls |
| Kill after human decision, before queue delivery | Decision persists; outbox replay creates one effective continuation |
| Expired lease worker publishes later | Lease/revision/epoch fence rejects commit |
| Audit event body tampered, reordered, removed | Verifier fails; writes/finalization quarantined until resolved |
| Entire DB chain truncated to older valid head | Independent latest checkpoint detects rollback; missing anchor disclosed |
| Current source text corrupted under stored hash | Read/egress/decision/publication/backup rejects corruption |
| Wrong existing erasure ledger supplied | Fail closed before copied data is served |
| Restore old snapshot after withdrawal/erasure | Erasure reconciled; approvals unusable; current authority reprovisioned |
| Disk full or audit write fails during decision | No committed decision without event/continuation consistency |
| Power loss after committed decision | Actual-host durability verified; no unsupported exactly-once claim |

## Erasure and audit coexistence

An authorized erasure may require removing contract text embedded in decision explanations as well as source/derived artifacts. Preserve only approved non-content receipts and explicit redaction/supersession events. Reconstruct or version the redacted audit representation with a documented verification boundary; do not silently edit a hash-chained payload and call the original chain intact. Retained external checkpoints prove the earlier head, not continuing availability of erased content. Detailed retention/redaction requirements must be resolved and tested before release.

No secure-wipe or regulatory compliance guarantee. Previously downloaded packets and offline media need separate disposal controls. Do not overwrite current authority/anchors when restoring an old product backup.
