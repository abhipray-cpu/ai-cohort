# Windows Codex handoff: the Sentiolus portfolio

Prepared 25 October 2026. Read this before changing deployment code on the old
Windows laptop. This is the agreed target and implementation guide, **not a
claim that container deployment or Windows acceptance already works**.

## 1. Mission and authority

Deploy all twelve products on the owner's Windows laptop, with containerized
backends, their existing UIs, one private routing gateway and Cloudflare Tunnel.
The gateway hostname is **`orch1.sentiolus.in`**. AI work must use an adapter to
Codex installed on that Windows laptop, not silently switch to another provider.

This handoff is documentation first. On the Windows machine, follow repository
instructions, inspect the actual checkout, then implement missing pieces with
test-driven development. Preserve user changes and product-specific safeguards.
Do not call deployment complete until the acceptance gates below have evidence.

Already agreed:

- The owner controls `sentiolus.in`; each product gets its own subdomain.
- All twelve backend applications run in containers on the Windows laptop.
- A gateway container receives traffic through Cloudflare Tunnel and routes it
  to the correct product container.
- Codex is installed on the Windows host. Its execution and credentials remain
  private; the public gateway is not a remote shell or Codex endpoint.
- The laptop reportedly has 12 CPU cores. RAM, disk, CPU topology, Windows
  support status and virtualization still need inspection.

Implementation within this plan may include local source edits and synthetic
tests. Obtain explicit owner approval before changing DNS/Access/account policy,
installing privileged software or startup tasks, migrating live data, performing
destructive operations, sending customer data, or initiating paid/live inference.
Do not inherit past products' call budgets. Initial live-call allowance here is
**zero** until a fresh bounded campaign is approved.

## 2. Target topology

```text
Browser -> https://<product>.sentiolus.in
        -> Cloudflare TLS + Access (approved pilot policy)
        -> outbound Tunnel -> cloudflared container
        -> gateway container (Caddy; original Host preserved)
        -> product API container -> existing UI assets / product API
                                 -> product store / durable jobs
        product worker container -> private authenticated Windows bridge
                                 -> bounded installed Codex CLI execution
                                 -> authenticated hosted model service

Browser -> https://orch1.sentiolus.in -> same tunnel/gateway
                                      -> protected minimal gateway status
```

Use Docker Compose for lifecycle. Caddy is the proposed HTTP routing component;
there is no requirement to invent a public workflow engine. The gateway must
have no Docker socket, shell, arbitrary proxy destination, deployment controls or
public job-execution API. Use a static, reviewed hostname-to-service registry.

`orch1` is a protected status/entry hostname, not the common browser API origin.
Product UIs call their own same-origin backend paths. Do not introduce cross-site
cookies/CORS by sending every UI's requests to `orch1`. A root-domain portfolio
launcher is optional, not a prerequisite or an instruction to build another UI.

For this first deployment, serve each built React UI from its product API image.
Cloudflare supplies edge routing/TLS; Cloudflare Pages is not required. Static UI
hosting elsewhere can be evaluated later with a separate authentication design.

### Host registry

| Day | Product ID | Public hostname | Private API service | Existing native port (reference only) |
| --- | --- | --- | --- | --- |
| 1 | tenderlens | tenderlens.sentiolus.in | tenderlens-api | 8000 |
| 2 | resolvedesk | resolvedesk.sentiolus.in | resolvedesk-api | 8001 |
| 3 | propertybrief | propertybrief.sentiolus.in | propertybrief-api | 8002 |
| 4 | patchdesk | patchdesk.sentiolus.in | patchdesk-api | 8003 |
| 5 | relaydesk | relaydesk.sentiolus.in | relaydesk-api | 8004 |
| 6 | clausegate | clausegate.sentiolus.in | clausegate-api | 8005 |
| 7 | catalogbridge | catalogbridge.sentiolus.in | catalogbridge-api | 8006 |
| 8 | buildrelay | buildrelay.sentiolus.in | buildrelay-api | 8007 |
| 9 | casecouncil | casecouncil.sentiolus.in | casecouncil-api | 8008 |
| 10 | shelfproof | shelfproof.sentiolus.in | shelfproof-api | 8009 |
| 11 | releasefence | releasefence.sentiolus.in | releasefence-api | 8010 |
| 12 | repairclaim | repairclaim.sentiolus.in | repairclaim-api | 8011 |
| — | gateway | orch1.sentiolus.in | gateway status only | no existing implementation |

