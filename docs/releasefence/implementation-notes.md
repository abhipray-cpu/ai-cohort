# ReleaseFence implementation and operating guide

21–22 October 2026. This describes executable code, not a claim of production acceptance.
Use [status](implementation-status.md) for measured checks and open gates.

## Module map

| Concern | Implementation |
| --- | --- |
| Finite wire contracts | `packages/contracts/src/contracts/releasefence.py` |
| Canonical release IDs, metrics, fixed-look analysis, loop rules | `releasefence_api/core.py` |
| PostgreSQL installation, FORCE RLS, users/sessions, tenant records, CI grants | `store.py` |
| Independent approvals, staged control, signed read-back, recovery, incident closure | `service.py` |
| Incidents, HMAC notification outbox, finite leases/retries/dead letters | `engine.py` |
| Encrypted backend settings, durable trace export, bounded owner replay | `integrations.py` |
| MLflow/Phoenix read-back, legacy LangSmith UUID mapping and named profile gates | `backends.py` |
| Privacy-minimal OTLP JSON/protobuf, dedicated OpenTelemetry SDK provider | `telemetry.py` |
| Authenticated browser/machine HTTP APIs and static UI | `api.py` |
| Completed-cycle observer readiness, safe per-tenant error status | `worker.py` |
| Crash-safe customer routing, command dedup, session retirement, signed counters | `connector.py` |
| Durable customer lifecycle spool, keyed tool fingerprints, task context | `sdk.py` |
| Real customer bundle HTTP dispatch and loaded-bundle probes | `gateway.py` |
| Outbound-only customer connector process | `client.py` |
| Explicit install/key generation, schema-scoped backup, new quarantined restore | `operations.py` |
| Operator desk, roles, unknown states, recovery controls | `apps/releasefence-web/src` |

Python files above live in `apps/releasefence-api/src/releasefence_api`.
Production application code does not import another cohort product's internals.

## Install and start the control plane

Prerequisites: Python 3.12+, Node compatible with Vite 7, and a dedicated PostgreSQL
database. Docker is not mandatory. Database/schema installation is explicit and
requires an administrative connection; runtime refuses superuser/BYPASSRLS roles.

```sh
.venv/bin/python -m pip install -e '.[dev]'
npm --prefix apps/releasefence-web ci
.venv/bin/python -m releasefence_api.operations keys var/releasefence-private-keys.json
```

The keys command creates a **new**, owner-readable file and refuses overwrite.
Keep it out of Git and backup it separately from database snapshots. On Windows,
use `.venv/Scripts/python.exe` and apply appropriate service-account ACLs; Unix
mode bits are not a Windows ACL guarantee.

Set `RELEASEFENCE_ADMIN_DATABASE_URL` and a newly generated, at least 24-character
`RELEASEFENCE_DATABASE_PASSWORD` in the operator shell, then run:

```sh
.venv/bin/python -m releasefence_api.operations install
```

This creates the `releasefence` schema and `releasefence_app` role. It does not
overwrite an existing installation or create a vendor account. Keep administrative
credentials out of the API/worker environment. Copy the ReleaseFence section of
`.env.example` into your private configuration and set:

- `RELEASEFENCE_DATABASE_URL`: the non-bypass runtime role, correct database and
  URL-encoded password; not the administrative DSN.
- `RELEASEFENCE_ENCRYPTION_KEY` / `RELEASEFENCE_SIGNING_KEY`: the generated values.
- `RELEASEFENCE_USERNAME` / `RELEASEFENCE_PASSWORD`: explicit initial platform
  administrator credentials, password at least 12 characters. No default account.
- `RELEASEFENCE_ORIGIN`: exact browser origin, loopback `http://127.0.0.1:8010` in
  development or your protected HTTPS origin later.
- `RELEASEFENCE_SCHEMA=releasefence`; lab-loopback is **off** for Internet-facing
  service instances.

```sh
make releasefence-up
make releasefence-status
make releasefence-down
make releasefence-test
```

On macOS/Linux the dev dependency `pgserver` provisions isolated real PostgreSQL
test instances when no external test DSN is provided. On Windows, set
`RELEASEFENCE_TEST_ADMIN_DSN` to an explicitly dedicated test PostgreSQL instance;
do not point engineering tests at production. The test fixture's bundled PostgreSQL
version is not a recommended current production patch level.

