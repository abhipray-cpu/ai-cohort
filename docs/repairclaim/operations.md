# Operations — implemented local lifecycle and Windows qualification plan

The API/static React app, worker, dedicated launcher, up/down/status and operator
CLI are implemented. Actual up/status/down passed against a temporary account and
free loopback port; only the two processes created by that check were stopped.
Windows/container/tunnel installation and performance qualification remain open.

## Run locally without acquiring real data

Install the monorepo editable package after adding this product and install the web
dependencies. No command below enables source fetching, real Codex calls or claims.

```bash
.venv/bin/python -m pip install -e .
npm --prefix apps/repairclaim-web ci --ignore-scripts
export REPAIRCLAIM_DATA_DIR="$PWD/var/repairclaim"
export REPAIRCLAIM_PUBLIC_ORIGIN=http://127.0.0.1:8011
.venv/bin/python -m repairclaim_api.cli provision your-username
make repairclaim-up
make repairclaim-status
make repairclaim-down
```

Provisioning prompts twice for a new password and never writes it to a config file.
There are no default credentials. Existing .env settings, other product users and
Codex authentication are not imported. On Windows use .venv/Scripts/python.exe and
set the corresponding environment variables; Make targets select that executable.
The launcher refuses occupied ports/existing managed state and binds only loopback.

The [environment template](../../infra/repairclaim.env.example) describes explicit
options. For Windows/Linux build the [restricted parser image](../../infra/repairclaim-parser/Dockerfile)
as repairclaim-parser:0.1 and set REPAIRCLAIM_PARSER=container. The image is never
pulled automatically at parse time. This container path has not been qualified on
the target Windows laptop. Native macOS sandbox/OCR process checks have passed.
Docker parsing explicitly targets the local Unix socket or Windows named pipe;
ambient remote Docker contexts are ignored. Podman is local-only. Unsupported
engine/runtime configurations fail closed rather than exporting private files.

## Explicit operator registry and recovery actions

```bash
# Captures a previously acquired official PDF; parses in the restricted runner.
.venv/bin/python -m repairclaim_api.cli capture SOURCE_ID https://static.nhtsa.gov/REVIEWED.pdf /path/to/acquired.pdf
# Definition must use immutable captured hashes, exact pages/quotes and reviewer metadata.
.venv/bin/python -m repairclaim_api.cli activate-programme /path/to/reviewed-definition.json
.venv/bin/python -m repairclaim_api.cli registry
.venv/bin/python -m repairclaim_api.cli backup
# Restore target MUST NOT exist. Supply the CURRENT externally held deletion ledger.
.venv/bin/python -m repairclaim_api.cli --data-dir /new/restore-target restore /path/to/backup.rcbk --erasure-ledger /current/erasure.jsonl
.venv/bin/python -m repairclaim_api.cli --data-dir /new/restore-target activate-restored
.venv/bin/python -m repairclaim_api.cli maintain
```

Paths/URLs above are placeholders, not acquired evidence. Source checking is
disabled by default. REPAIRCLAIM_ENABLE_SOURCE_CHECKS=1 enables bounded scheduled
official checks (24-hour due interval, stale after 48 hours). Programme changes
require operator review before activation; the worker rematches only separately
consented, retained cases. REPAIRCLAIM_ENABLE_CODEX=1 exposes the optional advisory
path, but each exact context still needs owner approval and a finite allowance.
Do not enable it as a substitute for campaign authorization.

Backups prompt for a separate passphrase, are encrypted and stored in managed
backups/repairclaim-*.rcbk paths. Maintenance removes those older than 30 days.
Externally copied exports/backups cannot be recalled. Never restore without the
current erasure ledger. Restore revokes all sessions/approvals and quarantines
access until explicit operator activation.

## Proposed runtime

Independent FastAPI API/static React build and one durable worker/scheduler under
a restricted Windows service account. Dedicated `var/repairclaim/` private state,
separate cache/backups and source registry. Proposed loopback port 8011, checked
for conflict before implementation. Reuse public shared library interfaces, not old
product credentials, processes, data or campaign budgets. UI/API same-origin.

Developer up/down/status/test targets now exist; backup/restore are explicit CLI
commands above, not an invented Make target. Actual-data campaign tooling belongs
to the next separately scoped phase. The Python launcher includes Windows process
handling but is not a Windows service installer. Up/down
must own only this product's verified process IDs. Startup must not fetch public
data, query a model, renew consent or start an unapproved live campaign.

## Host preflight

Inventory OS support, service-account ACLs, available RAM/CPU/disk, disk encryption,
OCR/parser binaries and licenses, Codex service-account authentication, clock sync,
backup destination/key, ports and Cloudflare route ownership. Do not alter model
settings/authentication or assume login from a different OS user is available.
Measure with other products idle and under the intended portfolio admission policy.
If isolation/capacity fails, report and re-plan; no silent move to external hosting.

## Tunnel and authentication

Bind only loopback. Protected Cloudflare Tunnel exposes application routes, never
Codex, database, document directories, metrics admin or worker control. An access-
controlled pilot can admit nominated consumers; do not claim public self-serve
SaaS onboarding. Validate edge identity/proxy headers, app sessions, HTTPS cookie
behaviour, upload limits, CSRF, cache-control/no-store and direct-origin denial.
Detailed health/readiness and operator routes remain private. Never paste keys
into docs or expose them through subprocess arguments/logs.

## Health and observability

Implemented liveness checks process response only. Implemented readiness checks
store/quarantine, worker heartbeat and parser startup probe without paid/network calls.
Disk reserve, alert delivery, service-account ACLs and load SLOs below are deployment
qualification work, not current readiness assertions. Readiness is not
source freshness, programme correctness or successful inference. Show separate
source last-success age, pending registry review, stale approvals, job/lease age,
queue depth, failures/validation retries, unknown usage holds, consent expiry,
deletion backlog, backup age and aggregate latency. No private payload tracing.

Source freshness warning after 48 hours without a successful scheduled check is a
proposed pilot default; source-specific policy can be stricter. A stale programme
can remain readable as historical evidence but cannot support a newly finalized
coverage packet until reconfirmed under its reviewed policy. Alert operator on dead
letters, worker outage, disk pressure, erasure delay and backup failure. Alerts
carry safe IDs, not consumer documents, and have rate limits/deduplication.

## Initial performance targets, not measured promises

With 5 concurrent household sessions, 100 retained cases and 1,000 public-source
records: local non-analysis API p95 under 500 ms, first partial result or explicit
waiting state within 60 seconds for a 10-page text document, no unbounded memory
growth or cross-household leakage during a one-hour soak. Scanned/OCR jobs have
visible progress and may take longer; analysis deadline is explicit in casework.
Measure actual host RSS/CPU/disk/latency and record capacity limits before launch.
Do not imply an uptime SLA from one laptop or the tunnel provider's availability.

## Runbooks to implement and exercise

Source unavailable/revoked: stop new authority, mark stale, preserve history and
contact owner through in-app status. Provider outage: partial result and bounded
hold. Clock jump: pause deadline automation. Lost credentials: stop affected jobs,
never borrow another product's identity. Suspected leakage: disable access, preserve
minimal safe incident evidence and follow reviewed notification policy. Corrupt store:
read-only/offline mode, restore to quarantine and reconcile tombstones before serve.

Backup targets: daily consistent encrypted snapshots; recovery-point target 24 h
and recovery-time target 4 h after a usable backup/host are available. These are
proposed drill targets, not proven RPO/RTO. Restore, Windows restart, sleep/wake,
low disk, proxy and concurrent portfolio behaviour remain release gates.