Private service names are target names, not existing Compose services. Container
ports can be uniform: distinct service DNS names provide isolation. Publish no
product ports on the Windows LAN. A commissioning gateway port, if necessary,
must bind only to host loopback and be removed or explicitly retained privately.

Forward the entire product hostname, not just `/api`. Existing products use
different routes, including `/v1`, `/api`, assets and webhooks. Reject unknown
hosts; never default to TenderLens or any other application's upstream.

## 3. What exists and what must be built

Read the [product catalog](docs/README.md) and each product's operations/status
documents before editing its entrypoints. The earlier
[native Windows guide](docs/windows-laptop-deployment.md) remains useful for
product configuration and diagnostics, but this container target supersedes its
direct-loopback public routing topology.

| Area | Current repository baseline | Work required |
| --- | --- | --- |
| Applications | Twelve API/worker implementations and React projects | Verify each container entrypoint and build |
| AI provider | `packages/agent-core/src/agent_core/codex_local.py` launches a local subprocess | Add private bridge transport without weakening existing contracts |
| Containers | RepairClaim parser Dockerfile | Portfolio API/worker images, exclusions and Compose |
| Routing | Native Cloudflare example, not the full target | Twelve product routes plus protected `orch1` |
| Windows startup | Native installers for some products | Container/bridge boot lifecycle and actual reboot proof |
| Validation | Product-specific development and real-data reports | New Windows/container/tunnel evidence; preserve existing limitations |

`apps/releasefence-api/src/releasefence_api/gateway.py` is ReleaseFence's customer
agent gateway. It is **not** this portfolio reverse proxy. Do not couple all
products to that module or overwrite its semantics.

## 4. First session: inspect before installing

Run read-only checks in PowerShell from the repository. Record sanitized results;
do not dump the environment, credential stores, `.env`, Docker inspect secrets,
or full Codex configuration into chat or committed reports.

```powershell
git status --short
git rev-parse HEAD
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory, HypervisorPresent
Get-Volume | Select-Object DriveLetter, FileSystem, Size, SizeRemaining
wsl --status
wsl --list --verbose
docker version
docker compose version
node --version
python --version
Get-Command codex -All | Select-Object CommandType, Source
codex --version
codex login status
```

Missing commands are findings, not permission to install or alter settings.
Confirm supported Windows edition/patching, virtualization, Docker Desktop Linux
container support, disk encryption, working backups, available RAM and SSD space.
Check Docker Desktop licensing for the actual user/organization. Confirm whether
Docker starts without an interactive desktop login; do not assume it does.

Twelve cores do not establish capacity: API/worker pairs, Docker's VM, databases,
embedding model, parsers and observability consume RAM and disk independently.
Measure idle and peak resource use. Begin Codex concurrency at one globally,
then qualify any increase. Do not start all workers unbounded to demonstrate load.

## 5. Codex runtime and host bridge

### Identity and authentication

Use a dedicated, limited Windows runtime identity with an explicit installed
Codex executable. Authentication must work under that identity, not just the
owner's interactive terminal. Never copy the owner's authentication cache into
images, repositories or every container. No need to leave this chat open.

Codex CLI runs locally; normal hosted inference still needs network access and
valid authentication. This is not an offline model or a GPU inference server.
Check current supported authentication and account entitlement for unattended
service use before public operation. Do not promise unlimited/free inference or
assume a personal subscription authorizes every commercial service scenario.
If the intended unattended usage needs a different approved authentication mode,
report that gate; do not silently change it or fall back to direct model APIs.

Record the tested CLI version and executable path. Preserve the current provider's
schema enforcement, timeout/output limits, ephemeral execution, isolation and
subprocess-tree cleanup. Its flags include `--ignore-user-config`; a desktop model
selection must not be assumed to control product runs. Test CLI compatibility;
do not remove safety flags merely to make a smoke test pass.

