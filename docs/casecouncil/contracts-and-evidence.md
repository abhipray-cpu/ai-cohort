# Contracts, evidence and API requirements

Requirements baseline. Strict Pydantic models, finite bounds and currentness are
implemented. The [actual contract/route map](implementation-and-operations.md)
supersedes planned route names below. Citations use source ID and exact selected
Unicode offsets rather than a redundant model-provided span ID. Conceptual objects
need not each be separate Pydantic classes.
Model, browser and import metadata are untrusted inputs; schema validity alone is
not source integrity, permission or semantic correctness.

## Core objects

| Contract | Required fields / meaning |
| --- | --- |
| `Scope` | Actor, workspace/case grants, current capability revision and restore epoch; server-resolved |
| `SourceRevision` | Case, immutable ID, original-byte digest, canonical/redacted text digests, extraction version, coverage, rights basis and source attribution |
| `EvidenceSpan` | Source revision, canonical text hash, exact text/offsets, optional page mapping; no hidden outcome label |
| `CaseContext` | Jurisdiction, product, dated facts, draft-response revision, confirmed issue registry, missing documents and attributed manual facts |
| `PolicyRevision` | Approved role roster, required issue/document checks, consensus rules, egress limits, resource policy, scope/effective dates |
| `AnalysisSnapshot` | Source/context/coverage/redaction/policy hashes, prompt/schema/provider-profile versions, authority revision and restore epoch |
| `RunGrant` | Snapshot, actor, egress approval, deadline, cumulative stage/call allowance, cancellation state and observed usage |
| `StageAttempt` | Controller role/stage, attempt sequence, lease, snapshot, request digest, safe outcome, usage receipt and validation events |
| `Proposal` | Role-bound issue alternatives, dispositions/conditions, evidence, counterarguments, missing facts and new-issue suggestions |
| `Critique` | Target proposal/issue IDs, finding type/severity, source support or exact challenged assertion, requested resolution |
| `CandidateRegistry` | Frozen candidates, canonical content/lineage, snapshot, critique/revision state and registry hash |
| `Ballot` | Issue, known candidate or explicit abstention, reasons/evidence, role and complete binding; no self-declared vote weight |
| `ConsensusResult` | Deterministic counts, quorum, blockers, route, dissent and confidence facets; never model-authored authority |
| `ReviewPacket` | Source coverage, proposals/critique/ballots, computed result, validated synthesis, usage, limitations and revision hash |
| `HumanReview` | Reviewer identity/capability, exact packet/dependency hash, corrections/override, reasons and current review state |
| `ExportManifest` | Exact packet/review hash, scope, currentness check, draft/reviewed label, unresolved items and generation time |
| `AuditEvent` | Sequence, actor/action, object/revisions, reason, safe attempt reference, predecessor and event integrity hash |

Initial API collection bounds: 20 documents/case, 10 confirmed issues/run, three
proposer roles and one critic; at most 8 citations/proposal-issue and 16 critique
findings. Reject excessive collections rather than truncate them invisibly. Validate
actual utility and prompt size during implementation; resource defaults are in
[protocol](debate-protocol.md) and [operations](operations.md).

## Citation contract

Model-facing evidence uses authorized selected spans. An implemented citation contains source
revision ID, exact quote and half-open Unicode character offsets into the
**redacted canonical revision**. Offsets use Python Unicode indexing, not UTF-8
bytes or browser UTF-16 units. The server verifies `text[start:end] == quote`, bounds,
permitted source/span membership and hashes, then supplies the exact UI highlight.
Do not silently substitute a different occurrence of a repeated quote.

Redaction/extraction may change layout and line counts. Original bytes, extracted
text and redacted text have different identities. Preserve an explicit mapping
where possible; otherwise cite the extracted/redacted revision and disclose the
missing original page mapping. Do not invent original-page coordinates.

Peer arguments and the customer's draft are attributed positions, not independent
primary evidence. Citations to them alone cannot establish policy wording or a claim
fact. Absence claims need declared complete assessment of the relevant document;
an omitted chunk is not proof a policy contains no exclusion. Missing originals,
image-only pages, unresolved OCR and inaccessible multimedia are coverage gaps.

## Revision and idempotency rules

Canonical snapshot binding covers case/source/context/issue/coverage/redaction/
policy/prompt/schema/provider profile versions plus authority and restore epoch.
Retain explicit fields so a mismatch can be explained. A hash is not an authorization
token and must be recomputed from stored content at publication boundaries.

Mutations require expected revision and idempotency key. Same key/same normalized
request returns the prior result; same key/different request is a conflict. A repeated
start cannot create a second job or reset its call counter. Review plus audit append
is atomic. Publication rechecks live access and all dependencies; a queued worker
cannot rely forever on an authorization snapshot from before grant revocation.

Historical work may be inspected by authorized users after a source change, but it
is visibly stale. Do not erase it, silently rebase it or label an old export current.

## Original proposed API routes (actual routes in runbook)

| Route family | Purpose |
| --- | --- |
| `POST/DELETE /api/session`, `GET /api/me` | Explicit per-user sessions and live scope |
| `/api/workspaces`, `/api/workspaces/{id}/members` | Authorized workspace/member administration |
| `/api/cases`, `/api/cases/{id}` | Scoped case creation, context and issue revisions |
| `/api/cases/{id}/sources`, `/api/sources/{id}` | Bounded uploads, extraction status, authorized source display |
| `/api/policies/{id}/revisions`, `/activate` | Versioned approved policy, not model-created authority |
| `/api/cases/{id}/egress-preview`, `/runs` | Exact input preview, explicit grant and idempotent scheduling |
| `/api/runs/{id}`, `/stages`, `/cancel`, `/changes` | Durable status/history and cooperative cancellation |
| `/api/runs/{id}/packet` | Authorized current/historical packet with stale/degraded flags |
| `/api/packets/{id}/reviews`, `/exports` | Attributed review and exact-revision local download |
| `/api/cases/{id}/audit` | Scoped pagination; no raw private prompts in routine logs |
| `/api/cases/{id}/erasure-preview`, `/erase` | Authorized dependency-aware retention workflow |
| `/health/live`, `/health/ready` | Safe liveness and readiness without client details |

Methods, status codes and final route names must be frozen through failing contract
tests before implementation. Mutations use CSRF/same-origin checks and capabilities;
cross-scope object existence is not disclosed. Upload URLs are not general web fetch
instructions. Dataset acquisition, user bootstrap and restore remain operator tools,
not routes exposed to the model. This table is the original design; use the
[runbook](implementation-and-operations.md) for the implemented routes and methods.
