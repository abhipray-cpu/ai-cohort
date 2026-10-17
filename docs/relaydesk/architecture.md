# Architecture: C4 levels 1–4

Status: implemented pilot, 16 October 2026. Local API/static UI, bounded worker, SQLite and genuine CPU embeddings run on macOS; Windows and protected Cloudflare remain acceptance targets. Installed Codex may use authenticated remote inference. [Actual code-level C4 and implementation deviations](implementation-and-operations.md) supersede indicative interfaces below.

Corrective architecture, 17 October: `grounding.py` adds a factual publication boundary between model response and `Store.finish`: exact single-source quotations, attribution/spans and neutral server summary rather than unverified narrative. Recall now uses a call-local matrix of SQL-authorized compatible vectors; publication/read paths revalidate source integrity and revision fences. `ledger.py` binds store identity to independent erasure authority, with explicit offline legacy enrollment; backups use schema 2. Context serialization includes omission metadata and projects recent turn fields only. These extend the C4 boundaries below; [corrective validation](corrective-validation-2026-10-17.md) records measured behavior and remaining gates.

## C4 level 1 — system context

```mermaid
flowchart LR
  engineer[Support engineer] -->|case conversation and corrections| app[RelayDesk]
  reviewer[Handover reviewer] -->|review exact revision and export| app
  owner[Team owner] -->|membership and egress policy| app
  sources[Approved conversation exports] -->|bounded import| app
  github[Approved public GitHub issues] -->|read-only source records| app
  app -->|authorized minimized prompt via installed CLI| model[Codex runtime and remote inference]
  app -->|reviewed local handover| engineer
```

There is no customer-message, production-command or repository-write arrow. An account/case boundary is an authorization boundary, not merely a browser filter. Model output is untrusted structured data.

## C4 level 2 — containers

```mermaid
flowchart TB
  browser[React and TypeScript browser] -->|HTTPS target| edge[Cloudflare Access and Tunnel]
  edge -->|loopback 8004| api[FastAPI and static UI]
  api --> db[(RelayDesk SQLite WAL on local disk)]
  worker[One memory and conversation worker] --> db
  worker --> embed[CPU semantic encoder and pinned local model files]
  worker --> cli[Isolated shared Codex adapter]
  cli --> remote[Authenticated remote inference]
  api -->|approved GETs only| github[GitHub API]
  api --> secrets[Protected host secrets and policy]
  worker --> secrets
  supervisor[Windows scheduled tasks target] --> api
  supervisor --> worker
  backup[Offline verified backup and restore tooling] --> db
  backup --> ledger[Protected erasure ledger and restore epoch]
```

These are C4 containers, not Docker requirements. Metadata, source/message bodies, memory revisions, normalized float32 vectors and index jobs live in the same product database. Separate model artifacts/logs/corpus archives are files with manifests. No external vector service or GPU is required by the initial proposal; actual CPU feasibility remains a gate.

Exact vector search operates over a SQL-authorized scope before similarity/top-k selection. Optional in-memory arrays are revision-keyed caches, not authority. Embedding computation happens outside write transactions; a short fenced commit publishes only vectors whose memory/text/model revisions still match. No network/model operation holds a database lock.

## C4 level 3 — application components

```mermaid
flowchart TB
  api[Session and scoped API] --> policy[Actor, account, case and egress policy]
  policy --> ingest[Import validator and source normalizer]
  ingest --> records[(Immutable source and message revisions)]
  records --> jobs[Durable queue, leases and reserved budgets]
  jobs --> extract[Structured memory proposal extractor]
  extract --> validate[Source span, identity and state validators]
  validate --> reducer[Deterministic applicability and supersession policy]
  reducer --> memory[(Versioned case and approved account memories)]
  memory --> outbox[Transactional embedding jobs and change events]
  outbox --> index[CPU encoder and fenced vector publisher]
  index --> vectors[(Revisioned vectors)]
  policy --> buffer[Bounded recent-turn buffer]
  policy --> retrieve[Scoped hybrid recall and relevance ranker]
  vectors --> retrieve
  memory --> retrieve
  records --> retrieve
  buffer --> context[Context budget and compression assembler]
  retrieve --> context
  memory --> compressor[Versioned structured compressor]
  compressor --> validate
  compressor --> context
  context --> reply[Structured cited reply or deterministic fallback]
  reply --> grounding[Exact original quotation and attribution publisher]
  grounding --> check[Canonical source digest, span, freshness and policy recheck]
  check --> review[Revision-bound handover review and local export]
  outbox --> sync[Scoped cursor events and invalidation]
  sync --> api
  policy --> audit[(Redacted audit events)]
  jobs --> audit
  check --> audit
  records --> backup[Schema-2 backup and new-directory restore]
  backup --> ledger[Independent ledger identity and store registration]
```

Compression is a derived view, never an authority above original sources. Extraction proposes memory; it does not approve promises, link customers or execute actions. Currentness comes from explicit state/revision policy, not from a model saying “latest.”

## C4 level 4 — proposed code interfaces