### Private bridge contract to implement

The Linux containers cannot execute a Windows CLI merely because `codex` exists
on the host. Add an adapter in `agent-core` that preserves structured generation
semantics while submitting bounded work to a private Windows bridge.

Required behavior:

- An allowlisted product identity, capability, request ID, prompt/schema payload
  and bounded deadline. Authenticate each worker with a product-scoped secret.
- Server-owned policy for executable, flags, permitted schema/capability and
  limits. Reject caller-supplied shell commands, executable paths, model overrides,
  arbitrary filesystem paths or arbitrary destination URLs.
- Durable admission and receipts, a global concurrency limiter initially set to
  one, bounded queues, cancellation, and per-product fair scheduling. Overload
  returns a clear retryable/degraded result instead of spawning more processes.
- Bind request ID to product identity and payload hash. Repeated submissions must
  return the existing receipt; the same ID with different content must fail.
- A disconnect after execution starts is an unknown outcome until reconciled.
  Never blindly retry potentially billed work. Exactly-once model execution
  cannot be promised across every crash boundary.
- Enforce process deadlines, output limits and Windows child-process cleanup;
  validate responses on the product side as well. An invalid result cannot become
  a successful completed job or disappear from audit history.
- Correlation IDs and privacy-filtered timings/outcomes, not raw prompts,
  documents, secrets or CLI authentication output in routine logs.
- Only the owning product may inspect/cancel its requests. No public bridge
  route, UI, shell, Docker API or administrative execution endpoint.

Container `localhost` is not the Windows host. Verify the Docker Desktop host
connection mechanism and firewall rules on the actual machine. A loopback-bound
Windows listener is not automatically reachable from Linux containers. Use a
reviewed private, authenticated transport with TLS where applicable; demonstrate
that an unauthorized LAN client cannot reach/use it. Do not solve connectivity by
opening an unauthenticated listener on `0.0.0.0`. If private isolation cannot be
proved, this phase remains blocked.

## 6. Implementation sequence: red, green, then integration

For each phase, first add a failing behavior test, implement the smallest change,
run targeted tests, then regression checks. Keep red/green evidence and actual
commands. Reading source and writing tests after implementation is not proof of
TDD. Never fabricate a historical red run.

The paths below are **proposed artifacts to create**, not commands/configuration
that already exist:

```text
infra/portfolio/compose.yml
infra/portfolio/Caddyfile
infra/portfolio/routes.json
infra/portfolio/cloudflare.example.yml
infra/portfolio/README.md
infra/windows/codex-bridge/                 # host-side service/installation
scripts/portfolio_stack.py                  # safe lifecycle wrapper, if needed
tests/test_portfolio_*.py
```

Adapt names to repository conventions, documenting the actual result. Do not add
dummy scripts or Make targets that only print success.

### Phase A — baseline and safe image context

1. Inspect applicable `AGENTS.md`, product runbooks, entrypoints and dirty files.
2. Capture baseline tests/builds without launching live provider calls or outbound
   workflow effects. Check pytest markers and integration fixtures first.
3. Before the first image build, implement/test `.dockerignore` and explicit COPY
   boundaries. Gitignore does not protect Docker's build context.
4. Exclude private `.env` files, `var`, logs, backups, credentials/auth caches,
   private corpora, `.git`, virtualenvs and `node_modules`; preserve required public
   manifests/templates deliberately. Inspect image files/layers for secret leaks.
5. Never bake credentials into ARG/ENV, layers or frontend bundles. Dependency
   downloads/build-time secrets need explicit, nonpersistent mechanisms.

### Phase B — routing contract

Test the registry against all twelve product IDs and the exact thirteen hosts.
Test unknown hosts, malformed/duplicate routes, a stopped upstream, prefix/path
preservation, query strings, uploads and streaming responses. Wrong/unavailable
upstreams must fail closed, never route to another product. Render/test Caddy
configuration from the registry or add a drift test if maintaining both files.

Keep status minimal: availability and sanitized version/health, not internal
addresses, credentials, prompts, stack traces or container administration.

