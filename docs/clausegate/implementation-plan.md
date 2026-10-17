# Dependency-ordered test-driven implementation plan

Status: **implementation explicitly authorized and pilot delivered**. This preserves the original dependency order; [actual mapping/deviations](implementation-and-operations.md) and [measured results](implementation-validation-2026-10-17.md) distinguish engineering delivery from release gates. Indicative interfaces are not all separate implemented modules. Every phase requires failing tests → minimal implementation → refactor → regression; adding tests after all behavior is written is not the intended cadence. Keep real semantic labels, policy fixtures and human usefulness evidence separate.

## Stack and proposed footprint

Python 3.12/FastAPI/Pydantic; React/TypeScript/Vite; independent SQLite/local artifact storage; API and one worker; shared installed isolated Codex adapter. No new direct LLM API, vector service, GPU or Docker requirement. Proposed port 8005 is a target, not an available running endpoint.

When implementation is explicitly authorized, add `apps/clausegate-api/src/clausegate_api/`, `apps/clausegate-web/`, `packages/contracts/src/contracts/clausegate.py`, product tests and capture/evaluation utilities. Add launcher/service/Make/config support only then. Do not import previous products' stores/controllers, touch their credentials or restart their processes. Run the full monorepo regression at integration boundaries.

## Phase 0 — verified real inputs and semantic oracle

First failing tests: archive path traversal, oversize/partial download, wrong hashes, schema/class mismatch, empty/missing annotations, Unicode span mapping, repeated IDs/body duplicates, source edit mismatch and split/gold leakage. Acquire/freeze authorized official ContractNLI artifacts; observe actual counts, notices, text/spans and source types. Keep labels evaluator-only. Do not build model prompts using answers.

Gate: reproducible raw/normalized manifest and full-primary deterministic checks; documented rights and negative/partial cases. A reachable dataset page or generated NDA is not a pass. CUAD remains optional secondary material with separate denominators.

## Phase 1 — strict domain, scoped identity and atomic store

Failing tests: untrusted actor/role IDs, cross-workspace lists/details, CSRF/origin, session expiry, idempotency same/different payloads, optimistic conflict, immutable source/policy/context revision, rollback/foreign keys and event append failure. Implement minimal schema/auth/scope/storage and revision-bound typed imports.

Gate: no cross-case evidence or metadata disclosure, no duplicate effective writes, decision cannot commit without its event. Test source hash corruption before evidence use. Roles are actual per-user grants, not a shared demo password representing both people.

## Phase 2 — intake, playbook and deterministic uncertainty

Failing tests: native PDF/text integrity and coverage; unsupported scans/encryption/oversize; absent clause versus incomplete document; company-side unknown; draft/unmapped playbook; mandatory exception versus model uncertainty; hard-block waiver attempts; typed predicate validation and required roles.

Implement bounded extraction, immutable approved rules and deterministic reducer using fixture findings first. Exact source evidence, coverage and policy version are prerequisites. No speculative legal positions or arbitrary executable rule expressions.

Gate: given frozen findings/context, the same playbook yields the same blocker/request requirements; unknown/incomplete cannot become compliant. Required checks retain their denominator even when analysis is partial.

## Phase 3 — durable pause and targeted input

Failing tests: pause/request/event atomicity, restart while waiting, no held model process/calls, duplicate worker delivery, missing reviewer, wrong question/response kinds, required rationale, self-approval, quorum/distinct actors, expiry and delegation/reassignment revocation.

Implement durable checkpoints and scoped inbox with in-app notices, explicit assignment, immutable typed decisions, expected request revision and binding. Clarification, interpretation confirmation/correction and exception approval are distinct. A rejection or request for revision cannot accidentally clear a blocker.

Gate: two separate actor sessions can complete authorized interaction; every pending rule remains visible. Waiting consumes no active lease or inference budget.

## Phase 4 — resume and race safety

Failing tests first: changed document/same filename; changed policy/business fact/finding; stale form; expired approval; withdrawn/revoked/delegated actor; cancel/erase while running; changed restore epoch; two final decisions race; source changes after preflight but before packet commit; replayed continuation intent and old lease.

Implement binding canonicalization, live authority checks, deterministic post-decision reevaluation, atomic continuation/outbox and final publication fences. No force-resume path. Human waiting does not reset cumulative usage; active grants have separate immutable deadlines. Persist earlier decisions/stages through provider failure.

Gate: stale/unauthorized contexts cannot finalize under any tested ordering. Each idempotent continuation has one effective committed effect, not an unproven exactly-once subprocess promise.

