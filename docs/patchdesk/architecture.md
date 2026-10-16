# Architecture

Status: implemented local pilot; Windows/Cloudflare portions remain deployment targets. C4 follows the [C4 model](https://c4model.com/diagrams). Separate API/worker/store and installed Codex adapter run locally on port 8003; [validation](implementation-validation-2026-10-15.md) records actual observations.

16 October assessment: [larger validation](validation-2026-10-16.md) blocks release. Current fixed selection represents only 69.15% of captured provider instance/advisory pairs. The bounded scheduler protects the host but is not a completeness mechanism. Bounded continuation/unassessed-identity reporting and safe structured-plan diagnostics are next architecture work, not implemented completion claims.

## C4 level 1 — system context

```mermaid
flowchart LR
  engineer[Agency maintenance engineer] -->|project, evidence, maintenance question| pd[PatchDesk]
  reviewer[Authorized reviewer] -->|review, export, exact publication approval| pd
  pd -->|approved package identity queries| public[OSV, npm registry, optional threat/data feeds]
  pd -->|scoped snapshot reads and approved issue publication| github[Configured GitHub repositories]
  pd -->|minimized authorized evidence through installed CLI| model[Codex CLI and remote model service]
  pd -->|reviewed maintenance pack| engineer
  reviewer -->|human delivery and maintenance coordination| client[Client stakeholders]
```

PatchDesk does not contact clients, deploy patches or execute application code. Source retrieval and inference require network access. Private-context egress to the model and package-query egress to public providers are separate permissions.

## C4 level 2 — containers

```mermaid
flowchart TB
  browser[React/TypeScript reviewer browser] -->|HTTPS| edge[Cloudflare Access and Tunnel: target]
  edge -->|loopback HTTP port 8003| api[FastAPI API and static web host]
  api --> db[(Product SQLite WAL: cases, snapshots, jobs, reports, approvals, outbox)]
  worker[Single orchestration worker with bounded async I/O] --> db
  api --> vault[Host-protected connector secrets]
  worker --> vault
  worker --> cli[Installed Codex subprocess adapter]
  cli --> inference[Remote model inference]
  worker -->|approved read requests| sources[Official public APIs and authorized repository reads]
  api -->|explicit approved dispatch only| issues[Configured GitHub Issues API]
  supervisor[Windows scheduled tasks: target] --> api
  supervisor --> worker
```

API/worker/database are local service containers in the C4 sense, not Docker requirements. SQLite holds immutable source payloads/export records transactionally to avoid a separate snapshot-file publication race. Large optional corpus/log files remain outside it and need separate retention/backup decisions. One active investigation initially protects the old laptop; parallelism is bounded I/O inside that run, not unbounded workers or model processes.

## C4 level 3 — orchestration components

```mermaid
flowchart TB
  queue[(Durable run queue)] --> controller[Lease, deadline, counter controller]
  controller --> inventory[Manifest/lockfile parser and graph builder]
  inventory --> planner[Typed capability planner]
  planner --> registry[Versioned trusted tool registry]
  registry --> router[Capability router: eligibility and deterministic rank]
  router --> policy[Project, permission, egress and health gate]
  policy --> scheduler[DAG scheduler with bounded concurrency]
  scheduler --> readers[Scoped read adapters]
  readers --> writer[Result validation and immutable snapshot writer]
  writer --> reducer[Deterministic identity/conflict reducer]
  reducer --> planner
  reducer --> report[Cited plan generator and independent validators]
  report --> review[Revision-bound review/export]
  review --> approval[Exact destination/body approval]
  approval --> outbox[Transactional publication outbox]
  outbox --> publish[Rechecked scoped issue publisher]
  controller --> preview[Deterministic partial preview]
  writer --> preview
  policy --> audit[(Safe policy/routing/action events)]
  scheduler --> audit
  reducer --> audit
  publish --> audit
```

The planner sees capability descriptions and safe metadata, not credentials or arbitrary code. The router selects concrete adapters; the scheduler owns execution. A registry revision is pinned for reproducibility, but live permission revocation/adapter disablement always takes precedence at dispatch. The publisher is an effectful boundary, not another automatically parallelized lookup.

## C4 level 4 — implemented code boundaries

```mermaid
classDiagram
  class ToolDescriptor {
    +id
    +version
    +capabilities
    +provider
    +packages
    +permission
    +enabled
    +priority
    +schema_version
  }
  class Registry {
    +register(descriptor)
    +snapshot()
    +set_enabled(name, enabled)
    +route(request, context, pinned)
  }
  class Investigation {
    +investigate()
    +batch(requests)
    +generate(model, context)
    +report()
  }
  class Reconciliation {
    +reconcile(inventory, results)
    +validate_references(report, snapshots)
    +validate_narrative(value, findings)
  }
  class Scheduler {
    +run(nodes, execute, save)
  }
  class Sources {
    +execute(adapter, request, context)
    +repository(policy, ref)
  }
  class Transport {
    +request(url, data, retry)
  }
  class StructuredProvider {
    <<interface>>
    +generate(prompt, schema) StructuredGeneration
  }
  class Store {
    +claim(runId)
    +reserve(runId, counter)
    +checkpoint(nodeId, result)
    +finish(runId, lease, payload, reason)
    +review(actor, objectId, value)
    +export(actor, objectId)
  }
  class Publisher {
    +draft(actor, report_id, title)
    +approve(actor, intent_id, approval)
    +dispatch(actor, intent_id)
    +reconcile(actor, intent_id)
  }
  Registry --> ToolDescriptor
  Investigation --> Registry
  Investigation --> Scheduler
  Investigation --> Store
  Investigation --> Reconciliation
  Investigation --> StructuredProvider
  Scheduler --> Sources
  Sources --> Transport
  Publisher --> Store
  Publisher --> Transport
```

Actual placement: `apps/patchdesk-api/src/patchdesk_api/{api,worker,store,inventory,registry,scheduler,adapters,reconcile,corpus,common,reports,publisher,backup}.py`, `apps/patchdesk-web/`, strict contracts in `packages/contracts/src/contracts/patchdesk.py`, and `tests/test_patchdesk*.py`. Router/policy are functions within registry/store/worker; reconciliation is functional, not an extra class hierarchy. `StructuredProvider` is the shared protocol. Live issue dispatch is an explicit authenticated API call, not an automatic background worker action.

Existing shared code to evaluate for reuse: [StructuredProvider](../../packages/agent-core/src/agent_core/provider.py), [LocalCodexProvider](../../packages/agent-core/src/agent_core/codex_local.py), [observability events](../../packages/observability/src/observability/events.py), and [service runner](../../scripts/run_product_service.py). Their existence does not make them PatchDesk-compatible without additive integration/tests. Reuse the audited isolated provider pattern with remaining-deadline propagation; independently verify that native runtime tools cannot bypass scoped application adapters. No earlier product's database/orchestrator may be imported.

## Dynamic sequence — bounded parallel investigation

```mermaid
sequenceDiagram
  participant U as Engineer
  participant A as API / Store
  participant W as Orchestration worker
  participant P as Policy / Router
  participant O as OSV adapter
  participant N as Release adapter
  participant T as Threat adapters
  U->>A: Start project-scoped run with input hash
  W->>A: Claim lease, pin registry, reserve budgets
  W->>P: Request eligible capabilities
  P-->>W: Scoped adapters or explicit denial/unavailable
  par Independent approved reads
    W->>O: Batched exact package/version lookup
    O-->>A: Validated advisory checkpoints
  and
    W->>N: Approved package metadata lookup
    N-->>A: Validated release checkpoints
  end
  W->>A: Normalize advisory aliases, derive CVE identities
  W->>T: Parallel bounded CVE enrichment after dependencies ready
  T-->>A: Dated signals or explicit gaps
  W->>A: Deterministic conflict reduction, cited draft, partial status
  U->>A: Review exact revision and export
  Note over U,A: Optional publication requires a separate exact approval
```

## States and persistence

```mermaid
stateDiagram-v2
  [*] --> queued
  queued --> running: claim and validate input scope
  running --> completed: required coverage and validation satisfied
  running --> partial: cap, source gap, conflict or provider failure
  running --> cancelled: cancellation observed
  running --> failed: unrecoverable internal/storage error
  partial --> queued: explicit bounded new grant
  running --> running: fenced crash recovery with original deadline
```

Node states: pending, ready, running, succeeded, partial, failed, skipped, denied, cancelled. A dependent node runs only when its declared prerequisites are satisfied; partial results must be explicitly accepted by its contract, not treated as success automatically. Run/report/review/publication states are separate.

Actual tables: users, sessions, login_attempts, projects, memberships, objects, runs, events, settings, resume_keys and publications. Client is a project field. Immutable `objects` contain input/snapshot/report/export JSON; run JSON holds conversation messages, registry snapshot, per-node results/counters; settings holds heartbeat and disabled registry. Connector credentials remain outside exported/restorable report data; password/session hashes are in the protected database. Every artifact lookup enforces project scope.

Parallel tasks never share a SQLite connection. A serialized short transaction writer or per-operation connections prevent long network work under database locks. Persist results independently and reduce by stable identity/order, not arrival order. A failed sibling cannot erase successful nodes. Lease/node fencing and pre-call counter reservations prevent stale saves and hidden duplicate attempts.

## Architecture decisions

| Decision | Reason / consequence |
| --- | --- |
| One run, bounded parallel I/O | Fits old host; graph/provider quotas still constrain throughput |
| Capability-based planner plus deterministic router | Makes provider selection observable and permission-constrained |
| Trusted registry manifests, revision pinning | Dynamic availability without arbitrary plugin/code execution |
| Deterministic evidence/constraint reconciliation | Natural-language confidence cannot settle range/identity conflicts |
| Local persistence, minimized authorized egress | Local service hosting does not imply private/offline inference |
| Explicit outbox publication | Remote writes are auditable; ambiguous remote outcomes need reconciliation |
| No project installation/execution | Avoids untrusted scripts and heavy runner requirements on Windows laptop |

See [permissions](permissions-and-security.md), [orchestration](orchestration.md) and [operations](operations.md) for enforceable limits and acceptance gates.
