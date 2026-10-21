# Permissions, safety and data protection

Requirements only; no security/deployment review has passed. The product's food
domain makes unsupported claims consequential even though this is a text-review
tool, not a regulatory/safety decision system. No output is certified safe/compliant.

## Actors and scope

| Actor | Permitted scope |
| --- | --- |
| Host administrator | Install/update and protect volumes/account; outside application tamper-proof boundary |
| Workspace owner | Client membership, rights, versioned policy/rubric activation, batch allowances, retention and erasure |
| Producer/editor | Approved imports/mappings, drafts, preview, authorized starts/cancel and attributed edits |
| Reviewer | Read authorized evidence, inspect history, review exact current eligible versions and download approved patches |
| Viewer | Read allowed artifacts; no start, review, policy or source mutation |
| Worker/model | Worker holds fenced stage capability; model returns untrusted proposals only, never actor authority |

Each client is a workspace boundary. Owner/admin is not a maker/checker exemption.
Never accept caller-provided actor, usage, source trust, adoption or approval fields.
Public API does not expose operator recovery, model configuration or a generic tool executor.

## Authentication and exposure

Unique product credentials, salted password hashes, short-lived revocable sessions,
CSRF tokens, same-origin mutation checks, bounded login failure throttling, secure
cookies over HTTPS and no wildcard CORS. Authenticate local loopback users too.
Scope object existence, filenames, metrics, receipts and exports before returning
them. Use indistinguishable forbidden/not-found responses where appropriate.

Bind only the API/static UI to loopback 8009. Cloudflare Access/TLS is additional
protection, not a replacement for application authorization. Every application
path is protected; no webhook/public hook exception is needed. Never tunnel the
worker, database, corpus directories, debug endpoints or installed Codex.

## Import, injection and output controls

CSV/JSON only: maximum 25 MiB upload, 1,000 rows/import, 64 KiB/row, bounded columns,
nesting and per-field lengths; reject ZIP/PDF/HTML/executable uploads. Archive
handling belongs only to the explicit acquisition utility with separate limits.
Reject path traversal, unsafe filenames, duplicate headers/keys, invalid encoding,
malformed numeric bases and guessed mappings. Parse in bounded child processes
where needed. Windows memory/resource limits require actual OS enforcement/testing.

Treat facts, existing copy, briefs, peer outputs and imported field names as data.
An imported instruction to increase score, fetch a site or suppress a warning has
no authority. The restricted provider must disable external tools and retain
audited tool status. Prompt instructions alone are not a sandbox. Tool-audit failure
or unexpected tool events open a hold; raw messages are not logged as diagnostics.

Escape all HTML, avoid unsanitized Markdown rendering and never evaluate imported
URLs/formulas. Spreadsheet-safe review CSV is distinct from the typed machine
patch. No formula execution, macro support or browser-side arbitrary fetch.

## Source rights, confidentiality and egress

The public FDC source basis is recorded in [research](research-and-sources.md).
It does not authorize private customer drafts, supplier agreements, trademarks,
imagery or unrelated platform scraping. Customer grants must cover actual processing,
retention and the configured external model destination. Default egress off until
approved; changing profile/destination/source invalidates old context authorization.

Preview exact bounded context. Redact personal identifiers where possible, but
do not promise anonymization or redact meaningful product quantities silently.
Residual sensitive data requires review, not a higher model score. Model egress
already performed cannot be recalled by deleting the local record.

Separate raw/normalized source facts, runtime context, evaluator gold and exports.
Enforce directory/account ACLs; same-host directories alone are not isolation.
Do not inherit another product's credential, account grant, data root or sessions.
Store no secrets in prompts, source-control, telemetry, URLs or operator reasons.

## Audit, retention and erasure

Content is available only through scoped artifact APIs. Routine logs retain IDs,
hashes, bounded codes/timestamps and usage flags, not full copy, private prompts,
stderr, tokens or vendor messages. A protected application store may retain the
approved artifacts required for review under the declared retention policy.

Erasure preview lists source/derived versions, plans, evaluations, reviews and cached
exports. Cancel/fence active work before erasure; delete retained content and indexes,
keep minimal pseudonymous accounting/audit/incident metadata and revoke download
access. Copies already downloaded, provider egress and backups need separate policy.
Hash retention is not a claim of complete anonymization.

Backups are plaintext unless encryption is explicitly implemented and verified.
Protect the volume/ACL and retention; do not call a hash chain encryption or
administrator-tamper-proof audit. Restore requires independent authority reconciliation
and quarantine. Threat/fault tests are required before any real customer rollout.
