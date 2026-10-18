# Implemented pilot and operator runbook

Updated 18 October 2026. This describes delivered behavior; original specifications retain broader targets. Read [current hardening evidence](runtime-hardening-2026-10-18.md) and the historical [engineering evidence](implementation-validation-2026-10-17.md) before interpreting release claims. This is a supervised pilot, not full design/production acceptance.

Historical [real-data diagnostics](real-data-validation-2026-10-17.md) acquired official sources and exercised 1,000 natural queries/200 actual calls; that diagnostic changed no runtime behavior. Later repairs and the current hardening report document implementation changes. References below to pending data work mean the **full** acceptance campaign, not absence of any real-data test.

## Delivered footprint

**Local-routing amendment:** [implementation and evidence](local-routing-validation-2026-10-18.md). Optional `CATALOGBRIDGE_ROUTER_PROFILE` points to a trusted, bounded JSON tree profile. Authenticated `GET /api/routing-profile` returns availability/hash/band summaries, never paths or weights. Batch setup opts into `routing_policy="local_review_v1"` with the returned `local_router_sha256`; default remains `llm_only`. Hash drift/invalid configuration is audited and falls back only through the ordinary budgeted route. Local exits stay uncalibrated `needs_review` drafts with no model attempt; they do not bypass egress/holds. Profile numeric statistics are not authenticated independent calibration. The real positive band is disabled. Latest live comparison stopped on quota; three new unknown liabilities remain held. Do not automatically retry or clear them.

**Latest amendment:** [timeout receipts and exact-context reuse](receipts-and-repeat-work-2026-10-18.md). Sanitized correlation receipts persist with settlement; completed usage received before timeout survives, while ambiguous streams remain unknown. `reuse_validated_drafts=false` by default. The setup checkbox/API option enables 24-hour workspace-scoped reuse of unchanged, unreviewed, revalidated binary drafts. Changes, expiry, uncertainty and human review invalidate reuse. Hits retain provenance, make no new attempt, remain `needs_review` and do not clear runtime holds or qualify confidence exits. No cache-clear HTTP endpoint or fuzzy reuse is provided. See the linked report for tests, commands and remaining gates.

**Current safety amendment:** [runtime hardening and measured limits](runtime-hardening-2026-10-18.md). Workspace holds now fence other batches and appear in the UI; evaluation failures stop all modes. Safe diagnostics retain hashes/categories, not raw logs. Authenticated `GET /api/runtime` exposes scoped state. Owner-only `POST /api/runtime/acknowledge` requires an investigation reason and refuses unknown/in-flight usage, journal divergence and restore quarantine; it never refunds usage, asserts health or dispatches work. Existing 61 historical unknown attempts remain held.

`BatchSpec.instruction_profile` defaults to `legacy`. `compact_classifier_v1` is explicitly selected and experimental, with a fixed packaged instruction asset included in preflight and calibration binding. No tool permissions are expanded. There is no completed UI profile selector. API calibration uploads remain operator attestations and cannot request `empirically_verified`; such attestations no longer authorize confidence exits even if model identity becomes available. No real qualified calibration exists.

Historical incident: [18 October fresh-data run](fresh-real-data-validation-2026-10-18.md). Preserve all 61 original unknown liabilities; a successful separate replay does not reconcile them. That run exposed missing cross-batch/campaign fencing. The current workspace circuit and shared evaluation guard now stop further inference, with safe failure evidence. No automatic refund or retry is authorized by a successful probe.

| Area | Actual files |
| --- | --- |
| Strict products/proposals/usage/rates/reviews | `packages/contracts/src/contracts/catalogbridge.py` |
| HTTP, scoped sessions and users | `apps/catalogbridge-api/src/catalogbridge_api/api.py`, `auth.py` |
| Intake, candidates and evidence | `ingest.py`, `matching.py` in the same package |
| Tasks, ledger, review and exports | `store.py` |
| Installed-model port and controller | `model_boundary.py`, `worker.py` |
| Dataset normalization/scoring and recovery | `corpus.py`, `backup.py` |
| React workbench and tested state helpers | `apps/catalogbridge-web/src/main.tsx`, `domain.ts`, `style.css` |

