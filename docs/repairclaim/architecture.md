# Architecture — C4 levels 1–4

The API, worker, ingestion, registry, monitoring, packets and React UI are
implemented. Deployment/evaluation nodes below still describe target qualification,
not an installed Windows/tunnel/evaluation environment. See the
[actual implementation map](implementation-notes.md) and [status](implementation-status.md).
The design supports all [twelve requirements](functional-requirements.md) without depending on
an experimental provider. Product API/web and shared contracts are additive to the
monorepo. No import from another product's application package or reuse of its DB.

## C4 level 1: system context

```mermaid
flowchart LR
  Owner[Vehicle owner / household case owner] --> RC[RepairClaim]
  Helper[Explicitly invited family helper] --> RC
  RC -->|bounded authorized reads| Official[Registered official public sources]
  RC -->|explicit minimized analysis context| Provider[Authorized analysis provider]
  RC -->|approved downloadable packet| Owner
  Owner -->|manual submission outside app| Recipient[Manufacturer / dealer]
  Recipient -->|response supplied by user| Owner
  Reviewer[Independent evaluation reviewer] --> Eval[Isolated evaluation environment]
  Eval -->|label-free permitted inputs| RC
```

No RepairClaim-to-recipient arrow: manual submission is a deliberate first-release
boundary. A helper cannot grant their own authority or approve an outbound packet.
Official-source evidence is untrusted content, not instructions or consumer consent.

## C4 level 2: containers and deployment boundary

```mermaid
flowchart TB
  Browser[Mobile / desktop React UI] --> Edge[Protected Cloudflare Tunnel and Access pilot gate]
  Edge --> API[FastAPI static UI and API - loopback port 8011 proposed]
  Local[Authenticated local browser] --> API
  API --> DB[(Dedicated SQLite WAL database)]
  API --> Files[Private encrypted documents and derivatives - opaque IDs and SHA256 manifests]
  Worker[One durable worker and scheduler] --> DB
  Worker --> Sandbox[Restricted PDF image and OCR child processes]
  Sandbox --> Files
  Worker --> Fetch[Allowlisted source-fetch adapter]
  Fetch --> Sources[Public official endpoints]
  Worker --> Ports[Typed analysis and drafting ports]
  Ports --> Adapter[Installed Codex adapter - proposed generation integration]
  Adapter --> Service[Configured authenticated model service]
  Ports -. optional evaluated adapter .-> Decision[Separate decision provider]
  Worker --> Files
  Backup[Restricted encrypted backup process] --> DB
  Backup --> Files
  Gold[Separate evaluator account and label store] --> Harness[Offline evaluation harness]
  Harness -->|authorized test cases only| API
```

Single Windows host is a bounded pilot target, not highly available SaaS. SQLite is
chosen for one writer, serialized expensive work and modest concurrency; use a
scoped repository with household keys on every query and constraint. There is no
database RLS claim. Measure lock/load behaviour; if capacity fails, re-plan storage
before launch instead of silently dropping durability or scope checks. Do not run
all portfolio workloads concurrently without measured host admission limits.

The app has its own authentication and household grants; Cloudflare is an extra
pilot gate, not the identity or authorization model. Private files are never served
as static assets. No credentials/source/model calls on basic startup or health checks.

## C4 level 3: application components

```mermaid
flowchart TD
  Routes[Authenticated scoped API] --> Intake[Upload quarantine / bounded parser]
  Intake --> Facts[Attributed fact revisions]
  Routes --> Grants[Household grants consent and deletion epoch]
  Facts --> Freeze[Immutable case snapshot]
  Freeze --> Controller[Bounded casework controller]
  Registry[Reviewed source and programme registry] --> Retrieve[Candidate retrieval]
  Retrieve --> Controller
  Controller --> Conditions[Condition evaluator and conflict gate]
  Conditions --> Clarify[Next useful evidence request]
  Conditions --> Draft[Evidence-bound draft and independent checks]
  Draft --> Review[User review and exact-artifact approval]
  Review --> Packet[Redacted render / approved download]
  Routes --> Responses[Response and outcome attribution]
  Responses --> Facts
  Scheduler[Consent-aware scheduler] --> Revisions[Capture compare and materiality review]
  Revisions --> Registry
  Revisions --> Impact[Invalidate / rematch / explain changes]
  Impact --> Inbox[Deduplicated in-app notifications]
  Controller --> Ledger[Checkpoints attempts and audit]
  Impact --> Ledger
  Grants --> Controller
  Grants --> Scheduler
  Grants --> Packet
```