`up` builds the web client and starts only this product's API/worker. It does not
start PostgreSQL, deploy a vendor, launch a model or create a rollout. API startup
may provision the explicitly configured initial administrator if absent; it does
not reset an existing password. The worker can resume existing enrolled work.
`down` does not stop customer agents, revoke their credentials or verify rollback.
Foreground service wrapper: `scripts/run_product_service.py --product releasefence
api` or `worker`. Target Windows service supervision remains unqualified.

## First organization and release

Sign in, create an organization, register both full manifests, and register an
application/environment with its stable digest. The registry returns SHA-256 of
canonical manifest JSON; do not invent the identity by hashing prettified JSON.
Code, prompt, model configuration, tools, policy and optional index are one bundle.
An unverified model identity stays explicitly unverified.

Create a second user using the platform-admin Settings form. Add them as an
organization approver. The release maker cannot approve their own rollout.
Use separate browser sessions/logins when exercising both roles.

CI can obtain an owner-issued application/environment grant, valid for at most one
hour. Send its bearer token to `POST /registry/v1/releases` with the manifest JSON.
It can register a release for that application but cannot enroll/control/ingest as
a runtime. The environment is issuance/audit scope; manifests remain immutable
application artifacts, not deployments into that environment. Owner revocation:
`POST /api/orgs/{tenant}/registration/{id}/revoke`. No CI workflow is installed into
a customer's repository automatically.

## Plug in customer infrastructure

The customer owns the agent and inference provider. Its adapter exposes two
authenticated endpoints for each already deployed immutable bundle:

| Endpoint | Contract |
| --- | --- |
| `POST /releasefence/v1/probe` | Accept `{release, nonce}`; return `{release, nonce, healthy: true}` only if that actual bundle is loaded and ready. **No inference or tool side effects.** Do not merely echo an unverified caller-supplied release. |
| `POST /releasefence/v1/tasks` | Accept `{id, session, input, release}`; execute that loaded bundle; return typed `TaskResult`: release, output, declared outcome/model-call count, usage records, optional stop_reason. |

Typed request/result models are in `gateway.py`; use them instead of guessing a
response schema. Failed HTTP transport is recorded as failed work with unavailable
usage, not free inference. Exhaustion cannot be recorded as task success. Bundle
invocation has a separately configured finite deadline (default 300s, maximum
3600s); probes/control/webhooks retain short deadlines. A timed-out remote task may
still run remotely: no cancellation or reversal guarantee is made.

Generate a separate customer signing key, enroll its public key in Connections,
and copy the returned one-time machine token and server public key. Select
observe-only unless this exact runtime is intended to accept deployment control.
Customer configuration is a private JSON file with these fields:

```text
control_url: authorized ReleaseFence HTTPS base URL
data_dir: dedicated customer-local durable directory
enrollment, application, environment, server_public_key: enrollment receipt/scope
stable: registered stable digest
bundle_endpoints:
  <stable digest>: {manifest: <complete manifest>, url: <owned adapter base>, token_env: <env key>, timeout_seconds: 300}
  <candidate digest>: {manifest: <complete manifest>, url: <owned adapter base>, token_env: <env key>, timeout_seconds: 300}
lab_loopback: false
```

Set `RELEASEFENCE_CONNECTOR_CONFIG` to that file, `RELEASEFENCE_RUNTIME_SIGNING_KEY`,
`RELEASEFENCE_CONNECTOR_TOKEN`, and each referenced bundle-token environment variable.
Set a separate strong `RELEASEFENCE_GATEWAY_TOKEN` for callers of the local gateway.
Run these independently under your customer service account:

```sh
python -m releasefence_api.client
python -m uvicorn releasefence_api.gateway:app_from_env --factory --host 127.0.0.1 --port 8110
```

Both processes intentionally share `router.db`/`events.db` under the dedicated
customer directory. SQLite is only customer-local state; the SaaS control plane is
PostgreSQL. The gateway's authenticated `POST /agent/v1/tasks` is the customer-facing
entry into registered bundle routing. Raw inputs/outputs stay on this customer
path; lifecycle telemetry contains neither. Tools may also instrument `Runtime`
directly with `task.tool`, `task.usage`, `task.model_attempt`, and finite human waits.

