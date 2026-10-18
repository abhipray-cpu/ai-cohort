# Operations and recovery target

Status: original operational targets. Commands/launcher/task packaging now exist; use the [actual runbook](implementation-and-operations.md) for executable settings, limits and deviations. No Windows task or external service was installed. Target: old Windows laptop, API/static UI and one worker on loopback **8006**, independent `var/catalogbridge` local-disk storage. No GPU, Docker or vector server required by the initial lexical design.

## Configuration and commands to implement

Proposed `CATALOGBRIDGE_` settings: `DATA_DIR`, `HOST`, `PORT`, `USERNAME`, `PASSWORD`, `SECURE_COOKIES`, `CODEX_COMMAND`, `MODEL_PROFILES_PATH`, `RATE_CARDS_PATH`, `BUDGET_MODE`, `USAGE_JOURNAL_DIR`, `ERASURE_LEDGER_DIR`, `LOG_DIR`. These are not recognized settings today. Bootstrap must never overwrite existing credentials; do not silently share passwords with another product.

Plan `make catalogbridge-build/up/down/status/test/validate/acceptance` and equivalent direct Python launcher commands on Windows without Make. Add start/stop only for owned PIDs and product paths. `up` should preflight capabilities and show degraded/manual-only readiness honestly; strict-token failure cannot look like AI readiness. No launcher or `.env` changes in the docs phase.

## Starting resource envelope to measure

| Resource | Initial proposed bound |
| --- | --- |
| Feed | 20 MiB each, 25,000 rows, 20,000 chars/field; reject oversize explicitly |
| Retrieval | Up to 10 candidates per row; index bound by feed cap |
| Worker | One active row, queue cap 20 batches, bounded API rate per actor |
| Model attempts | At most three per row including repair; ≤90 seconds/call and remaining row deadline |
| Row budget | Initial target in [budget design](budgets-and-analytics.md); advisory versus strict explicit |
| Polling | Paginated rows 50/page, audit 100/page; summary polling without complete history |
| Logs | Redacted rotating 5 MiB×3 per process; no prompts/source bodies/secrets |

These are bounds to implement and stress, not measured capacity. The feed cap does not guarantee affordable whole-feed inference. Preflight estimates/review fallback must expose that gap. Target UI/read API p95 ≤300 ms at eight concurrent clients, measured separately from model time; record RSS/CPU/disk/WAL and inference throughput on the actual laptop with all seven products. Do not claim macOS measurements are Windows SLOs.

## Startup, shutdown and limited identity

Validate data/journal identity, schema/current epoch, free disk, explicit credentials, approved profiles/egress, port ownership and model capability freshness. Missing/corrupt current liability journal blocks dispatch. Model unavailable may allow manual review with explicit degraded readiness. Provision installed Codex/auth under the service identity; a developer's interactive login does not prove unattended access. Never expose CLI control over HTTP.

Shutdown stops claims, fences publication, attempts bounded descendant cleanup and persists unknown liabilities. Restart must not refund reservations or redispatch unknown attempts blindly. Windows Task Scheduler packaging is not an SCM service guarantee; verify startup/reboot/logoff and task ownership. Do not kill all Python/Node/Codex processes.

## Backup and restore

Use consistent SQLite backup plus checksummed immutable artifacts. Restore into a new quarantined directory, never overwrite live storage. Compare against independently retained current usage/dispatch liability and erasure/revocation ledgers; invalidate sessions/leases and old review/export eligibility with a new epoch. Reconcile actual spending before re-enabling dispatch. If current journal evidence is missing, manual review can remain available but no spending is admitted. Restoring a snapshot cannot undo a provider charge or resurrect deleted content.

Required drills: kill between reservation/launch/result/settlement; later-row timeout with earlier reviewable results; disk-full rollback; corrupted artifact; older restore after spending/top-up/revocation/erasure; duplicate worker lease; unavailable profile; logs rotation. Record real process and filesystem evidence, not only mocked exceptions.

## Protected entry and deployment authority

Future route `catalogbridge.<your-domain> → http://127.0.0.1:8006` requires actual Cloudflare Access policy and application authentication. Test unauthenticated external denial, cookie/CSRF/proxy headers, limits and scoped exports. No DNS/tunnel/account changes in docs or automatic implementation setup without deployment authority. Do not expose an unprotected quick tunnel as production acceptance.

Maintenance includes explicit retention, dataset notices, fresh backups before migration and documented rollback reconciliation. No destructive cleanup or credential migration across products. Operator handoff must identify real commands, runtime/model versions, tested envelope, preserved failed evidence and open release gates.