Independent SQLite state, separate current usage-liability journal, API/static UI and one worker. The provider subclasses shared installed-Codex primitives; earlier products' controllers/data/provider defaults are unchanged.

CSV/JSON imports require `id,title`; optional `brand,description,model,gtin,price,currency`. Unknown/gold fields, duplicate IDs and blank titles are rejected. Literal whitespace is preserved. Import creates a frozen canonical-record revision immediately; arbitrary field mapping, separate server-side draft/freeze and original-file byte retention are not implemented. Preserve original files separately where required. Retrieval is bounded lexical matching, not a persisted/tuned large-catalog index. Attribute conflicts and literal evidence checks constrain proposals; they do not prove identity.

## Start and stop

From repository root:

```bash
.venv/bin/python -m pip install -e '.[dev]'
npm --prefix apps/catalogbridge-web ci
make catalogbridge-up
make catalogbridge-status
make catalogbridge-down
make catalogbridge-test
```

Before `up`, set explicit `CATALOGBRIDGE_USERNAME` and a password of at least 12 characters in uncommitted `.env` or the service environment. No cross-product credential fallback; existing passwords are never reset. No real `.env` or credential was changed during delivery. See `.env.example` for recognized settings. The launcher loads `.env`; direct API/worker invocations require environment variables already loaded.

Open `http://127.0.0.1:8006/`. Product data defaults to `var/catalogbridge`; the current liability journal is `var/catalogbridge-usage`. Logs/PIDs are in `var/catalogbridge-dev`. Only temporary smoke processes were started, and they were stopped; no service is left running publicly.

On Windows, create/install using `py -3.12 -m venv .venv` and `./.venv/Scripts/python.exe -m pip install -e ".[dev]"`. Build with `npm --prefix apps/catalogbridge-web run build`; run `./.venv/Scripts/python.exe scripts/dev_stack.py --product catalogbridge up` (or `down`/`status`) without Make. `infra/windows/install-catalogbridge.ps1` provides limited-account startup tasks but is not target-host tested/installed. `CATALOGBRIDGE_SECURE_COOKIES=true` is required for protected HTTPS. Cloudflare ingress example is additive; Access policy and external denial still need verification. No tunnel/DNS/account changes occurred.

## Actual routing and confidence

Owner creates a batch binding two requested models, source revisions, allowance and explicit model egress. Operators start/cancel; reviewers review; auditors cannot mutate. Owner-only `POST /api/users` provisions separate workspace identities. Grants are workspace-wide, not the richer per-case design. Model/rate/calibration administration remains API-based rather than a complete settings UI.

Without egress, rows remain manually reviewable and consume no model calls. Policy v2 uses economy for up to three candidates (unless brand is missing with multiple candidates), otherwise direct strong. Economy escalates once after invalid output or `insufficient_evidence`, even when effective identity is unknown. A decisive source-validated proposal stops as a **review draft**, not a confidence-qualified match: missing calibration alone is not a reason to buy another opinion. Each invocation reserves 12,000 advisory tokens against row and batch accounts; at most three cumulative slots, bounded deadlines and a 20-active-batch queue apply. Invalid proposals create validation-history events. Retries/continuation retain counters; unknown or in-flight usage prevents further dispatch. Cancellation fences publication but retains incurred tokens.

The installed adapter checks the complete serialized prompt/schema envelope before any reservation; oversize refusal records `preflight_refused` with no attempt or unknown liability. Exceptions after dispatch remain conservatively unknown. Valid proposals are retained in `proposal_history` with attempt, route and requested/observed identity. Later budget/provider failures retain the earlier draft in `needs_review`, mark `degraded` and append `partial_proposal_retained`; they do not erase incurred usage or approve the draft. A failure before any valid proposal remains failed.

