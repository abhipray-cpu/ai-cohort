# Implementation and operations

## Install and start

Python 3.12+, Node/npm, installed authenticated Codex CLI. From repo root:

```sh
.venv/bin/python -m pip install -e '.[dev]'
npm --prefix apps/buildrelay-web ci
make buildrelay-build
```

Add explicit `BUILDRELAY_USERNAME` and a unique password of at least 12 characters
to local `.env`; placeholders fail closed. Set `BUILDRELAY_DATA_DIR=var/buildrelay`.
Bootstrap creates the first owner only; changing environment credentials does not
reset an existing account. Do not commit `.env` or use evaluation passwords remotely.

```sh
make buildrelay-up
make buildrelay-status
make buildrelay-down
```

Open `http://127.0.0.1:8007/`. Create a client in Workspace, then connect its
`owner/repository`, numeric GitHub repository ID and response team label. Issue
writes are **off by default** and must be explicitly enabled on that repository.
Configure the referenced `BUILDRELAY_<CLIENT>_SECRET` and `_TOKEN` values on the
service host, then restart the stack. UI configuration accepts environment **names**,
not token values. Health checks never claim AI quality has been accepted.

Create a repository webhook for **Workflow runs**, JSON content type, the configured
secret, and `https://your-host/hooks/github/<configured-repo-id>`. Only completed
events enter workflows. A successful durable inbox commit returns 202; no model
call occurs inside the webhook request.

Use a fine-grained GitHub token scoped to only the selected repositories: Actions
read for private run evidence; Issues write only when issue synchronization is
explicitly enabled. Validate actual permissions in an owned test repository.

Windows without Make: `.venv/Scripts/python.exe scripts/dev_stack.py --product buildrelay up`
(also `status`/`down`). Build the web app first. For startup tasks, use
`infra/windows/install-buildrelay.ps1 -RepoPath <repo> -Credential <limited account>`.
This does not install/provision NATS or Codex, and is not verified Windows acceptance.
Development launcher logs/PIDs: `var/buildrelay-dev`; service runner rotates logs.
AI execution may take up to its 90-second call timeout during graceful shutdown.

## Enable independent queue ingress

