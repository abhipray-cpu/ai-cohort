# Architecture: C4 levels 1–4

## Read consistency boundary — post-validation correction

[Rigorous validation](rigorous-validation-2026-10-17.md) rejected the earlier build because audit and case reads could observe different committed snapshots. The [post-validation correction](fixes-and-validation-2026-10-17.md) introduces `Store.coherent_read()`: a short `BEGIN IMMEDIATE` fence shared by case/audit/source/worker-check/export reads and anchor publication. Backup verification/copy also holds that fence, using a separate SQLite source connection for the backup operation. This serializes these reads against domain writes and ordinary external-head publication; no model/PDF/network/human waiting occurs inside it. Actual loopback testing now passes 600 reads during 100 updates, with a valid audit. Throughput on the older Windows target remains unverified; the fix is not a claim of lock-free or highly concurrent reads. Source-byte authorization/retrieval is atomic, and the independent erasure receipt blocks source access before local reconciliation finishes.

Status: implemented pilot, 17 October 2026. Diagrams preserve intended C4 boundaries; indicative classes are folded into Store methods/worker functions. See [actual code mapping](implementation-and-operations.md) and [measured evidence](implementation-validation-2026-10-17.md). Independent API/worker, SQLite and React run on macOS; Windows/edge remain targets. No earlier product business logic/database is imported.

## C4 level 1 — system context

```mermaid
flowchart LR
  requester[Business requester] -->|NDA and business context| app[ClauseGate approval workspace]
  reviewer[Authorized clause reviewer] -->|interpretation or exception decision| app
  owner[Workspace and playbook owner] -->|policy and scoped grants| app
  final[Final packet reviewer] -->|exact-revision internal sign-off| app
  data[Licensed public benchmark] -->|explicit offline acquisition| app
  app -->|approved minimized context via installed adapter| codex[Installed Codex and possible remote inference]
  app -->|authorized local export only| packet[Internal approval packet]
```

No e-sign, CRM, email, payment or counterparty-write integration. Public benchmark ingestion is an operator-controlled evaluation capability, not arbitrary network fetch driven by a contract.

## C4 level 2 — containers

```mermaid
flowchart TB
  browser[React TypeScript browser] -->|same-origin HTTPS and session| edge[Protected Cloudflare entry]
  edge -->|loopback 8005| api[FastAPI and static UI service]
  local[Loopback browser] --> api
  api --> db[(Independent SQLite WAL local disk)]
  api --> blobs[Scoped immutable uploads and text artifacts]
  worker[One bounded worker] --> db
  worker --> blobs
  worker --> adapter[Shared installed-Codex adapter]
  adapter --> inference[Configured model inference boundary]
  operator[Offline backup verifier] --> db
  operator --> authority[Independent ledger and external audit anchor]
```

Browser/API and worker are separate processes on one host. The API owns decisions and transactions. The worker claims bounded analysis/continuation tasks; waiting for people is a database state, not a sleeping subprocess. Static assets and API share origin; application auth remains required even behind Access. External audit anchoring is optional operational hardening until configured and tested, not a built-in immutable service claim.

## C4 level 3 — components

```mermaid
flowchart TB
  routes[Scoped API and session controls] --> auth[Roles and live authority resolver]
  routes --> intake[Bounded PDF/text intake]
  intake --> sources[Immutable source revision and coverage ledger]
  sources --> queue[Durable jobs and usage reservations]
  queue --> interpret[Structured interpretation proposer]
  interpret --> evidence[Source hash, span and coverage validator]
  evidence --> uncertainty[Uncertainty signals and deterministic policy evaluator]
  uncertainty --> checkpoint[Transactional checkpoint and request creation]
  checkpoint --> inbox[Authorized human decision inbox]
  inbox --> decisions[Strict response and authority validator]
  decisions --> resume[Dependency and expiry revalidator]
  resume --> queue
  resume --> packet[Version-bound packet builder]
  packet --> finalize[Final human review and scoped export]
  checkpoint --> audit[Transactional audit events]
  decisions --> audit
  resume --> audit
  finalize --> audit
  audit --> verify[Chain verification and external checkpoint comparison]
```

The model proposes interpretations and question wording. It cannot choose its own permission, approve an exception, assign an untrusted reviewer, mutate playbooks, waive blockers or decide that a partial document is complete. Deterministic state reduction owns those transitions. Human input is validated data, not a new system prompt.

## C4 level 4 — proposed code relationships

```mermaid
classDiagram
  class ScopedStore {
    +authorize(actor, object, capability)
    +claim_job(worker, lease)
    +pause_with_requests(snapshot, blockers)
    +record_decision(actor, request, expected, response)
    +enqueue_resume(snapshot, idempotency)
    +publish_packet(snapshot, artifact)
  }
  class EvidenceValidator {
    +validate_revision(source, digest)
    +resolve_span(text, start, end, quote)
    +coverage_complete(manifest)
  }
  class PolicyEvaluator {
    +evaluate(findings, context, playbook)
  }
  class ResumeValidator {
    +validate_bindings(snapshot, decisions, live_scope)
  }
  class AnalysisController {
    +run(job, budgets)
    +propose(context, schema)
  }
  class AuditLedger {
    +append_in_transaction(event, previous_hash)
    +verify_chain(expected_anchor)
  }
  AnalysisController --> ScopedStore
  AnalysisController --> EvidenceValidator
  AnalysisController --> PolicyEvaluator
  ScopedStore --> ResumeValidator
  ScopedStore --> AuditLedger
  ResumeValidator --> EvidenceValidator
```

