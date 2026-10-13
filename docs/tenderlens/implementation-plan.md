# Implementation plan

This is a dependency ordered delivery plan for TenderLens. Each phase produces a demonstrable artifact and has a gate. The 14 day challenge is a scheduling constraint, not a reason to waive the release gates. If the gates fail, ship an explicitly labeled pilot with limited document types and review only output.

## Technical baseline

| Concern | Initial choice | Reason / check |
| --- | --- | --- |
| Backend | Python, FastAPI, Pydantic v2 | Schema generation and server side validation in one language |
| Frontend | React + TypeScript | Responsive reviewer workspace and typed API client |
| Storage | SQLite WAL + private filesystem | Simple single Windows host operations; backups and recovery tested |
| Work queue | SQLite job table with lease/heartbeat | Durable jobs without another server process |
| PDF | Text extraction first, OCR fallback | Preserve page/offset provenance and support scanned input |
| AI | `codex exec` through `LocalCodexProvider` | Installed executable; schema output and last message file supported by official examples |
| Remote access | Cloudflare Tunnel + Access | Product URL on the Windows host; identity at the edge |
| Tests | pytest + browser end-to-end tests | Covers contracts, real PDFs, and reviewer behavior |

Versions are pinned only after a working spike on the deployment laptop. Record exact versions in lockfiles and an operations inventory. OpenAI's [Codex JSON Schema example](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex) establishes the CLI pattern, but Windows service account authentication and version behavior still need a host test.

## Phase 0 — runtime and data feasibility

- Prove the installed Windows `codex exec` can read a small bounded input, accept an output schema, write a final JSON file, and run under a dedicated noninteractive service account.
- Prove its sandbox/approval settings stop document content from triggering filesystem writes or tools. Confirm the model/network authentication path and usage limits.
- Parse three different public tender packs: native text, image scan, and amended pack. Capture pages, offsets, tables, and OCR quality.
- Create a corpus manifest with source URLs, document hashes, rights notes, and known document relationships.

Gate: repeatable CLI invocation on the target host; 3 documents retain page references; no unbounded subprocess or hidden interactive prompt.

## Phase 1 — contracts and persistence

- Add a Python workspace and pinned dependencies; add backend and shared package pyprojects. Add a frontend workspace and lockfile.
- Define versioned Pydantic models for opportunity, document, page, claim, requirement, citation, extraction result, review action, and export.
- Define strict tool request/result contracts, especially `PageLookupRequest` and `PageLookupResult`.
- Implement SQLite migrations, document storage, job lease/heartbeat, event persistence, and schema version fields.
- Add API authentication/authorization, request limits, upload validation, and safe error responses.

Gate: migrations run forward on a clean Windows install and from a previous schema; contracts reject unknown/malformed fields; restart preserves jobs and reviews.

## Phase 2 — ingestion and evidence index

- Upload multiple PDFs per opportunity; calculate SHA 256; reject duplicate content by hash while allowing multiple source references.
- Extract native text by page with normalized offsets and keep original page rendering for side by side review.
- Add OCR fallback only for pages below an extraction quality threshold; expose the quality signal.
- Detect title/reference/date/corrigendum candidates and link amendments to the original pack with reviewable provenance.
- Build deterministic page search and quote matching; validate every lookup tool result before passing it onward.

Gate: sampled quotes resolve to the correct PDF page; bad OCR and table loss are visible and do not silently become extracted facts.

## Phase 3 — structured agent

- Generate JSON Schema from the versioned Pydantic output contract; simplify unsupported schema constructs only through a tested transformation.
- Implement `LocalCodexProvider` with safe argument arrays, per run temp paths, subprocess deadline, output size limit, exit code and stderr capture, and cleanup policy.
- Send bounded document evidence and field instructions. Treat PDF text as untrusted source content.
- Validate JSON syntax, output schema, cross field rules, tool results, and page/quote evidence independently of provider schema enforcement.
- Repair parse/schema errors with a maximum of two attempts; distinguish operational retries from output repair. Persist every attempt and failure.
- Plan bounded page/character chunks; checkpoint each validated chunk by run and pinned document hash. On a typed Codex timeout, split a multi-page chunk and retry smaller leaves; keep completed leaves durable. On a terminal failure, expose a partial non-exportable brief and same-run retry. Log provider timeouts in run history.

Gate: fault injection proves repair, timeout splitting, partial export lock, and checkpoint resume; all successful outputs pass Pydantic and citation checks; no false `verified` status without evidence. A long-pack live run must complete within documented limits before claiming long-pack support.

## Phase 4 — premium reviewer product

- Build opportunity list, upload progress, extraction status, two pane brief/PDF review, amendment conflict view, and audit timeline.
- Provide claim accept/edit/unresolved actions and keyboard navigation. Keep original AI value and reviewer value separately.
- Add organization profile and fit assessment only after requirement extraction is reliable. Never label a company eligible without profile evidence.
- Export approved JSON and Markdown; include source metadata, provenance, version, and review state.
- Test desktop, tablet, and narrow viewport flows; include accessible focus, contrast, empty/error/loading states.

Gate: a reviewer completes the prescribed tasks in [reviewer UI](reviewer-ui.md) without inspecting logs or using developer tools.

## Phase 5 — evaluation, operations, release

- Freeze a real document test split and adjudicated gold labels; run the full evaluation in [data and evaluation](data-and-evaluation.md).
- Add browser end-to-end tests with public documents, failure fixtures, and evidence navigation.
- Package Windows services with explicit startup order, health endpoints, log rotation, backup, restore, and update/rollback runbook.
- Configure Cloudflare Tunnel for the product only, enable Access, test session expiry and unauthorized requests.
- Run a restart and recovery drill on the actual laptop, then publish a versioned pilot release with measured limits.

Gate: quality, security, recovery, and usability targets all pass. Record any unmet target as a release blocker or narrow the supported input scope.

## Main API contract (proposed)

| Route | Purpose |
| --- | --- |
| `POST /v1/opportunities` | Create an opportunity |
| `POST /v1/opportunities/{id}/documents` | Upload a PDF with source metadata |
| `POST /v1/opportunities/{id}/runs` | Enqueue extraction for a document set version |
| `GET /v1/runs/{id}` | Poll status, attempts, errors, and draft reference |
| `POST /v1/runs/{id}/retry` | Requeue a failed/partial run without discarding completed chunks |
| `GET /v1/opportunities/{id}/brief` | Read current draft plus verified source links |
| `PATCH /v1/claims/{id}/review` | Accept, edit, or mark unresolved with reason |
| `POST /v1/opportunities/{id}/exports` | Export only an approved snapshot |
| `GET /health/live`, `GET /health/ready` | Process and dependency readiness |

All mutable routes require authenticated users and idempotency keys where a retry could duplicate work. Use opaque IDs. Document files are served through an authorized route, not a public file directory.

## Definition of done

- Product: the user journey from PDF upload to reviewed export works on the old Windows laptop and through the protected tunnel.
- Reliability: a valid brief has verified citations, all validation layers pass, and errors surface as actionable states.
- Data: benchmark dataset and scoring script are versioned with documented provenance and adjudication.
- Operations: host restart, queued job recovery, restore from backup, and CLI auth failure are tested.
- Evidence: release notes include dataset version, model/CLI/parser versions, measured accuracy, latency, and known unsupported document types.
