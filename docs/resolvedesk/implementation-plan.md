# Implementation plan

## Chat-first correction (implemented with tests first)

1. Write failing persistence, follow-up retrieval, general-query, idempotency and retry tests.
2. Add `ChatCreate` / `ChatMessage` / `ChatResolution`, additive chat/turn tables and atomic send endpoints.
3. Resolve follow-ups with bounded same-thread history; checkpoint resolution and run fresh retrieval, grounding, uncertainty and search within a six-call chat budget.
4. Make conversation UI the default; keep source management and approval/export secondary. Preserve historical citations and show actual worker progress.
5. Run regression tests, web build and real two-turn HTTP/Codex acceptance against official documents. Record results and unresolved browser/Windows/quality gates in [validation](validation-2026-10-13.md).

See [chat architecture and contracts](chat.md). Original phases below still apply to the shared RAG/review pipeline.

This is the dependency-ordered delivery plan, retained alongside [actual implementation status](implementation-status.md). Core pilot phases are implemented; data-quality, browser, and Windows gates remain open.

## Technical decisions

| Concern | Initial choice | Gate / reason |
| --- | --- | --- |
| API and contracts | Python 3.12, FastAPI, Pydantic | Reuse workspace tooling and strict boundaries |
| Web | React/TypeScript | Three-pane investigation and evidence review |
| Persistence and queue | Separate SQLite WAL DB and one worker | Durable single-host processing |
| Retrieval | SQLite FTS5 BM25, section passages, version filters | Establish and score a lexical baseline before adding semantic dependencies |
| Semantic retrieval | Deferred behind a retriever port | Add only if measured recall improvement justifies CPU/RAM cost |
| AI | Existing `StructuredProvider` and installed Codex adapter | Product never calls an LLM API directly; provider still needs network/auth |
| Search | Version-scoped official PostgreSQL site search; optional Brave adapter | Default remote search needs no key; pages fetched and ranked independently |
| Hosting | Separate loopback port, Windows services, Cloudflare Access/Tunnel | Prove service identity, restart, and protected access on target host |
| Testing | pytest, captured-source fixtures, real live runs, browser acceptance | Distinguish deterministic invariants from model-quality evidence |

TenderLens extraction logic and default `make up` remain product-specific. ResolveDesk now has explicit `make resolvedesk-up`, `resolvedesk-down`, and `resolvedesk-status` targets; the common development launcher uses a product selector with separate process state and modules.

## Phase 0 — feasibility and source freeze

Verify SQLite FTS5 availability, installed Codex schema generation, and service-account runtime on the target Windows architecture. Fetch a small official 16/17 source set with notices; record hashes and headings. Select and review a handful of real historical questions, retaining original versions. Confirm the search adapter can return and fetch a relevant official page. If search credentials are absent, mark live fallback blocked while continuing contracts/retrieval work.

Gate: source provenance is reproducible, target-host dependency assumptions are known, and any external-service prerequisite is explicit. No placeholder corpus or simulated search counted as live acceptance.

## Phase 1 — contracts, persistence, and API

Start with failing tests for unknown fields, version ambiguity, passage identity, revision conflicts, and authentication. Implement the records in [contracts](contracts-and-grounding.md), SQLite migrations, immutable snapshots, cases, queue/lease, and separate answer/review revisions. Store product-specific contracts in a new `contracts.resolvedesk` module. Reuse generic provider and event primitives only after checking product coupling.

Gate: fresh and upgrade migrations preserve cases/reviews, unauthorized requests reveal no case/source data, and a retry cannot overwrite an approved revision.

## Phase 2 — ingestion and retrieval

Write tests against frozen actual manual sections: preserve headings, paragraphs, anchors, and code blocks; normalize offsets deterministically. Build FTS5 indexing and version/visibility filters. Handle punctuation-heavy error strings, quoted phrases, and safe FTS query construction. Return typed passage results and a deterministic ranking trace. Add bounded adjacent-section expansion when an answer requires surrounding conditions.

Gate: version leakage is zero on labelled cases and Recall@5 meets the development gate. Record misses before considering local embeddings. Index refresh failure must leave the prior complete revision usable.

## Phase 3 — cited answer generation and assessment

Test malformed JSON, invented passage IDs, exact but irrelevant quotes, unsupported claims, wrong versions, and missing environment details before implementing the orchestrator. Render technical reply segments from validated claims. Add bounded repair, deterministic citation/applicability checks, conservative support assessment, uncertainty reasons, and persistent events. Treat model entailment checks as advisory pending evaluation.

Gate: presented drafts meet schema/provenance rules; weak evidence is visibly qualified; provider outages have actionable errors; successful and failed stages are auditable.

## Phase 4 — actual search fallback

Deterministic adapter fault tests cover malformed results, forbidden destinations, redirects, timeout, empty results, and budget limits. Implemented fallback uses version-scoped PostgreSQL site search by default, plus optional Brave Web Search and allowlisted page fetching. Persist sanitized query, source snapshots, and checkpoint before regenerating. Distinguish missing public knowledge from missing customer environment data.

Gate: a live held-out-source case finds and uses the official page; citations reference fetched evidence rather than snippets. Search unavailable/failed states preserve prior evidence and never claim search succeeded. Validate that no confidential ticket tokens leave in queries.

## Phase 5 — reviewer workbench

Implement case queue, environment form, editable reply, evidence panel, clarification/escalation mode, investigation history, and reviewed exports. Display conflicts and missing details prominently. Keep internal investigation notes separate from customer text. Review updates use revision checks; editing invalidates prior approval.

Gate: actual browser tests complete evidence navigation, correction, reload, approval, export, and search-failure recovery at specified viewports. A successful build does not establish this gate.

## Phase 6 — evaluation and host acceptance

Acquire and adjudicate the [60-case target](data-and-evaluation.md); freeze development/test by issue family, run real Codex and search, and publish raw counts plus failure categories. Test reboot, offline provider/search, backup/restore, service account auth, protected tunnel access, and low-resource operation on Windows. Confirm reviewer effort improves relative to manual investigation.

Gate: all release criteria pass or scope is explicitly narrowed. Write the study guide and blog from measured results, including unsuccessful cases.

## Proposed API

| Route | Purpose |
| --- | --- |
| `POST /v1/cases`, `GET /v1/cases` | Create/list cases |
| `GET /v1/cases/{id}` | Case, environment revision, latest investigation |
| `PATCH /v1/cases/{id}/environment` | Supply missing details with revision check |
| `POST /v1/cases/{id}/runs` | Queue a scoped investigation; accept idempotency key |
| `GET /v1/runs/{id}` | State, stage, evidence limits, history, revision |
| `POST /v1/runs/{id}/retry` | Resume failed run from validated checkpoints |
| `GET /v1/sources/{snapshot_id}` | Authorized evidence snapshot/section |
| `PATCH /v1/answers/{revision_id}/review` | Review/edit with optimistic revision check |
| `POST /v1/answers/{revision_id}/exports` | Export approved reply or labelled escalation |
| `POST /v1/sources/refresh` | Authorized source collection refresh |
| `GET /health/live`, `GET /health/ready` | Process/storage readiness |

Mutable requests require authentication and actor attribution. Use idempotency for run/export creation. Readiness distinguishes usable local storage from optional external-provider health; do not reveal credentials in health responses.

## Definition of done

Real case → scoped retrieval → cited answer → visible uncertainty → live search when needed → human review → stable export works through the browser and target deployment. Reproduction artifacts pin source hashes, index/schema/prompt versions, runtime versions, case split, and reviewer labels. Evidence of correctness and usability is required in addition to passing unit tests.
