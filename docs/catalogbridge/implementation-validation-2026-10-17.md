# Implementation evidence — 17 October 2026

Verdict: **implemented supervised pilot; full design/release acceptance incomplete**. The 15-document planning pack and its local links were checked before implementation. No real-world quality or savings claim follows from this engineering milestone.

## Observed TDD progression

| Stage | Red observed before implementation/fix | Green behavior |
| --- | --- | --- |
| Contracts/intake/ledger | Missing contracts module at collection | Strict source data and atomic scoped reservations |
| Worker/provider | Missing boundary at collection | Requested-model routing, evidence validation, fenced checkpoints |
| API/workflow | Missing API at collection | Sessions, CSRF, object scope, review/export |
| Hardening | Second dispatch admitted while in flight; corrupted source exported | Admission fence and integrity check |
| Recovery/evaluation | Missing corpus/backup modules | Safe normalization/scoring and quarantined restore |
| Accounting | Missing journal looked healthy; quarantine could dispatch; model rates missing | Conservative liabilities and per-model scenarios |
| Delivery | Replay duplicated batches; literal whitespace lost; lookup missing | Idempotency, literal preservation and manual master lookup |
| Actual telemetry | Current CLI fields caused unknown usage; reasoning subset unsupported | Supported usage without double counting; unknown categories fail closed |
| Worker safety | Expired lease could dispatch; queue unbounded | Pre-dispatch lease fence and queue cap |
| Pricing | Mixed reference/credit bases aggregated | Incompatible scenarios remain unknown |
| Frontend | Missing helpers for unknown usage, stale forms, continuation and cost | Explicit state gates and units |

Final full monorepo check: **404 Python tests pass**, including **58 CatalogBridge tests**, no skips/failures. Seven frontend domain tests pass; TypeScript/Vite production build and Ruff pass. Existing dependency deprecation warnings remain. These are engineering checks, not independent matching labels or visual QA.

## Actual process/provider evidence

Local gitignored artifacts under `var/validation/`:

| Artifact | Observed outcome | Boundary |
| --- | --- | --- |
| `catalogbridge-http-smoke-v1.json` | Nine actual API/separate-worker checks pass: auth denial, imports, checkpoint, explicit/stale review, reviewed export, accounting, audit and UI HTTP serving | Artificial inputs; no browser/model call |
| `catalogbridge-provider-smoke-v1.json` | Initial sandboxed calls fail before useful response | Preserved failure, not a routing pass |
| `catalogbridge-provider-smoke-v2.json` | Requested models return audited answers; initial parser misses actual usage schema | Unknown was not zero; prompted corrective tests |
| `catalogbridge-provider-smoke-v3.json` | `gpt-6-luna` requested: 8,300 input/115 output; `gpt-6.1-sol` requested: 8,988 input/86 output; both audited, exit 0 | First output includes 17 reasoning tokens; effective identities absent |
| `catalogbridge-http-live-smoke-v2.json` | Nine actual HTTP/worker checks pass, including one real installed call settling **8,414 measured tokens**, then fixture human review/export | Artificial pair; no calibrated auto-acceptance |

Sandbox startup failed with an OS permission error. A scoped approved retry allowed the CLI client to initialize, still with read-only/restricted model execution and tool auditing. No unsafe Codex sandbox-bypass flag was used. Observed JSON events omit effective-model identity; requested names are not relabeled independently verified identities. Actual billing/savings were not inferred from access.

Smoke processes used temporary product data and random test-only credentials, then shut down. No `.env`, real credentials or previous product processes changed. Static UI HTTP serving is not a browser journey. Browser setup and documented discovery found no available connection, so no visual screenshots/acceptance are claimed.

## Remaining gates and design gaps

No WDC archive acquisition/rights verification, full live cohort, paired baseline, retrieval campaign, independent challenge or customer-time study occurred. No qualified real calibration is installed; effective identity is unverified, so automatic acceptance stays blocked. Hard token mode is unavailable/refused. Browser, old Windows host, protected edge and seven-product resources are unaccepted.

Broader field mapping, scalable persisted indexing, original byte-artifact provenance, settings UI, comprehensive erasure/current-authority restore and external audit anchoring remain beyond this pilot. The acceptance command deliberately returns nonzero. [Actual runbook](implementation-and-operations.md) lists delivered commands and deviations; [evaluation](data-and-evaluation.md) defines the next real-data stage. Study guide and single blog follow that stage.
