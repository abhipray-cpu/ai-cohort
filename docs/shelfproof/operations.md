# Operations — local service and target Windows/tunnel acceptance

The commands below exist. Local owned-fixture up/status/down was exercised without
model calls. Windows/Cloudflare installation has not been performed. Read
[implementation status](implementation-status.md) before treating any acceptance
gate as passed. Real `.env` and model authentication were not changed by this work.

## Isolation and launch contract

Applications: `apps/shelfproof-api/`, `apps/shelfproof-web/`; default data root
`var/shelfproof`; independent API/worker PID/heartbeat state. Default loopback port
8009, after checking host conflicts. Product prefix `SHELFPROOF`; no inheritance
of other products' credentials, workspace grants, incidents or data roots.

Make/launcher interface:

```text
make shelfproof-build
make shelfproof-up / shelfproof-down / shelfproof-status
make shelfproof-test
make shelfproof-acceptance SHELFPROOF_ACCEPTANCE_ARGS=...
```

Windows without Make can use `.venv/Scripts/python.exe scripts/dev_stack.py
--product shelfproof up|down|status` after building the frontend. The acceptance
target requires `--evidence` and a new `--output` directory; it exits 2 while quality,
browser or host gates are pending. That is not a build failure or a fabricated pass.

Configuration: explicit `SHELFPROOF_USERNAME`, unique strong (12+ character)
`SHELFPROOF_PASSWORD`, `SHELFPROOF_HOST=127.0.0.1`, `SHELFPROOF_PORT=8009`,
`SHELFPROOF_DATA_DIR`, `SHELFPROOF_CODEX_COMMAND` and exact `SHELFPROOF_ORIGIN`.
HTTPS origin selects Secure cookies automatically; local default is
`http://127.0.0.1:8009`. Existing accounts are not reset by changing environment
passwords. Create a separate reviewer through the administrator's workspace UI.
Use `pip install --no-deps --no-build-isolation -e .` after adding the new app to an
already provisioned development environment, and `npm ci --prefix apps/shelfproof-web`
to install the locked web dependencies.

## Installed provider port

The worker uses the shared provider abstraction through a product-specific wrapper;
no direct LLM API calls in domain logic. The service account must have the installed
Codex executable and its configured authentication. Local installed execution does
not mean local model weights/offline inference or unlimited subscription usage.

Before real payloads: verify effective runtime/schema/tool-audit/usage behaviours
using an explicitly authorized owned fixture, without inspecting private auth files
or changing login/model settings silently. No arbitrary model choice supplied by
client/model content. Pin and record observed runtime/protocol/config versions.
Unknown usage opens the documented circuit; diagnostics must not persist private logs.

## Old-laptop resource envelope

One provider invocation at a time; model work is serialized independently of API
responsiveness. Limits: 100 selected rows/batch, 1,000 rows/import and 1,000 globally
queued/running tasks. Reserve refuses below 64 MiB free; upload needs additional
twice-raw-size headroom. Model grant must cover admitted rows or mark
the unadmitted remainder explicitly—never promise a huge queue will finish overnight.

Use bounded flat CSV/JSON parsing and indexed local storage for application records;
the separate archive utility streams the large source member.
The [source registry](research-and-sources.md) documents release sizes; acquire once
with bounded disk checks, not on each boot. Proposed child-parser memory/time limits
must be enforced/qualified on Windows; POSIX resource limits are not Windows proof.
Ingestion/model reservations block on the protected disk headroom check. Parser
process isolation and physical Windows resource qualification are not claimed.

Provider context cap 256 KiB including schema; source fact pack 64 KiB; output
100 KiB; stdout/stderr collection 1 MiB/64 KiB. Upload is 25 MiB; timeout is 90 seconds
per model invocation. Qualify real process-tree cancellation, resource cleanup and
API responsiveness under these limits, including a sleep/network outage experiment.
Do not promise hard sandboxing or low-RAM performance before target-host measurement.

## Service and tunnel

Package API and worker under a limited Windows service identity/Task Scheduler
policy, not administrator. Do not overwrite existing tasks or unrelated product
services. Set working directory/environment explicitly; supervise/restart without
recreating the database, session secrets, model grants or usage counters.

Tunnel only the application port behind Cloudflare Access and HTTPS. Protect all
paths; ShelfProof has no public webhook. Secure cookies are required over HTTPS.
Keep local authentication, CSRF and role checks. Never publish a development server,
provider port, DB, source archive, metrics with client data or debug endpoint.

`live` means API process alive. `ready` checks schema, current journal and worker
heartbeat and reports active holds; neither endpoint invokes a model or establishes
factual quality. Owner-only operational diagnostics show safe fixed error codes.

## Acquisition/evaluation commands — only after the implementation gate

