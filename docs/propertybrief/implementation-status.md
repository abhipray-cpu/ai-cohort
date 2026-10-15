# Implementation status — 15 October 2026

Stage: implemented, locally runnable pilot with real-data functional validation. **Not production-ready.** Independent semantic quality, browser acceptance and target Windows/Cloudflare acceptance remain open. See [measured validation](validation-2026-10-15.md); failed runs are retained, not relabelled passes.

## Delivered

- Separate FastAPI application, authenticated same-origin static web host, React/TypeScript reviewer workbench and product-specific SQLite WAL store.
- Official property resolution with explicit candidate confirmation, building/parcel scope, immutable identity evidence, case conversation and pinned follow-up evidence.
- Eight HPD/DOB investigation adapters with bounded queries/paging/HTTP, metadata/hashes, status mapping, conflict flags and completeness.
- Application-controlled Observe → Think → Act → Reflect loop; typed source/inspection/comparison actions; dynamic tool/row/field schemas; exact citation validation.
- Persisted counters, finalization allowance, repeated-action stop, deadline, cancellation, single-worker leases/fencing, idempotent starts and bounded resume grants.
- Separate advisory self-critique, one conservative revision, durable deterministic previews and partial reports after provider/source/parse failures.
- Review/edit with citation revalidation, immutable edited report IDs, qualified partial acknowledgment, reviewed Markdown/JSON exports and printable UI.
- Isolated shared Codex adapter with restricted runtime configuration, native-tool event auditing and tracked subprocess timeout cleanup; old product defaults remain compatible.
- Product Make targets, development launcher, rotating service runner, Windows startup packaging, example tunnel route and verified SQLite backup/restore helpers.
- Real acquisition/frozen replay/live model/recovery/HTTP validation scripts; corpus snapshots and unsuccessful evaluation sessions retained under ignored storage.

## Measured versus open

| Area | Evidence / gate |
| --- | --- |
| Tests | Full repository Python suite, 59 PropertyBrief tests, shared adapter tests, four frontend presentation tests; see final counts in validation |
| Build | TypeScript and production Vite build pass; authenticated HTML/assets served |
| Actual data | 12 buildings, all five boroughs, 3,346 records; 96 source checks, 91 complete-for-query and five unknown |
| Real model | Recorded adaptive source choices, inspections, reflections, citation checks, critique objections and timeout fallback; not a held-out accuracy benchmark |
| HTTP journey | Actual address/BIN resolution, eight source attempts, durable report, reviewed gap-preserving export and persistent follow-up |
| Backup | Live product-store backup/restore verified into a separate directory; counts match for cases/runs/snapshots/reports/exports |
| UI browser | Unverified: browser runtime listed no available browser; no screenshots or interaction pass claimed |
| Quality | No independently adjudicated 60-case cohort, finding recall/precision or expert critique calibration |
| Target host | Windows service auth, reboot/sign-out, descendant cleanup, resource/queue measurements and protected tunnel still untested |
| Commercial value | No buyer trial, pricing result or paired analyst-effort measurement |

## Explicit implementation decisions / deferred scope

Snapshots, raw/normalized records, reports and export payloads all live in SQLite, not a separate content-addressed filesystem. PropertyBrief events use its own store, not a changed shared observability schema. Product code does not import earlier products' orchestrators.

The resolver supports exact official address forms/BIN/BBL, not comprehensive aliases/geocoding. Registrations are in the source registry but not automatically queried. Follow-ups reuse pinned evidence until explicit refresh; there is no TTL refresh or automatic semantic snapshot diff. Plans provide proposed professional tasks and review notes, not external messaging or a full task-assignment/completion product.

No ACRIS/title, permits, zoning, physical inspection, valuation, repair estimates, offline model inference or multi-tenant SaaS identity is included. No automatic retention deletion is enabled. Current prose guards are conservative pattern checks, not a general entailment engine.

## Handoff

Local URL: http://127.0.0.1:8002/. Use `make propertybrief-up`, `make propertybrief-status`, `make propertybrief-down`; Windows alternatives and credentials behavior are in [operations](operations.md).

Learning material follows the completed functional validation stage: [study guide](study-guide.md), [single blog draft](blog.md). These explain actual code and failed/partial behavior, not hypothetical production-quality results.