Install an official [NATS server](https://docs.nats.io/concepts/getting-started/) binary
matching the host; enable JetStream on persistent local storage. Bind a local broker
to `127.0.0.1`, configure authentication, and use ACL-restricted credentials. Use TLS
and authenticated credentials for a remote broker. Never tunnel the raw broker publicly.

Set `BUILDRELAY_NATS_URL`, optionally `BUILDRELAY_NATS_CREDS`, and the stream/subject
names from `.env.example`. Empty URL explicitly disables queue ingress. The default
subject is agency-wide; its producers are trusted agency integrations with authority
to publish for configured repositories, **not untrusted per-client public producers**.
Do not grant clients generic write access to that subject.

```sh
.venv/bin/python scripts/buildrelay_queue.py provision
.venv/bin/python scripts/buildrelay_queue.py inspect
.venv/bin/python scripts/buildrelay_queue.py publish --envelope path/to/event.json
```

Provisioning is explicit and creates a dedicated file-backed stream with 64 MB / 7-day
retention and a 64 KB message bound. Worker does not replace broker stream policy.
Broker storage/retention is finite; long outages/overflow need operator investigation.
The broker is not automatically started/stopped by `make buildrelay-up/down`.

Queue envelope (replace values with actual source identities):

```json
{
  "schema_version": 1,
  "repo_id": "configured-repository-id",
  "delivery_id": "producer-stable-id",
  "event": {
    "repository_id": 123,
    "repository": "acme/shop",
    "run_id": 77,
    "attempt": 1,
    "conclusion": "failure",
    "workflow": "CI",
    "branch": "main",
    "sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "source_url": "https://github.com/acme/shop/actions/runs/77"
  }
}
```

The example is synthetic documentation, not a real observed run. Producers must
preserve source identity across HTTP/queue delivery. ACK means committed to inbox,
not completed AI processing. Disk failures NAK with delay; invalid inputs are
terminated only after a durable digest/error audit. Invalid raw payloads are not
retained because they may contain secrets; correct the producer to submit a new
valid envelope. Workflow failures retain their validated event and checkpoints in
the replayable dead-letter inbox.

## Retry, dead-letter and ambiguous-effect operation

Transient network/5xx/rate-limit failures retry with bounded backoff and jitter,
honoring numeric retry/reset headers within a 24-hour scheduling cap. Four workflow
attempts or permanent failures dead-letter. Authentication/schema failures require
configuration correction, not infinite retries. AI unavailability or repeated invalid
generation produces a durable manual-triage incident with validation audit; it is
not silently dropped or called a successful diagnosis.

Inspect dead letters, fix the cause, then Replay with a reason. Completed evidence/
analysis checkpoints are preserved. Replay is not a command to regenerate analysis.
An uncertain issue POST is reconciled against repository issue markers. If not found,
the event stops; an owner must check GitHub directly before confirming no issue was
created and rearming it in the evidence drawer. Incorrect human confirmation can
cause a duplicate; never treat rearming as a generic retry button.

Recent-run repair scans every five minutes (up to three pages / 300 runs by default).
GitHub orders these by creation, so old reruns outside that window may be missed.
Coverage exhaustion and repair errors are audit entries. Requesting a scan does not
guarantee complete history. GitHub does not automatically retry failed webhooks:
[delivery semantics](https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries).

## Security and limits

Owners configure all clients; operators/viewers see explicit client grants only.
Operators replay and acknowledge; viewers read/export. Owners manage/revoke accounts
and grants immediately. Sessions expire after eight hours, store only hashed token
values, and use HttpOnly/SameSite cookies plus CSRF for mutations. Set
`BUILDRELAY_SECURE_COOKIES=true` for HTTPS deployment. Login throttling is bounded and
in-process, not a replacement for a gateway rate limiter/SSO.

Cloudflare Access must protect the UI/API but allow GitHub's narrow HMAC webhook
path without interactive login. Ingress configuration alone is not authorization.
Keep API bound to loopback and protect storage/backups with service-account ACLs.
Neither model runtime nor broker may be publicly exposed.

Downloads are restricted to GitHub API-derived allowlisted storage hosts; tokens
are not forwarded to log storage. Archives are never extracted or executed, have
compressed/expanded/file-count bounds, and skip unsafe paths. Evidence selects
up to 64,000 characters total: complete small archives, otherwise early diagnostic
clusters, terminal summaries, recent diagnostic windows and heads ranked across
files. This replaces 6,000-character/file tails and the old 32,000 aggregate cap.
Prompt numbering/JSON add overhead; this is a character bound, not a token budget.
Window ranges refer to redacted-source lines; citations refer to selected-evidence
lines. Any skipped unsafe/oversized file or omitted content marks partial coverage
and caps confidence at 0.49. Selection can still miss relevant failures. Exact
citation checks prove quote presence, **not causal correctness**.

On expired/replaced leases, typed `LeaseLost` propagates through analysis and is
handled around both processing and failure recording. An audit entry is appended,
but the stale worker must not renew, retry or modify the event. It remains eligible
for normal reclamation, subject to the four-attempt limit. Do not bypass fencing to
make a failed checkpoint appear successful.

Redaction removes known repository secrets and common credential patterns before
checkpointing/model prompts. It is best effort, not a guarantee against every
secret format. Do not ingest sensitive customer logs until redaction/retention review.
Codex receives a reduced environment without product credentials and has tools,
MCP, web search and related capabilities disabled/audited. Output is untrusted draft
text. No app-level code execution, deployment, client-message sending, or merges.

UI lists the latest 1,000 events/audit entries; database retention is not automatically
pruned. Plan disk monitoring/retention, backup encryption, and stronger independent
audit storage before production. This pilot is single-host, not highly available.

## Backup / restore

```sh
.venv/bin/python scripts/buildrelay_backup.py backup var/buildrelay var/backups/buildrelay-001.sqlite3
make buildrelay-down
.venv/bin/python scripts/buildrelay_backup.py restore var/backups/buildrelay-001.sqlite3 var/buildrelay-restored
```

Snapshot destinations and restore directories must be new; existing data is never
overwritten. SQLite online backup is integrity-checked. Restore revokes sessions and
requeues in-progress work with existing effect/checkpoint records preserved. Point
the stopped service at the restored directory before restart. Backups contain client
logs and identity data; protect them. Broker storage needs its own backup/recovery.
