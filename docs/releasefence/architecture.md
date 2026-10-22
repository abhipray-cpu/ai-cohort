# Implementation architecture — C4 levels 1–4

Diagrams describe component boundaries, not qualified deployed infrastructure. Other cohort products
are external workloads reached through explicit adapters/HTTP; no imports from
their application internals or reuse of their databases/secrets/grants.

MLflow and LangSmith nodes are **alternative profiles**, not three simultaneously
enrolled destinations. Each organization retains the two-backend cap. The chosen
policy profile is bound into approval scope; see [ADR 0002](adr-0002-self-hosted-mlflow.md).

## C4 level 1: system context

```mermaid
flowchart LR
  Owner[Customer release owner] --> RF[ReleaseFence SaaS]
  OnCall[Customer on-call operator] --> RF
  Runtime[Customer agent infrastructure] -->|scoped telemetry and runtime attestations| RF
  RF -->|authorized bounded commands| Runtime
  RF -->|selected legacy profile| LS[Customer-owned LangSmith]
  RF -->|selected OSS profile| MF[Customer-owned MLflow]
  RF -->|filtered spans and read-back| PX[Customer-owned Arize Phoenix]
  RF --> Notify[Approved incident webhook]
  CI[Customer CI] -->|scoped manifest registration| RF
  RF --> Evidence[Operator evidence export]
```

Observe-only mode has no deployment-command capability. Customer inference remains
in customer infrastructure. Optional incident summarization uses only approved
redacted evidence through the installed-Codex port and cannot actuate a change.

## C4 level 2: containers and trust boundaries

```mermaid
flowchart TB
  UI[React release desk] --> Edge[Protected HTTPS entry]
  Edge --> API[FastAPI control plane - default loopback 8010]
  API --> DB[(Dedicated PostgreSQL tenant store)]
  Engine[Policy and incident worker] --> DB
  Delivery[Notification and command outbox worker] --> DB
  Delivery --> Webhook[Allowlisted webhook destination]
  Connector[Customer Python connector] -->|outbound enrollment-bound polling| API
  Connector --> Router[Enrolled session router and agent runtime]
  Router --> Stable[Immutable stable bundle]
  Router --> Candidate[Immutable candidate bundle]
  Instrumentation[TraceBridge or owner-managed collector] -->|OTLP metadata| API
  Engine -->|legacy profile export and read-back| LS[Authorized LangSmith endpoint]
  Engine -->|OSS profile export and read-back| MF[Authorized MLflow endpoint]
  Engine -->|durable filtered export and read-back| PX[Authorized Phoenix endpoint]
  Connector -->|attestations and outcome events| API
```

PostgreSQL owns transactions, RLS-enforced tenant records, durable work/outbox and
decision evidence. Raw third-party trace storage remains in customer backends;
ReleaseFence stores minimal normalized events/aggregates and trace references.
No Redis/Kafka dependency is mandatory initially. Windows/WSL2 or external managed
PostgreSQL feasibility must be measured; no silent SQLite substitution for SaaS.

## C4 level 3: control-plane components

```mermaid
flowchart TD
  Routes[Scoped API and auth] --> Enrollment[Connector capability enrollment]
  Routes --> Releases[Immutable release and policy registry]
  Intake[Bounded OTLP and event intake] --> Normalize[Privacy mapping deduplication and bounded rejection]
  Normalize --> Windows[Watermarks coverage and metric windows]
  Windows --> Detector[Loop and release failure detection]
  Windows --> Analyzer[Deterministic canary evidence analysis]
  Detector --> Incidents[Incident state and durable notification outbox]
  Analyzer --> Machine[Rollout state machine]
  Releases --> Machine
  Enrollment --> Machine
  Machine --> Authz[Exact-target approval and capability check]
  Authz --> Commands[Signed idempotent command outbox]
  Commands --> Verify[Read-back attestations and fresh-session probes]
  Verify --> Machine
  Machine --> Audit[Append-only decision evidence]
  Routes --> Views[Metric release incident and audit queries]
```

## C4 level 4: implemented code relationships

```mermaid
classDiagram
  Store --|> Operations
  Store --|> Integrations
  Engine --> Store : scan / deliver
  Integrations --> Backend : export / verify
  Operations --> Router : signed Command / Attestation
  Connector --> Router : apply / attest
  Router --> HTTPBundles : loaded-bundle probe
  Runtime --> Router : atomic begin_task / end_task
  Runtime --> Spool : durable lifecycle events
  HTTPGateway --> Runtime : task context
  HTTPGateway --> HTTPBundles : invoke selected release
  TraceBridge --> TelemetryNormalizer : bounded OTLP
  Operations --> CanaryAnalyzer : core.analyze
```

`HTTPGateway`, `TelemetryNormalizer` and `CanaryAnalyzer` are diagram labels for
`gateway.create_gateway`, `telemetry.normalize_otlp` and `core.analyze`, not classes.
The module map and concrete entrypoints are in implementation-notes.md.

## Deployment and failure sequence

The future lab control plane is independently runnable on the Windows laptop;
only authenticated application routes pass through Cloudflare. Database, collector,
Phoenix, admin ports and Codex are not publicly exposed. No commercial availability
claim follows from a tunnel. A commercial service needs its own availability,
restore, isolation, capacity and support qualification.

If control-plane/telemetry connectivity is lost, connectors keep the last committed
routing configuration (which can still include canary traffic), reject expired new
commands and buffer only
bounded telemetry. They do not autonomously expand a canary. A requested rollback
without current runtime evidence remains unverified, not successfully completed.
Approval expiry is not a runtime traffic lease and does not itself change routing
or kill in-flight inference. Operationally monitor this exposure; no autonomous
offline rollback or forced task cancellation is claimed.
