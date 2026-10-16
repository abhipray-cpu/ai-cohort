# Operations and validation runbook

Status: runnable pilot on macOS; Windows/Cloudflare acceptance remains open. Local application code invokes the installed Codex CLI, not an LLM API. Codex inference/public sources still need outbound network/authentication.

## Install and start

From the repository root, using Python 3.12 and Node/npm:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
npm --prefix apps/patchdesk-web ci
make patchdesk-up
make patchdesk-status
make patchdesk-down
```

On Windows Python is `.venv\Scripts\python.exe`; use the service runner if Make is unavailable. `patchdesk-up` builds the UI and starts independent API/worker processes on loopback port 8003. Open http://127.0.0.1:8003/. Logs/PIDs: `var/patchdesk-dev/`; database: `var/patchdesk/patchdesk.sqlite3`. Earlier products retain separate ports/stores/processes.

Create local `.env` from `.env.example` only if absent; preserve existing values. Set a unique password (12+ characters, not a placeholder). Development can reuse TenderLens credentials **only to bootstrap the first PatchDesk admin**, when PatchDesk credentials are absent. Later users have independent hashed passwords/memberships. Changing bootstrap settings does not reset an existing user's password. Never print/commit real values.

The production runner requires explicit PatchDesk credentials and loads `.env` without overriding shell environment. Run as separate supervised processes:

```bash
.venv/bin/python scripts/run_product_service.py api --product patchdesk
.venv/bin/python scripts/run_product_service.py worker --product patchdesk
```

Service logs rotate at 5 MiB with three backups. `/health/live` and `/health/ready` report safe readiness, not private evidence. Service-identity Codex availability remains a separate deployment check.

## Configuration and authority

| Setting | Behavior |
| --- | --- |
| `PATCHDESK_USERNAME`, `PATCHDESK_PASSWORD` | First-store administrator bootstrap only |
| `PATCHDESK_HOST`, `PATCHDESK_PORT` | Default `127.0.0.1:8003`; do not publicly bind origin |
| `PATCHDESK_DATA_DIR` | Default `var/patchdesk`, independent WAL database |
| `PATCHDESK_CODEX_COMMAND`, `CODEX_COMMAND` | Product-specific executable override, falling back to shared CLI setting |
| `PATCHDESK_RUN_TIMEOUT_SECONDS` | Default 900 seconds; original deadline retained on recovery |
| `PATCHDESK_SECURE_COOKIES` | `1` for protected HTTPS tunnel; `0` for loopback HTTP |
| `PATCHDESK_GITHUB_READ_TOKEN` | Optional explicit repository/advisory read connector |
| `PATCHDESK_ENABLE_PUBLISH` | Default `0`; enabling is not issue approval |
| `PATCHDESK_GITHUB_PUBLISH_TOKEN` | Optional explicit connector; target still scoped/approval-bound |

Sign in through the application form. Opaque sessions are hashed at rest, expire after eight hours and use HttpOnly/SameSite cookies; mutations require CSRF. Five failed username attempts throttle for 15 minutes. Admin creates pilot actors; project owners assign analyst/reviewer/publisher roles. Admin alone does not grant read access to every project. No two-person control is claimed.

Projects initially deny public-package and model egress. Import, inspect identities/gaps, explicitly authorize intended public names, then separately enable model egress. Raw manifests, credential URLs and private/unknown dependencies do not enter prompts. Codex receives a minimized environment without product/connector credentials; native tools are disabled/audited. This is not a full OS sandbox.

## Validate actual data

```bash
make patchdesk-test
.venv/bin/python scripts/fetch_patchdesk_sources.py var/patchdesk-corpus/my-new-capture --count 10
.venv/bin/python scripts/validate_patchdesk.py --corpus var/patchdesk-corpus/my-new-capture --all
.venv/bin/python scripts/validate_patchdesk.py --corpus var/patchdesk-corpus/my-new-capture --live
.venv/bin/python scripts/smoke_patchdesk_http.py --live
```

Acquisition/live validation consume network/model usage and refuse overwriting captures/evaluation sessions. HTTP smoke defaults to the acquired `20261015-expanded` corpus; see `--help`. It creates a dedicated validation project, checks auth/CSRF, imports the real Newman pair, explicitly grants scoped egress, waits for the worker, reviews a partial pack, checks Markdown/JSON and asks a follow-up. It never publishes an issue. Credentials are read internally, not output.

Frozen replay is repeatable, not fresh-source coverage. Missing responses remain unavailable, never simulated successful data. Corpus tests explicitly skip when ignored captures are absent; reacquire to run them. Counts may change with source dates.

Manual journey: sign in, select the smoke-created Newman project, inspect cited findings/snapshots, activity routes/counters, coverage/gaps and conversation. Upload your own paired files in a separate project for new work. A match is not demonstrated exploitation; a candidate is not a verified upgrade.

## Limits and recovery

Current measured release blockers: [larger validation](validation-2026-10-16.md). For rigorous frozen replay and separate semantic/coverage audits (use fresh output directories):

```bash
.venv/bin/python scripts/capture_patchdesk_cohort.py var/patchdesk-corpus/my-cohort40 --count 40
.venv/bin/python scripts/audit_patchdesk_quality.py var/patchdesk-corpus/my-cohort40 var/patchdesk-quality/my-oracle-audit
.venv/bin/python scripts/validate_patchdesk.py --corpus var/patchdesk-corpus/my-cohort40 --all --session var/patchdesk-evaluation/my-cohort40
.venv/bin/python scripts/audit_patchdesk_runs.py var/patchdesk-corpus/my-cohort40 var/patchdesk-evaluation/my-cohort40 var/patchdesk-quality/my-coverage-audit
.venv/bin/python scripts/validate_patchdesk.py --corpus var/patchdesk-corpus/my-cohort40 --all --split held_out --live
```

The collector defaults to the existing 10-input freeze as parent; supply `--parent` for another verified input capture. It preserves discovery exclusions, input checkpoints and bounded lookup batches. Its consolidated evaluation index is not one oversized dispatched `ToolResult`. New acquisition can select different latest commits: preserve the original freeze for historical replay. The oracle requires the frontend's installed `semver` dependency and does not load audited project code.

Use `scripts/smoke_patchdesk_http.py --live --corpus <freeze> --repository <captured-repo>` for a distinct real project. Then `scripts/validate_patchdesk_access.py <smoke-report>` checks live scoped/revoked access with a temporary audit actor: roles are revoked and it is logged out; the account remains for audit. `scripts/validate_patchdesk_connectors.py <freeze> <new-directory>` checks configured repository import and actual optional/secondary-provider reads; its primary outage is injected and labelled. No utility creates a third-party issue.

One active investigation; four concurrent reads globally/two per actual provider; 20 queued. Per grant: 128 actions/HTTP attempts, eight model calls, 64 MiB source bytes; maximum two grants. Model timeout 120 seconds; HTTP 20; remaining deadline applies. Inputs cap at 5,000 entries/2,000 public version queries, 60 details, 12 initial release lookups, eight EPSS enrichments and 16 fixed-version targets. Caps/sampling remain gaps. See [orchestration](orchestration.md).

Node snapshots persist independently; later failures finalize durable partial evidence with stage events. Follow-ups reuse successful/partial results; additional requests or failed nodes can require new authorized reads. Refresh explicitly reacquires. Cancel/resume is not unlimited retry. Recovery retains original counters/deadline with lease fencing. Publication `outcome_unknown` is never blindly resent.

## Backup/restore

```bash
.venv/bin/python -m patchdesk_api.backup backup var/patchdesk var/backups/patchdesk-new
.venv/bin/python -m patchdesk_api.backup restore var/backups/patchdesk-new var/patchdesk-restored-new
```

Choose new destinations. Online SQLite backup verifies integrity, canonical object/publication hashes and file checksum. Restore refuses overwrites, invalidates sessions, expires stale running leases and quarantines publisher/pending approval states. Do not switch live storage without review; credential rebinding/reconciliation is manual. Backups contain password hashes/private evidence and need protection; no Codex/token secrets are stored in this database.

No automatic retention deletion exists. Back up before updates; rollback needs schema compatibility or a separate verified restore, not destructive copying over live data.

## Windows/protected tunnel target

After installing/building under the intended account, review `infra/windows/install-patchdesk.ps1 -RepoPath <absolute-path> -Credential (Get-Credential) -Start`. It creates separate `AI-Cohort-PatchDesk-api` / `-worker` startup tasks with limited privileges and refuses replacing existing tasks. Verify Codex authentication, writable paths and executable resolution **under that identity**.

Cloudflare example routes PatchDesk to `http://127.0.0.1:8003`; configure an authorized hostname/Access policy before exposure. Set secure cookies for HTTPS. Never expose Codex, shell, SQLite or an unprotected public origin. Project checks still apply behind Access; proxy headers are not actor authority.

Open gates: Windows install/reboot/sign-out, descendant cleanup, tunnel revocation, multi-product CPU/RSS/disk measurements, disk-full recovery, sustained load, browser accessibility and live owned-repository publication. Host targets (idle <400 MiB, active <1 GiB) are not measurements. See [status](implementation-status.md).
