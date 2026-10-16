# TDD implementation plan

Status: implementation executed under the subsequent user request, 15 October 2026. This original gate plan remains the acceptance checklist, not a claim that every proposed release gate passed. See [current status](implementation-status.md) and [dated evidence](implementation-validation-2026-10-15.md).

Delivered mapping: phases 0–4 are implemented in capture/corpus, inventory/store, registry/policy, adapters/evidence and scheduler modules with test-first checks. Agent/review/publication/UI/operations are implemented as a pilot. Independent gold, browser acceptance, Windows/tunnel and live external-write gates remain open. TDD regression evidence includes observed failing tests for schema/range handling, live registry disablement, alias duplication, receipt verification and repository-import registry bypass, followed by fixes and full regression.

## Technical choices and repository scope

Proposed stack: Python 3.12/FastAPI/Pydantic, React/TypeScript/Vite, separate SQLite WAL store, one worker with bounded concurrent I/O, installed shared Codex adapter, loopback port 8003 and protected Windows/Cloudflare deployment. No local GPU/vector database/Docker or project execution is required.

Future additions: `apps/patchdesk-api/`, `apps/patchdesk-web/`, product contracts/tests, actual-source/evaluation utilities, `data/patchdesk` metadata, backup/restore, product Make/development/service configuration and Windows task installer. Reuse shared provider/observability interfaces additively; do not couple to earlier product databases or orchestration modules. Do not modify `.env`, credentials or public integrations merely while scaffolding.

## Phase 0 — actual-data capture and freeze

Write capture/manifest integrity tests before acquisition tooling. Freeze ten real snapshots from at least five repositories, paired manifests/commit hashes, raw advisory/release/threat payloads, pagination/completeness and natural conflict sources. Implement bounded non-overwriting acquisition and deterministic replay. Check rights/privacy before committing fixtures.

Gate: matching has a real reproducible corpus and independently checked positive/negative/range/conflict seeds. Four successful sample GETs alone do not pass this gate. Record unsupported strata and incomplete acquisitions rather than filling them with fictional favourable data.

## Phase 1 — strict contracts, input graph and scoped store

Write failing tests for v2/v3 formats, scoped names, aliases, nested duplicates, workspaces/links, roles/optional/peer metadata, manifest/lock disagreement, invalid source protocols and oversized inputs. Use real captured patterns plus labelled mutations. Implement deterministic parsing, package/location identities, graph edges/gaps and input hashes without installing/running projects.

Write failing persistence/API tests for actor/project ownership, duplicate enqueue, input/report revisions, leases/counter reservation, stale writes and authenticated artifact/export access. Implement scoped tables and per-user pilot authentication/session/membership, not only one shared credential and a client dropdown. Define secure browser session/CSRF handling before exposing mutations.

Gate: wrong-project data is inaccessible; graph support/unknown cases are explicit; prior product tests still pass. Real artifact identity/counts reconcile to capture, not just parser self-consistency.

## Phase 2 — registry, routing and permission policy

Write failing tests for descriptor/schema validation, duplicate IDs, add/disable/version changes, pinned registry revision, missing credentials, semantic incompatibility, route ranking and unauthorized failover. Implement trusted adapter registration, registry snapshots and capability-based routing with safe explanations.

Write failing tests for client/project/repository scope, private identity/model egress, queued grant revocation, cached result ownership, SSRF/host/path attempts and source prompt injection. Inject actor/credentials/scope server-side. At least two compatible detail adapters must prove real provider selection rather than a renamed fixed switch.

Gate: all requested routing/registry/permission behavior exists in code and is auditable. No fallback may broaden authority, leak private names or replace exact graph evidence with generic metadata.

## Phase 3 — source adapters and evidence

Write failing tests for OSV batch-to-query correspondence, detail retrieval, per-query pagination, alias lineage, withdrawn records, malformed ranges, npm release/engine metadata, fresh/stale caches, 429/timeout/byte caps and partial pages. Implement typed bounded transports and raw/normalized evidence snapshots with exact reference validation.

Implement core OSV/npm and optional reviewed-advisory/EPSS adapters, then optional deps.dev/KEV only after actual access/schema checks. Required coverage failures remain partial; optional missing capabilities are visible. No arbitrary links, npm installs or unrestricted web fallback.

Gate: frozen replay round-trips payload hashes, matching/version fields and coverage. A no-match result is distinguishable from denied/unsupported/unavailable. Independent reference checks reject invented source/row/field/value claims.

## Phase 4 — DAG scheduler and bounded parallelism

Write failing deterministic tests with controllable delayed adapters around real payloads: dependencies before dispatch, cycles rejected, two ready nodes overlap, global/provider concurrency never exceeds limits, task expansion bounded, counters reserved before each attempt, stable reduction under reversed arrival order and duplicate delivery, partial sibling survival, cancellation and lease takeover.

Implement bounded scheduler, durable per-node checkpointing, serialized short DB writes, deadline propagation and safe read retries. Keep model calls serial. Record start/end/route events and provide deterministic partial previews without AI.

Gate: measured overlap plus bound correctness; no shared SQLite connection across concurrent tasks; restart preserves input/registry revisions, deadlines and consumed counters. A `gather()` call alone is not evidence of safe orchestration.

## Phase 5 — conflict reducer, candidates and AI plans

Write failing tests for the actual Axios affected-range discrepancy, alias double counting, separate version branches, severity metric differences, missing CVEs, incompatible engines/peers, newly matched target advisories and unknown constraints. Implement versioned deterministic reconciliation and conservative candidate checks.

