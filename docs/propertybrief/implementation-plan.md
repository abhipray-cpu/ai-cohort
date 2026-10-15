# Implementation plan

Original dependency-ordered plan: 14 October 2026. Implementation followed this TDD sequence. This remains the acceptance plan, not a claim that every release gate passed. See [implementation status](implementation-status.md) and [measured validation](validation-2026-10-15.md) for delivered code and remaining gates.

## Technical decisions and repository scope

| Concern | Proposed decision | Verification |
| --- | --- | --- |
| API/contracts | Python 3.12, FastAPI, Pydantic | Strict product boundaries and independent parsing |
| Web | React and TypeScript | Conversation, report, evidence and reviewer workflow |
| Persistence/queue | Per-product SQLite WAL and one worker | Lease fencing, migrations, crash/restart tests |
| Source access | Typed HPD/DOB adapters over bounded HTTPS | Actual schemas, identifier joins, paging, completeness |
| Agent | Product-specific application-controlled ReAct loop | Data-dependent branching, bounded attempts and reflection |
| AI | Shared provider interface and installed Codex adapter | Deadline propagation, structured decisions, controlled runtime tools |
| Output | Markdown/JSON export and printable HTML | Evidence/gap preservation and immutable revision |
| Hosting | Windows API/worker processes plus Cloudflare Access/Tunnel | Actual laptop acceptance |
| Isolation | Port 8002 proposed; separate DB/cache/config/process state | Existing products still operate independently |

Proposed additions: `apps/propertybrief-api`, `apps/propertybrief-web`, product contracts, product tests, `data/propertybrief` manifests, source-acquisition and evaluation utilities, backup/restore helpers, development launcher selector, and Windows startup packaging. Update workspace discovery and shared helpers only when implementation needs it; prior products must remain compatible.

## Phase 0 — actual-data feasibility and freeze

Already observed: ten dataset sample endpoints and one identity join. Remaining: metadata/dictionary capture, complete property-scoped paging, query-filter checks, stable row keys, eight-source coverage profiles, and independent portal comparison.

Acquire the 12-building feasibility cohort described in [evaluation](data-and-evaluation.md). Freeze source payloads/hashes, map status fields, identify source caps and corpus sizes, and document exact property joins. Record data-use terms and source attribution. Confirm the installed Codex provider can generate the proposed decision schema without unintended runtime tool execution.

Gate: actual records are reproducibly retrievable for a useful cohort and source-specific interpretations are documented. If one source cannot be acquired, preserve that failure and explicitly revise the coverage promise before calling the feature complete. Do not replace real validation data with invented favorable examples.

## Phase 1 — contracts, identity, persistence and API

Write failing tests for unknown product fields, invalid BIN/BBL values, multi-building lots, inconsistent supplied identifiers, unusual addresses, and candidate ambiguity. Use actual frozen field patterns, including zero/inactive identity rows. Implement contracts, deterministic candidate resolution, case/conversation revisions, jobs, budget grants, lease fencing, events and authenticated routes.

Gate: ambiguous identity cannot generate building conclusions; migrations and transaction boundaries preserve revisions; idempotent start/message requests create at most one job; unauthorized callers cannot read cases or snapshots. No automatic candidate selection based only on a model score.

## Phase 2 — source adapters and evidence

Write failing tests for complaint/problem deduplication, open/closed/program status mapping, source-specific dates, DOB test/deletion records, contradictory vacate dates, missing BIN, parcel scope, schema drift, repeated pages, caps, 429, timeout and byte limits. Distinguish actual data defects from injected transport/fixture faults.

Implement registry-driven queries, validated filters, bounded HTTP transport, source snapshots, row-key normalization, immutable evidence references, quality flags and coverage. Capture upstream metadata around pagination and report drift. Publish durable deterministic previews from source records.

Gate: complete actual property queries reconcile to independently counted frozen rows; unknown/truncated results cannot appear as no records; provenance hashes and exact field references round-trip. Wrong-property rows are excluded or explicitly parcel-scoped.

## Phase 3 — bounded adaptive agent

Write tests first using scripted provider decisions and deterministic clocks. Cover counter reservation before work, parse repair consuming calls, repeated-action detection, missing required checks, finalization allowance, timeout propagation, cancellation, worker death and stale lease writes. Supply different observations for the same initial question and require appropriate next-action/reflection changes.

Implement the loop in [agent-loop](agent-loop.md). A provider factory or compatible adapter extension must enforce the remaining deadline on each invocation. Verify the chosen Codex configuration cannot bypass application tool restrictions; read-only sandboxing alone is insufficient. Run a real structured decision smoke through the installed adapter.

Gate: all requested concepts have observable traces, attempts cannot reset budgets, and the agent selects meaningful next actions based on actual evidence. Scripted traces prove orchestration invariants; they do not establish model capability.

## Phase 4 — findings, critique, partial reports and review

Write failing tests for invented IDs/field values, valid references supporting overbroad prose, complaints promoted to violations, closed records described as current, hidden coverage gaps, and review/export revision races. Include a later-call timeout after saved findings, failed critique, malformed synthesis, and exhausted finalization budget.

