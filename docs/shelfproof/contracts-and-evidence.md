# Planned contracts, provenance, API and exports

Normative contract design. Application models/endpoints now exist; see the
[implementation map](implementation-notes.md) for actual module/DTO names and
consolidated routes. Untrusted contracts forbid extras and bound finite values.
IDs/scope/receipts/adoption/review authority are derived by code, not models.

## Domain and generation contracts

| Contract | Required information and invariant |
| --- | --- |
| `SourceGrant` | Workspace, basis/reference, permitted processing/egress, retention/expiry; owner attestation is not automatic rights verification |
| `ImportRevision` | Input hash, parser/mapping version, encoding, row/error counts, source grant and freeze status |
| `ProductIdentity` | Stable row ID, literal GTIN as text, source version/date, brand name/owner kept distinct; ambiguous mapping blocks freeze |
| `Fact` | Source field path/row, literal value, typed value, unit, measurement basis, provenance and approved use; null is not zero |
| `FactPack` | Immutable identity/facts/limitations, full hash, explicit required/optional fields, claim prohibitions and coverage |
| `DraftVersion` | Title, description, bounded claim span-to-fact map, parent/hash, source/profile/brief binding and source type |
| `CheckFinding` | Code-owned rule/family/target, severity, exact span or missing field, evidence and blocking state |
| `JudgeEvaluation` | Draft/fact/rubric hashes, five anchored ratings, evidence-bound findings, unassessable reasons; no self-authorized pass |
| `CorrectionPlan` | Parent/evaluation hashes, finding-bound operations, immutable-fact constraints and requests for missing source |
| `SelectionDecision` | Incumbent/candidate hashes, recomputed checks, adoption/rejection, improvement deltas and stop reason |
| `AttemptReceipt` | Attempt/prompt/schema/profile binding, timestamps, exit/audit status, nullable measured usage, safe diagnostic and reservation |
| `ReviewDecision` | Reviewer, exact selected artifact/snapshot, accept/reject/needs-data, reason and findings acknowledged; no maker self-approval |
| `PatchExport` | Current approved row IDs/hashes, typed content patch, provenance/source labelling, reviewer and unresolved summary |

Model text bounds: title 1–150 code points; description 1–5,000; at most 40 declared
claims per draft, eight fact references per claim, 20 judge findings and 40 plan
items. Claim spans use canonical Unicode offsets and exact quotes. Independent
validators reject unknown paths, unsupported numeric transformations and references
outside the approved task. Full natural-language claim detection is not guaranteed.

## Source normalization rules

Store raw source bytes/hash before parsing; canonical text and typed facts are a
new hashed representation. Preserve literal source fields and extraction/mapping
lineage. Use decimal arithmetic, not unbounded float guesses. Do not treat a serving
quantity as package size or silently change per-100-g values into per-serving values.
No density conversions between g/ml. Any permitted explicit conversion must be
deterministic, versioned and retain its operands/formula; v1 defaults to no conversion.

Ingredients remain literal ordered source data, not reconstructed from prose.
If a profile requires the ingredient list in the description, insert the approved
literal list deterministically within the field budget; if it cannot fit, block
the row instead of truncating or paraphrasing it. Raw facts and optional mentions
are distinct from a required complete ingredient disclosure. Do not infer a formal
allergen declaration from an ingredient token.
Diet/certification/allergen-free/medical claims are forbidden output categories in
v1; source presence is not a model-issued certification. Missing required evidence
cannot be repaired by a judge score. A raw brand-owner field is not a brand-name alias.
Restricted claims embedded in an official product name require an out-of-scope
outcome, not a fabricated replacement name or covert loss of identity.

Version bindings include client/workspace, source/mapping revisions, facts, existing
draft, profile, brief, rubric, protocol/prompt/schema versions and actor/authority
epoch. Review/export must recheck the same binding and current source authority.

## Proposed HTTP surface

All mutable operations use authenticated sessions, CSRF/same-origin protection,
idempotency keys and expected revisions. Objects are workspace-scoped before
existence/metadata is exposed. Arbitrary URL fetch and model configuration are absent.

| Route group | Purpose |
| --- | --- |
| `/api/session`, `/api/me`, `/api/users` | Explicit credentials, sessions and admin-created users |
| `/api/workspaces`, `/{w}/members`, `/{w}/rights` | Client isolation, roles and expiring source/egress grants |
| `/{w}/profiles`, `/{w}/briefs`, `/{w}/rubrics` | Versioned owner-approved policy; immutable activated revisions |
| `/api/imports`, `/{id}/mapping`, `/{id}/freeze`, `/{id}/rows` | Bounded upload, explicit mapping/error preview and frozen facts/drafts |
| `/api/batches`, `/{id}/egress-preview`, `/{id}/start`, `/{id}/cancel` | Frozen row selection and cumulative allowance, explicit start/cancel |
| `/api/batches/{id}/tasks`, `/api/tasks/{id}` | Paginated row state, version history and nullable receipts |
| `/api/tasks/{id}/versions`, `/{id}/evaluations`, `/{id}/plans` | Scoped exact artifact inspection; no blind model retries |
| `/api/tasks/{id}/reviews`, `/{id}/edits` | Exact-version review or a new attributed draft requiring separately authorized reevaluation |
| `/api/batches/{id}/metrics`, `/{id}/audit`, `/{id}/exports` | Stable metrics/denominators, audit and explicit patch creation |
| `/api/exports/{id}`, `/api/imports/{id}/erasure-preview` | Authorized download and dependency-aware erasure |
| `/health/live`, `/health/ready` | Safe liveness and worker/schema/journal readiness, not model-quality assurance |

Use 401 for no session, 403/indistinguishable 404 for forbidden objects, 409 for
revision/idempotency/authority conflicts, 413 for limits, 422 for invalid contracts,
429 for admission/rate limits and 503 for unavailable required capabilities. Do not
echo credentials, private rows or raw provider errors in responses.

## Export boundary and Google profile

Versioned profile `google-merchant-us-en-text-v1` targets **partial text patches**.
Follow the [official title](https://support.google.com/merchants/answer/6324415?hl=en-GB)
and [description](https://support.google.com/merchants/answer/6324468?hl=en) source
specifications for structured fields and AI provenance. Both generated/revised text
fields retain `trained_algorithmic_media`; human review must not silently remove it.

Machine JSON patches contain the original row key/GTIN, structured title/description,
source bindings and versioned serialization metadata. They do not synthesize price,
availability, URLs, nutrition panels or a complete merchant feed. Customer merging
into their authorized full feed occurs outside the service. No live credentials.

Review CSV is a distinct spreadsheet-safe view: formula-leading cells are neutralized
with a documented reversible display escape and GTINs preserved as text. It is not
the machine-authoritative upload artifact. Serializer tests cover Unicode, quotes,
newlines, separators, long values and lossless source-key semantics.

Draft exports are visibly `UNAPPROVED` and non-upload review artifacts. Only current
independently reviewed, hard-gate-passing rows enter the approved machine patch.
Unresolved/stale/erased/unauthorized rows are excluded explicitly with counts/reasons,
not silently omitted from a success denominator. Edits invalidate old approvals;
historical downloaded files cannot be recalled and must not be represented as current.
