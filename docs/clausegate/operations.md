# Operations and deployment target

Status: original operational target specification; current commands/settings/service packaging now exist. Use [the implemented runbook](implementation-and-operations.md) for actual executable commands/ceilings/deviations. Windows tasks/Cloudflare accounts were not installed or configured; target-host drills remain open. Previous product services/data remain unchanged.

## Service host

Target old Windows laptop, independent loopback port **8005**, API/static UI plus one worker, local SQLite WAL and immutable source artifacts. Python 3.12 and Node build tooling follow the monorepo convention; verify versions, Windows wheels, patched SQLite and service compatibility before pinning. No Docker/GPU or vector database is required. Do not place live SQLite on a network share/cloud-sync folder; see [SQLite WAL requirements](https://www.sqlite.org/wal.html).

Installed Codex generation is accessed through the shared adapter. Provision its existing authentication/executable under the limited service identity; interactive developer login is not proof a scheduled task can run it. Inference may be remote and requires explicit case egress permission. Never expose the CLI over Cloudflare or allow uploaded document paths to choose its workdir/config/tools.

## Proposed configuration — not recognized yet

| Setting | Intended purpose |
| --- | --- |
| `CLAUSEGATE_DATA_DIR` | Independent `var/clausegate` database/uploads/checkpoints |
| `CLAUSEGATE_ERASURE_LEDGER_DIR` | Protected independent current ledger, outside ordinary restorable snapshot |
| `CLAUSEGATE_AUDIT_ANCHOR_DIR` | Independently retained latest audit checkpoints; explicit assurance if absent |
| `CLAUSEGATE_USERNAME/PASSWORD` | Explicit initial owner bootstrap, no existing-password overwrite |
| `CLAUSEGATE_CODEX_COMMAND` | Installed trusted executable, not source/user-provided command text |
| `CLAUSEGATE_HOST/PORT` | Default loopback/8005; explicit refusal of unsafe broad exposure |
| `CLAUSEGATE_SECURE_COOKIES` | Required for protected HTTPS; loopback-only development exception documented |
| `CLAUSEGATE_LOG_DIR` | Protected rotating safe logs, no contract bodies/credentials |

Plan `make clausegate-build/up/down/status/test/validate/acceptance` plus direct Python launcher parity where Make is absent. Do not add aliases that start/stop unrelated products. Startup/PID ownership checks and additive Windows installer come only with implementation authorization.

## Starting resource and workload ceilings

These are proposed bounds to test, not measured SLOs or user-data truncation permissions.

| Resource | Proposed initial limit / required handling |
| --- | --- |
| Upload | 20 MiB/file, 150 PDF pages, 500,000 extracted characters/document; reject unsupported limits with reason |
| Import/archive | 256 MiB compressed/512 MiB total expanded, 10,000 entries, safe paths; adjust only through tested operator config |
| Active worker | One analysis grant at a time; bounded queue 20; per-user rate limits |
| Model | Four calls/active grant including repair, two explicit grants per bound checkpoint; reserve before invocation |
| Active deadline | 600 seconds/grant, call ≤120 seconds and remaining allowance; waiting has separate expiry, no live lease |
| Worker lease | Proposed 150-second renewable lease; old lease cannot commit; heartbeat tested against call runtime |
| Serialized prompt/schema | ≤48,000 characters per call including metadata/instructions/schema; not exact token accounting |
| Case/workflow payload | Bounded request lists with pagination; UI page 50, audit page 100; no full history embedded in every request |
| Log rotation | Proposed 5 MB ×3 per role; private evidence stays in protected data store, not routine logs |
| Load fixtures | 100 cases/1,000 pending requests/10,000 decisions; replicas separately labelled |

Source max size is an intake ceiling, not proof it can be completely analyzed within model grants. Long documents may need bounded chunk coverage and explicit additional authorized grants within the cumulative limit, or manual review. Missing chunks prohibit complete absence/clearance assertions. Never silently truncate an agreement or reset usage to make a long case pass. Actual supported envelope/coverage and failed provider batches must be measured before release.

Provisional target-host goals: authenticated inbox/decision-write p95 ≤250 ms at eight concurrent clients over 1,000 pending requests; decision-to-resume scheduling ≤2 seconds when an idle worker is available, excluding model runtime; no model work while waiting. Record distribution, environment and repetitions. Measure working set/RSS, CPU, disk/WAL growth and p95 over all six products at once on the actual laptop. A fast macOS test is not Windows acceptance.

## Startup and shutdown

Preflight must validate independent paths/ACLs, schema/ledger identity, source and audit integrity, correct restore epoch, explicit bootstrap configuration, port ownership, free disk and executable/service identity. If audit/authority integrity fails, block mutations/finalization and offer only explicitly scoped diagnostic/quarantine access. Provider unavailable can allow manual review with clear degraded readiness, not fake AI readiness.

Graceful shutdown stops new job claims, cancels/fences active work within a bound, cleans up only owned descendant processes and preserves waiting requests/decisions/outbox. Restart recovers durable work under the original counters/deadline; it never repeats human approvals or assumes pending equals approved. Do not kill all Python/Node/Codex processes on the host.

## Windows and protected entry

Plan two named limited-identity startup tasks (API/worker), protected local paths and explicit refusal to replace unrelated tasks. Verify foreground runner, startup/reboot/logoff, account profile/auth availability, child cleanup and log rotation. Task Scheduler packaging is not an SCM service claim. Do not perform installation in the docs stage.

Future Cloudflare route: `clausegate.<your-domain> → http://127.0.0.1:8005`, protected by actual Access policy and application auth. DNS/tunnel/Access account changes require later explicit deployment authority. Test external unauthenticated denial, origin/CSRF, secure cookies, header handling and rate limits. No quick public tunnel as production security proof.

## Backup, recovery, privacy and maintenance

Use online consistent SQLite backup and hash-verified artifacts, new destination restore, external ledger identity/currentness checks and trusted audit-head comparison. Quarantine restore; rotate epoch, expire sessions/leases, invalidate all prior approvals and reprovision current authority before serving. Do not restore a stale ledger over the live one. [Audit and recovery](audit-and-recovery.md) defines required drills and limits.

No automatic deletion of user cases or datasets. Define retention/erasure preview and protected backup disposal with the customer; downloaded exports are outside remote recall. Upgrade with fresh backup/schema checks and a tested new-directory recovery path, not destructive copying over live files. Source/API data acquisition is read-only, bounded and checkpointed; no quota bypass or automatic licensing consent.

Deployment handoff must include actual runtime versions, supported input envelope, tested command output, artifact manifests, preserved failed cases, release gate verdict and operator recovery instructions. Never mark an unavailable Windows/browser/legal/customer gate passed because the documentation is complete.
