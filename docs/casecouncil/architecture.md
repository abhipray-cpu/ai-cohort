# Architecture — C4 levels 1–4

The application components below are implemented; Cloudflare/Windows deployment
and independent expert evaluation remain target boundaries, not accepted deployments.
CaseCouncil's service, database, credentials and evaluator are separate from Days 1–8.
See the [actual module map and deviations](implementation-and-operations.md).
20 October adds [owner-approved irrecoverable incident closure](incident-closure-2026-10-20.md),
a cooperative runtime fence and monotonic campaign call ceiling. These do not
convert unknown receipts into observed usage or independent semantic acceptance.
Alternative-source research adds an explicit isolated IE evaluation Store/factory;
normal UK intake/publication rejects IE. Source reuse and external-model egress are
separate gates. See [source evidence](fspo-source-and-validation-2026-10-19.md).

## Level 1 — system context

```mermaid
flowchart LR
  Handler[Complaint handler] --> CC[CaseCouncil second-review desk]
  Reviewer[Senior human reviewer] --> CC
  Owner[Workspace and policy owner] --> CC
  CC -->|approved redacted context only| Codex[Installed Codex and model-service boundary]
  Sources[Authorized case files] --> CC
  CC -->|explicit reviewed or draft download| Export[Customer's existing case workflow]
  Rights[Rights-cleared evaluation sources] --> Eval[Separate evaluator and expert reviewers]
  Eval -->|label-free packets only| CC
```

FOS acquisition is not a live application feature. Source permission and commercial
validation are outside the model's authority. Nothing sends a final response for a user.

## Level 2 — containers

```mermaid
flowchart TB
  Browser[React and TypeScript review workbench] --> Edge[Cloudflare Tunnel plus Access]
  Edge --> API[FastAPI API and static UI - loopback 8008]
  Local[Authenticated local browser] --> API
  API --> DB[(CaseCouncil SQLite WAL - local disk)]
  API --> DB
  Worker[One durable serialized CaseCouncil worker] --> DB
  Worker --> Journal[Independent fsynced usage-authority journal]
  Worker --> Port[Restricted structured provider adapter]
  Port --> CLI[Installed Codex process]
  CLI --> Model[Configured authenticated model service]
  Eval[Authorized local evaluation process] --> Gold[Restricted gold, manifests and reports]
  Eval -->|label-free packets via same Store and Controller ports| Worker
```

API/worker are separate local processes under a restricted Windows service identity.
Only the UI/API are eligible for tunnel ingress. No public model, database, artifact
directory, debug server or worker endpoint. Cloudflare identity is additional to,
not a substitute for, application authorization. Local-host access also authenticates.

The runtime receives extracted/redacted permitted evidence, not evaluator originals
containing decisions. Separate directories alone are not a security boundary:
service-account ACLs and disabled/audited model tools must enforce the intended separation.

## Level 3 — application components

```mermaid
flowchart TD
  Routes[Scoped API and sessions] --> Intake[Bounded document intake and extraction]
  Intake --> Revisions[Immutable sources, redaction and evidence coverage]
  Routes --> Policy[Versioned role, consensus and egress policy]
  Revisions --> Snapshot[Canonical analysis snapshot]
  Policy --> Snapshot
  Snapshot --> Controller[Durable debate controller and resource grants]
  Controller --> Roles[Three isolated proposal contexts]
  Roles --> Validator[Schema, reference and quote validation]
  Validator --> Critic[Non-voting structured critic]
  Critic --> Revision[At most one proposal revision cycle]
  Revision --> Registry[Frozen candidate registry]
  Registry --> Ballots[Three structured blind ballots]
  Ballots --> Consensus[Deterministic quorum and blocker engine]
  Consensus --> Synthesis[Bounded synthesis with immutable decision fields]
  Synthesis --> Review[Human review and current-revision export]
  Controller --> Audit[Transactional audit and call receipts]
  Review --> Audit
  Operator[Filesystem operator and workspace owner] --> Recovery[Verified reconciliation or bounded incident acceptance, then separate resume]
  Recovery --> Guard[Exclusive cooperative runtime guard and store-wide liabilities]
  Guard --> Journal[Independent incident and cumulative-call authority]
  Recovery --> Audit
  Recovery --> Controller
```