Implement candidate synthesis, deterministic validators, structured critique, one bounded revision cycle, deterministic fallback and immutable report revisions. Add reviewer edits with revalidation, qualified partial export and persistent source manifests. Each provider/source failure has both a stage event and appropriate report/run outcome.

Gate: source citations resolve exactly; critical unsupported assertions are blocked; completed observations survive later failures; review cannot remove coverage limitations. Qualify unresolved semantics instead of asking the model to assert certainty.

## Phase 5 — conversational premium UI

Implement the [UI specification](reviewer-ui.md), including case list, property confirmation, persistent conversation, live checks, evidence drawer, report, task checklist, review/export and history. Follow-ups preserve identity and pinned evidence; refresh creates new revisions. Show concise decision summaries rather than hidden reasoning.

Verify actual browser journeys and screenshots at all specified viewports with real frozen cases and outage scenarios. Check keyboard/focus/contrast, source escaping, reload recovery and concurrent stale reviews. An HTTP smoke or successful build does not satisfy browser acceptance.

Gate: an analyst can investigate, inspect, follow up, edit, export and resume through the UI without losing evidence or uncertainty. Premium visual quality receives recorded review, not only a screenshot-generation claim.

## Phase 6 — actual-data/model evaluation

Build independently adjudicated labels, freeze development/calibration/held-out splits, and run manual, checklist, one-shot, and adaptive baselines. Report per-category results and failure counts against [provisional thresholds](data-and-evaluation.md). Use live Codex on frozen actual records for repeatability, then separate live-source refresh tests for integration.

Run sensitivity tests for critique, action limits, and missing data on development cases. Preserve failed sessions and avoid prompt tuning on held-out labels. Complete the real-data end-to-end matrix and record source/code/prompt versions.

Gate: thresholds pass with denominators and reviewer evidence, or the release scope/claim is narrowed explicitly. All seven requested Day 3 behaviors have a recorded actual-model example or a clearly stated failure. Customer effort/pricing remain separate validation outcomes.

## Phase 7 — operations and target host

Implement product-specific up/down/status/build/test/validate targets, a Windows-compatible direct launcher, backup/restore, product process logs and startup packaging. Test service-account Codex auth, executable path, process-tree cleanup, reboot, source/provider outages, disk full, leases and restoration into a fresh directory.

Validate the protected Cloudflare hostname and case/export authorization on the actual laptop. Measure resource use alongside the previous products and inspect queue latency under realistic work. Verify update/rollback compatibility with the database and snapshot format.

Gate: a reproducible laptop deployment, protected access, retained partial results, and a tested restore. Development convenience scripts are not a production service-management acceptance result.

## Phase 8 — learning and handoff

After implementation and validation, write `study-guide.md` and `blog.md`. The study guide traces each concept through actual contracts, orchestrator code, events, UI, and tests. The single blog draft explains the customer problem, design decisions, real datasets, observed failures, fixes and measured limits. Neither should claim successful behavior before recorded evidence exists.

Update the pack index, implementation status, dated validation report, and runbook with real commands. Include outstanding gates even if the pilot is usable. Do not publish externally as part of document creation.

## Proposed API

| Route | Purpose |
| --- | --- |
| `POST /v1/cases`, `GET /v1/cases` | Create/list property cases |
| `GET /v1/cases/{id}` | Input, selected identity, conversation and latest report state |
| `POST /v1/cases/{id}/resolve` | Generate identity candidates |
| `POST /v1/cases/{id}/identity` | Confirm candidate with expected input revision |
| `POST /v1/cases/{id}/messages` | Persist user follow-up and atomically enqueue scoped work |
| `POST /v1/cases/{id}/runs` | Start an investigation with idempotency key |
| `POST /v1/cases/{id}/refresh` | Queue new evidence acquisition/report revision |
| `GET /v1/runs/{id}` | State, steps, counters, coverage, preview and stop reason |
| `POST /v1/runs/{id}/cancel` | Persist cancellation request |
| `POST /v1/runs/{id}/resume` | Grant bounded additional work, preserving prior counters |
| `GET /v1/snapshots/{id}` | Authorized captured fields and source provenance |
| `GET /v1/reports/{revision_id}` | Immutable report revision |
| `PATCH /v1/reports/{revision_id}/review` | Reviewer edits/decision with revision checks |
| `POST /v1/reports/{revision_id}/exports` | Create reviewed complete/qualified partial export |
| `GET /v1/exports/{id}` | Authorized download |
| `GET /health/live`, `GET /health/ready` | Process/storage/worker state without secrets |

All routes are proposals. Mutations require actor attribution, authenticated access, and input/review revision checks as applicable. Use idempotency for messages, run creation, resume grants and exports. Polling is the initial progress transport; add SSE only if needed and tested through Cloudflare.

## Proposed verification commands

Implemented targets: `make propertybrief-up`, `propertybrief-down`, `propertybrief-status`, `propertybrief-test`, `propertybrief-validate-live`. Acquisition/evaluation utilities support explicit corpus/session directories and opt-in live model usage. Tested setup and target-host caveats are in [operations](operations.md).

Definition of done: real address → verified identity → adaptive bounded investigation → evidence/critique → useful complete or qualified partial report → reviewer follow-up/export works through the browser on the target Windows deployment, with independent actual-data validation and measured limitations.