Mandatory conditions are evaluated deterministically when computable. Semantic
matching is advisory; source ambiguity remains a review obligation. A changed
source, fact, grant, consent or renderer invalidates dependent approval as needed.

## C4 level 4: implemented code relationships

The Store facade inherits feature mixins to share one scoped SQLite transaction
boundary. Core evaluation and document primitives remain separate modules.

```mermaid
classDiagram
  class Store {
    +authenticate(token)
    +snapshot(token, case_id)
    +replace_facts(token, case_id, revision, facts)
    +delete_case(token, case_id, revision)
  }
  class FeatureStore {
    +capture_source(source_id, url, bytes, parsed)
    +activate_programme(programme)
    +start_investigation(token, case_id, revision, key)
    +claim_job()
    +checkpoint_job(item, result)
    +commit_job(item, result, status)
  }
  class PacketMixin {
    +create_packet(token, case_id, job_id, recipient)
    +queue_packet(token, packet_id)
    +render_packet(token, packet_id, parser)
    +approve_packet(token, packet_id, fingerprint)
    +download_packet(token, packet_id)
  }
  class ContinuityMixin {
    +set_monitoring(token, vehicle_id, cases, ttl)
    +rematch_monitoring()
    +record_response(token, case_id, document_id, key)
    +record_outcome(token, case_id, event, key)
  }
  class PrivacyMixin {
    +apply_erasure_ledger()
    +export_case(token, case_id)
    +erase_account(token, confirmation)
    +maintenance()
  }
  class RestrictedParser {
    +run(operation, bytes, filename)
  }
  class LocalCodexProvider {
    +generate(prompt, schema)
  }
  class worker_module {
    +run_once(store, parser, provider)
  }
  class core_module {
    +evaluate_search(snapshot, programmes)
    +next_question(assessment)
    +verify_anchor(anchor, pages)
  }
  FeatureStore <|-- Store
  PacketMixin <|-- FeatureStore
  ContinuityMixin <|-- FeatureStore
  PrivacyMixin <|-- FeatureStore
  worker_module --> Store
  worker_module --> RestrictedParser
  worker_module --> core_module
  worker_module --> LocalCodexProvider : optional advisory port
  PacketMixin --> RestrictedParser
```

Implemented ownership: `apps/repairclaim-api/src/repairclaim_api/` (API, auth, store,
ingestion, coverage, casework, packets, monitoring, worker, operations),
`apps/repairclaim-web/` (consumer UI),
`packages/contracts/src/contracts/repairclaim.py` (bounded shared schemas),
`tests/test_repairclaim_*.py` and frontend domain tests. These modules and the React
app exist; interactive browser verification remains open. The public shared
LocalCodexProvider adapter is optional. Port 8011 is the development default and
the launcher checks occupancy before starting. Windows and Cloudflare nodes remain
deployment targets. See actual module names and design deltas in implementation notes.

## Key sequences and consistency

Upload → quarantine → safe extraction → user confirmation → immutable snapshot →
retrieval → condition findings → focused clarification or draft → independent checks
→ rendered disclosure preview → owner approval → authorized download.

Source capture → reviewed material change → invalidate impacted assessments and
approvals → consent check → durable rematch → source-linked change notification.
Invalidation precedes notification completion; failures leave stale outputs blocked.
Household scope, deletion epoch, expected revision and lease token are rechecked
at writes and downloads, not just at the beginning of a long job.