If revision is unnecessary, the controller freezes validated initial proposals.
Provider output cannot mutate policy, choose its role, change permissions, fabricate
ballots or declare consensus. Mechanical validators cannot prove semantic truth;
critic findings and independent human acceptance remain distinct layers.

## Level 4 — implemented code relationships

```mermaid
classDiagram
  class Controller {
    +once()
    +process(job)
    +generate(job, stage, model, snapshot, extra)
  }
  class Store {
    +claim(lease)
    +fenced(db, job, context)
    +reserve(job, stage, prompt_hash, timeout)
    +settle(attempt, receipt)
    +checkpoint(job, stage, value)
    +review(actor, job, value, key)
    +reconcile_attempt(actor, attempt, head, evidence, reference, key)
    +close_incident(actor, attempt, head, reason, isolation, acknowledgement, key)
    +resume_job(actor, job, packet_hash, head, wall_seconds, reason, key)
  }
  class AuditedProvider {
    +generate(prompt, schema)
    +last_receipt
  }
  class EvidenceModule {
    +extract(id, name, raw)
    +evidence_for(sources)
    +validate_citations(citations, evidence)
  }
  class ConsensusModule {
    +registry(proposals, snapshot)
    +aggregate(issues, registry, ballots, blockers)
  }
  class JournalModule {
    +append(db, path, event)
    +assert_current(db, path)
  }
  class RecoveryModule {
    +checked_evidence(attempt, evidence)
    +reconcile_attempt(store, actor, attempt, head, evidence, reference, key)
    +close_incident(store, actor, attempt, head, reason, isolation, acknowledgement, key)
    +resume_job(store, actor, job, packet_hash, head, wall_seconds, reason, key)
  }
  class RuntimeGuard {
    +runtime_guard(root)
  }
  class CampaignModule {
    +limit_store_calls(store, actor, workspace, ceiling, reference)
    +summarize_replay(selected_ids, results)
  }
  Controller --> Store
  Controller --> AuditedProvider
  Controller --> EvidenceModule
  Controller --> ConsensusModule
  Controller --> RuntimeGuard
  RecoveryModule --> RuntimeGuard
  CampaignModule --> JournalModule
  Store --> EvidenceModule
  Store --> JournalModule
  Store --> RecoveryModule
  RecoveryModule --> JournalModule
```

Implemented modules under `apps/casecouncil-api/src/casecouncil_api/`: `api`,
`store`, `controller`, `consensus`, `evidence`, `pdf_worker`, `runtime`, `worker`,
`journal`, `backup`, `evaluation`, `recovery`, `verification`. Auth/audit are in Store/API; roles and synthesis
in Controller. `EvidenceModule`, `ConsensusModule`, `RecoveryModule` and `JournalModule` denote
Python modules/functions, not additional classes. Sources and packets are immutable
SQLite rows/BLOBs. Contracts live in `packages/contracts`, UI in `apps/casecouncil-web`.

## Execution and failure sequence

```mermaid
sequenceDiagram
  actor User
  participant API
  participant Store
  participant Worker
  participant AI as Restricted provider
  User->>API: authorize exact snapshot and bounded run
  API->>Store: commit job, resource grant and audit
  API-->>User: accepted job ID, not a completed decision
  Worker->>Store: claim leased job and validate current context
  loop bounded controller-owned stages
    Worker->>Store: reserve call and persist attempt identity
    Worker->>AI: permitted role context and strict schema
    AI-->>Worker: untrusted structured output or explicit failure
    Worker->>Store: validate, settle receipt and fenced checkpoint
  end
  Worker->>Store: deterministic consensus and draft packet
  User->>API: review exact packet revision
  API->>Store: recheck authority/currentness, commit review and audit
  API-->>User: explicit local export, no external send
```

No database transaction spans parsing, inference or human waiting. Checkpoints make
restart economical, not exactly-once inference: a process can die after model usage
but before checkpoint. Reserve/receipt reconciliation retains that ambiguity.
Lease loss is typed and handled in both execution and error-recording paths.
Changed evidence, policy, authority, cancellation or restore epoch prevents stale
publication. See [recovery](audit-and-recovery.md) and [operations](operations.md).