Class/module names are illustrative interfaces, not implemented classes. Suggested files under `apps/clausegate-api/src/clausegate_api/`: `api.py`, `store.py`, `ingest.py`, `evidence.py`, `policy.py`, `approvals.py`, `worker.py`, `audit.py`, `reports.py`, `backup.py`. Web client under `apps/clausegate-web/`; strict contracts under `packages/contracts/src/contracts/clausegate.py`.

## Decision and continuation sequence

```mermaid
sequenceDiagram
  participant Q as Requester
  participant A as Scoped API
  participant D as SQLite
  participant W as Worker
  participant H as Human reviewer
  Q->>A: Start review for document/playbook revision
  A->>D: Atomic job, input snapshot and audit
  W->>D: Claim fenced job and reserve call
  W->>W: Analyze, validate evidence, evaluate policy
  W->>D: Commit checkpoint, blockers, requests and audit
  W-->>W: Release lease; no waiting model process
  H->>A: Decision with expected request/context revision
  A->>D: Live role, binding and expiry checks; commit decision
  A->>D: If all blockers satisfied, enqueue one continuation
  W->>D: Recheck context and current authority
  alt Bindings changed
    W->>D: Stale/reopen request and audit; no final packet
  else Bindings valid
    W->>D: Build packet; commit only after final fence
  end
```

No SQLite transaction remains open during human waiting, network access or model calls. Atomic domain transitions include their audit event and outbox/job entry. Decisions and queued continuation are not an exactly-once subprocess guarantee: use at-least-once jobs plus idempotent, lease-fenced commits.

## State model

```mermaid
stateDiagram-v2
  [*] --> draft
  draft --> queued: explicit review request
  queued --> analyzing: fenced worker claim
  analyzing --> waiting_human: unresolved blockers committed
  analyzing --> review_ready: all checks covered, no blockers
  waiting_human --> resume_queued: all required decisions valid
  waiting_human --> needs_revision: reviewer requests document change
  waiting_human --> rejected: authorized rejection
  resume_queued --> analyzing: new lease and revalidation
  resume_queued --> waiting_human: stale, expired or revoked approval
  review_ready --> finalized: final human exact-revision sign-off
  finalized --> stale: document, context, policy or authority changes
  review_ready --> stale: dependency change
  stale --> queued: explicit reanalysis
  analyzing --> partial: provider or coverage failure
  partial --> queued: explicit bounded retry
  draft --> cancelled
  queued --> cancelled
  waiting_human --> cancelled
```

Finalized means internally reviewed for the recorded scope—not legally safe, signed or enforceable. Request/decision/job lifecycles are separate and detailed in [approval lifecycle](approval-lifecycle.md).

## Storage and concurrency

Proposed tables: users/sessions, workspaces/memberships, cases, document_versions/text_spans/coverage, playbook_versions/rules, business_context_versions, jobs/stage_checkpoints, findings/uncertainty_signals, approval_requests/decisions/delegations, packets/reviews/exports, audit_events/outbox, settings/restore_epoch and independent erasure/authority records.

Source identity includes bytes hash, canonical text hash and extraction version. A new upload creates a new document revision even if the filename is unchanged. Original text is preserved for exact offsets; normalization for model input needs an explicit reversible map. Rules and context are immutable versions. Foreign keys, unique keys and compare-and-swap revisions enforce idempotency and conflict behavior. Use short `BEGIN IMMEDIATE` transitions where needed; live grant checks and final writes must share the transaction or use an equivalent revision fence.

## Deployment and decisions

Old Windows laptop: proposed independent limited-account API and worker startup tasks, local disk DB/uploads, installed Codex authenticated under the service identity, bounded rotating logs. Cloudflare exposes only the application through Access; never the model CLI. No GPU/Docker/vector service is required. Actual host compatibility and all-six-product capacity are acceptance gates, not assumptions.

| Decision | Reason / consequence |
| --- | --- |
| Durable domain state rather than an in-memory interrupt | Waiting survives restart and consumes no model runtime |
| Default deny, final human packet review | Prevents model certainty from becoming organizational authority |
| Approval bound to full versioned context | Conservative invalidation costs reviewer time but avoids approval reuse on changed content |
| Deterministic rules plus model proposals | Workflow semantics testable without provider dependence |
| Source-linked interpretation, not exact-quote-only NLI | ContractNLI needs classification over exceptions/multiple spans; exact provenance does not prove the classification |
| Independent audit/deletion recovery authority | Ordinary DB rollback cannot safely reauthorize old decisions or resurrect deleted evidence |