### Phase C — bridge and provider adapter

Implement the contract in section 5 with a fake executor first. Test admission,
scope denial, duplicate requests, crash recovery, process timeout, cancellation,
output/schema errors and unknown outcomes. Prove all affected products select the
bridge explicitly. Existing local-native execution must remain usable where
documented; adding an unused adapter is not integration.

### Phase D — product images and storage

Build React assets in a reproducible Node build stage and install Python workspace
packages in the runtime image. Use supported pinned toolchain/image versions and
the repository lockfiles. Audit native parser and ONNX dependencies per product.

Run API and worker as separate services, commonly using the same image. Bind API
to `0.0.0.0` **inside** its private container; no public host-port mapping. Use
unprivileged runtime users, least-privilege mounts, read-only root filesystems
where compatible, explicit writable temp space and bounded resources/logs.

Keep each product's store, uploads, secrets and erasure/authority ledgers isolated.
Do not mount the entire repository, Windows user profile or shared `var` into all
services. Prefer qualified Linux named volumes for Linux SQLite workloads; do not
assume WAL/locking is safe on an arbitrary Windows bind mount. Preserve independent
ledgers and test cross-product read denial. No shared application database just
because it simplifies Compose.

### Phase E — dependencies and special cases

| Product/component | Required deployment consideration |
| --- | --- |
| TenderLens | Dedicated data root; avoid accidentally inheriting shared `APP_DATA_DIR=var` |
| RelayDesk | Explicitly provision the CPU ONNX model/tokenizer manifest; retain independent erasure ledger |
| ClauseGate | Preserve independent authority state and restore/review grant rules |
| BuildRelay | Authenticated persistent NATS JetStream; no public broker/monitoring ports; preserve webhook HMAC and idempotency |
| ReleaseFence | Dedicated PostgreSQL database and non-superuser runtime role; preserve RLS, explicit installation and separate runtime keys |
| ReleaseFence tracing | Owned MLflow/Phoenix only if the chosen validation/profile requires them; keep private and resource-budgeted |
| RepairClaim | Preserve encrypted blobs, external erasure ledger, explicit owner provisioning, exact public origin and isolated parser |

RepairClaim's current parser launcher expects a local Docker interface. Moving
the API/worker into Linux containers does not automatically preserve that design.
Do **not** mount the Docker socket into product APIs/workers or the gateway. Make
an explicit ADR and tests for a constrained parser broker/pool or equivalent
isolation: no network, restricted input/output, bounded CPU/RAM/time, per-job
cleanup and no arbitrary container/host control. Both API preview and worker
parsing paths need coverage. Never fall back to unsafe in-process PDF parsing.

Identify every workflow with possible outbound side effects before starting
restored data. Start with fresh commissioning data; do not accidentally replay
pending issue writes, queue messages, notifications or rollout actions.

### Phase F — Compose and operational behavior

Define explicit networks: tunnel-to-gateway, gateway-to-APIs and product-scoped
dependency networks. Keep databases, workers and broker ports off the public
network. Document necessary outbound access; do not mark every network internal
if that prevents required provider/download access without an alternative.

Distinguish liveness, readiness and dependency health. A provider outage should
produce an honest degraded service/queued job, not route traffic to another app.
Startup ordering alone is not recovery. Test restart policies, backoff, durable
leases, shutdown ordering and recovery after dependent services restart.

Use private secret files with Windows ACLs; Compose secrets alone do not encrypt
their source files on disk. Do not print fully interpolated Compose configuration
with real secrets into committed logs. No `latest` images for accepted releases.

### Phase G — local acceptance before public routing

Bring up one product with fake provider, then all twelve. Test through the gateway
with explicit Host headers. Do not weaken application TrustedHost, CSRF, cookie or
origin checks merely to make loopback health checks pass. Set each product's
documented HTTPS origin and secure-cookie settings using its actual variable names.
Some booleans use `1`, others `true`: do not invent a universal environment flag.

Test the built UI, login, assets, product API and durable workflow. A 200 response
from `/` is not end-to-end acceptance. Use supported browser automation when
available; record blocked interactive cases honestly when it is not available.

