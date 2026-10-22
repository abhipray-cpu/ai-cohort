# ADR 0002 — MLflow/Phoenix self-hosted qualification profile

22 October 2026. Accepted by the user: choose the recommended option and run E2E.
This supersedes the mandatory-LangSmith requirement **only for the new named
profile**. It does not turn a LangSmith test into a pass or rewrite old receipts.

## Decision

Use upstream **MLflow 3.17.2** alongside **Phoenix 20.23.0** as actual independent
trace destinations. Keep ReleaseFence's PostgreSQL state, privacy filter, metrics,
alerts, canary decisions and signed runtime controls. No tracing platform is
reimplemented, rebranded or maintained as a private fork. The dependencies run in
separate environments; MLflow is not installed into the monorepo service venv.

| Policy profile | Required actual backends |
| --- | --- |
| `langsmith-phoenix-v1` | LangSmith and Phoenix; backward-compatible API default |
| `mlflow-phoenix-v1` | MLflow and Phoenix; explicit new UI default |

`Policy.trace_profile` accepts only these names. The chosen profile is part of the
stored policy and exact approval scope; it cannot silently change after approval.
Old policies missing this field retain the LangSmith/Phoenix requirement. This
does **not** lower sample floors, statistical bounds, coverage, cost completeness,
freshness, privacy, backlog or signed-control checks. Missing either selected
backend/release proof or an incomplete export holds analysis. Unknown profiles fail.
The organization still has a two-backend cap: no implicit replacement/deletion or
three-vendor migration is installed. Existing organizations need an explicitly
planned configuration migration or a newly provisioned scope, not relabelled data.

## Why this option

- MLflow accepts standard OTLP/HTTP and has SQL-backed server/UI/API operation;
  unlike the full Langfuse deployment, this trace deployment does not require
  separate ClickHouse, Redis and blob-storage services.
- Its upstream code is Apache-2.0 licensed. License/NOTICE obligations remain;
  no ownership or trademark claim is made. Phoenix remains ELv2, customer-owned
  infrastructure, not an unrestricted hosted/managed resale component.
- A simpler topology is a reason to test it on the old laptop, **not** evidence
  that its RAM/CPU, Windows service configuration or soak requirements have passed.
- Langfuse remains a credible alternate adapter, but adding it is outside this
  implementation. Opik's local and production deployments are distinct options.

Primary sources checked on 22 October:
[MLflow OTLP](https://mlflow.org/docs/latest/genai/tracing/opentelemetry/ingest/),
[server](https://mlflow.org/docs/latest/self-hosting/architecture/tracking-server/),
[authentication](https://mlflow.org/docs/latest/self-hosting/security/basic-http-auth/),
[license](https://github.com/mlflow/mlflow/blob/master/LICENSE.txt),
[Langfuse sizing](https://langfuse.com/self-hosting/configuration/scaling),
[Phoenix license](https://raw.githubusercontent.com/Arize-ai/phoenix/main/LICENSE).
Those documents establish feasibility; actual pinned server tests establish the
specific integration evidence. Latest documentation is not a release checksum.

## Adapter and authentication contract

MLflow export uses `/v1/traces`, OTLP protobuf and the required
`x-mlflow-experiment-id`. Credentials are a scoped `username:password` pair, stored
encrypted and sent using HTTP Basic authentication over HTTPS (or the existing
explicit loopback-only lab exception). The project field is a numeric experiment
ID, **not** its display name. The connection UI labels that distinction.

Read-back uses the pinned server's `/api/3.0/mlflow/traces/get?trace_id=tr-<hex>`.
The response's protobuf-JSON byte fields are base64, unlike OTLP's hexadecimal
JSON identity representation. Check experiment scope, original trace/span IDs,
parent and release metadata; a successful status/empty response cannot qualify.
Read-back failure stays visible and follows the existing durable retry/dead-letter
path. Do not infer serving adoption from a trace upload.

Qualification creates separate non-admin users/experiments, deny-by-default
permissions, explicit workspace USE and experiment EDIT grants. Credentials are
not shared between tenants or published in reports. Read and write cross-scope
denial is tested, not assumed from experiment names. The test MLflow uses SQLite;
ReleaseFence itself continues to use real PostgreSQL with non-bypass RLS roles.

Lifecycle usage remains the cost authority. MLflow price-table estimates are not
subscription bills. Unknown per-call Codex USD cost stays unknown and blocks an
ordinary cost-qualified promotion. No local-model invoice or zero-cost claim is
manufactured to make a canary green.

## Operations and qualification

Pinned optional backend requirements are in
`infra/releasefence-observability/`. Install them into separate venvs. The owned
lab helper `scripts/releasefence_backend_lab.py` binds both servers to loopback,
disables vendor telemetry/assistant features, creates isolated state and explicit
MLflow authentication, and stops only its own processes. It is an acceptance
fixture, **not** a production deployer or a default `make up` side effect.

For a customer deployment: supply an explicit backend service account, restrict
experiment/workspace permissions, protect both server/UI paths, configure the
dedicated SQL/artifact stores, backup and restore, and supervise the processes.
Do not expose an unauthenticated vendor service through a tunnel. Windows ACLs,
supervision, proxy policy and resource capacity still need actual host evidence.

See [OSS acceptance](oss-validation-2026-10-22.md) for measured results and open
gates. The previous [validation report](real-data-validation.md) is retained as
historical evidence, including its failures and earlier 18-call budget checkpoint.
