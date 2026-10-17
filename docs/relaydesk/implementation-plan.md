# Dependency-ordered TDD implementation plan

Status: implementation authorized and pilot delivered via failing tests → implementation → refactor → regression. This preserves the original dependency order and broader acceptance gates. [Implemented scope/deviations](implementation-and-operations.md), [engineering evidence](implementation-validation-2026-10-16.md). Independent quality/browser/Windows/commercial gates are not silently marked complete.

## Stack and boundaries

Proposed: Python 3.12/FastAPI/Pydantic, React/TypeScript/Vite, separate SQLite WAL with revisioned vectors, CPU encoder, installed shared Codex adapter, loopback port 8004 and Windows scheduled-task/Cloudflare target. Pin dependencies/model artifacts only after host compatibility checks. No GPU, Docker, remote embedding API or separate vector service required by this proposal.

Add under `apps/relaydesk-api/`, `apps/relaydesk-web/`, product contracts/tests, acquisition/audit utilities and additive launcher/service configuration. Do not import earlier product databases/orchestrators. Reuse provider contracts only after isolation/timeout/environment tests. Do not treat ResolveDesk's retrieval as proof of learned vector embeddings.

## Phase 0 — source feasibility and immutable inputs

First failing tests: source identity, pagination correspondence, duplicate/bot separation, source edits/current-state leakage, malicious URLs, oversized inputs, quota checkpoint/resume and hash-tampered freeze. Implement read-only acquisition/normalization with immutable raw snapshots and explicit missing coverage. Start with a small seed for development, then acquire the full 200-thread/20-repository/5,000-message cohort before release evaluation.

Gate: declared selection/splits/terms/privacy manifest, usable positive/negative/correction examples and preserved failures. One successful API page or a synthetic chat is not enough. Review unknown historical edits conservatively; do not fabricate original revisions.

## Phase 1 — strict contracts, durable history and authorization

Failing tests: bounded JSON/enums, untrusted actor/account IDs, password/session/CSRF handling, scoped lists/artifacts/events, grant revocation, idempotent append, ordered turns, optimistic revision conflicts, closed DB connections, transaction rollback, lease fencing and reserved counters.

Implement independent store/auth/memberships/source revisions/conversations. Replay persistence after restart before adding model calls. Explicit namespaces distinguish account, case, conversation and interactive session; multiple sessions must share only authorized durable case/account memory.

Gate: no cross-account metadata/content exposure, duplicate turns or silent stale edits; full previous-product regression remains green.

## Phase 2 — memory proposals, states and source evidence

Failing tests: proposed versus performed action; outcome attribution; reporter/version differences; unknown ownership/date; correction/supersession ambiguity; assistant suggestion poisoning; exact source offsets/hashes; denied account promotion; erase dependency graph.

Implement deterministic state reducer and source-linked immutable memory revisions. Model extraction may later propose typed items but cannot overwrite verified state or invent commitments. Build independent expectation fixtures from reviewed real source spans, with synthetic mutations explicitly labelled.

Gate: important investigation categories and uncertainties survive without any model “truth” shortcut. Case closure/participant authority is not inferred evidence.

## Phase 3 — real CPU embedding and vector recall

First tests: fixed model manifest/hash/dimension, pooling/normalization, invalid/zero/nonfinite vectors, text chunk coverage, exact cosine ordering, hard prefilter isolation, incompatible models, restart persistence, source/row revision mismatch, batch/CPU bounds and lexical-only degradation.

Provision a trusted pinned CPU artifact explicitly. Verify ONNX compatibility if selected; do not execute untrusted model code. Implement actual learned embeddings and bounded exact vector retrieval, plus optional lexical candidates. Fake vectors are allowed only in unit-bound tests, not concept acceptance. Test paraphrase recall outside the buffer using the real encoder.

Gate: actual model artifacts/results recorded; correct scope before ranking; supported Windows wheels/resource cost assessed; embedding outage never impersonates vector success.

## Phase 4 — buffer, relevance and compression

Failing tests: token/character budgets including schemas, restart reconstruction, a critical old fact beyond the buffer, rank feature normalization and calibration, negation/version/error-code matches, irrelevant queries/abstention, unresolved low-similarity commitments, multi-stage compression drift and omission denominators.

Implement versioned buffer/context assembly, rank policy and structured compressor using original-source dependencies. Compression retains critical state or declares partial coverage. Select rank thresholds only on development/calibration data; a similarity score is not confidence. Keep deterministic source-only fallback.

Gate: labelled preservation/recall/abstention checks and explicit coverage; no all-green metric computed solely from presented memories.

## Phase 5 — real cross-session sync and erasure

Failing tests: two separate clients/processes, expected-revision race, index lag/read-your-writes, edited source during generation, stale job after erase, scope revocation mid-flight, duplicate event delivery, cursor expiry/reset, API/worker crash and old-backup forgotten-data resurrection.

