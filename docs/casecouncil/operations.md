# Operations and Windows deployment requirements

Application/Make/worker and additive Windows/tunnel packaging now exist. This is
the original target-host requirements baseline; use the [implemented runbook](implementation-and-operations.md)
for actual commands and qualified limits. Windows/Cloudflare have not been deployed
or accepted. Readiness does not verify a model connection. macOS/Windows PDF parsing
has bounded child/time/input limits but no qualified hard memory sandbox.

## Target environment and isolation

Old Windows laptop running a separate API/static-UI process and a durable worker
under a restricted service account. Proposed loopback port 8008 and runtime directory
`var/casecouncil`; verify port conflict before binding. Other products keep their
ports, credentials and databases. SQLite and artifacts stay on local disk, not a
network share or aggressively synchronized folder.

The AI boundary invokes installed Codex through an adapter, not a direct LLM API.
Installed executable, supported restrictions, authentication, network access and
runtime auditing must be verified on the real Windows host. Do not promise offline
inference. Never expose Codex, worker internals or database over Cloudflare.

## Initial resource defaults to qualify

| Resource | Proposed initial ceiling |
| --- | --- |
| Active CaseCouncil jobs / live model processes | One / one |
| Intake formats | Text-bearing PDF and UTF-8 text only |
| Per-file bytes | PDF 10 MiB; text 1 MiB |
| Per-case bytes / files / PDF pages | 40 MiB / 20 / 200 total |
| Extracted canonical text | 1,000,000 Unicode characters/case maximum; excess rejected or explicit partial intake before inference |
| Confirmed issues/run | 10 |
| Selected provider evidence | 64,000 Unicode characters with coverage manifest |
| Full provider input / output | 256 KiB serialized UTF-8 / 100 KiB |
| Logical calls / total invocations | 8 normally or 11 with revision / maximum 22 including repairs |
| Stage timeout / active run deadline | Up to 90 seconds / 30 minutes cumulative |
| Job lease / renewal / claim attempts | 600 seconds / 20 seconds / maximum four including crash reclaims |
| Parsing timeout | Proposed 20 seconds/document in isolated child; memory/process enforcement verified on Windows |

Byte, character, page, call and time bounds are different units. No hard model-token
ceiling, cloud billing cap or guaranteed latency is inferred from them. Refuse a
strict financial/token-budget promise the provider boundary cannot enforce. Other
products can still consume machine/quota resources; this product's serialization
is not a cross-monorepo global scheduler.

Start with these conservative limits, measure memory/disk/latency on representative
actual cases, then revise policy and invalidate incompatible qualification evidence.
Do not lower coverage silently to make the laptop appear faster. Selecting excerpts
marks partial assessment unless the relevant declared checks were genuinely covered.

## Bootstrap and lifecycle plan

Additive integration should eventually supply `make casecouncil-up`, `down`, `status`,
`test` and `acceptance` with documented Windows equivalents. Startup builds/serves
the UI, checks explicit credentials, source/data configuration, runtime capabilities,
store integrity and restricted worker startup. Missing auth/runtime produces a
clear safe readiness failure; it must not fall back to a canned proposer.

Use a product-owned PID/identity registry so stop cannot kill unrelated Python,
Node, Codex or other-product processes. Graceful stop fences dispatch, cancels local
children, persists safe attempt state and retains unknown usage. Start does not
automatically authorize egress or rerun every incomplete historical analysis.

Owner bootstrap is explicit, without a committed/default password. Environment
references rather than raw secrets appear in configuration examples; logs must not
echo credentials or full private prompts. Protect runtime storage, backups, Codex
authentication files and service logs with ACLs and disk encryption as appropriate.

## Health, accounting and observability

Readiness checks API/store schema/integrity, artifact root, worker heartbeat,
runtime capability verification and any circuit/quarantine state. Liveness alone
is not proof the provider can generate or the laptop has internet. Health endpoints
return no client identities, source text or private counts.

Track stage durations, queue age, completed/failed/degraded runs, validation error
classes, stale results, lease losses, call allowance, known usage and unknown
liabilities. Cached input is a subset, not additional input tokens. Failed calls
can cost usage. A runtime/unknown-usage incident stops automatic dispatch; owner
intervention must reconcile the actual state rather than set missing usage to zero.
An acknowledgement alone cannot clear a liability or establish provider health.

Logs and audit resolve sensitive evidence by reference. Operator diagnostics are
scoped and redacted. No background “health test” sends customer data or consumes
unbounded model quota. Define disk thresholds and warn/block intake before storage
exhaustion; actual thresholds need target-host free-space measurements.

## Tunnel and service acceptance

After authorization, install a restricted Windows scheduled task/service convention
with restart policy and explicit working directory. Cloudflare Tunnel routes only
the protected application hostname to loopback; Access covers all paths. Application
sessions, HTTPS secure cookies and CSRF remain required behind Access. Do not add a
public-webhook exception copied from BuildRelay.

Verify actual login/logout, session revocation, uploads, stage updates, cancellation,
source display, review/export, origin handling and request limits through the tunnel.
Test reboot, task startup, host sleep past a lease, network loss, expired Codex auth,
worker crash, full disk, restore and shutdown cleanup on the old laptop. Record
unexecuted physical tests explicitly rather than infer them from macOS unit tests.

## Recovery and retention

Follow [audit/recovery](audit-and-recovery.md). Backup to a separate protected
location, test a new-root restore before replacement, rekey epoch/sessions and
quarantine in-flight work. Do not delete a runtime tree as routine troubleshooting.
Retention periods come from customer/source policy, not a universal guessed rule.

Proposed pilot recovery objectives: restore the last verified daily snapshot within
four working hours, with up to 24 hours data loss. These are operator targets to
test and agree, not SLAs or achieved guarantees; a single laptop is not highly
available. Customer-required tighter objectives may make this hosting model unsuitable.
