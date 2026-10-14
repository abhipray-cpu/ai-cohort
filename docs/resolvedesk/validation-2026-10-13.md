# Implementation validation — 13 October 2026

## Chat-first correction and live acceptance

Initial workbench delivery was single-ticket RAG, not the requested conversational interface. The default screen now opens persistent RAG chat. Nine additional deterministic tests cover follow-up scope, persistence, thread isolation, general queries without mandatory environment, idempotency/pending guards, failure/retry, stale-turn retry rejection, fetched search evidence and insufficient-evidence warnings. Full suite: **83 passed**.

Real HTTP acceptance via `scripts/smoke_resolvedesk_chat.py` passed against the running service, installed Codex and frozen official documents. Turn one asked about pg_dump 16 / PostgreSQL 17 compatibility: `draft`, three cited claims, 100.7 seconds. Turn two asked whether the same rule applies to PostgreSQL 16: `draft`, two cited claims, 64.5 seconds; all follow-up citations used version-16 evidence. Exact quote membership, duplicate-send idempotency, context events, reloaded transcript and preservation of the first answer were checked. Report: `var/resolvedesk-evaluation/reports/20261013T175637-chat.json`; conversation `dc6f0cd4-dd66-4589-8cb4-bec520518d13` remains in the local UI.

This is functional smoke, not human-adjudicated quality. Model response latency is substantial. Browser runtime was retried and reports no available browsers, so no visual/interaction pass is claimed. Windows and production gates remain open. See [chat design](chat.md). The observations below describe the earlier shared RAG pipeline checks.

This records implementation evidence on macOS, not a release or accuracy certification. User-requested wider real PostgreSQL validation is the next phase. No Windows acceptance or independent human gold set has been completed.

## Automated and running-system checks

Before the chat correction, the Python suite passed **74 tests**: 37 ResolveDesk-specific cases and 37 pre-existing regressions. Current total is 83 as recorded above. Ruff and the ResolveDesk TypeScript/Vite production build pass. ResolveDesk's actual API and worker start and stop through their independent Make targets. Readiness returns 200; unauthenticated case access returns 401; cross-origin mutations are rejected. The HTTP smoke fetched both built UI assets, created a case, waited for the actual worker's clarification result, and exported a labelled escalation packet. It did not invoke a fake generation provider in the running app. This shared-workflow smoke passed again after the chat correction.

Tests cover strict contracts, unsafe query punctuation, version/visibility filtering, pinned source revisions, retrieval-tool identity, invented citations, repair budgets, semantic support flags, environment clarification, search failure, fetching evidence rather than snippets, late-page relevance, query privacy, redirect/DNS checks, failed-candidate approval locks, stale environments, idempotency, internal export authorization, immutable approvals, worker recovery, and backup/restore.

## Actual source corpus

Sixteen official HTML pages are frozen in [sources.json](../../data/resolvedesk/manifests/sources.json): eight topics each for PostgreSQL 16 and 17 (`pg_dump`, `pg_restore`, `pg_dumpall`, `pg_upgrade`, connection parameters, authentication overview, backup overview, and upgrading). Raw HTML is ignored; original notices remain in it. Normalized application snapshots live in SQLite. This initial selection is not every linked subchapter of the manuals.

The real-source regression found the critical `pg_dump` compatibility rule initially ranked eighth and therefore omitted from the 16,000-character context budget. A utility-page preference brought it into the bounded context. A second regression ensures a relevant rule late in a fetched search page is ranked rather than discarded by front-of-page truncation. Source section headings/anchors and exact normalized text spans are retained.

## Live Codex smoke observations

| Run | Input and path | Result | Duration | Calls | Findings |
| --- | --- | --- | ---: | ---: | --- |
| Empty-index fallback | Adapted PostgreSQL 17 server / 16 pg_dump mismatch; local index revision 0 | Draft, supported evidence assessment, 2 cited claims | 56.3 s | 2 | Remote version-scoped site search returned official pages; five pages were fetched; passages were ranked; answer and advisory support pass succeeded. Search results were not auto-promoted to the index. |
| Indexed corpus | Same adapted question against frozen 16/17 sources | Draft, supported evidence assessment, 1 cited claim | 54.6 s | 3 | First output failed claim-version/citation applicability; failure event was persisted, repair succeeded, then support assessment succeeded. |

Both drafts cited the actual manual rule that `pg_dump` cannot dump a server newer than its own major version. The fallback draft also recommended matching the client major version to the server. This is a focused implementation sanity check on an adapted question, not a reproduced database incident or an independent human quality score. The separate support pass uses the same model provider and remains advisory.

Machine-local reports:

- `var/resolvedesk-evaluation/reports/20261013T171326501651-backup-mismatch-17.json` — empty-index fallback; source store in `var/resolvedesk-fallback-smoke`.
- `var/resolvedesk-evaluation/reports/20261013T171950329770-backup-mismatch-17.json` — indexed corpus; source store in `var/resolvedesk-local-smoke`.

Reports and SQLite evidence are ignored. Source manifests and this aggregate record are versioned. Each report carries run/index IDs, safe stage events, citations, and the provisional label warning.

## Search backend decision

The originally proposed Brave integration is implemented but has no configured key on this machine. Read-only checks verified PostgreSQL's actual public search form uses `/search/?q=...&u=/docs/17/`. A dedicated adapter now uses that remote version-scoped search by default, avoiding a credential prerequisite for the supported domain. It parses result links, discards wrong versions/unapproved URLs, and fetches actual pages before generation. HTML changes or service outages remain possible and produce explicit failure/uncertainty states.

## Open acceptance

The browser runtime returned no available browsers, so no screenshots, keyboard/click-through acceptance, or premium-UI visual sign-off is claimed. Windows/Cloudflare scripts are unexecuted on the actual host. The 60-case independently reviewed dataset, lab incident reproductions, precision/recall, abstention quality, reviewer effort, p95 latency, and hardware profile remain to be measured. Optional semantic retrieval and queued collection-wide atomic refresh are later extensions.

## Reproduce

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
npm --prefix apps/resolvedesk-web run build
.venv/bin/python scripts/fetch_resolvedesk_sources.py --data-dir var/resolvedesk-evaluation
.venv/bin/python scripts/benchmark_resolvedesk.py --live
make resolvedesk-up
.venv/bin/python scripts/smoke_resolvedesk_http.py
```

Live commands require authenticated Codex and network access. For the empty-index path choose a fresh isolated data directory with `--data-dir`; do not run another worker against the same evaluation store. Search needs no key with the default adapter. Never interpret one successful smoke as the proposed quality gates passing.