Destination policy currently supports public HTTPS and an explicit isolated-lab
exception for literal loopback HTTP. Arbitrary RFC1918 targets, redirects, proxy
inheritance, arbitrary shell execution and dynamic code download are not supported.
The loopback exception is not an Internet-deployment recommendation. DNS resolution
still depends on OS resolver timing; the transport's wall-clock cap starts after
resolution. Customer app request/client timeouts must accommodate the chosen task
deadline. Protect the gateway separately; it is not a public unauthenticated API.

## Tracing, metrics and alerts

Use `telemetry.TraceBridge` with the enrollment's `/ingest/v1/traces` URL, bearer
headers and current release. Its dedicated tracer provider does not replace the
application's global provider; use `with bridge.span('agent')`, `llm`, `tool` or
`retriever`, and shut it down explicitly. Raw exception recording is disabled.
Custom collector instrumentation may use the same bounded OTLP JSON/protobuf API.
The SDK trace batch queue is finite but not disk durable; the lifecycle event spool
is disk durable. Missing trace coverage must hold qualification, never be hidden.

For the user-approved OSS profile, select `mlflow-phoenix-v1` explicitly when
creating a rollout (`policy: {"trace_profile": "mlflow-phoenix-v1"}`). New UI
rollouts select this by default; API callers omitting it retain the legacy
LangSmith/Phoenix profile. The profile is bound into approval scope. Changing
destinations is not a way to relabel existing backend receipts; organizations
retain the two-backend cap. See [ADR 0002](adr-0002-self-hosted-mlflow.md).

Enroll owner-authorized **MLflow and Phoenix** endpoints in Connections. MLflow
uses `/v1/traces`, protobuf, a numeric experiment ID as Project, and a scoped
`username:password` as Secret. Read URL is its API base, queried through
`/api/3.0/mlflow/traces/get?trace_id=tr-<original-trace-hex>`. Its account must have
only the appropriate workspace/experiment permissions; never use the lab admin
as the enrolled exporter. Require protected HTTPS outside the explicit loopback
lab. URLs/credentials are encrypted at rest and must not appear in docs/logs.

Pinned optional backend manifests are
`infra/releasefence-observability/mlflow-requirements.txt` and
`infra/releasefence-observability/phoenix-requirements.txt`. Install them into
**separate** virtual environments, not the main service environment. For example,
from the repository root:

```sh
.venv/bin/python -m venv var/validation/releasefence-mlflow-venv
var/validation/releasefence-mlflow-venv/bin/python -m pip install -r infra/releasefence-observability/mlflow-requirements.txt
.venv/bin/python -m venv var/validation/releasefence-phoenix-venv
var/validation/releasefence-phoenix-venv/bin/python -m pip install -r infra/releasefence-observability/phoenix-requirements.txt
```

Create environments only when absent; do not overwrite an existing deployment.
The owned acceptance helper `scripts/releasefence_backend_lab.py` checks exact
versions, generates private credentials, disables telemetry, denies default
MLflow permissions and provisions isolated scoped users/experiments. Its SQLite
backends are disposable **lab infrastructure**, separate from the actual
ReleaseFence PostgreSQL store. This is not a production backup/Windows installer.
The [measured follow-up](followup-acceptance-2026-10-22.md) contains browser and
zero-inference replay commands. Original grant: 24/24 spent; independently approved
larger grant: 239/240 spent. Do not reset either ledger or rerun a full live campaign.
`make releasefence-test-browser` requires an explicit frozen corpus and a new output
directory; it uses isolated test services/profiles, never personal browser state.

For the retained legacy profile, LangSmith commonly uses
`/otel/v1/traces` with its API base for read-back; Phoenix uses protobuf at its
`/v1/traces` endpoint with `x-project-name`, and `/v1/projects/{project}/spans` for
read-back. Local Phoenix 20.23.0 passed the bounded [actual campaign](real-data-validation.md)
and a real process outage/restart/retry drill. LangSmith remains unqualified: no
account/entitlement was provisioned. Exact deployed versions, API permissions and
license terms must be qualified for each customer deployment.

Export acceptance is distinct from read-back verification. UI shows proof time and
IDs, retry state and dead letters. Owner can disable a destination or perform one
bounded replay; traces are not billed again as model calls. Backend proofs cover
their named spans only. Canary analysis requires fresh proofs from **both** vendors
for both releases in that application/environment and measurement window.
Known pending/dead-letter trace exports in the scoped window also hold promotion;
one successful read-back cannot hide the rest of a failed export batch/backlog.

