# PropertyBrief operations

Updated 15 October 2026. Local macOS startup/shutdown, authenticated HTTP, tests and backup/restore logic are verified. Windows startup, reboot, resources and protected Cloudflare access remain target-host acceptance gates.

## Install and start locally

From the repository root, with Python 3.12, Node/npm and installed authenticated Codex:

```bash
.venv/bin/python -m pip install -e '.[dev]'
npm --prefix apps/propertybrief-web ci
make propertybrief-up
make propertybrief-status
make propertybrief-down
```

The launcher builds the web client and launches API/worker on loopback http://127.0.0.1:8002/. It loads `.env`; shell variables take precedence. Development startup can reuse existing TenderLens credentials if explicit PropertyBrief credentials are absent. The browser requests those configured HTTP Basic credentials. No password is included in documentation. The launcher refuses starting over an already-running managed stack: stop it first when loading new worker code. PID state/development logs live in ignored `var/propertybrief-dev/`.

On Windows without Make, first build with `npm --prefix apps/propertybrief-web run build`, then use:

```powershell
.\.venv\Scripts\python.exe scripts/dev_stack.py --product propertybrief up
.\.venv\Scripts\python.exe scripts/dev_stack.py --product propertybrief status
.\.venv\Scripts\python.exe scripts/dev_stack.py --product propertybrief down
```

The development launcher is not Windows service acceptance. Product stores/processes are independent from TenderLens and ResolveDesk.

## Actual configuration

| Setting | Meaning |
| --- | --- |
| `PROPERTYBRIEF_USERNAME`, `PROPERTYBRIEF_PASSWORD` | Explicit product credentials required by foreground/service startup; missing or placeholder values refused |
| `PROPERTYBRIEF_DATA_DIR` | SQLite directory, default `var/propertybrief` |
| `PROPERTYBRIEF_HOST`, `PROPERTYBRIEF_PORT` | Development bind defaults loopback/8002; service runner deliberately binds loopback |
| `PROPERTYBRIEF_CODEX_COMMAND` | Executable name/path; fallback `CODEX_COMMAND`, then `codex` |
| `PROPERTYBRIEF_RUN_TIMEOUT_SECONDS` | Worker deadline from first claim, default 900 seconds |
| `NYC_OPEN_DATA_APP_TOKEN` | Optional source application token, server-side only |

Action/model/HTTP/byte/page/context limits are fixed application policy, not extra environment variables. See [agent-loop](agent-loop.md). There is no automatic TTL refresh: follow-ups reuse pinned evidence until explicit refresh. No retention deletion/garbage collector is enabled.

Codex uses the service account's authentication and network connection. Source APIs also need outbound HTTPS/DNS. Pinned evidence remains reviewable without new generation, but this is not offline inference. Product users never receive direct CLI access. Runtime restrictions and native-tool event auditing are described in [architecture](architecture.md).

## Windows startup packaging

After dependencies, UI build, explicit product credentials and Codex verification under the intended Windows account:

```powershell
$PropertyBriefCredential = Get-Credential
.\infra\windows\install-propertybrief.ps1 -RepoPath 'C:\ai-cohort' -Credential $PropertyBriefCredential -Start
Get-ScheduledTask -TaskName 'AI-Cohort-PropertyBrief-*'
```

The installer creates separate `AI-Cohort-PropertyBrief-api` and `AI-Cohort-PropertyBrief-worker` startup tasks, refuses existing task names, and sets restart-on-failure. It does not silently overwrite tasks. Password material is passed to Task Scheduler, not written into repo scripts. Validate account logon rights and Codex availability after sign-out/reboot on the actual laptop.

Tasks run `scripts/run_product_service.py <api|worker> --product propertybrief`. Service logs rotate at 5,000,000 bytes with three backups per role in `var/propertybrief-service/`. Development logs are not this rotating service stream. CLI timeouts kill a tracked subprocess group on POSIX; Windows uses `taskkill /T /F`. The Windows branch still needs a real descendant-process test.

`infra/cloudflare/config.example.yml` includes a PropertyBrief origin route on 8002. It is an example, not an installed tunnel/verified Access policy. Require Access and HTTPS, keep origin loopback-only, and verify denied case/snapshot/export access without credentials. Shared Basic auth is a private single-team pilot boundary, not multi-tenant SaaS authorization.

## Health, queue and recovery

`GET /health/live` checks the process; `/health/ready` checks SQLite and reports worker heartbeat. Readiness does not prove provider/source availability. Authenticated `/v1/runs/{id}` exposes counters, events, coverage and preview without raw lease tokens. Full snapshots require authenticated evidence endpoints.

One worker/run is active per store; pending jobs cap at 20. Enqueue/resume are idempotent. Leases fence stale writers; expiry permits checkpoint recovery with original deadline and persisted counters. Explicit resume preserves observations/cumulative counters, up to two grants. Cancellation is cooperative: an in-flight model call can take up to its 120-second/remaining-deadline bound before cancellation is observed.

Failed pages, metadata requests, drift, schema rejection or caps remain gaps. A later provider timeout leaves earlier observations and a failure-stage event. Do not relabel a partial pack complete to make a check pass. Refresh produces a new evidence revision; old reports/exports remain pinned.

Proposed resource acceptance remains unmeasured on Windows: idle combined API/worker RSS below 400 MiB, active peak below 1 GiB, acceptable queue latency alongside earlier products. Functional latency is not an SLA.

## Backup and restore

Raw snapshots, normalized evidence, reports, reviews and export payloads live in `propertybrief.sqlite3`. Use its online consistent backup, not a live file copy without WAL handling:

```bash
.venv/bin/python -m propertybrief_api.backup backup var/propertybrief var/backups/propertybrief-new
.venv/bin/python -m propertybrief_api.backup restore var/backups/propertybrief-new var/propertybrief-restored
```

Both commands refuse existing destinations. Backup verifies SQLite integrity/source raw hashes and writes a file-checksum manifest. Restore verifies manifest/evidence hashes, preserves reports, and expires stale leases. Restore into a new directory, inspect it, stop services, and explicitly select the new data directory for cutover. Never overwrite live storage as a restore test. Rotated logs/optional evaluation corpora are outside this product-store backup.

Tests cover evidence/report preservation, tamper rejection, non-overwrite behavior and single-worker ownership. Before updates, back up and record code/schema versions; automatic migration/rollback across arbitrary future schemas is not promised. Pilot retention was proposed at 90 days, but no deletion policy is active or authorized.

## Validation commands and open drills

```bash
make propertybrief-test
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python scripts/smoke_propertybrief_http.py
# Optional actual public-source/model usage:
.venv/bin/python scripts/smoke_propertybrief_http.py --live
.venv/bin/python scripts/validate_propertybrief.py --corpus var/propertybrief-corpus/20261014-final --all
.venv/bin/python scripts/validate_propertybrief.py --corpus var/propertybrief-corpus/20261014-final --live --case 375411
```

The frozen corpus is local ignored data; new checkouts must acquire a new capture using [data instructions](../../data/propertybrief/README.md). Freeze counts are not promised for changing public data.

Still required: browser/viewport/accessibility journeys; Windows startup/reboot/sign-out/auth; resource measurements with all products; process-tree cancellation; actual disk-full recovery; protected tunnel revocation; independent semantic/gold quality review and customer effort/value evaluation. See [validation](validation-2026-10-15.md).
