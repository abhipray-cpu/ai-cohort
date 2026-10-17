# Typed contracts, evidence and API proposal

Status: strict Pydantic ingress/analysis/decision/review models and application-level scope/evidence/currentness checks implemented. The broader vocabulary/routes below are design names, not all separate runtime classes/endpoints. [Actual mapping](implementation-and-operations.md). Actual schemas forbid extra fields and bound text, collections and revisions. Server-resolved identity/authority cannot come from model or browser claims.

## Domain contracts

| Contract | Required meaning and key fields |
| --- | --- |
| `Scope` | Authenticated actor, workspace/case grants, current authority revision and restore epoch |
| `DocumentRevision` | Case/version, original bytes digest, canonical text digest, extraction/version map, page/chunk coverage, source identity |
| `BusinessContextRevision` | Company side, permitted purpose and typed policy facts, provenance, actor and expected revision |
| `PlaybookRevision` | Approved rule IDs/types, supported checks, required roles/quorum, missing-data actions, owner, version/hash |
| `AnalysisSnapshot` | Bound source/text/coverage, playbook/context/finding versions, policy/model/prompt/schema versions and epoch |
| `FindingProposal` | Check/hypothesis ID, interpretation enum, multiple evidence spans, AI rationale, reason codes; no approval authority |
| `FindingReview` | Reviewer correction/confirmation, exact old/new value, rationale and current bound snapshot |
| `UncertaintySignal` | Reason, affected check/source, deterministic versus model origin, severity, detector version and resolution requirement |
| `ApprovalRequest` | Stable ID/revision, question kind, blockers, source/policy references, permitted response schema, assignees/roles, due/expiry, binding hash |
| `Decision` | Actor, request/revision, explicit response type, validated fact/exception scope, rationale, time/expiry, binding/idempotency key |
| `ResumeIntent` | Checkpoint, valid decision-set hash, expected case/authority/epoch and cumulative grant counters |
| `JobGrant` | Lease token, original active deadline, reserved call counts, attempt IDs and explicit continuation authority |
| `PacketRevision` | Source/check coverage, findings/decisions, unresolved items, exact source/policy/context hashes, internal status and limitations |
| `FinalReview` | Final-review capability, exact packet/dependency hash, acknowledgment and expected revision |
| `AuditEvent` | Scope, sequence, actor/action, object/version references, outcome/reason, canonical event hash and prior hash |
| `SyncPage` | Authorized events/cursor, current revision/epoch, reset and has-more; no unrelated metadata |
| `BackupManifest` | Schema/store identity, payload hashes, ledger binding, audit head, epoch and restoration constraints |

Interpretation enum: `Entailment`, `Contradiction`, `NotMentioned`, plus a separate execution assessment `supported`, `uncertain`, `unavailable`, `incomplete` or `unassessed`. Do not add abstention as if it were a dataset gold class. Request/decision state is separate from semantic labels.

## Evidence rules

Implemented post-validation addition: `Finding.evidence_quotes` is an optional bounded list of `{span_id, quote}`. Each `span_id` must be unique within that list and present in `evidence_ids`; the verbatim quote must occur exactly once inside that original authorized span. `intake.resolve_evidence` derives the narrower original Unicode offsets server-side and checks the resulting source slice. Unknown/ambiguous/invented quotes fail validation and receive only bounded repair. ID-only legacy/manual findings retain whole-span evidence. Exact substring validity is provenance, not semantic correctness. See [fix validation](fixes-and-validation-2026-10-17.md).

Each citation binds source document version, canonical text hash, original character start/end, exact quote and optional page/box mapping. Offsets are Python Unicode character indices, half-open `[start,end)`, not UTF-8 bytes or browser UTF-16 positions. APIs return server slices so the browser does not recalculate offsets incorrectly. Original bytes and extracted text use distinct hashes. Normalization must retain a reversible offset map; if it cannot, cite the exact extracted revision and disclose extraction limits.