Dashboard metrics use retained application/environment lifecycle events, not a
rolling 24-hour window. Latency includes failed closed tasks; open tasks and missing
latency/usage stay visible. Reported and estimated USD are separate, cached input
is a subset of input, and zero-success/unknown cost-per-success is null. A versioned
estimate is not provider-billing reconciliation. UI pages load at most 100 records;
the list API supports explicit pagination, and page counts are not global totals.

Notifications are HMAC-signed and at-least-once. Verify
`X-ReleaseFence-Signature` against exact body bytes and deduplicate the stable
`Idempotency-Key`. Initial retry limit is five attempted deliveries, including
crashed/unknown attempts. One owner replay extends total attempts to ten, not ten
additional attempts. Acknowledgement is not resolution; critical episode closure
requires fresh verified mitigation. Use an external customer monitor for observer
`/health/ready`; a process cannot reliably page about its own total outage.

## Canary and rollback safety

Register exact runtime scope and a finite rollout. Approve independently, then
start 5%; only a passing closed window permits 25%, then a separate authorized
100% promotion. Minimum evidence is per arm. One independent task/session is the
current analysis unit; dependent or cross-arm sessions hold rather than receiving
an unqualified clustered-bootstrap pass.

The frozen implementation uses conservative Wilson failure-rate intervals and
2,000 seeded bootstrap resamples for p95/cost-per-success at two fixed looks.
Reproducibility tests are not population-level calibration. Missing closed-window
signed counters, trace proofs, latency/cost, freshness or sample floors cause an
inconclusive hold. Changed/later evidence never rewrites a closed decision.
Critical candidate failures independently block expansion even if aggregate rates
would pass; they are hard failures, not statistically averaged away.

Commands bind exact targets, epoch, expected routing revision, authority and expiry.
The runtime persists results before acknowledgement; retry of the same committed
ID is read-back, not new execution. A routing-table-only proof cannot verify control.
Loaded-bundle probes must succeed. Rollback is partial while candidate tasks remain
active; fresh sessions route stable. Completed candidate sessions are retired and
cannot resume the bad release by reusing their old session ID. Start a new session
after that retirement. Task admission/routing is atomic with command application.

Only unstarted rollouts can be cancelled. Unknown expired commands require fresh
signed evidence observed after expiry plus the 60s reconciliation margin; owner
recovery changes scope and invalidates old approvals. Recovery permits only a newly
independently approved rollback, not renewed promotion. Offline/unknown runtime
scope can therefore remain blocked beyond the 120s target. Do not label it recovered.

Approval expiry prevents new actuation; it is **not** a serving lease. Connectivity
loss keeps last committed routing, possibly including canary traffic. No implicit
offline rollback, forced task kill or reversal of prior customer tool effects.

## Backup and quarantine

In an operator shell with a separate administrative DSN:

```sh
python -m releasefence_api.operations backup <new-private-artifact> --schema releasefence
python -m releasefence_api.operations restore-quarantined <artifact> --schema releasefence
```

These require matching PostgreSQL `pg_dump`/`pg_restore` binaries. Backup refuses
overwrite and snapshots only the specified schema. Restore creates a **new**
random `rf_restore_*` database, never overwrites a live one, starts no services,
invalidates machine/browser tokens and approvals, revokes enrollments, pauses
environments and disables outbound destinations. A failed backup/restore artifact
is retained for investigation and is not a successful backup.

There is deliberately no automatic unquarantine/resume button. New runtime-role
grants, fresh keys/enrollment, independently retained deletion/revocation records
and actual runtime reconciliation require operator review. Existing immutable audit
evidence survives. Key rotation, retention archival, tenant erasure/backups/WAL
remnants and commercial disaster-recovery procedures remain production-hardening
work, not advertised solved by a lab restore.

## Scope limits and next validation

This engineering build does not include billing, SSO/MFA, arbitrary cloud controllers,
Arize AX qualification, trace UI deep links, raw GenAI payload retention, an optional
AI incident summarizer, automatic archive/erase or a bundled third-party deployment.
Applications provide project-level scope; a separate project-management entity is
not implemented. The optional summary is not required for any of the five requested
concepts and no inference credentials or actions are entrusted to an LLM.

Next: the frozen real-source workload campaign in data-and-evaluation.md, both
authorized vendor endpoints, broader calibration/partition/kill tests, actual browser
and accessibility work, independent security review, and Windows/Cloudflare/resource
qualification. Real-source volume gates were not lowered into unit-test passes.