```text
.venv/bin/python scripts/acquire_shelfproof_corpus.py --output NEW_CORPUS_DIR
# Inspect the official field dictionary (external fallback if absent), then bind its actual hash:
.venv/bin/python scripts/acquire_shelfproof_corpus.py --output NEW_CORPUS_DIR --reviewed-dictionary-hash HASH --target 1000
.venv/bin/python scripts/validate_shelfproof.py --mode software --corpus CORPUS_DIR --output NEW_ENGINEERING_DIR
# Only under the recorded six-product / 96-call user approval:
.venv/bin/python scripts/validate_shelfproof.py --mode actual-smoke --corpus CORPUS_DIR --output NEW_SMOKE_DIR --approval-reference USER_APPROVAL_REF
```

Download is fixed to the official frozen source, bounded and new-only. Initial
acquisition does not map data until dictionary review is bound. An absent bundled
guide uses a hashed official external PDF, with explicit provenance. A completed
download can be resumed using `--expected-archive-sha256`; it is verified, not
overwritten/redownloaded. No public endpoint
fetches arbitrary URLs. The actual runner uses temporary API/worker/CLI processes,
not a fixture provider, and persists an approval registry under
`var/validation/shelfproof-authority`. Reusing an approval cannot silently create
another clean allowance/store after a fault. Unknown usage stops dispatch; no
incident is automatically accepted. Baselines/larger quality studies need a new
explicit cumulative grant. Reports retain pending IDs and zero human labels.

## Filesystem-operator maintenance

`scripts/shelfproof_operator.py --root DATA_ROOT --help` lists status, new-only
backup/restore, stopped-runtime orphan isolation, verified receipt supplementation,
bounded resume, tightly limited incident acceptance, grant amendment and explicit
restore-quarantine release. These are not public HTTP routes. Mutations require
owner authority/current journal head/idempotency/evidence as applicable; an incident
closure does not dispatch anything. No live incident approval is implied by these
commands or the initial validation-call grant. Restore needs the independently
current journal, revokes sessions, reapplies newer erasures and leaves old tasks
stale. A journal/DB mismatch cannot be waved away by release-quarantine.

For the explicitly approved 21 October campaign recovery only,
`scripts/recover_shelfproof_campaign.py` adds a tested operator queue-parking
procedure. It requires the exact complete queue, untouched/current tasks, owner
role, verified integrity, matching journal head and the stopped runtime lock.
It moves queued tasks to attributed `manual_required` states without changing
calls, claims, facts, grant or journal. The one-time incident is then accepted
through the existing policy; the original incident task is separately resumed
before the parked tasks. It does not cancel/recreate products or reset spend.
The helper's `run-worker` uses the unchanged production adapter and worker with
bounded, allowlisted failure categories only; no raw stderr/reasoning is saved.
Original and recovered reports are separate files. This driver exercises the
worker/store path; it does not repeat authenticated browser/API acceptance.
No code-fingerprint rebind, model override, auth change or second incident is
authorized by this procedure.

### Explicit fixed-code revalidation (separate user approval)

`python -m scripts.revalidate_shelfproof_campaign --help` documents the bounded
fixed-code driver. It accepts the original owned campaign directory, exact parent
report and six product IDs, current journal head, expected charged-call count and
explicit approval reference. It creates a new-only backup/evidence directory and
linked successor tasks, not a new store or grant. It rejects active work, reviewed
parents, unchanged code, changed policy/epoch, already-branched parents and exhausted
row/claim/grant budgets. Frozen facts and imported originals are retained; generation
tasks remain generation tasks. The prior tasks become stale, but their snapshots,
artifacts, usage and failed reports remain intact. Successors inherit call/claim
counts, and accepted-unknown warnings follow the full parent chain into review.

Each changed-code context still has two attempts per stage and two revisions;
the inherited per-product 16-call/four-claim and original 96-call campaign ceilings
are not renewed. `actual_calls`/`unknown_attempts` in its report refer to the current
pass; `cumulative_calls` and `historical_unknown_attempts` separately retain prior
spend/liability. Never label a clean current pass as erasing the original unknown.
All six rows must reach `review_ready` and the full concept loop must be observed
before the live-workflow gate can pass. This is not human review or publication.

## Target-host acceptance checklist

Actual laptop: confirm port/disk/RAM/account; install dependencies; verify isolated
services/ACLs; run owned fixture; start/stop/restart API and worker; interrupt network
and sleep; confirm no duplicate calls/vanished charges; cancel child tree; replay
partial work under authority; restore into a quarantined new root; test local and
protected external browser sessions, cross-client denial and secure cookies.
Record exact host/versions, measured timings/memory, failures and unresolved limits.

Backups and exports require protected storage/retention; plaintext plus a hash is
not encryption. Use the [recovery runbook design](audit-and-recovery.md) before any
restore/incident action. Packaging alone is never deployment acceptance.
