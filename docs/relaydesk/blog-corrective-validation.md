# Our memory agent passed JSON validation—and still failed the product test

*Engineering blog draft, 17 October 2026. Corrective results are measured; full production acceptance remains incomplete. Not published externally.*

The most useful test of our memory-enabled agent was not a model benchmark. It was a deliberately fabricated recovery statement with a valid citation ID.

The response passed.

That exposed the mistake: we had enforced the shape of evidence without sufficiently restricting what the answer could claim from it.

RelayDesk helps support engineers resume long investigations. It combines a short-term session buffer, durable vector memory, recall, structured compression, relevance scoring and revision-aware synchronization. Its purpose is continuity, not autonomous resolution. A polished handover that promotes a failed workaround into a successful fix defeats that purpose.

## Reproduce before repairing

Our initial aggressive campaign retained 49 actual public threads across 22 repositories and 3,576 non-bot messages. It found wrong-ledger recovery, source corruption under stale hashes, self-citation, stale index publication, negation false positives, unbounded context metadata and slow large-scope recall. Five of ten live jobs completed the AI stage. We kept the failures.

After approval to fix them, the reproductions became mandatory regression tests. A source edit was injected between embedding computation and publication. A source body was changed without changing its digest. A backup was restored against an unrelated existing erasure ledger. A current question was allowed to retrieve itself.

These are not exotic model problems. They are ordinary data-integrity and concurrency problems at an AI boundary.

## A source needs more than an identifier

A vector can represent an old revision. A valid memory ID can refer to the user's question rather than supporting evidence. A stored source hash can be stale after corruption. A claim can cite a real source and still say the opposite.

The corrective design checks each boundary separately. Recall authorizes before scoring and excludes the active question as supporting evidence. Index publication rechecks source activity, hash, state and revision inside its commit transaction. Reads and publication validate canonical source integrity and exact spans.

We also narrowed factual generation. Each published factual claim must now be one contiguous quotation from one supplied source. The server restores original offsets, attaches author/state/time metadata and replaces model-written narrative with a neutral quotation count or abstention.

This sacrifices fluent synthesis. It does not solve truth or relevance: a participant may be wrong, or a perfectly quoted sentence may answer the wrong question. But it makes the machine-enforced guarantee explicit and testable. Independent quality review remains a separate gate.

## Our “compressed” context was not bounded

We counted selected text, then attached every omitted memory ID. At ten thousand memories, serialized compression reached 366,025 characters—larger than the entire model-context allowance.

The fix was not to hide omitted records. It was to keep a full omission count and hash, a bounded sample of up to eight IDs, and an authorized ledger reference. All serialized text and metadata share the budget.

A second test caught nested old assistant outputs inside apparently short chat turns. The buffer now projects only conversational turn fields. A short visible message cannot secretly drag a previous evidence pack into the next prompt.

## Faster recall without widening access

The initial ten-thousand-memory probes took 5.7–7.2 seconds. The revised implementation batches only authorized, compatible vectors and uses a call-local matrix for cosine scoring rather than per-candidate connection work.

Final probes at 1k/5k/10k memories were approximately 39–43 ms, 137–150 ms and 216–218 ms. Serialized compression stayed between 5,884 and 5,926 characters. SQLite integrity checks passed.

These fixtures are labelled replicas of real payloads. They test bounded capacity, not additional unique histories. Two probes on macOS do not establish latency distributions, process RSS or an old Windows laptop's SLO.

## Recovery cannot forget later deletion

An external deletion ledger is only useful if restore uses the correct one. Missing-file checks were insufficient: an unrelated valid ledger was accepted.

Schema-2 backups now bind the store to an independent ledger identity and per-store registration nonce. Restore verifies that binding before copying data, then reapplies current erasures. Existing unbound stores require explicit offline enrollment with a quarantined pre-migration snapshot; old sessions expire and old drafts become stale.

The remaining operational obligation matters: an old clone of the correct ledger still has the same identity. Identity is not freshness. Protect the latest authoritative ledger outside ordinary rollback snapshots.

## What the final rerun actually proved

The final code was frozen and its hashes checked throughout the campaign. A bounded acquisition after public quota reset expanded the deduplicated corpus to 89 threads, 22 repositories and 6,680 non-bot messages. Eighty-four captures were complete and five explicitly partial. They are discovery candidates, not a human-screened gold set.

The final unmasked suite passed 283 Python tests. Frontend state tests and production build passed. The original, long and expanded replay runs executed 2,921 invariant assertions with no failures; overlapping data was not counted as independent new evidence.

Eleven live installed-Codex jobs completed the AI stage, including same-session and fresh-session follow-ups. All remained qualified partial drafts. Their 78 factual quotations resolved to original source hashes, revisions and spans. The controlled unsupported outcome was rejected, and the labelled injection marker was absent from the published answer.

Nineteen HTTP workflow checks, twenty bounded stress/negative checks and five isolated crash/restart checks also passed. None of those substitutes for actually using the UI in a browser.

## A nonzero acceptance exit is useful

The final acceptance command still exits nonzero: six gates passed, one failed and five remain blocked. We do not yet have the full screened cohort, independent two-human-reviewed questions, actual browser acceptance, target Windows/protected-edge drills or consenting-customer usefulness evidence.

That is not a contradiction. Correcting engineering failures is progress; it is not permission to declare every untested product claim true.

The lesson from this build is that memory quality is inseparable from provenance, budgets, permissions, revision control and recovery. The model is one participant in that system—not the authority that certifies it.

[Measured report](corrective-validation-2026-10-17.md) · [Study guide](study-guide.md) · [Acceptance gates](product-acceptance.md)
