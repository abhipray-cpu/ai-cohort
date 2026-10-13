# Product specification

## Customer and outcome

Primary user: a bid manager at a small or medium services firm deciding whether to pursue an opportunity. Secondary user: a reviewer who checks legal, finance, and technical obligations. The job is to turn long, amended tender packs into a concise, source backed action list without overlooking a mandatory requirement.

The product ingests one opportunity with one or more PDFs, including corrigenda. It produces a versioned bid brief. The human reviewer remains responsible for the final bid decision.

## Core journey

1. Create an opportunity and upload PDFs or add a source URL. The system records filename, source URL, checksum, and capture time.
2. Inspect page extraction quality. Image only or low quality pages are flagged for OCR and review.
3. Run extraction. The backend builds bounded document chunks and asks the local Codex CLI for a schema constrained result.
4. See a draft brief with deadline, buyer, scope, eligibility, required submissions, technical requirements, evaluation criteria, disqualifiers, and financial terms. Every material claim has a page and quoted evidence.
5. Reviewers accept, edit, or mark each claim unresolved. A claim that cannot be grounded stays unresolved.
6. Record organization capabilities separately; only then compute a preliminary fit assessment. Users can override it with a reason.
7. Approve and export JSON and a readable brief. The export records reviewer, time, document set version, and schema version.

## Scope of the first release

| In | Later |
| --- | --- |
| PDF upload, PDF text extraction, OCR fallback | Email/portal monitoring and automatic ingestion |
| Manual addition of corrigenda | Automatic corrigendum discovery |
| Structured extraction and claim citations | Multilingual review interface |
| Pydantic validation, repair attempts, failure log | Cross opportunity analytics |
| Reviewer edits, approval, JSON/Markdown export | CRM and bid management integrations |
| Real corpus benchmark and fault injection | Automated proposal drafting |

No automatic bid submission or autonomous bid/no bid decision is in scope.

## Contract outline

`Opportunity` has buyer, procurement identifier, title, captured source URLs, jurisdiction, and document set version. `Document` has checksum, MIME, page count, ingestion state, and extraction quality. `Claim` has type, normalized value, original text, source document/page/quote, verification state, and reviewer change history. `Requirement` adds mandatory/optional status, category, due stage, and evidence. `BidBrief` groups claims, open questions, reviewer state, schema version, and export provenance.

Use explicit `unknown` or `not_stated` states. Do not substitute null with a guessed value. Deadline normalization stores the source string, parsed local time, timezone if stated, and UTC only when timezone is known. A deadline in the past remains a valid extraction and is flagged as expired; it is not a schema failure. Evaluation weights need not total 100 when the tender only lists some criteria.

## Business rules

- A material claim cannot be marked `verified` without a matching source page and quote.
- A corrigendum supersedes an older claim only when the replacement is explicit; otherwise show both and flag a conflict.
- A `mandatory` requirement without evidence cannot be approved.
- The fit assessment is `insufficient_profile` until the user supplies the organization profile. Missing evidence cannot become `eligible`.
- AI generated text is draft content. Review state and manual edits are distinct, never overwritten by a rerun.
- Every run is reproducible from document checksums, parser version, schema version, prompt version, Codex CLI version, and model identifier.

## Release acceptance

- A bid manager can upload a representative 20 to 60 page tender pack, obtain a draft, review evidence, and export an approved brief.
- Clicking any material claim opens the cited page and highlights its quote or reports why highlighting was unavailable.
- Bad JSON, invalid types, bad tool results, missing citations, and conflicting corrigenda have visible, recoverable states.
- Critical errors and usability targets meet the gates in [data and evaluation](data-and-evaluation.md).
- A Windows restart restores the service and queued work without losing approved reviewer changes.