Implement atomic memory/event/index-job writes, fenced async indexing, scoped cursor polling, revision-aware caches and final publish checks. Suppression and erasure have separate contracts/UI semantics. Erasure ledger/restore epoch cannot be an afterthought. No offline multi-master mode.

Gate: a newly opened session/restarted process sees latest authorized memory; correction/deletion cannot be resurrected by a stale index/summary/prompt cache.

## Phase 6 — installed Codex conversation and handovers

Failing tests: strict structured extraction/summary/reply, foreign or stale IDs, source-injected tools, unsupported technical claims/promises, invalid JSON, bounded repair, provider nonzero exit/timeout, egress denial, safe stage diagnostics, descendant cleanup and later-stage failure preserving earlier checkpoints.

Use the shared isolated provider through an application-owned boundary with minimized environment, no native tool bypass and remaining deadline. One repair per stage, no unlimited hidden retries. Separate completed AI stages from durable fallback reports. Review/export binds the exact fresh revision; partial limits survive export.

Gate: actual Codex calls over real data, recorded stages/source manifests, no direct product model API or automatic customer actions.

## Phase 7 — premium UI and HTTP/browser acceptance

Test server contracts and frontend presentation behavior first. Implement case rail, conversation/take-over handover, timeline, memory/source drawers, rank/readiness indicators, revision conflicts, reviewed exports and explicit forget workflow. Forms must expose egress and privacy choices.

Run full authenticated HTTP journeys, then actual two-browser keyboard/viewport/accessibility journeys from [UI](reviewer-ui.md). Build/HTTP success does not pass the browser gate. If browser tooling is unavailable, preserve that limitation.

## Phase 8 — rigorous cohort validation

Run all 200 frozen-thread ingestion/replay cases and complete independent labels for the 300-question split. Audit stage-wise omitted facts, retrieval/answer/summary support, temporal leakage and poisoned-source isolation. Actual Codex validation must cover the preselected held-out questions within declared usage budgets; any unrun/provider-unavailable case remains unvalidated/failed, not a pass.

Compare prescribed baselines/ablations and retain failures. Report distinct threads/messages/facts/queries separately from repeated comparisons. No tuning on held-out failures followed by calling the same questions a fresh blind pass. Corrective revalidation is labelled as such and needs a new held-out cohort for generalization claims.

Gate: [proposed release criteria](data-and-evaluation.md), independent reviewer agreement/adjudication, honest partial outcomes and no critical scope/erasure/currentness errors. Customer effort value remains a separately consenting pilot, not a GitHub benchmark result.

## Phase 9 — Windows, recovery and learning handoff

Add future `relaydesk-up/down/status/build/test/validate-live` Make/launcher targets, independent service/data paths and supervised Windows startup. Test explicit bootstrap identity, model artifacts, Codex under service account, rotating logs, backup/erasure-safe restore and protected tunnel. Measure all five products together; no old-laptop readiness from macOS tests alone.

Only after implementation/validation, write `study-guide.md` and one `blog.md` around actual code, data, metrics and failures. Update docs/index/status with evidence, not retroactive success claims. No external publication is automatic.

## Proposed API surface — not available endpoints

| Route family | Purpose |
| --- | --- |
| `/v1/auth/session`, `/v1/me` | Per-user login/logout and scope |
| `/v1/accounts`, `/v1/accounts/{aid}/cases` | Authorized account/case list/create |
| `/v1/cases/{cid}/members`, `/policy` | Owner-scoped grants/egress/revisions |
| `/v1/cases/{cid}/imports`, `/sources/github` | Bounded export import/read-only approved issue capture |
| `/v1/cases/{cid}/conversations`, `/v1/conversations/{id}/sessions` | Persistent conversations and new interactive sessions |
| `/v1/conversations/{id}/messages`, `/v1/jobs/{id}` | Idempotent queued turn and safe job/results view |
| `/v1/cases/{cid}/recall`, `/takeover` | Scoped evidence recall and handover generation |
| `/v1/cases/{cid}/memories`, `/v1/memories/{id}/corrections` | Inspect and revision-bound correction/rejection |
| `/v1/memories/{id}/promotion`, `/suppression` | Explicit account promotion or recall suppression |
| `/v1/cases/{cid}/erasures` | Preview/confirm authorized source/derived-content erasure |
| `/v1/cases/{cid}/changes?cursor=...`, `/readiness` | Scoped sync/reset and memory/index freshness |
| `/v1/sources/{id}`, `/v1/summaries/{id}` | Authorized source/summary revision reads |
| `/v1/handovers/{id}/reviews`, `/exports` | Exact-revision reviewed local artifacts |
| `/v1/jobs/{id}/cancel`, `/continue` | Cooperative cancellation / explicit bounded grant |
| `/health/live`, `/health/ready` | Safe process/storage/worker/index status, no private counts |

API methods/typed payloads are finalized with failing contract tests. All mutations require CSRF plus applicable expected revisions/idempotency; object identity never substitutes for authorization.
