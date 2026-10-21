# Architecture — C4 levels 1–4

The application components are implemented; deployment and independent evaluation
remain acceptance work. External reviewers/gold/tunnel boxes are target boundaries,
not a claim those resources have been acquired or deployed. Products remain
independently runnable, without application-to-application imports or shared data.

## C4 level 1: system context

```mermaid
flowchart LR
  Operator[Agency catalog specialist] --> SP[ShelfProof content review desk]
  Reviewer[Brand-authorized independent reviewer] --> SP
  Owner[Workspace owner] --> SP
  Source[Approved customer product data] --> SP
  SP -->|approved bounded context| Codex[Installed Codex and configured model service]
  SP -->|explicit reviewed patch download| Workflow[Customer catalog workflow]
  USDA[USDA public record releases] --> Eval[Isolated acquisition and evaluation]
  Eval -->|frozen label-free test facts| SP
```

No arrow publishes to a retailer. Public research facts are not customer approval;
evaluation labels are outside runtime authority. Local hosting and remote model
egress are separate trust boundaries.

## C4 level 2: containers

```mermaid
flowchart TB
  Browser[React TypeScript workbench] --> Access[Cloudflare Access and Tunnel]
  Access --> API[FastAPI and static UI - loopback 8009]
  Local[Authenticated local browser] --> API
  API --> DB[(Dedicated SQLite WAL store)]
  Worker[Serialized durable worker] --> DB
  Worker --> Journal[Independent fsynced usage and incident journal]
  Worker --> Adapter[Restricted provider port]
  Adapter --> CLI[Installed Codex child process]
  CLI --> Service[Authenticated configured model service]
  Acquisition[Explicit bounded acquisition utility] --> Corpus[Frozen local source manifests]
  Corpus --> Evaluator[Isolated evaluator and independent reviewers]
  Evaluator -->|authorized facts only| API
  Evaluator --> Gold[Restricted labels and adjudications]
```

Port 8009 is the implemented loopback default; a temporary owned-fixture stack was
started/stopped on macOS. Windows identity/tunnel qualification remains pending.
Gold isolation needs process/account ACLs, not
merely directory naming. No source fetching, model health call or evaluation occurs
on ordinary startup. Bulk acquisition is not part of the public service.

## C4 level 3: application components

```mermaid
flowchart TD
  Routes[Scoped auth and API] --> Import[Bounded CSV JSON parser]
  Import --> Mapping[Explicit mapping and source normalization]
  Mapping --> Facts[Immutable fact and draft revisions]
  Routes --> Policy[Versioned channel brief and rubric]
  Facts --> Snapshot[Authorized snapshot and egress preview]
  Policy --> Snapshot
  Snapshot --> Orchestrator[Durable reflection controller]
  Orchestrator --> Execute[Version 0 producer]
  Execute --> Check[Deterministic facts coverage and profile checks]
  Check --> Judge[LLM judge in separate context]
  Judge --> Plan[Finding-bound correction plan]
  Plan --> Revise[Constrained regeneration - at most twice]
  Revise --> Check
  Judge --> Select[Deterministic incumbent and stop policy]
  Select --> Review[Human review and exact-version approval]
  Review --> Export[Typed patch and unresolved manifest]
  Orchestrator --> Ledger[Reservations receipts checkpoints and safe diagnostics]
  Operator[Filesystem operator plus owner] --> Recovery[Audited evidence or bounded incident recovery]
  Recovery --> Ledger
```

The selection policy never treats a judge score as factual authority. Source gaps
stop with `needs_data`; a later fault preserves earlier versions. Models cannot
edit facts, change the rubric, add iterations, approve exports or grant egress.

## C4 level 4: implemented code relationships

```mermaid
classDiagram
  class Worker {
    +run_once()
    +_run(task, lease)
    +_judge(task, lease, revision)
    +_invoke(stage, model, context)
  }
  class Store {
    +create_task()
    +claim()
    +_fence()
    +checkpoint(stage, artifact)
    +reserve(attempt)
    +settle(receipt)
    +review(version_hash)
    +export(workspace)
  }
  class CoreModule {
    <<module>>
    +freeze_import()
    +check_draft()
    +weighted_score()
    +select_version()
  }
  class CodexProvider {
    +generate(prompt, schema)
    +last_receipt
  }
  class Lifecycle {
    +create_batch()
    +batch_preview()
    +start_batch()
    +edit()
    +erase_import()
  }
  class Operations {
    +backup()
    +restore()
    +isolate_orphans()
    +reconcile_receipt()
    +accept_incident()
    +resume()
  }
  Store --|> Lifecycle
  Store --|> Operations
  Worker --> Store
  Worker --> CoreModule
  Worker --> CodexProvider
```

Actual package: `apps/shelfproof-api/src/shelfproof_api/` contains `api`, `store`,
`core`, `workflow`, `worker`, `runtime`, `lifecycle`, `operations`, `corpus`,
`validation` and `errors`. Frontend: `apps/shelfproof-web/`; bounded untrusted
contracts: `packages/contracts/src/contracts/shelfproof.py`. Pure core functions
are shown as a module, not imaginary application classes. See the
[implementation map](implementation-notes.md) for consolidation decisions.

## Data ownership and immutable bindings

Workspace -> client-scoped imports -> product source revisions -> fact packs and
drafts -> batch/task snapshots -> attempts and checkpoints -> version/evaluation/
plan lineage -> selected incumbent -> review -> export manifest.

Every evaluation binds version hash, fact hash, profile/rubric revision and task
snapshot. Each plan binds the exact findings and parent version. Approvals bind the
selected text, evidence, policy and authority, not merely a mutable product ID.
Audit/accounting retain minimal hashes after case-content erasure as documented in
[security](permissions-and-security.md) and [recovery](audit-and-recovery.md).

## Execution sequence and failure boundary

1. API validates scope, expected revision and idempotency key, then persists intent.
2. Worker acquires runtime guard/lease and checks current authority plus allowances.
3. Reserve before each invocation; persist even failed/unknown attempts.
4. Validate output, record findings/receipt, checkpoint accepted stage once.
5. Run the bounded state machine; materialize incumbent and terminal reason.
6. Human independently reviews exact current artifacts; explicit patch download only.

Lease loss fences late success *and* failure writes. A restart reuses stage
checkpoints, not fresh counters. Restore creates a new quarantined root, revokes
sessions and leaves old jobs stale. See [audit/recovery](audit-and-recovery.md).

Real child/HTTP and crash/recovery engineering tests exist. Browser responsiveness,
real-model quality and Windows/tunnel deployment need their own actual acceptance
evidence; a healthy API cannot clear those gates.