Retrieval v2 normalizes Unicode and punctuation and indexes compact hyphen/dot/slash identifiers alongside components. A sole master record remains assessable even with zero lexical overlap; this is candidate retrieval, not an accepted match. Title capacity/form-factor/pack constraints take precedence over marketing descriptions; descriptions are a fallback when the title has no such attribute. Generic description words “new”/“used” no longer establish condition; title condition remains checked. Brand normalization ignores punctuation/case, not semantic aliases. Contradictory source descriptions still require model/reviewer scrutiny: this heuristic is not exhaustive structured SKU extraction. Literal evidence validation remains strict, with no automatic quote rewriting.

**Advisory token mode only:** the CLI does not expose verified hard-token enforcement; strict mode refuses dispatch. A single call may exceed its estimate. Both requested model names returned audited fixture responses. Observed JSON events provide actual input/cache/output and reasoning-subset tokens, but no effective model identity. Unsupported positive cache-write/unknown usage categories remain unknown rather than free.

Calibrated exit logic is implemented and fixture-tested, but no qualified real-data profile exists. Owner-uploaded calibration is attested, not independently verified. Bindings include model names, policy/prompt/retrieval and relevant code hashes. Initial acceptance supports only unique-candidate same-product proposals. Unverified effective identity prevents automatic acceptance even with a profile. No fabricated calibration or aliased model tier is installed.

## Review, exports and cost

Review requires rationale and expected revision. Polling cannot replace the revision of an open form; changed context requires refresh. Reviewers can inspect an exact master ID missed by retrieval. Default formula-neutralized CSV includes current explicitly reviewed links only. The same response includes hashes, task revisions and unresolved coverage; the UI offers the matching same-snapshot coverage file. No catalog/price/inventory writes occur.

Usage settlement is idempotent. Unknown spending holds reservations; missing/divergent current journal blocks dispatch; overruns are not clipped. Monetary totals are fixed-point microunits, with per-row microunits rounded upward. Per-model rates are explicit reference/credit scenarios, never inferred subscription invoices. Incompatible currency/basis cannot be aggregated. Actual charge stays null without authoritative reconciliation. No savings baseline or customer-time study exists.

## Backup and validation utilities

`catalogbridge_api.backup.backup(store, new_destination)` makes a consistent checksummed snapshot. `restore(snapshot, new_destination, current_journal_directory)` refuses overwrite and quarantines the result, expires sessions/leases and invalidates reviews. Earlier snapshots cannot refund spending. Automatic unquarantine/current-authority reprovisioning and comprehensive erasure are not delivered; do not manually clear quarantine without reviewed reconciliation.

- `scripts/prepare_catalogbridge_corpus.py --archive <authorized.zip> --member <exact-split-member> --output <new-dir> --source-url <origin> --rights-note <recorded-notice>` safely normalizes one split into separate inputs/gold. It does not automatically download or clear reuse rights.
- `scripts/validate_catalogbridge.py --inputs <inputs.jsonl> --gold <gold.jsonl> --output <new-dir> --max-pairs <limit> --max-calls <limit>` runs a bounded pair campaign. Add `--live` only for authorized installed-model usage; otherwise it is not AI-quality validation.
- `scripts/smoke_catalogbridge_provider.py --models <economy> <strong> --output <new.json>` checks the installed provider on artificial records.
- `scripts/smoke_catalogbridge_http.py --output <new.json>` runs actual temporary API/worker fixtures. `--live` also exercises a real model call and settlement, still not real-world accuracy evidence.
- `make catalogbridge-acceptance` intentionally exits nonzero, naming current blockers; it is not automatic certification.

The full [actual-data protocol](data-and-evaluation.md), independent adjudication, real calibration, browser/Windows/edge/coexistence and buyer acceptance remain pending. No browser connection was available. Comprehensive erasure, external anchoring, field mapping, persisted candidate indexing and broader settings UI remain design work. Study/blog documents follow real-data validation.