Only after this phase passes request a fresh bounded live Codex campaign with
specified public/consented records, allowed products, call/retry ceilings, time
and spend limits. Known/unknown usage and incomplete runs must be accounted for.

## 7. Cloudflare commissioning — after local gates

Owner-approved changes only. Do not create or alter DNS merely because the domain
is named in this guide. Confirm the correct Cloudflare account/zone and existing
records first; preserve unrelated DNS/email services.

1. Create/configure one named Tunnel with a scoped private connector credential.
2. Route all thirteen hostnames from the registry to the **same private gateway**,
   for example `http://gateway:8080` if that is the tested Compose listener.
3. Preserve original Host and required forwarded scheme information. Trust proxy
   headers only from the actual trusted proxy chain, not arbitrary browser input.
4. Configure a final deny/unmatched ingress rule. Keep the gateway inaccessible
   directly from the LAN/internet so the Tunnel/Access policy cannot be bypassed.
5. Protect the pilot hosts with Cloudflare Access. Validate Access JWTs at the
   connector/origin as configured; never trust a spoofable email header alone.
6. Retain application authentication and role/tenant scopes. Access identity is
   not a replacement for product authorization, CSRF defenses or broker identity.
7. BuildRelay may need a narrowly approved public GitHub webhook path
   `/hooks/github/{repo_id}`. Interactive Access cannot authenticate GitHub
   deliveries. Bypass only the necessary path, retain application signature,
   replay/idempotency/rate checks, and test sibling paths stay protected.
8. Check Cloudflare plan limits for actual PDF sizes, request durations and
   streaming. Use durable job submission/polling instead of requiring a model
   call to finish within an edge HTTP timeout. Do not disable limits globally.

Do not expose PostgreSQL, NATS, Docker, parser control, Codex bridge or raw tracing
stores via this tunnel. `orch1` provides no exceptions to that rule.

## 8. Acceptance matrix and required evidence

Use fresh test identities and approved data. Record commit, Windows/WSL/Docker/
Codex versions, image digests, sanitized configuration fingerprint, commands,
counts, duration and evidence locations. Prefer private runtime evidence under
`var/windows-deployment/`; commit only reviewed sanitized reports.

| Gate | Required demonstration |
| --- | --- |
| ROUTE | All thirteen hosts; wrong Host denied; each product UI/API reaches only its own service; stopped upstream fails safely |
| AUTH | Access rejection, product login/logout, role separation, secure cookies, origin/CSRF protection and forged proxy headers |
| STORE | Independent product data/ledgers; unauthorized cross-product access denied; restart retains expected state |
| BRIDGE | Product-scoped identity, fake executor contract, deduplication, queue caps, timeout/process cleanup, cancellation and restart reconciliation |
| CONTAINER | No Docker socket or credentials in images, no privileged services, scoped mounts and no unintended listening LAN ports |
| WORKFLOW | Each product's representative durable workflow, UI review/approval where relevant, failure state and audit trail |
| SPECIAL | NATS redelivery, ReleaseFence RLS/trace outage, RelayDesk model availability and RepairClaim parser isolation |
| LIVE | Separately approved bounded real-data/Codex runs; actual calls and unknown liabilities reported, no synthetic passes labeled real-data |
| EDGE | External authorized/unauthorized browsers, uploads/downloads, streaming/polling, narrow webhook exception and protected sibling paths |
| RECOVERY | Worker/API/bridge/tunnel restart, interrupted jobs, host reboot without interactive chat/terminal, no duplicate external effects |
| RESTORE | Encrypted backup restored into isolated test volumes, keys/ledgers accounted for and product-specific quarantines honored |
| CAPACITY | All twelve running together; measured idle/peak RAM/CPU/disk, queue latency, bounded load and at least a one-hour observed soak |

Agree measured capacity/SLO thresholds with the owner before the load run; a
one-hour soak is only a commissioning baseline, not evidence of long-term SLA.
Do not mask skipped Windows security tests as passed. ReleaseFence database tests
must use a dedicated disposable test database/admin DSN, never production storage.

