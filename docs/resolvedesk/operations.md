# Operations and deployment plan

The local launch, worker, acquisition, backup/restore, and service-entrypoint commands below are implemented. Windows startup-task installation and Cloudflare configuration await target-host acceptance; they have not been executed on this macOS host.

## Runtime layout

The target Windows laptop runs a dedicated ResolveDesk API/static host and one worker, with a separate product data directory and loopback port (proposed 8001). TenderLens retains its existing service, port, and data. Cloudflare Tunnel maps a distinct product hostname to ResolveDesk; Access protects remote entry. Do not expose the Codex executable, search credentials, source store, or database through the tunnel.

Run services under a dedicated least-privilege account that can access its own data, the installed Codex executable, and required network endpoints. Verify the service account can authenticate noninteractively after reboot. An interactive terminal success does not establish service readiness. Measure performance with both challenge products running before promising concurrent workloads on the laptop.

## Configuration

| Variable | Purpose |
| --- | --- |
| `RESOLVEDESK_DATA_DIR` | Private product DB, source snapshots, exports, and checkpoints |
| `RESOLVEDESK_HOST`, `RESOLVEDESK_PORT` | Default `127.0.0.1` and separate product port |
| `RESOLVEDESK_USERNAME`, `RESOLVEDESK_PASSWORD` | Pilot application authentication; not long-term multi-user identity |
| `CODEX_COMMAND` | Installed host executable, preferably an explicit validated path |
| `RESOLVEDESK_SEARCH_PROVIDER` | `postgresql` by default; optional `brave` or explicit `disabled` |
| `BRAVE_SEARCH_API_KEY` | Search credential loaded by the service; never included in logs or browser code |
| Source allowlist | Enforced in code: HTTPS `www.postgresql.org/docs/16/` or `/17/`, without credentials or nonstandard ports |
| `RESOLVEDESK_RUN_TIMEOUT_SECONDS` | Run wall-clock budget; proposed 600 seconds |

Configuration is documented in [`.env.example`](../../.env.example). Default remote PostgreSQL site search needs no key. Brave requires its key; missing credentials produce an unavailable state. The development launcher can reuse TenderLens credentials if explicit ResolveDesk credentials are absent; the Windows service runner requires explicit product credentials.

## Failure and retry behavior

| Failure | Expected operational behavior |
| --- | --- |
| Codex timeout/auth/quota/capacity | Record safe provider event, retain prior checkpoints and validated candidates, expose retry |
| Search 401/429/outage | Explain unavailable fallback; do not reclassify weak local evidence as supported |
| Fetch timeout/unsupported page | Keep other validated sources, log the missing source, obey page/run budget |
| Invalid retrieval/search/tool payload | Reject before generation, log contract stage, do not reuse unvalidated content |
| Validation retry budget exhausted | Fail generation safely; preserve earlier evidence and provide escalation |
| Worker death | Reclaim stale lease and resume durable stages; approved revisions unchanged |
| Source refresh fails | Retain prior published index; record stale-source status |
| Disk full/storage failure | Stop new work and report not ready; never claim checkpoint/approval was saved |

Use one worker initially. Lease duration must exceed the maximum single external-call interval, with heartbeats between stages. All external retries are bounded by both stage and run budgets. Service restart backoff must not cause an endless high-cost investigation loop.

## Fetch and privacy boundaries

Only the fetch adapter makes external page requests. Enforce HTTPS, allowed host/path, bounded response size/content type, redirect validation, and checks against loopback/private/link-local destinations. Revalidate destination addresses for every connection; a search result or source document cannot override the policy. Preserve safe failure reasons without revealing internal hostnames.

Construct search queries from permitted public terms rather than sending raw tickets. Credentials, customer names, private domains, and connection strings remain local product data. Send only the bounded approved evidence needed for generation through Codex; a locally installed CLI still uses the model service. Private runbooks require explicit source approval and documented handling expectations.

## Backup, restore, retention

The backup command uses SQLite's online backup mechanism and verifies integrity; copying only the main DB while ignoring live WAL state is insufficient. Normalized source snapshots, evidence, reviews, events, and export records are stored in SQLite. Raw corpus HTML/manifests are separate evaluation artifacts. Store backups outside the active data directory with appropriate access control.

Restore into an isolated directory/port, run integrity checks, verify source hashes, open a reviewed revision, and confirm its citations still resolve. Proposed pilot recovery targets: RPO 24 hours and RTO 60 minutes, pending an actual measured drill. Define retention with the pilot team before accepting private tickets; expired source material and associated exports require a deliberate policy, not blanket automatic deletion.

## Target-host acceptance checklist

- Cold start and reboot bring the API and worker up under the service account.
- Codex auth, timeout, quota, and network outage produce recoverable states.
- Real official-source search works; optional Brave credentials and disabled search states are handled explicitly.
- Unauthorized local and tunneled requests cannot read cases, internal evidence, or exports.
- Cloudflare Access sign-in, expiry, and revocation are tested on the actual hostname.
- Backup restore preserves approved reply text, source snapshots, reviews, and audit history.
- Memory, CPU, disk, and latency are measured with realistic corpus size and both products present.
- Update/rollback preserves data schema compatibility and reviewed revisions.

## Executable local commands

```bash
npm --prefix apps/resolvedesk-web ci
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/fetch_resolvedesk_sources.py
make resolvedesk-up
make resolvedesk-status
.venv/bin/python scripts/smoke_resolvedesk_http.py
.venv/bin/python scripts/smoke_resolvedesk_chat.py
make resolvedesk-test
# Opt-in real model and official-site search, with isolated evaluation stores:
make resolvedesk-validate-live
make resolvedesk-down
```

On Windows use `.venv/Scripts/python.exe` and `scripts/dev_stack.py --product resolvedesk up|down|status` if Make is unavailable; build with npm first. This launcher is a development convenience, not a service manager.

The development worker is serial. HTTP smoke scripts should be run sequentially on an idle queue: the clarification/export smoke has a 30-second wait and can time out behind a long model-backed chat. Such a timeout is not a worker crash and must not be reported as a passing check. Chat latency and queue latency are distinct; no concurrent-user SLA has been demonstrated.

Consistent backup and restore into a new directory:

```bash
.venv/bin/python scripts/resolvedesk_backup.py var/backups/resolvedesk-2026-10-13 --data-dir var/resolvedesk
.venv/bin/python scripts/resolvedesk_restore.py var/backups/resolvedesk-2026-10-13 var/resolvedesk-restored
```

Choose a fresh backup destination each time. Restore checks SQLite integrity and source hashes, refuses an existing destination, and does not replace live data. Open the restored DB on an isolated port and verify reviewed replies before choosing a recovery cutover.

## Windows startup packaging

[`install-resolvedesk.ps1`](../../infra/windows/install-resolvedesk.ps1) registers two startup tasks under an explicit credential with limited run level. It preflights the Python/web build and refuses to overwrite existing tasks. It does not provision Codex authentication, Cloudflare, or file ACLs. This is Task Scheduler packaging, not a Windows SCM service; validate restart and child-process behavior on the laptop.

```powershell
$TaskCredential = Get-Credential
.\infra\windows\install-resolvedesk.ps1 -RepoPath 'C:\apps\ai-cohort' -Credential $TaskCredential -Start
```

Tasks run `scripts/run_product_service.py`, which loads configuration, requires explicit credentials, and rotates role logs (5 MB × four files). The [Cloudflare example](../../infra/cloudflare/config.example.yml) contains a ResolveDesk hostname placeholder; actual DNS, tunnel identity, and Access policies still require configuration and acceptance.
