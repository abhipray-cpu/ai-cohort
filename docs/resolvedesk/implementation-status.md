# Implementation status — 14 October 2026

ResolveDesk is an implemented pilot. Scoped actual-document functional validation is complete; production and target-host sign-off remain open. See [current validation](validation-2026-10-14.md) and [earlier evidence](validation-2026-10-13.md).

## Completed

- Final actual-Codex matrix: 11/11 scenarios, 12 chat turns, 16/16 expected-page retrieval checks. All 23 claims and 31 citation references pass structural provenance/version checks. Both empty-index and weak-local-evidence live search recoveries passed. Adapted/provisional inputs, not human gold or reproduced database incidents.
- Real-data defects reproduced with failing regressions and corrected: multi-utility retrieval coverage; privacy-safe `pg_hba` topic preservation; bounded second-query search behavior and canonical `pg_hba.conf` spelling. Earlier failed reports are retained.
- Study guide written after the final functional matrix passed: [study guide](study-guide.md).

- Chat-first correction: persistent conversations, bounded same-thread follow-up resolution, fresh retrieval and citations per turn, idempotent sends, pending-turn guards, latest-turn retry, and secondary knowledge/review views. See [chat architecture and acceptance](chat.md).
- Live two-turn HTTP/Codex chat passed against frozen official sources: 100.7 seconds / three claims, then 64.5 seconds / two claims with version-16 sources. First answer and evidence preserved. Functional evidence only, not an accuracy or latency benchmark.

- FastAPI application, separate durable SQLite worker/store, installed-Codex generation adapter, and React/TypeScript reviewer workbench.
- Strict input/output and retrieved-passage contracts; version-filtered FTS5 retrieval with utility-page preference; immutable source snapshots, section anchors, and pinned index revisions.
- Bounded generation/repair, exact citation membership and applicability checks, separate advisory support assessment, explicit evidence states, clarification and escalation.
- Real official PostgreSQL site search without a key, optional Brave adapter, sanitized queries, pinned-DNS allowlisted fetches, fetched-passage ranking, search evidence checkpoints, and explicit outage handling.
- Human review, immutable approved revisions, edits/escalations as new revisions, stale-environment rejection, internal-evidence export authorization, approved Markdown/JSON and labelled escalation exports.
- Product-specific start/stop/status commands, actual HTTP/worker smoke script, consistent SQLite backup and checked restore into a new directory, rotating-log service runner, Windows startup-task installer, and Cloudflare example.
- Sixteen selected PostgreSQL 16/17 documentation pages checksum-frozen and indexed. Four provisional public/adapted smoke inputs are labelled honestly; no synthetic case is presented as a customer ticket or independent gold.
- 89 Python tests pass across the monorepo (52 ResolveDesk-specific cases plus 37 existing regressions), including nine chat tests and six acceptance regressions. Five frontend presentation tests pass. Ruff and the ResolveDesk production web build pass. Actual loopback chat and UI assets/API/worker/clarification-export checks passed; the final search fixes are loaded in the running service.
- Live empty-index search-fallback smoke completed in 56.3 seconds with two cited claims and separate support assessment. Indexed-corpus smoke completed in 54.6 seconds with one cited claim after a logged version-grounding repair. These are single functional observations, not accuracy or p95 results.

## Remaining release gates and limits

- Human-adjudicated 60-case corpus, measured retrieval/answer/support/abstention quality, actual PostgreSQL error reproductions, and pilot reviewer-effort measurements.
- Browser visual/interaction acceptance: the available browser runtime reports no connected browser. A build and HTTP smoke do not replace this gate.
- Actual Windows task/service-account, Codex auth, reboot, file ACL, restore/cutover, resource-use, and protected Cloudflare acceptance. Packaging scripts are provided but not executed on Windows.
- Brave live integration requires credentials; the default PostgreSQL search path has a successful live smoke.
- Source refresh is bounded and synchronous with per-source atomic publication. Background collection-wide atomic refresh, semantic retrieval, multi-user roles, and automatic helpdesk connectors remain outside this pilot implementation.
- Full successful-call model/CLI identity telemetry and longer-term operational measurements need refinement; current safe events identify prompt/schema and stage outcomes but do not invent unavailable model identity.
- Customer interviews and consented pilot tickets; commercial demand remains a hypothesis.

## Decisions and gates to close first

| Decision / prerequisite | Proposed position | Required evidence |
| --- | --- | --- |
| Domain and source versions | PostgreSQL 16/17, selected support topics | Reviewed source subset and actual-case coverage |
| Retrieval implementation | FTS5 lexical baseline | Availability on Windows and measured Recall@5 |
| Semantic retrieval | Deferred | Recall gain versus host RAM/latency cost |
| Search backend | Official PostgreSQL site search by default; optional Brave | Default live fallback passed; Brave credentials/acceptance remain separate |
| Gold review | Two independent reviewers and adjudication | Named reviewers and frozen labels; single-review labels remain provisional |
| Customer fit | Small support teams/database providers | Interviews and observed manual baseline |
| Host operation | Separate product service and port | Reboot/auth/restore and resource measurements |

## Evidence discipline

Do not mark a feature complete because a diagram or mock exists. Deterministic fake-provider tests prove specified control behavior, not live model quality. Quote membership proves provenance, not semantic support. Search-result fixtures do not prove an operational search integration. A passing build does not establish UI usability. Every release claim needs its corresponding test/run artifact and remaining limits.

The study guide and blog use recorded functional results and explicitly retain release limits. Wider independent quality evaluation remains required. Do not extrapolate smoke tests into commercial readiness or corpus-wide accuracy.