Test actual externally generated URLs and downloaded case packets, not only
internal health checks. Separate route readiness, engineering acceptance and
semantic/customer-quality acceptance. Existing product status docs contain open
quality gates; successful hosting does not erase them or make all products
production-ready.

## 9. Daily operations, backup and rollback

Implement and document real status/up/down/logs commands after the underlying
configuration exists. Stop gracefully and preserve volumes by default. Never
recommend `docker compose down -v`, blanket prune, forced Git reset or deleting a
data directory as routine troubleshooting.

Set log rotation, disk-space alarms, bounded queue alerts and bridge failure
alerts. Scrub payloads/credentials from diagnostics. Back up product state using
supported consistent database snapshots; copying a live SQLite file alone is not
a qualified backup. Include encrypted documents, authority/erasure ledgers,
PostgreSQL, queue state and required keys as product policies demand. Keep backup
keys separate and perform restore tests. Backups must not resurrect erased data.

Before upgrades record image digests, schema versions and last successful backup.
Test forward migrations on a copy. Rolling back an image does not necessarily
roll back its database; stop writes and follow the tested migration/restore plan.
Never overwrite a newer erasure ledger with an older backup. Keep connector and
runtime credentials out of source control; rotate any previously shared keys.

Use an approved Windows startup mechanism for both container stack and host
bridge under the intended identity. Verify actual cold reboot, credential access,
network recovery, Docker readiness and restart after power loss. Prevent laptop
sleep/hibernation only with owner approval; assess ventilation, battery condition,
power and ISP availability. A single laptop is one failure domain, not HA.

## 10. Required handoff and honest completion

At the end of each working session report:

- Implemented changes and files, tests actually run and red/green evidence.
- Per-gate status: `passed`, `failed`, `blocked` or `not run`, with reasons.
- Any live calls/spend, unknown execution liabilities and remaining allowance.
- Current services and pending work; safe shutdown/recovery instructions.
- Updated implementation notes and sanitized validation evidence, without new
  blog content. The owner requested removal of blog drafts from this repository.

Call the container deployment accepted only when the relevant matrix gates pass
on the actual target Windows laptop and public endpoints, with no undisclosed
skips. Otherwise state exactly what is implemented and what remains unvalidated.
Do not substitute Linux/macOS regression success for Windows acceptance.

### Starter prompt for Codex on the Windows laptop

> Read `guide.md`, applicable `AGENTS.md`, and the linked product operations/status
> docs. This machine is the target Windows host. Start with read-only preflight and
> report the current commit, dirty worktree, host capabilities and missing tools.
> Implement this container deployment incrementally using TDD, preserving product
> security and data boundaries. Gateway hostname: `orch1.sentiolus.in`; each
> product's UI/API stays on its own subdomain. Codex stays on the Windows host
> behind a private authenticated bridge. Do not change DNS, Access, authentication,
> model settings, privileged host configuration or live data without approval.
> Do not run live inference until a fresh bounded campaign is approved. Report
> actual evidence and blocked gates; do not claim completion from health checks.

## 11. Primary references to recheck during commissioning

These document mechanisms, not a promise that the target host is already supported.

- [Codex authentication](https://learn.chatgpt.com/docs/auth): runtime identity,
  credential storage and supported authentication choices.
- [Codex CLI](https://learn.chatgpt.com/docs/codex/cli) and
  [developer commands](https://learn.chatgpt.com/docs/developer-commands): installed
  CLI compatibility and noninteractive execution.
- [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/):
  current host requirements and supported installation options.
- [Compose networking](https://docs.docker.com/compose/how-tos/networking/) and
  [Docker Desktop networking](https://docs.docker.com/desktop/features/networking/):
  private service addressing and host/container connectivity.
- [Docker build contexts](https://docs.docker.com/build/concepts/context/): why
  image build exclusions are a separate security boundary from Gitignore.
- [Cloudflare Tunnel routing](https://developers.cloudflare.com/tunnel/concepts/routing/):
  multiple published hostnames routed through a connector.
- [Cloudflare Access self-hosted applications](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/):
  protected application access; validate the chosen deployment's policy.
- [Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy):
  routing and proxy behavior to verify in configuration tests.