```mermaid
classDiagram
  class Scope {
    +actor_id
    +account_id
    +case_id
    +policy_revision
  }
  class Store {
    +authorize(actor, object, action)
    +append_turn(scope, idempotency_key)
    +commit_memory(expected_revision)
    +claim_job_and_reserve()
    +events_after(scope, cursor)
  }
  class BufferBuilder {
    +build(session, snapshot, budget)
  }
  class EmbeddingProvider {
    <<interface>>
    +encode(chunks, model_revision)
  }
  class VectorIndex {
    +publish_if_current(job, vectors)
    +search(authorized_ids, query_vector)
    +watermark(scope)
  }
  class RecallService {
    +retrieve(scope, question, as_of)
    +rank(candidates, policy)
  }
  class Compressor {
    +propose(source_range, prior_summary)
    +validate_coverage(summary)
  }
  class MemoryReducer {
    +reconcile(proposals, source_revisions)
    +correct(expected_revision, evidence)
    +suppress_or_erase(dependencies)
  }
  class ConversationController {
    +run(job, snapshot)
    +validate_and_publish(reply)
    +finalize_partial(reason)
  }
  class StructuredProvider {
    <<interface>>
    +generate(prompt, schema)
  }
  class SyncService {
    +changes(cursor, authorized_scope)
    +freshness(snapshot)
  }
  class ExportService {
    +review(exact_revision)
    +export_if_current()
  }
  Store --> Scope
  ConversationController --> Store
  ConversationController --> BufferBuilder
  ConversationController --> RecallService
  ConversationController --> Compressor
  ConversationController --> StructuredProvider
  RecallService --> VectorIndex
  VectorIndex --> EmbeddingProvider
  MemoryReducer --> Store
  Compressor --> MemoryReducer
  SyncService --> Store
  ExportService --> Store
```

This preserves the original indicative interfaces. The pilot combines buffer/compression in `context.py` and sync/evidence/reduction in `store.py`, alongside `api,worker,ingest,embeddings,recall,reports,backup,common`. The [implementation supplement](implementation-and-operations.md) maps actual classes/functions. Shared provider interfaces are reused, never another product's database/orchestrator.

## Sequence — restart, recall and concurrent correction

```mermaid
sequenceDiagram
  participant A as Engineer A
  participant B as Engineer B
  participant API as API and Store
  participant W as Worker
  participant V as Scoped vector index
  A->>API: Append correction with expected memory revision
  API->>API: Commit revision, source links, embedding job and event
  B->>API: Poll scoped cursor from a separate session
  API-->>B: Revision changed and index pending
  W->>API: Claim embedding job with source hash and fence
  W->>V: Encode and publish only if revision still current
  B->>API: Ask take-over question with minimum revision
  API->>W: Durable job and authorized snapshot token
  W->>V: Scoped semantic recall at compatible model revision
  V-->>W: Ranked evidence or explicit index lag
  W->>W: Assemble buffer, summary and original evidence
  W->>API: Recheck grants, source dependencies and revision
  API-->>B: Current cited reply or stale/partial outcome
  Note over API,W: A later deletion/revocation invalidates in-flight publication
```

Sync is server-mediated across sessions attached to this instance. Offline multi-master writes, merging independent databases and peer-to-peer laptop synchronization are not v1.

## State and persistence

```mermaid
stateDiagram-v2
  [*] --> queued
  queued --> processing: fenced claim and reserve
  processing --> complete: declared coverage and validation satisfied
  processing --> partial: cap, unavailable model or incomplete indexing
  processing --> failed: unrecoverable storage or internal error
  processing --> cancelled: explicit cancellation
  partial --> queued: explicit bounded continuation
```

Memory lifecycle is separate: proposed → active/rejected; active → disputed/superseded/suppressed; any eligible state → erased with dependency invalidation. Summary lifecycle: pending → validated/published; source changes → stale → rebuild. An existing response is historical or stale after changes; “complete job” is not verified technical resolution.

Proposed durable tables: users, sessions, memberships, accounts, cases, conversations, messages/source revisions, memory revisions, memory-source dependencies, summaries/coverage, embeddings/model manifests, jobs/checkpoints, events, reviews/exports, erasure receipts and settings. Server ownership and grants apply to every table/object path. Restore creates a new cursor epoch and consults the independent erasure ledger before serving.

## Architecture decisions

| Decision | Consequence |
| --- | --- |
| Durable messages, bounded reconstructed buffer | Session restart does not erase history; short-term window remains bounded |
| Case-first semantic vectors plus lexical evidence | Genuine long-term recall without arbitrary account blending |
| Same SQLite for authoritative data and vectors | Transactional ownership/revision checks; no second service initially |
| Async fenced indexing with visible watermark | Deletions/corrections cannot be resurrected by late jobs; lag is explicit |
| Structured compression plus original source access | Context savings do not silently become lossless-history claims |
| Ordered events and optimistic edits | Cross-session consistency, explicit conflicts rather than last-writer-wins guesses |
| Isolated CLI generation and local CPU embedding | Fits stated hosting model; remote generation privacy/availability remains relevant |

See [memory](memory-and-recall.md), [sync](compression-and-sync.md) and [operations](operations.md) for detailed bounds and acceptance.
