# Contracts, API and evidence lineage

Status: original target contracts/API; implemented subset and deviations are in the [runbook](implementation-and-operations.md). Not every proposed endpoint/class below exists. Strict contracts reject extra fields, oversized strings/lists, invalid enums, NaN/infinite numbers and caller-supplied ownership/usage authority. Use server-derived scope and immutable revisions throughout.

## Domain contracts

| Proposed contract | Required contents / invariants |
| --- | --- |
| `FeedRevision` | Workspace, role (master/supplier), raw/normalized hashes, parser/mapping version, row/error counts, charset and import provenance |
| `ProductRecord` | Stable source-row ID, literal supplied fields, normalized values with location mapping, no inferred missing attributes |
| `CandidateSnapshot` | Query revision, index revision, ordered candidate IDs/scores, retrieval config and truncation/coverage warnings |
| `ModelProfile` | Approved configured identity, verified effective identity evidence, capability timestamp, usage semantics and enforceable controls |
| `RouteDecision` | Frozen policy/calibration, feature summary, selected profile or deterministic/manual route, reason and expected allowance |
| `GenerationRequest` | Isolated label-free context/schema digest, actual chosen profile, deadline and enforceable limits |
| `GenerationResult` | Proposal text, effective identity evidence, elapsed/exit/audit status, bounded events and usage with source/unknown flags |
| `PairProposal` | Same/different/insufficient enum, known candidate ID, source field references, literal evidence, conflicts and optional diagnostic self-confidence |
| `TaskDecision` | Pair outcomes, row outcome, applicable calibrated score, blockers, terminal reason and source/policy/model binding |
| `BudgetReservation` | Attempt/account IDs, authorized ceiling, reserved units, state, epoch and optimistic revision |
| `UsageEvent` | Unique attempt/event, measured nullable fields, semantic version, cost-basis/rate-card IDs, settlement status and liability |
| `ReviewDecision` | Actor, expected task revision, explicit accept/correct/reject, target ID, reason and exact context binding |
| `MappingExport` | Current reviewed links, exclusions/coverage, revision manifest, generating actor/time, hash and snapshot ID |

Do not add usage/model telemetry as model-generated JSON. It must come from audited runtime events/capability evidence; unknown is a legitimate state. Provider stderr is bounded diagnostic data, not a trustworthy usage oracle or raw user-facing error.

## Evidence validation

Source citations identify feed hash, row ID, original field and exact substring/offset. A valid quote must resolve to the current immutable text. Unit normalization records the rule and original; never overwrite the literal source. Candidate IDs must belong to this task's scoped snapshot. A foreign row, stale digest, impossible offset or quoted-but-nonexistent attribute rejects the proposal.

Literal evidence proves provenance, not semantic correctness. A quoted “8GB” on each side does not establish equal form factor, pack size or condition. Deterministic conflict validators remain conservative; absent attributes cannot be generated into existence. Validate row-level exclusivity after pair checks. Reviewer corrections are attributed human assertions, not retroactive model successes.

## Proposed same-origin API

All protected endpoints perform object authorization before retrieval. Mutations require session/CSRF checks and scoped idempotency or expected revision as appropriate.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/session`, `DELETE /api/session` | Authenticate/logout; hashed expiring session |
| `POST /api/feeds`, `POST /api/feeds/{id}/freeze` | Bounded import/preview and immutable accepted revision |
| `GET /api/feeds/{id}/records` | Scoped paginated literal evidence |
| `POST /api/batches`, `POST /api/batches/{id}/start` | Bind revisions/policy/budget and enqueue once |
| `GET /api/batches`, `GET /api/batches/{id}` | Coherent batch/coverage/accounting summaries |
| `GET /api/batches/{id}/tasks`, `GET /api/tasks/{id}` | Paginated rows and current evidence/attempts |
| `POST /api/tasks/{id}/review` | Expected-revision accept/correct/reject; no approval default |
| `POST /api/batches/{id}/cancel`, `POST /api/batches/{id}/continue` | Fence dispatch or authorize bounded continuation |
| `POST /api/batches/{id}/budget-increases` | Owner-only explicit additional allowance; no history reset |
| `GET /api/batches/{id}/analytics`, `GET /api/batches/{id}/audit` | Snapshot-consistent usage/coverage and events |
| `POST /api/batches/{id}/exports`, `GET /api/exports/{id}` | Explicit current-snapshot creation and authorized download |
| `GET /api/readiness` | Safe readiness summary; private capability details owner-scoped |

Use 400/422 for malformed input, 401 for no session, 403 or indistinguishable 404 for forbidden objects, 409 for revision/idempotency/lease conflicts, 413 for size limits, 429 for rate/queue limits and 503 for unavailable required capability. Do not expose feed names, counts or private diagnostics through forbidden-object errors. Budget exhaustion is a persisted domain outcome, not merely a transient HTTP exception.

## Event and export contracts

Transactional events include import/freeze, index completion/failure, batch authorization, route selection, reservation, dispatch intent, provider result/failure, usage settlement/unknown/overrun, validation rejection, early exit, escalation, review, budget increase, cancel, stale transition, export and restore reconciliation. Redact content; restricted evidence links serve authorized readers separately.

CSV export escapes formula-leading cells and distinguishes own IDs from external supplier SKUs. Include source revisions, decision/reviewer identity, confidence basis, timestamps and coverage manifest; never silently omit unresolved rows from the summary. Export a separate unresolved report. Schema versions and stable IDs make replay comparison possible. Saved historical exports retain their original binding; changing inputs cannot make an old file current.

Existing shared `StructuredGeneration` lacks typed model/usage fields. Extend the shared boundary additively or wrap a new version behind a CatalogBridge port; preserve old consumers' construction behavior. No product-controller imports across apps. Contract tests must prove backwards compatibility and that raw runtime telemetry is not discarded before settlement.