Then write failing structured-provider tests for capability allowlists, invented artifact IDs, malformed JSON, bounded repair, unsupported candidate/compatibility claims, context omissions, model timeout and partial survival. Integrate the existing provider behind scoped application orchestration; verify no native CLI tools bypass policy. Generate a concise cited maintenance plan with explicit verification pending.

Gate: requested conflict resolution is observed, not an LLM choosing a winner. Actual Codex traces over frozen records demonstrate capability requests and qualified interpretation; scripted providers prove invariants, not real model quality.

## Phase 6 — review, export and approved issue outbox

Write failing tests for material-edit revalidation/new revision, stale review conflict, partial acknowledgment, exact payload/destination approval, expiration/revocation, outbox idempotency, response-lost unknown outcome and restore replay prevention. Implement review/export first, then scoped publisher with reconciliation.

No live publication until the user explicitly authorizes an owned test repository and connector. Without that authority, complete deterministic policy/outbox tests and keep live-write gate unverified. Do not create an unsolicited upstream issue. External credentials are not approval.

Gate: authorized reviewed exports preserve all machine coverage/conflicts; unapproved/stale/wrong-target writes cannot dispatch. A local idempotency key is never claimed to guarantee exactly-once GitHub creation.

## Phase 7 — premium conversation/reviewer UI

Implement [UI](reviewer-ui.md) with scoped project switching/import, conversation, capability/parallel activity, graph/evidence/conflicts, candidates, maintenance batches, review/export and separately explicit publication approval. Persist reload/history and meaningful partial states.

Verify actual browser journeys, keyboard/focus/contrast, input errors, long/large real data, three viewports, denied permissions, unknown publication outcome and stale approval changes. Capture screenshots and record results. Do not count asset/build checks as browser or premium visual acceptance.

Gate: real project → observable multi-tool work → reviewed maintenance pack is usable without hiding uncertainty. If browser tools are unavailable, mark acceptance unverified.

## Phase 8 — actual-data/model quality and customer comparison

Freeze independent labels/splits, run baselines and actual-model development/held-out evaluations from [evaluation](data-and-evaluation.md). Preserve all failures/partial outcomes; publish source caps and strata, raw metric denominators and critical errors. Measure parallel correctness separately from speedup and narrative completion separately from evidence retention.

Perform a live-source read-only end-to-end run, then independently authorized issue publication if available. Record every requested Day 4 concept in actual traces or explicitly mark missing evidence. Customer effort/willingness-to-pay testing is a separate authorized activity, not invented validation.

Gate: provisional thresholds pass with evidence, or release scope/readiness remains explicitly restricted. A successful sparse run is not proof of dense-project reliability.

## Phase 9 — Windows operations, learning and handoff

Implement per-product up/down/status/test/validate targets, Windows-compatible launcher/startup tasks, rotating logs, consistent backups and restore quarantine. Test service identity/secrets, Codex, reboot/sign-out, process cleanup, resource/queue limits, tunnel access and restore on the actual old laptop.

Only after implementation and validation, write `study-guide.md` tracing the five concepts through actual contracts/code/UI/tests and a single `blog.md` explaining actual data, failures/fixes and measured limits. Do not create pretend-completed learning content now. Update index/status/runbook/dates with real commands and open gates.

## Proposed API surface

Routes below and `GET /v1/clients` are implemented. Clients are derived from authorized projects, not separate tenancy records. Server-owned scope applies to every object. Mutations use expected revisions/idempotency where applicable and require CSRF. Additional project policy/membership/admin actor/registry endpoints support the workbench.

| Route | Purpose |
| --- | --- |
| `POST /v1/session`, `DELETE /v1/session`, `GET /v1/me` | Per-user pilot login/logout and scoped identity |
| `GET /v1/projects`, `POST /v1/projects` | Authorized project list/create; client is a project field |
| `POST /v1/projects/{id}/inputs` | Upload bounded paired manifests/lockfile with provenance |
| `POST /v1/projects/{id}/repository-snapshots` | Read approved configured paths/ref and pin commit |
| `GET /v1/projects/{id}/capabilities` | Registry/roles/egress and publisher availability, not complete live provider health |
| `POST /v1/projects/{id}/runs`, `/messages`, `/refresh` | Idempotent scoped investigation, follow-up, explicit refresh |
| `GET /v1/runs/{id}` | Safe run/node/route/events/counters/preview view |
| `POST /v1/runs/{id}/cancel`, `/resume` | Cooperative cancellation / explicit bounded grant |
| `GET /v1/snapshots/{id}`, `/v1/reports/{id}` | Authorized evidence/report revisions |
| `POST /v1/reports/{id}/reviews`, `/exports` | Revision-bound review/immutable export |
| `POST /v1/reports/{id}/publication-drafts` | Exact target/title/body draft, no external effect |
| `POST /v1/publications/{id}/approve`, `/dispatch`, `/reconcile` | Explicit approval, separately authorized dispatch/recovery |
| `GET /v1/publications/{id}` | Receipt/denial/unknown outcome without secrets |
| `GET /health/live`, `/health/ready` | Process/storage/worker health, not implied provider availability |

Transport is polling. Implemented Make targets: `patchdesk-build`, `patchdesk-up`, `patchdesk-down`, `patchdesk-status`, `patchdesk-test`, `patchdesk-validate-live`. See [runbook](operations.md).

Definition of done: scoped actual input → dynamic eligible registry/routing → correct bounded parallel work → evidence/conflict resolution → useful reviewed plan/export, with approval-safe publication where explicitly configured/tested, measured quality and target-host/browser acceptance. Unmet gates remain visible rather than being redefined as passes.