## Phase 5 — audited source-grounded model analysis

Failing tests: strict JSON/proposition enums; foreign span IDs; quote/hash mismatch; distributed exception evidence; absent hypothesis predictions; unassessed text called absent; prompt injection; no audited provider output; nonzero exit; timeout; bounded parse repair; egress revoked mid-run; private labels/credentials in prompt; later failure losing earlier checkpoint.

Integrate shared installed Codex through an application boundary after adapter isolation tests. Model output proposes interpretation/questions but cannot route authority, approve, change policy or execute tools. Validate evidence separately; semantic correctness needs the gold/qualified evaluation. Keep manual review fallback and safe stage failure history. Minimize/budget the full serialized prompt including schemas/metadata.

Gate: actual installed-provider calls on preselected real documents; correct denominator for complete/partial/failed. Mocked providers establish boundary behavior, not natural model quality.

## Phase 6 — packet, audit and recovery

Failing tests: packet review binding/export staleness; missing event; event tamper/reorder/truncation versus external head; disk-full rollback; immutable source corruption; wrong existing/missing ledger; source erasure dependency closure; restart after decision/outbox; older restore reviving revoked memberships/withdrawn approvals.

Implement complete event taxonomy and chain verifier, explicit external anchor assurance, scoped exports, current-ledger binding and quarantined new-directory restore. Restored decisions/final reviews are unusable; sessions/leases expire; operator must reprovision current authority. Finalize approved retention/redaction protocol with tests so content erasure cannot silently falsify the original audit chain.

Gate: real kill/restart and restore drills, not only mocked exceptions. Preserve original failed artifacts. No secure-wipe, immutable-host-audit or legal-compliance claims.

## Phase 7 — premium UI and joint workflow

Start with frontend state tests for waiting versus loading, no preselected approval, source context, allowed response types, conflict/expiry, binder changes, export invalidation and epoch resets. Build intake/inbox/reader/decision/audit/final review workbench from [UI spec](reviewer-ui.md).

Run authenticated HTTP journeys, then actual browser journeys at prescribed viewports with separate identities. We jointly operate requester and reviewer on real public contracts; record human corrections and usability issues honestly. Source labels and qualified legal review remain separate oracles. If no browser is connected, browser gate is blocked rather than replaced by build/HTTP checks.

Gate: version change invalidation and resume are visible and understandable; keyboard/responsive/accessibility acceptance and screenshots actually executed.

## Phase 8 — rigorous evaluation and held-out freeze

Freeze product/model/prompt/policy/data/split hashes before evaluation. Complete full-primary deterministic checks, official held-out semantic metrics, independent challenge review, ≥60 real-document fixture workflows, ≥30 distinct live-provider workflows and original-artifact intake sample. Compare baselines and uncertainty ablations; do not count overlapping/replicated examples as fresh evidence.

Report class/evidence quality, incomplete coverage, risk–coverage, false clearances, reviewer workload and every provider failure. Thresholds and required original-document/legal-review gates are in [data and evaluation](data-and-evaluation.md). Corrective retesting is new labelled evidence, not a reset of the blind test.

Gate: every mandatory criterion passes or release remains failed/blocked with a precise reason. Dataset success is not customer value or jurisdiction advice.

## Phase 9 — target host and learning handoff

Only now add/verify proposed `clausegate-build/up/down/status/test/validate/acceptance` integration, Windows limited-identity tasks and protected Cloudflare application route. Test Codex under the service account, reboots/logoff, local storage/ACL/disk limits, process cleanup, independent erasure authority, backup/restore and all six products together.

Run authorized consenting-customer usefulness work when people/data are available. No unauthorized outreach or external publication. After implementation/validation, create `study-guide.md` mapping all five concepts to code/tests/results and one `blog.md` grounded in actual observations, including failed/blocked gates. Update all docs from targets to evidence without rewriting history as success.

## Proposed integration tests by concept

| Concept | Mandatory end-to-end observation |
| --- | --- |
| Uncertainty | Real clause interpretation/evidence gap routes with an explicit reason; certainty does not bypass mandatory review |
| Pause | Commit waiting checkpoint, stop worker, restart, observe identical requests and no additional calls |
| Human input | Separate authorized person sees sources, submits typed scoped response; unauthorized/self-approval rejected |
| Validated resume | Valid response continues once; document/policy/authority/expiry change prevents old response from continuing |
| Audit | Reconstruct complete input-to-export lineage; injected tamper/rollback detected relative to trusted head; no eventless decision |