Validate `text[start:end] == quote`, range bounds, source ownership, current dependency hash and page coverage. Canonical integrity must be recomputed, not trust a stored hash after body corruption. A model-proposed evidence ID must be in the supplied authorized set and resolve to the original text at read, egress, decision and publication boundaries. Multiple exception/support spans may be necessary; copied rationale is not original evidence.

`NotMentioned` has no supporting positive span by default; it is permitted only for a fully assessed declared check/document scope and must expose coverage. A context window lacking a clause is not proof the entire NDA lacks it. An unsupported quote rejects the proposal or yields uncertainty, not arbitrary exact-quote substitution.

## Binding and optimistic concurrency

Define a canonical versioned binding over case ID, document revision/digests, extraction/coverage, approved playbook revision/hash, business context revision, findings revision, request purpose/revision, required authority policy and restore epoch. Store explicit fields alongside the digest so differences can be explained. A hash is an integrity binding, not a capability token or signature.

Mutations require expected object revision plus idempotency key. Same key/same normalized request returns the original result; same key/different request conflicts. Exact duplicate bytes do not silently create a new independent benchmark example. Source changes append a new version and invalidate dependent approvals; a browser cannot choose an old version and call it current.

Keep deterministic checks separate from model schema validation. A valid JSON decision with a real request ID can still be unauthorized, expired, overbroad or stale. Decision and audit append must be atomic. If audit persistence fails, no decision commit.

## Validation and diagnostics

Stages: bounded ingress → extraction integrity/coverage → structured model shape → source references/interpretation eligibility → deterministic policy → request authority → human response → resume dependency fences → final review/export currentness.

One repair maximum per model stage under a pre-reserved grant. Parse/quote/schema validation failures, provider timeouts, unavailable tool audits and policy denials have separate safe events. Persist stage/checkpoint/attempt IDs and error categories; do not put raw private prompts, document bodies, session tokens or credentials into routine logs. A final job error never replaces earlier validation history.

## Proposed API surface

| Method / route family | Purpose |
| --- | --- |
| `POST/DELETE /v1/auth/session`, `GET /v1/me` | Per-user authenticated sessions/logout |
| `/v1/workspaces`, `/v1/workspaces/{wid}/members` | Workspace list/create and privileged role management |
| `/v1/workspaces/{wid}/cases`, `/v1/cases/{cid}` | Scoped case creation/context and status |
| `POST /v1/cases/{cid}/documents`, `GET /v1/documents/{id}` | Bounded uploads and authorized immutable source reads |
| `/v1/workspaces/{wid}/playbooks`, `/v1/playbooks/{id}/revisions`, `/activate` | Draft/version/approve policy with authority separation |
| `POST /v1/cases/{cid}/analyses`, `GET /v1/jobs/{id}` | Explicit bounded analysis grants and safe status |
| `GET /v1/cases/{cid}/findings`, `/coverage` | Findings, uncertainty and full assessment denominator |
| `GET /v1/approval-requests`, `/v1/approval-requests/{id}` | Authorized request inbox and source/policy detail |
| `POST /v1/approval-requests/{id}/decisions`, `/assignments` | Typed immutable decisions and explicit reassignment |
| `POST /v1/decisions/{id}/withdrawals` | Authorized withdrawal and dependent readiness invalidation |
| `POST /v1/cases/{cid}/resume`, `/cancel` | Idempotent validated scheduling/cooperative cancellation; no force-resume |
| `GET /v1/cases/{cid}/changes`, `/audit` | Scoped cursor sync and authorized audit inspection |
| `/v1/packets/{id}/reviews`, `/exports` | Final exact-revision review and local download |
| `/v1/cases/{cid}/erasures/preview`, `/confirm` | Dependency-aware explicit owner erasure |
| `/health/live`, `/health/ready` | Safe process/storage/audit readiness, no private counts |

Finalize routes through failing contract tests during implementation. All mutations use applicable capability, CSRF/same-origin, revisions and idempotency. Dataset capture, backup restore and user bootstrap are explicit operator tools, not model-callable admin endpoints. A `resume` request schedules a recheck; it cannot grant approval by itself.
