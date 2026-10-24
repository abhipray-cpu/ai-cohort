# Contracts, persistence and implemented API

The typed API is implemented in [routes](../../apps/repairclaim-api/src/repairclaim_api/routes.py)
and [API boundary](../../apps/repairclaim-api/src/repairclaim_api/api.py); core records
below describe the design bindings rather than literal one-table-per-type storage.
The web app has explicit input/approval guards; backend Pydantic remains authoritative.
Reject extra fields, nonfinite
numbers, invalid enums, excessive nesting, overly long text and malformed IDs.
Validation failures have safe audit events; never echo private input in errors.

## Core records

| Record | Required identity, bindings and purpose |
| --- | --- |
| Household / User / Grant | Server-derived household, role, case scope, expiry and revocation epoch; owner/viewer/editor, no self-escalation |
| Vehicle | Household ID, attributed VIN/attributes, jurisdiction, identity-conflict state; VIN is not an authorization key |
| Case / Snapshot | Vehicle/case ID, revision, deletion epoch, fact/source registry hashes, allowed fields, active allowance |
| Document / FactRevision | Quarantine ID, private file hash, type, scan/parser status, page map, source span, actor and prior revision |
| SourceCapture | Registry source ID, final validated URL, fetched/publication/effective times, status, bytes hash, parser and access notes |
| ProgrammeRevision / Condition | Family, category, source hashes, reviewer/interpretation version, typed predicates, supersession and unknowns |
| Assessment / Finding | Snapshot, candidates/exclusions, per-condition result/evidence, bounded search scope, overall state and stop reason |
| Question / Answer | Condition linkage, source/fact revision, answered/unknown/deferred, actor/time; no inferred answer |
| Draft / PacketManifest | Immutable message and recipient, ordered original/redacted attachments and hashes, findings, amounts, renderer and parent |
| Approval | Owner, exact rendered bytes/manifest hash, fact/source/case revisions, grant epoch, creation/expiry, revocation/staleness |
| Response / OutcomeEvent | Source document or user attribution, reasons, money/currency/type, repair allocation and reversal linkage |
| MonitoringConsent | Vehicle/case/history scope, purpose, retention end, schedule, granted/revoked time and epoch |
| Job / Attempt / Receipt | Idempotency key, lease fence, counters, checkpoints, provider identity/version, nullable usage, error and safe diagnostic |
| Notification / Reminder | Household, consent/source/case revision, dedup key, trigger/deadline attribution, status/expiry and cancellation |
| AuditEvent / Tombstone | Actor/scope, action, revision/hash references, redacted reason/time; deletion barrier without raw VIN or content |

All private tables use household scope in primary relationships/queries. Composite
foreign keys must prevent a household-scoped child from referencing another
household's case. Global public-source records never contain private case facts.
Private blob references require scoped lookup, never direct path construction.

## API surface, all under `/api/repairclaim/v1`

| Operation | Actual endpoints and controls |
| --- | --- |
| Identity | `POST /sessions`, `DELETE /sessions/current`, `GET /me`; secure sessions and CSRF for writes |
| Garage/cases | `GET/POST /vehicles`, `GET/POST /cases`, `GET /cases/{id}`, `GET /cases/{id}/workspace`, `GET /cases/{id}/snapshot`, `POST /cases/{id}/lifecycle` |
| Upload/facts | `POST /cases/{id}/documents?filename=...&kind=...&revision=...` (bounded octet-stream), `GET /documents/{id}`, `GET /documents/{id}/preview?page=...`, `POST /documents/{id}/confirm`, `POST /cases/{id}/corrections`, `POST /cases/{id}/fact-revisions` |
| Investigation | `POST /cases/{id}/investigations`, `GET /jobs/{id}`, `POST /jobs/{id}/cancel`, `POST /jobs/{id}/resume` |
| Evidence | Findings are in job/workspace results; `POST /jobs/{id}/answer`, `GET /sources/{id}/revisions/{sha256}/preview`, `GET /cases/{id}/analysis-preview`, `POST /jobs/{id}/usage-acknowledgement`, `GET /capabilities` |
| Packets | `POST /cases/{id}/packets`, `GET /packets/{id}`, `POST /packets/{id}/render`, `GET /packets/{id}/preview`, `POST /packets/{id}/approve`, `POST /packets/{id}/revoke`, `POST /packets/{id}/download` |
| Case progress | `POST /cases/{id}/submissions`, `POST /cases/{id}/responses`, `POST /cases/{id}/outcomes`, `GET /cases/{id}/timeline` |
| Monitoring | `POST/DELETE /vehicles/{id}/monitoring`, `GET /notifications`, `POST /notifications/{id}/acknowledge`; changes/consents are in workspace/inbox |
| Reminders | `POST /cases/{id}/reminders`, `DELETE /reminders/{id}`; provenance/expiry mandatory |
| Privacy | `GET /cases/{id}/export`, `DELETE /cases/{id}` with If-Match, `POST /cases/{id}/grants`, `DELETE /cases/{id}/grants/{user_id}`, `POST /cases/{id}/invitations`, `POST /invitations/accept`, `DELETE /invitations/{id}`, `POST /account/erase` |
| Source administration | Registry/capture/review operations restricted to service operator; no consumer-provided arbitrary fetch URL |

Finalized download uses a CSRF-protected POST returning private bytes, not a
long-lived public link. Draft review uses scoped images and visible unapproved
UI state; final bytes do not change at approval. Standalone unapproved renderer
fixtures also carry a watermark. Case-data export
is a separate privacy function, not an approved correspondence packet. Responses
never expose service paths, raw provider errors or credentials.

## Write semantics and errors

Require idempotency keys for investigation/draft creation, responses, outcomes and manual-send
records. Same key/same canonical body returns the original result; changed body is
409. Approval is separately bound to the exact fingerprint and current owner/revisions.
Require `If-Match` (or a bounded expected-revision field) for case/fact mutations;
stale writes are 409. Missing identity is 401; an authenticated user lacking private
resource scope gets a non-enumerating 404. Return 413 for size limits, 415 for
unsupported formats, 422 for safe schema errors and 429 with bounded retry advice.
Operational failures are distinct from completed negative assessments. Domain
errors use stable codes, safe messages, retryability and correlation IDs.

An approval fingerprint includes canonical content, rendered bytes, ordered
attachments, redaction revision, recipient, sources, facts and authority epoch.
Changing any covered element creates a new packet and invalidates old authority.
Before download, recheck source validity/freshness, ownership, approval expiry,
case revision and deletion epoch. One database transaction records the approved
download event; this is never delivery or recipient acceptance.

## Initial resource bounds

Per upload: 20 MiB; per PDF: 100 pages; at most 20 documents and 200 MiB per case,
10 open cases per household and two active jobs per household. Image decompression
limit: 30 megapixels; parser/OCR child timeout: 60 seconds per document. Enforce
both streamed-upload and decoded/derivative limits. Resource exhaustion returns a
useful partial/manual path. These are design defaults to validate on the actual
host, not evidence of supported capacity. Generated archives also have bounded
entry counts, sizes and sanitized names.
