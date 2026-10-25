# Run the portfolio on the Windows laptop

Prepared 25 October 2026. Scope: all twelve products, installed Codex on the same
Windows host, and protected Cloudflare access. This is a deployment runbook, **not
evidence that the target laptop has passed deployment acceptance**.

## 1. The deployment we are building

```text
Owner / approved pilot user
          |
          v
Cloudflare HTTPS + Access
          |
Outbound cloudflared tunnel from the Windows laptop
          |
127.0.0.1:8000 through 127.0.0.1:8011
          |
Product API + built React UI + its independent worker/store
          |
Installed Codex CLI adapter -> configured authenticated model service
```

The laptop hosts application code, documents, queues, stores and the Codex CLI.
This does not require leaving this chat, VS Code or a browser automation tab open.
The CLI is invoked by product workers; this conversation is not the runtime.
With the normal OpenAI provider, inference still requires network access. This is
not an offline-model deployment and does not require a GPU for hosted inference.

Do not expose the Codex executable/app-server, a shell, PostgreSQL, NATS, model
caches, source files or observability admin interfaces through the tunnel.

Start as an **Access-protected personal/limited pilot**, not unrestricted public
self-service. Repository publication does not authorize anonymous visitors to
consume your Codex account or use agents with your privileges.

### Authentication and usage boundary

