# Contracts, state and exact evidence

Status: pilot schema `relaydesk-1` implemented in `packages/contracts/src/contracts/relaydesk.py`: strict types, extra-field rejection, bounded text/collections and enums. The broader vocabulary below is a design target, not a claim each name is an existing class. [Actual mapping](implementation-and-operations.md); reference/quote checks do not certify semantic entailment.

Corrective publication policy (17 October): `Reply.Claim` permits exactly one supplied memory ID and requires a verbatim source span. `grounding.py` maps to original offsets (including CRLF/LF rendering), adds author/state/time/type and exact citations, and replaces the model narrative with a neutral server summary. `answer_state` distinguishes `quoted_evidence` from `abstained`; `semantic_paraphrase_verified=false` is explicit. Proposed questions/limitations are not factual verification. Quotation establishes provenance, not truth/relevance/completeness. Canonical source digests and spans are checked at publication/read boundaries.

## Domain boundaries

| Contract | Required fields/meaning |
| --- | --- |
| `Scope` | Server-resolved actor, workspace/account/case, grants and policy revision |
| `ConversationImport` | Bounded source records, origin, source identities, timestamps and capture completeness; no arbitrary fetch URL |
| `SourceRevision` | Provider/repository/issue/comment IDs, raw-body hash, created/updated/observed times, role attribution and revision |
| `Turn` / `Session` | Conversation ID, ordered durable sequence, speaker, timestamp, expected/minimum revision and idempotency |
| `MemoryProposal` | Kind, subject, claim/polarity, status proposal, applicability, source spans and uncertainty; no granted authority |
| `MemoryRevision` | Case/account scope, immutable revision, proposal/active/disputed/superseded/suppressed/erased state, valid interval and provenance |
| `AttemptOutcome` | Proposed/performed action distinct from observed/reported outcome, linked IDs and evidence |
| `SummaryRevision` | Covered source range/IDs, structured state, omission counts, dependency hashes, validity and prompt/model versions |
| `EmbeddingManifest` | Model/tokenizer/artifact hashes, dimension, pooling/normalization, precision, runtime and chunk policy |
| `VectorRecord` | Scoped memory/chunk/source ID, source/text hash, model/memory revision and validated finite normalized vector |
| `RecallRequest` | Server-owned scope, bounded question, as-of cutoff, minimum revision and query intent |
| `RecallHit` | Eligible memory/source revisions, exact spans, score components, applicability and rank reasons |
| `ContextManifest` | Buffer/summary/recall IDs, token/character budgets, omissions, source/index/policy revisions |
| `ConversationReply` | Cited claims, chronology, uncertainties, clarification/abstention, recall mode and coverage; no action execution |
| `MemoryCorrection` / `ErasureRequest` | Expected revision, explicit requested scope/effect, actor authority and reason; erasure confirmation separate |
| `SyncPage` | Restore epoch, authorized event cursor, next cursor/has-more, current revision and readiness |
| `HandoverReview` / `Export` | Exact report/context revision, reviewer, acknowledged limits, immutable hash and invalidation dependencies |

Generate JSON Schema from actual models at implementation time. Restrict output IDs to the supplied authorized set where useful, then independently check membership/ownership/currentness. A model selecting an allowed ID cannot authorize an otherwise denied operation.

## Evidence references

Reference source ID/revision, exact JSON path or body character offsets, quoted value/hash and speaker/time metadata. Offsets use a documented canonical representation; preserve original bytes/text and transformation mappings. Do not change whitespace/Unicode normalization and pretend old offsets still match. Resolve source links through trusted provider identity, not a model-generated URL.

Validate every material reply/summary/memory claim against available sources and scope. Quotes from later messages cannot support an earlier historical answer. A citation can resolve while the interpretation is wrong; semantic support and preserved qualification need separate tests/human labels.

Imported source author roles are descriptive, not verified organizational authority. GitHub association is not proof of a customer representative, engineer confirmation or promise. Distinguish a participant reporting a successful test from an independently executed validation—which RelayDesk never performs.

## Temporal model

Store at least `created_at`, `updated_at`, `observed_at`, asserted event time and explicit valid interval where supplied. Use source timestamps for ordering, stable source IDs for ties and an ambiguity flag when timezone/date inference is uncertain.

Current captured bodies can contain edits made after the historical question. Without original revision history, do not reconstruct earlier wording. Conservatively expose an edited body no earlier than its known update time or exclude it from that replay with a coverage gap. Current closed/reopened state and later timeline metadata are also unavailable to an earlier cutoff unless their historical event is captured.

Relative dates require an attributed reference time. Unknown dates remain unknown. “Next release” is not a calendar commitment. Different versions/users can have different simultaneous outcomes; temporal reduction cannot flatten these into one universal latest fact.

## Trust and validation stages

1. Validate bounded import identity, types, dates, page coverage and raw hashes; reject malicious locations/URLs.
2. Validate extraction shape, source ownership, exact spans and category/attribution; unsupported inference remains proposed/disputed.
3. Validate embedding dimensions, finite values, normalization and revision compatibility before index publication.
4. Validate compression source coverage, references, preserved state/qualifications and omissions; partial summaries cannot claim exhaustive handover.
5. Validate recall eligibility and rank inputs, then reply references, currentness, permission and context dependencies.
6. Recheck review/export revision and source availability; source erasure invalidates dependent outputs even if previously reviewed.

One bounded model repair per stage. Log a safe stage/error category, not raw private output or prompt. Reserve attempts before calls. Type/reference validation errors and timeouts are separate events; a final run error must not replace validation history. Preserve successful extraction/index/source checkpoints when later generation fails.

## Completeness and status language

Use distinct states: complete_for_declared_scope, partial, unavailable, denied, unsupported, stale, indexing_pending, cancelled and failed. No evidence/no relevant hit/permission denial/provider outage are different outcomes. Similarity score is not confidence, and confidence is not technical truth.

Track imports by discovered/selected/available/processed/omitted messages, extraction by source coverage/proposals/accepted/rejected, recall by indexed/eligible/selected/omitted memories, and compression by full source interval. Per-item success cannot conceal unprocessed required items. Persist these denominators in handover exports.

## Audit events

Record actor/scope, ingestion grants, source revisions, extraction/repair outcomes, index publish/skip, compression coverage, recall mode/score policy, context manifests, memory correction/promotion/suppression/erasure, cursor resets, stale publication rejection, reviews/exports, cancellation and restore reconciliation. Routine telemetry excludes bodies, embeddings, private queries and credentials.

Keep full authorized evidence separate from safe diagnostics. Historical revisions are retained by policy except actual erasure; metadata-only audit must not resurrect erased text.
