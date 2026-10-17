# Operations and deployment target

Status: original deployment target specification. Service/installer/commands/model/database now exist; use [the current runbook](implementation-and-operations.md) for exact setup, ceilings and backup. The resource/Windows drills below remain acceptance targets, not passed results.

The corrective implementation requires an identity-bound independent erasure ledger and schema-2 backups. Existing unbound stores need explicit offline enrollment with a quarantined pre-enrollment snapshot; old schema-1 snapshots are not accepted by normal restore. Do not roll back the authoritative current ledger. Local macOS corrective capacity/recovery passes are in [17 October validation](corrective-validation-2026-10-17.md), not proof of the Windows targets below.

## Host and runtime

Old Windows laptop: proposed loopback **8004**, independent FastAPI/static UI, one worker, separate local-disk `var/relaydesk` SQLite WAL store and protected model/log paths. Verify port availability and compatibility during implementation. Preserve all earlier products' processes, stores, credentials and release evidence.

CPU semantic embeddings run locally from explicitly provisioned pinned artifacts. Generation invokes installed authenticated Codex through the shared adapter; model inference still needs outbound network. Public source reads require network and scoped consent. Do not expose Codex, a shell, the database or model cache through Cloudflare.

Cloudflare Access plus Tunnel is the HTTPS target, not a replacement for per-user application grants. Never trust arbitrary proxy identity headers. Verify loopback origin cannot be reached through an unintended public binding and use secure cookies behind HTTPS.

## Proposed settings — not implemented

| Setting/object | Intended role |
| --- | --- |
| `RELAYDESK_USERNAME`, `RELAYDESK_PASSWORD` | Explicit first-store admin bootstrap; subsequent per-user memberships/passwords independent |
| `RELAYDESK_HOST`, `RELAYDESK_PORT` | Default target `127.0.0.1:8004` |
| `RELAYDESK_DATA_DIR` | Separate product store, target `var/relaydesk` |
| `RELAYDESK_CODEX_COMMAND`, `CODEX_COMMAND` | Explicit local runtime executable/fallback |
| `RELAYDESK_SECURE_COOKIES` | HTTPS cookie enforcement, loopback-only development exception |
| `RELAYDESK_EMBEDDING_DIR` | Trusted local pinned model/tokenizer manifest; no source-selected URLs |
| `RELAYDESK_ERASURE_LEDGER_DIR` | Protected independent erasure log/epoch used during restore |
| `RELAYDESK_GITHUB_READ_TOKEN` | Optional explicit least-privilege read connector, not authority for every repository |
| Account/case policy | Membership, approved source identities, storage/model egress and account promotion |
| Budget/ranking/summary policy | Versioned settings pinned per job/grant; validate safe values before accepting |

No real secrets in docs/example env, registry/vector records or browser bundles. Do not discover/copy personal runtime tokens. Product/connector secrets stay out of the Codex subprocess environment. Changing bootstrap settings must not silently reset existing actor passwords.

## Initial limits to validate

Proposed starting ceilings, not supported configuration or measured capacity:

| Resource | Target |
| --- | --- |
| Active worker/model job | One; separate bounded ingestion/index queue, no model subprocess per message |
| Pending interactive jobs | 20; backpressure explicit; ingestion cannot starve replies indefinitely |
| Source GET concurrency | Two globally, provider rate/byte/deadline constraints apply |
| Input | 20 MiB per import, 2,000 messages per case capture; longer sources require explicit continuation/partial status |
| Individual text/response | 32 KiB per turn, 4 MiB per source response, 64 MiB acquired per grant; rejected/omitted coverage visible |
| Generation timeout/deadline | 120 seconds per invocation, 600 seconds per interactive job, remaining deadline propagated |
| Model calls | At most four per interactive grant, including one repair/stage; ingestion/compression grants separately bounded and auditable |
| Indexing | One resident CPU encoder, batch up to 16, initial CPU threads 1–2; verify actual settings/host behavior |
| Eligible vector search scope | Initial 10,000 vectors; no silent truncation beyond this, use tested continuation/backend change or explicit partial outcome |
| Context | Proposed 12,000 tokens total with validated accounting and conservative serialized-character ceiling |
| Continuation | Explicit, idempotent, cumulative budget/deadline; initially at most two grants per operation |

Resource targets to measure: warmed API+worker/encoder idle RSS <=750 MiB, active peak <=1.5 GiB; scope search p95 <=500 ms and active local sync p95 <=2 seconds. These are provisional gates, not promises or observations. Measure cold start, long imports, model descendants and five-product coexistence on the actual laptop. If targets fail, revise design/limits openly, not benchmark only tiny cases.

## Startup and supervision

Preflight should verify compatible schema/local writable paths, protected erasure ledger, model/tokenizer hashes, finite test embedding, FTS availability if used, identity safety, executable resolution and loopback port. Missing encoder can permit clearly degraded historical review, but cannot claim semantic recall readiness. Missing storage/auth/erasure safety blocks serving as appropriate.

Implemented targets: `make relaydesk-build`, `relaydesk-up`, `relaydesk-down`, `relaydesk-status`, `relaydesk-test`, `relaydesk-model`; validation uses `scripts/validate_relaydesk.py --output <new-path> [--live]`. Windows tasks refuse replacement and production logs rotate; actual reboot/sign-out acceptance remains required. Full prompts/bodies are not routine logs.

Graceful stop halts new claims, fences stale workers, bounds in-flight reads/model processes and preserves checkpoints. Restart keeps cumulative reservations, source/memory revisions, pending embedding jobs and change events. No unlimited automatic retry after usage/provider outages.

## Backup, restore and erasure

Use SQLite online consistent backup and verify integrity plus source/memory/vector/summary/export manifests. Include model manifest and settings/schema version, not raw credentials. SQLite data and corpus/log/model files have different retention/protection requirements; the backup plan must state each explicitly.

Restore into a **new** directory, refuse live overwrite, reconcile the independent erasure ledger, invalidate sessions and in-flight jobs, rotate restore epoch, verify vector/source revisions and rebuild missing indexes under fresh grants. Fail closed if later erasures cannot be reconciled. Historical downloaded files and backup media disposal need their own approved policy; no secure-wipe claim.

Protect backup storage because messages, vectors and password hashes are sensitive. Do not automatically delete user data based on a provisional retention number. Implement reference-aware retention/preview only after policy approval and tests. Updates require pre-backup/schema/model compatibility; rollback is a separate verified restore, never destructive copying over a live store.

## Required operational drills

Worker killed between memory commit and vector publish; two sessions editing/erasing during generation; provider timeout/usage denial; embedding missing/model changed; event cursor reset; disk full/permission denial; backup with erased data; Windows reboot/sign-out/service identity; protected-tunnel revocation/no alternate origin; five-product CPU/RSS/disk coexistence. Record actual outcomes, durations, cleanup and residual limitations.

Browser, Windows/tunnel, model provisioning, paid-pilot operations and all resource/SLO gates remain open. [Evaluation](data-and-evaluation.md) and [status](implementation-status.md) are the release checklist.