The repository already invokes installed Codex; do not replace it with a direct
LLM API client just to deploy. Sign in on the laptop as the actual runtime user.
However, subscription authentication is not a promise of unlimited inference or
approval for any commercial automation. Official OpenAI guidance recommends API
key authentication for programmatic CLI workflows and warns against exposing Codex
execution in untrusted/public environments. Confirm an appropriate supported
authentication/entitlement arrangement before unattended multi-user service.
Do not add API billing, buy credits, change model settings or copy auth caches
without a separate decision. [Official authentication guidance](https://learn.chatgpt.com/docs/auth).

## 2. First check whether the old laptop is suitable

Run PowerShell on the laptop, not the Mac:

```powershell
Get-CimInstance Win32_OperatingSystem |
  Select-Object Caption, Version, OSArchitecture, LastBootUpTime
Get-CimInstance Win32_ComputerSystem |
  Select-Object Manufacturer, Model, TotalPhysicalMemory
Get-CimInstance Win32_Processor |
  Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, VirtualizationFirmwareEnabled
Get-PSDrive -PSProvider FileSystem
```

Record the OS edition/build, RAM, CPU, free storage, virtualization support and
available update path. Keep the inventory private if it includes identifying data.

- Use a supported, security-updated 64-bit Windows installation. Ordinary Windows
  10 support ended on 14 October 2025; check the actual edition's lifecycle/ESU
  status rather than assuming an old installation is maintained.
  [Microsoft lifecycle information](https://learn.microsoft.com/en-us/windows/release-health/release-information).
- RepairClaim needs a supported local Linux-container runtime on Windows. Docker's
  current Windows requirements include virtualization and 8 GB system RAM; check
  the current OS/WSL requirements before installing. These are runtime prerequisites,
  not proof that the whole portfolio fits in 8 GB.
  [Docker requirements](https://docs.docker.com/desktop/setup/install/windows-install/).
- An SSD and 16 GB or more RAM are a planning preference, not a measured portfolio
  minimum. Below that, start with one product and measure. PostgreSQL, ONNX, OCR,
  tracing backends and concurrent builds can dominate memory/disk usage.
- Keep the laptop powered, ventilated, awake and time-synchronized. Configure sleep,
  lid-close and update/reboot behaviour deliberately; turning the screen off is fine.
  A sleeping laptop cannot serve requests, regardless of tunnel status.
- No router port forwarding is needed for this design. Keep Windows Firewall on.

If the host cannot meet supported OS/container requirements, stop at preflight.
Do not disable PDF isolation or install unsupported software to claim a pass.
Changing the host/OS or adding another machine requires a separate deployment choice.

## 3. Product map and existing packaging

| Day / product ID | Loopback port | Additional setup | Existing startup-task installer |
| --- | --- | --- | --- |
| 1 `tenderlens` | 8000 | Explicit account; dedicated `APP_DATA_DIR` | None |
| 2 `resolvedesk` | 8001 | Reviewed/indexed PostgreSQL documentation for useful RAG | `install-resolvedesk.ps1` |
| 3 `propertybrief` | 8002 | Authorized source access and case data | `install-propertybrief.ps1` |
| 4 `patchdesk` | 8003 | Client/project scope; external publication disabled initially | `install-patchdesk.ps1` |
| 5 `relaydesk` | 8004 | Local ONNX encoder plus independent erasure ledger | `install-relaydesk.ps1` |
| 6 `clausegate` | 8005 | Reviewer permissions; independent authority/erasure ledger | `install-clausegate.ps1` |
| 7 `catalogbridge` | 8006 | Supplier/catalogue data and independent usage journal | `install-catalogbridge.ps1` |
| 8 `buildrelay` | 8007 | Repository/HMAC configuration; NATS JetStream for queue ingress | `install-buildrelay.ps1` |
| 9 `casecouncil` | 8008 | Permitted evidence and bounded debate campaign | `install-casecouncil.ps1` |
| 10 `shelfproof` | 8009 | Permitted food facts and explicit inference grants | `install-shelfproof.ps1` |
| 11 `releasefence` | 8010 | Dedicated PostgreSQL, keys, enrolled tracing/runtime targets | None |
| 12 `repairclaim` | 8011 | Provisioned owner, isolated parser image, reviewed source registry | None |

Installer paths are under [infra/windows](../infra/windows/README.md). These are
Task Scheduler packages, not Windows SCM application-service installers. They do
not provision account login, ACLs, dependencies, source data, DNS or Cloudflare.
Do not invent an `install-tenderlens.ps1`, `install-releasefence.ps1` or
`install-repairclaim.ps1` command: those files do not exist.

All products can be brought up for manual qualification with the foreground
procedure below. Missing startup packaging remains a real gap for unattended
deployment of those three products; opening their UI does not close it.

## 4. Install the tools and clone a clean checkout

Create a dedicated non-administrator Windows runtime account, for example
`cohort-runner`, with a strong password. Use an administrator only for machine
installation/task registration when required. Sign into that account to set up
its CLI authentication and verify dependencies.

Install Git for Windows, Python 3.12 with pip, a supported Node.js LTS compatible
with the locked Vite dependencies, Codex CLI and cloudflared from their official
distributions. The current lockfile requires Node `^20.19.0 || >=22.12.0`; prefer a
currently maintained LTS satisfying that range rather than treating the oldest
accepted version as a security recommendation. Install Docker Desktop only if
the host satisfies its requirements; use Linux containers for RepairClaim.

Check tools in a **new** runtime-account PowerShell:

```powershell
git --version
py -3.12 --version
node --version
npm.cmd --version
Get-Command codex -All
cloudflared.exe --version
```

Use a short path outside OneDrive and Program Files:

```powershell
New-Item -ItemType Directory -Force C:\AICohort | Out-Null
Set-Location C:\AICohort
git clone https://github.com/abhipray-cpu/ai-cohort.git
Set-Location C:\AICohort\ai-cohort
git rev-parse HEAD
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
```

Use explicit Python paths; activating the virtual environment is optional. Do not
copy the Mac `.venv`, `node_modules`, `.env`, private data or Codex auth directory.
Reinstall dependencies on Windows and record installed versions. Dependency ranges
are not a fully reproducible lock; build and qualify a revision before exposing it.

Build the web apps serially; this does not start them or invoke a model:

```powershell
$CohortProducts = @(
  'tenderlens','resolvedesk','propertybrief','patchdesk','relaydesk','clausegate',
  'catalogbridge','buildrelay','casecouncil','shelfproof','releasefence','repairclaim'
)
foreach ($CohortProduct in $CohortProducts) {
  npm.cmd --prefix "apps/$CohortProduct-web" ci --ignore-scripts
  if ($LASTEXITCODE -ne 0) { throw "Dependency install failed: $CohortProduct" }
  npm.cmd --prefix "apps/$CohortProduct-web" run build
  if ($LASTEXITCODE -ne 0) { throw "Build failed: $CohortProduct" }
}
```

Do not serve Vite's development server. Each Python application serves its own
production `dist` build. Make is optional; this guide uses native PowerShell/Python.

## 5. Set up Codex under the runtime identity

Follow the [official Windows CLI installation steps](https://learn.chatgpt.com/docs/codex/cli).
Prefer a native executable for this deployment: the Python adapter uses argument
arrays with `shell=False`, so a PowerShell/npm shim is not a sufficient subprocess
compatibility test. If only `codex.ps1`/`codex.cmd` resolves, locate/install the
supported native CLI and verify it rather than adding `shell=True` to the adapter.

```powershell
whoami
Get-Command codex.exe -All
codex --version
codex login
codex login status
codex exec --help
```

For headless login, the documented alternative is `codex login --device-auth` when
enabled for your account/workspace. Login on this Windows account, not an admin
account whose cache the tasks cannot access. Credentials belong in the supported
local credential store, never Git, screenshots, task arguments or this guide.
[Authentication and credential storage](https://learn.chatgpt.com/docs/auth).

Record the working CLI version. The adapter uses `exec`, read-only sandboxing,
`--ephemeral`, `--ignore-user-config`, `--ignore-rules`, `--skip-git-repo-check`,
`--cd`, `--output-schema`, `--output-last-message` and stdin. Its isolated mode also
audits JSON events. CLI upgrades must pass compatibility checks before rollout.
Do not remove isolation/validation flags to make an incompatible release run.
[Scripted command reference](https://learn.chatgpt.com/docs/developer-commands).

After explicitly approving one small live call with public toy text, run the
existing adapter smoke test under the runtime identity:

```powershell
$env:CODEX_COMMAND = (Get-Command codex.exe -ErrorAction Stop).Source
.\.venv\Scripts\python.exe scripts\smoke_codex.py
```

This can consume service allowance; it is not an offline check or a zero-cost
guarantee. A successful interactive login alone does not prove the adapter works
from Python or from a startup task. Test the same call once under the scheduled
identity/environment before enabling real work; set a finite campaign allowance.

Persist the verified native executable path in private product configuration as
described next. Do not change the selected model/authentication merely to deploy.
The adapter deliberately ignores user configuration for its invocation, so a model
chosen in this chat or a desktop setting is not automatically the runtime model.
Record actual invocation/receipt behaviour during the authorized smoke check
instead of promising that the deployment runs this conversation's model.
RepairClaim currently constructs its optional provider with the default command
`codex`, so its native CLI must also resolve on the runtime account's actual PATH;
`CODEX_COMMAND` alone does not override that RepairClaim constructor.

## 6. Private application configuration

```powershell
if (Test-Path .env) { throw 'Existing .env: review it; do not overwrite.' }
Copy-Item .env.example .env
New-Item -ItemType Directory -Force var | Out-Null
notepad.exe .env
git check-ignore .env var
```

Generate/store unique long product passwords privately. Configure the first eleven
products' explicit `PREFIX_USERNAME` / `PREFIX_PASSWORD` values; don't rely on
development credential fallbacks. RepairClaim uses its provisioned owner instead.
Empty values and `replace-me` are not deployment credentials. Keep external
publishing, paid providers and source acquisition disabled until separately approved.

Important settings to edit, using the real native Codex path on **your** machine:

```dotenv
CODEX_COMMAND=C:/Tools/Codex/codex.exe
APP_DATA_DIR=C:/AICohort/ai-cohort/var/tenderlens
CLAUSEGATE_CODEX_COMMAND=C:/Tools/Codex/codex.exe
CATALOGBRIDGE_CODEX_COMMAND=C:/Tools/Codex/codex.exe
BUILDRELAY_CODEX_COMMAND=C:/Tools/Codex/codex.exe
CASECOUNCIL_CODEX_COMMAND=C:/Tools/Codex/codex.exe
SHELFPROOF_CODEX_COMMAND=C:/Tools/Codex/codex.exe

REPAIRCLAIM_DATA_DIR=C:/AICohort/ai-cohort/var/repairclaim
REPAIRCLAIM_PUBLIC_ORIGIN=http://127.0.0.1:8011
REPAIRCLAIM_PORT=8011
REPAIRCLAIM_PARSER=container
REPAIRCLAIM_CONTAINER_ENGINE=docker
REPAIRCLAIM_ENABLE_SOURCE_CHECKS=0
REPAIRCLAIM_ENABLE_CODEX=0
REPAIRCLAIM_ENABLE_JEV=0
```

The executable path is illustrative, not a promised installer destination. Use
independent product data directories/ledgers as specified in `.env.example`.
Set `APP_DATA_DIR` explicitly: the template's generic `var` is not the desired
dedicated TenderLens directory for this deployment.

Existing OS environment variables override `.env` in `scripts/dev_stack.py`.
After editing a value, restart the relevant process and check for stale inherited
variables without printing secrets. RepairClaim's own dev launcher does **not**
load `.env`; the explicit foreground environment loader below does.

Restrict access to `.env`, `var`, Codex auth, model cache, tunnel credentials,
runtime keys and backups using Windows ACLs for the runtime account and designated
administrators. Review ACLs with `icacls`; Unix `chmod`/Python mode bits are not a
Windows permission guarantee. Do not make the whole drive writable or use a
broad recursive ACL-reset command. A shared Windows account is a shared OS trust
boundary even when application households/products have separate authorization.

### HTTPS settings, applied only when switching to real hostnames

| Product | Required private configuration |
| --- | --- |
| PatchDesk | `PATCHDESK_SECURE_COOKIES=1` |
| RelayDesk | `RELAYDESK_SECURE_COOKIES=1` |
| ClauseGate | `CLAUSEGATE_SECURE_COOKIES=1` |
| CatalogBridge | `CATALOGBRIDGE_SECURE_COOKIES=true` |
| BuildRelay | `BUILDRELAY_SECURE_COOKIES=true` |
| CaseCouncil | `CASECOUNCIL_SECURE_COOKIES=true` |
| ShelfProof | `SHELFPROOF_ORIGIN=https://shelfproof.example.com` |
| ReleaseFence | `RELEASEFENCE_ORIGIN=https://releasefence.example.com`; keep `RELEASEFENCE_LAB_LOOPBACK=0` |
| RepairClaim | `REPAIRCLAIM_PUBLIC_ORIGIN=https://repairclaim.example.com` |

Replace reserved example hostnames with your domain. ShelfProof/ReleaseFence cookie
security follows the configured origin; RepairClaim also derives its deployed
boundary from that origin. The first three products use HTTP Basic authentication;
always place remote use behind HTTPS and Access. Don't invent unimplemented cookie
environment settings for them. Do not disable CSRF checks to fix proxy errors.

## 7. Product-specific prerequisites

### RelayDesk: explicitly provision its encoder

```powershell
.\.venv\Scripts\python.exe scripts\provision_relaydesk_model.py var/models/relaydesk-minilm
```

This downloads pinned ONNX/tokenizer artifacts, consumes bandwidth/disk and refuses
an existing directory. Keep the manifest with the model and set
`RELAYDESK_EMBEDDING_DIR` to that directory. This CPU embedding model is separate
from Codex generation. [Current runbook](relaydesk/implementation-and-operations.md).

### BuildRelay: distinguish webhooks from queue ingress

Configure repositories and their scoped HMAC secrets through the product workflow.
For queue validation, provision an independently authenticated local NATS server
with JetStream and persistent storage, then set `BUILDRELAY_NATS_URL`, stream,
subject and credential-file settings. Leave them empty only if queue ingress is
intentionally disabled; do not call that validation of both trigger transports.
Never tunnel ports 4222/8222 or accept unauthenticated broker access.
[BuildRelay operations](buildrelay/implementation-and-operations.md).

### ReleaseFence: PostgreSQL and private keys

Install and maintain a dedicated PostgreSQL database; do not use a superuser or
BYPASSRLS role for the API/worker. In a private operator shell, follow the exact
[installation procedure](releasefence/implementation-notes.md) to configure
`RELEASEFENCE_ADMIN_DATABASE_URL` and a new `RELEASEFENCE_DATABASE_PASSWORD`, then:

```powershell
.\.venv\Scripts\python.exe -m releasefence_api.operations keys var/releasefence-private-keys.json
.\.venv\Scripts\python.exe -m releasefence_api.operations install
```

The commands do not load `.env` themselves; supply the operator settings in that
operator process. The private key file must not already exist. Apply Windows ACLs.
Transfer only the non-admin runtime DSN, generated runtime keys and explicit app
admin settings into private service configuration; close the operator shell.
Do not put administrative DSNs in the shared runtime `.env`.

MLflow/Phoenix are separately enrolled dependencies, not services automatically
started by `releasefence-up`. Use the owned OSS profile/runbook when chosen; never
expose backend admin ports or assume tracing is working because the UI opens.
The customer gateway/connector is a separate runtime, not the control-plane worker
and not an automatically installed Codex endpoint.
[Deployment limits](releasefence/operations.md).

### RepairClaim: isolated parser and explicit owner

As the runtime account, with a functioning local Docker Linux engine:

```powershell
docker version
docker info --format '{{.OSType}}'
docker build -t repairclaim-parser:0.1 -f infra/repairclaim-parser/Dockerfile .
.\.venv\Scripts\python.exe -m repairclaim_api.cli --data-dir C:/AICohort/ai-cohort/var/repairclaim provision owner
```

`OSType` must be `linux`. Provisioning prompts for a password; it does not borrow
another product's account. Verify Docker/named-pipe access as the scheduled user,
including after reboot without an interactive desktop login. Docker Desktop being
installed or its helper service running does not prove the Linux engine is ready.

RepairClaim deliberately selects the local Windows Docker named pipe and does not
honour an arbitrary remote Docker context. The image is not pulled at parse time.
Its base/dependency versions and PyMuPDF licensing need deployment review. Keep
Jev disabled for the requested Codex deployment. Enable `REPAIRCLAIM_ENABLE_CODEX=1`
only after the runtime smoke check and explicit owner-approved bounded analysis.
Programme captures/review/activation are separate operator actions; an empty
registry is not a complete coverage search. [RepairClaim operations](repairclaim/operations.md).

For the remaining products, follow their linked delivery-pack runbooks for actual
corpus acquisition and account/grant setup. A clean clone intentionally does not
contain your previous local datasets, keys, private cases or accepted grants.
[All delivery packs](README.md).

## 8. Start and verify locally before configuring the tunnel

Check for conflicting listeners first:

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -ge 8000 -and $_.LocalPort -le 8011 } |
  Select-Object LocalAddress, LocalPort, OwningProcess
```

For convenience, existing dev launchers manage owned API/worker processes and
load `.env` for products 1-11:

```powershell
.\.venv\Scripts\python.exe scripts\dev_stack.py up
.\.venv\Scripts\python.exe scripts\dev_stack.py status
.\.venv\Scripts\python.exe scripts\dev_stack.py down

# Example for another product; choose one product ID from the map.
.\.venv\Scripts\python.exe scripts\dev_stack.py --product resolvedesk up
.\.venv\Scripts\python.exe scripts\dev_stack.py --product resolvedesk status
.\.venv\Scripts\python.exe scripts\dev_stack.py --product resolvedesk down
```

Use these for loopback commissioning, not as startup-task actions: `up` detaches
children and exits, so Task Scheduler would not supervise the continuing worker.
Dev logs are not the service runner's rotating logs. Don't run a dev launcher and
scheduled tasks for the same product simultaneously.

### Foreground recipe, including the products without an installer

Run from the repository root. In one PowerShell window, select product and `api`:

```powershell
$env:COHORT_PRODUCT = 'repairclaim'
$env:COHORT_ROLE = 'api'
$env:PYTHONUTF8 = '1'
@'
import os
import runpy
from scripts.dev_stack import environment

os.environ.update(environment())
products = (
    'tenderlens', 'resolvedesk', 'propertybrief', 'patchdesk', 'relaydesk',
    'clausegate', 'catalogbridge', 'buildrelay', 'casecouncil', 'shelfproof',
    'releasefence', 'repairclaim',
)
product = os.environ['COHORT_PRODUCT']
role = os.environ['COHORT_ROLE']
if product not in products or role not in {'api', 'worker'}:
    raise SystemExit('Choose a listed product and api/worker role')
if role == 'api':
    import uvicorn
    uvicorn.run(
        f'{product}_api.api:app_from_env', factory=True,
        host='127.0.0.1', port=int(os.environ.get(f'{product.upper()}_PORT', 8000 + products.index(product))),
        proxy_headers=True, forwarded_allow_ips='127.0.0.1', access_log=False,
    )
else:
    runpy.run_module(f'{product}_api.worker', run_name='__main__')
'@ | .\.venv\Scripts\python.exe -
```

In a second window, use the **same block** with `COHORT_ROLE='worker'` and the same
product/root/configuration. This is a foreground diagnostic recipe, not new
supervised-service packaging. Ctrl+C stops the foreground run; inspect descendants
and jobs afterward. Start with fresh state: restarting existing state may resume
previously authorized outbound work in products that support it.

For local RepairClaim, use the loopback public origin until commissioning passes.
The foreground loader reads the selected host's `.env`; the existing RepairClaim
dev launcher can instead be used after setting its environment explicitly, but
does not itself read that file.

Verify the selected port, app login and worker result. A loopback health example:

```powershell
Invoke-RestMethod http://127.0.0.1:8011/health/ready
```

Once RepairClaim has its HTTPS public origin, that bare loopback Host is rejected
by its trusted-host middleware. Probe locally with the matching Host instead:

```powershell
Invoke-RestMethod http://127.0.0.1:8011/health/ready -Headers @{ Host = 'repairclaim.example.com' }
```

Its dev launcher's bare-loopback readiness probe can consequently fail in public-
origin mode. Use the foreground/service commissioning path with an origin-aware
probe; do not claim `repairclaim-up` is qualified for that mode or loosen trusted
hosts to bypass the issue. Health checks do not prove successful inference or
fresh source data; TenderLens readiness in particular is primarily a store check.

## 9. Protected Cloudflare exposure

Before publishing DNS, create an Access self-hosted application/policy covering
each intended hostname. Initially allow only your selected identity; keep app login
enabled too. Test denied access separately. Access is not configured by the YAML.
[Cloudflare Access setup](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/).

Create the tunnel only in your own Cloudflare account/domain:

```powershell
cloudflared.exe tunnel login
cloudflared.exe tunnel create ai-cohort-laptop
```

Keep the resulting credential JSON private. Create a host-local configuration
outside the repo, such as `C:\AICohort\private\cloudflared\config.yml`. Do not
overwrite existing tunnel configurations. Replace `example.com`, UUID and the
credential path in this complete **route plan**; enable only commissioned products:

```yaml
tunnel: REPLACE_WITH_TUNNEL_UUID
credentials-file: C:/AICohort/private/cloudflared/REPLACE_WITH_TUNNEL_UUID.json
ingress:
  - hostname: tenderlens.example.com
    service: http://127.0.0.1:8000
  - hostname: resolvedesk.example.com
    service: http://127.0.0.1:8001
  - hostname: propertybrief.example.com
    service: http://127.0.0.1:8002
  - hostname: patchdesk.example.com
    service: http://127.0.0.1:8003
  - hostname: relaydesk.example.com
    service: http://127.0.0.1:8004
  - hostname: clausegate.example.com
    service: http://127.0.0.1:8005
  - hostname: catalogbridge.example.com
    service: http://127.0.0.1:8006
  - hostname: buildrelay.example.com
    service: http://127.0.0.1:8007
  - hostname: casecouncil.example.com
    service: http://127.0.0.1:8008
  - hostname: shelfproof.example.com
    service: http://127.0.0.1:8009
  - hostname: releasefence.example.com
    service: http://127.0.0.1:8010
  - hostname: repairclaim.example.com
    service: http://127.0.0.1:8011
  - service: http_status:404
```

The repository's existing [example](../infra/cloudflare/config.example.yml) stops
at ShelfProof; it does not already include ReleaseFence/RepairClaim. The map above
is the twelve-product plan. Preserve the original Host header; do not override it
to `localhost` for origin-bound apps. Uvicorn may trust forwarded headers only from
the loopback proxy, never arbitrary external clients.

For each enabled hostname, configure the exact HTTPS origin/cookies, restart its
API/worker, validate ingress, create the DNS route and run the tunnel:

```powershell
cloudflared.exe tunnel --config C:/AICohort/private/cloudflared/config.yml ingress validate
cloudflared.exe tunnel route dns ai-cohort-laptop tenderlens.example.com
# Repeat DNS routing only for the other hostnames you actually enabled.
cloudflared.exe tunnel --config C:/AICohort/private/cloudflared/config.yml run ai-cohort-laptop
```

These are explicit Cloudflare account/DNS changes when executed on the laptop;
none were performed while writing this guide.
[Official local-tunnel procedure](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/create-local-tunnel/).

BuildRelay's external GitHub webhooks cannot complete interactive Access login.
If enabled, review a narrowly scoped exception for **only** `/hooks/github/{repo_id}`;
keep HMAC signature and replay checks, app routes and every other product protected.
Never bypass Access for the whole hostname just to make a webhook work. ReleaseFence
machine clients require both an appropriate edge authentication method and their
application-scoped credentials; an interactive Access login is not a machine token.

## 10. Boot startup and service identities

First demonstrate local function, then configure persistent startup. For each of
the nine supplied installers, use an elevated **operator** PowerShell with an
explicit limited runtime credential. Example:

```powershell
$CohortCredential = Get-Credential -Message 'Limited Windows runtime account'
.\infra\windows\install-resolvedesk.ps1 -RepoPath C:\AICohort\ai-cohort -Credential $CohortCredential -Start
Get-ScheduledTask -TaskName 'AI-Cohort-ResolveDesk-*'
Get-ScheduledTaskInfo -TaskName 'AI-Cohort-ResolveDesk-api'
```

Select the exact installer from the map for the next product. Install one at a
time; scripts refuse existing task names instead of replacing them silently.
They start foreground `run_product_service.py` roles, restart on failure and use
bounded rotating logs under `var/<product>-service/`. Task registration may require
batch-logon rights; verify the effective account, working directory, Python path,
PATH and CLI auth from the actual task, not just the operator's terminal.

There is no tested unattended installer for TenderLens, ReleaseFence or RepairClaim.
Keep their foreground commissioning explicit until equivalent foreground-role
Task Scheduler/service packaging, log rotation and child shutdown are implemented
and accepted. Do not register `dev_stack.py up` as a substitute supervisor. A
completed manual setup does not mean all twelve are reboot-durable yet.

Configure cloudflared's separate Windows service with the actual service identity's
credential/config paths, not an assumed interactive `%USERPROFILE%`. Follow the
[official Windows service instructions](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/as-a-service/windows/)
and inspect the registered executable/config path before starting it. Keep this
administrative network connector separate from the limited application/Codex user.
No blanket admin execution for product workers. Validate tunnel reconnection on
boot and local dependencies before claiming remote readiness.

Starting a task and receiving a success registration message is not acceptance.
Verify processes, authenticated requests, job completion, logs and health. Killing
an API/worker must not leave a live Codex child consuming allowance indefinitely.
Dependency startup ordering, Docker readiness and failure recovery remain host tests.

## 11. Capacity, backups and updates

Do not start twelve simultaneous analyses because twelve UIs are reachable. Workers
have product-specific queues/limits; there is **no demonstrated portfolio-wide
Codex admission controller**. Initially admit one expensive analysis/OCR operation
across the laptop, manually, and increase only with measured memory, queue latency,
CPU, disk pressure and account usage. A product's grant is not another's grant.

Observe the host with Task Manager/Resource Monitor and record safe aggregate
metrics. Keep private prompts, documents, tokens and login logs out of telemetry.
PostgreSQL, NATS, Docker and tracing backends need independent persistence and
health checks; a green Cloudflare connector does not prove they are available.

Before real data, configure a private backup destination and run a restore drill.
Use each product's consistent backup procedure, not a casual copy of a running
SQLite file without WAL handling. Preserve independent erasure/authority/usage
ledgers and model/source manifests. Restore into a new quarantined location;
never overwrite live state or roll back usage/approval/deletion authority.

ReleaseFence needs database backup plus separately protected keys and external
state. RepairClaim has encrypted `.rcbk` backups and requires the current deletion
ledger at restore. Other product details are in their runbooks. Exported/downloaded
copies are not remotely erased by deleting an application account.

For updates: block new analysis, let safe work settle or cancel it through the app,
record unresolved side effects, stop only owned roles, take consistent backups,
record the old commit/dependency/image versions, deploy a reviewed revision, build
serially and repeat smoke checks. Do not `git reset --hard` a dirty deployment or
blindly downgrade a migrated live database. Test CLI and parser upgrades separately.

## 12. Laptop acceptance checklist

Save results privately in `var/windows-acceptance/` with commit ID, tool versions,
product, time, expected/actual outcome, failures and redacted evidence. A checklist
item is not passed merely because its command was written here.

- [ ] Supported updated OS, adequate resources, protected runtime account/ACLs.
- [ ] All enabled frontends build; only intended loopback listeners exist.
- [ ] Each app/worker uses its own store, credentials, ledgers and configured port.
- [ ] Codex Python-adapter smoke succeeds under the actual runtime identity with
  an explicitly approved allowance; incompatible flags do not get removed.
- [ ] One separately authorized product workflow completes with evidence review,
  expected uncertainty/approval and correct terminal state; no invented outcome.
- [ ] Unauthenticated edge and app access denied; unauthorized household/tenant
  documents, exports and jobs inaccessible; authenticated origin/CSRF paths work.
- [ ] HTTPS cookies/origins, uploads, rendered previews and approved downloads work
  through the real hostname, including mobile/keyboard paths.
- [ ] RepairClaim container parses/redacts/re-OCRs original bytes; Windows isolation,
  resource limits and no-network policy tested. Native macOS denial evidence is not
  a Windows container pass.
- [ ] BuildRelay webhook signature/replay and authenticated JetStream paths tested
  separately if both transports are enabled; no public broker/admin listener.
- [ ] ReleaseFence DB/RLS and enrolled tracing/read-back/canary/rollback paths
  tested against authorized targets; unverified rollback is not reported success.
- [ ] Worker crash, timeout, quota exhaustion, lost network, stale approval, low
  disk and cancelled/erased case preserve authority and bounded recovery.
- [ ] Full reboot without interactive app login starts dependencies, roles and
  tunnel; no orphan Codex children, duplicated workers or resurrected authority.
- [ ] Backup restores into quarantine with current independent ledgers and fresh
  access/approvals; previously downloaded files aren't promised deleted.
- [ ] One-hour soak at the intended admitted concurrency has recorded latency,
  memory/disk behaviour and no scope leakage. Targets are defined before measuring.

For engineering tests on Windows, provision a **separate disposable test PostgreSQL
instance** and set `RELEASEFENCE_TEST_ADMIN_DSN` only in the test shell. The macOS/
Linux `pgserver` fallback is not installed on Windows. Never point those tests at
the serving database. General tests don't intentionally call live models, but
opt-in live/acceptance campaigns can; read their grant requirements first.

RepairClaim's opt-in local process suite is:

```powershell
$env:REPAIRCLAIM_PROCESS_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest tests/test_repairclaim_process.py -q
```

One test is specifically macOS-native and skips on Windows; it does not certify
Windows sandbox denial. An expected skip must be recorded, not counted as a pass.
Likewise, a product's remaining source-quality/customer gates do not disappear
after successful deployment. Preserve [current product limits](README.md).

## 13. Troubleshooting order

| Symptom | First checks |
| --- | --- |
| Works in your shell, fails at boot | Actual task user, native Codex/Python PATH, auth store, working directory, batch-logon rights, dependency readiness |
| `Codex invocation failed` / no JSON | Executable vs shim, installed CLI version/flags, service-account login, structured smoke output; no broad sandbox bypass |
| UI opens but jobs never finish | Worker heartbeat, queue/lease, grant/usage holds, model/source network, correct store path |
| RepairClaim readiness fails | Docker Linux engine under runtime user, local named pipe, built image, parser log, matching Host for configured public origin |
| Login/POST fails behind HTTPS | Exact origin/Host, cookie syntax, Access session, app credentials, CSRF token; do not disable checks |
| Cloudflare 502 | Correct loopback port, running API, origin Host and dependency health before changing DNS |
| Webhook hits Access login | Review only the exact BuildRelay HMAC webhook exception; don't expose its entire hostname |
| ReleaseFence tests fail importing `pgserver` | Dedicated Windows test DSN absent; do not use serving DB to make the suite green |
| Host swaps or freezes | Stop admitting expensive work, reduce active products, inspect Docker/ONNX/DB/tracing memory; don't promise all-product concurrency |

End state: an owned, protected single-laptop pilot with recorded limitations. Public
commercial hosting, unsupported hardware workarounds and uptime guarantees need a
separate decision and evidence; this guide has not deployed anything or consumed
model allowance on the laptop.
