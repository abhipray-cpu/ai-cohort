# Browser and larger live cohort — 22 October 2026

**Partial acceptance only. The larger live campaign failed.** This supersedes the
current browser/authority status in the [previous checkpoint](oss-validation-2026-10-22.md),
not its historical results. Windows/Cloudflare is unavailable, as confirmed by the
user. No target-host result is inferred from the Mac lab.

## Browser: six actual end-to-end cases pass

The attached browser remained unavailable. Following browser-skill discovery and
troubleshooting, the campaign used Playwright **1.64.1**, isolated headless installed
Chrome, fresh profiles, actual FastAPI/PostgreSQL and no personal browser state.
`@axe-core/playwright` **4.14.0** scans all seven operator views for WCAG 2 A/AA and
2.1 AA automated rules. This is not full accessibility certification or testing
with assistive technology, every browser, every permission/state combination.

Six tests pass (6.2s; isolated Python process orchestrator 8.41s):

1. Invalid login, keyboard submission and session revocation on logout.
2. Actual API metric rendering, all seven navigation views, no page exceptions,
   and automated accessibility scans.
3. Organization switching clears old evidence; unavailable cost remains unknown.
4. Independent reviewer lacks owner mutation UI and receives cross-tenant denial.
5. Explicit OSS canary profile and 390-pixel mobile navigation/layout.
6. Owner creates a canary, a separate reviewer session approves it, owner dispatches;
   the UI/API do not call an unacknowledged command verified or enable promotion.

The browser fixture uses ten actual USDA records for source binding, with authored
lifecycle measurements and deliberately unavailable usage. It is **not inference**,
actual customer latency or the live cohort. Its declared model-call values are
unknown-usage UI fixtures, not additional calls against either approval.

The first runs caught inadequate text/badge/notice/audit-timestamp contrast. These
were fixed without disabling axe rules. Screenshot review also exposed excessive
floating-point latency digits; an observed red/green domain test now bounds
presentation precision without converting missing values to zero. Four web domain
tests and the production build pass. Failed browser reports remain retained.

Evidence under `var/validation/`:

- `releasefence-browser-20261022-r7/browser.xml` — six passing browser tests.
- `releasefence-browser-orchestrator-20261022-r7.xml` — one orchestration test;
  do not count this as another independent six-case campaign.
- `releasefence-browser-20261022-r7/artifacts/mobile.png` and `desktop.png`.
- Earlier `r1`–`r6` artifacts retain setup, assertion and actual contrast failures.

Re-run without inference, with Chrome installed and browser dependencies installed
using `npm --prefix apps/releasefence-web ci`:

```sh
RELEASEFENCE_ACCEPTANCE_CORPUS="$PWD/var/validation/shelfproof-usda-grouped-20261021" \
RELEASEFENCE_BROWSER_OUTPUT="$PWD/var/validation/releasefence-browser-next" \
  make releasefence-test-browser
```

The output must be a new directory. Test fixture credentials stay private; do not
reuse them for a real deployment. The runner starts/stops only owned test services.

## Larger live cohort: failed, not waived

The user separately approved **up to 200 public products and 240 total Codex calls**.
The original 24-call ledger is untouched and remains spent. New ledger:
`var/validation/releasefence-live-cohort-approval-20261022.sqlite3`;
identity `user-2026-10-22-releasefence-200-products-240-calls`.
The new ledger records **239/240 reserved calls**, including unsuccessful attempts.
One remains unused; this is not authority to reset or launch another 200-task run.

The campaign used the first 200 frozen USDA records, unique unfiltered session IDs,
the normal 5% sticky canary routing and four bounded concurrent HTTP requests.
Real customer-side bundle/gateway/SDK calls emitted events and agent/LLM spans to
the actual API/worker/PostgreSQL and both owned tracing backends. Inference used the
restricted installed-Codex adapter, with no model/authentication setting changes.
There was no deliberate critical-failure injection in this cohort.

| Measurement | Observed result |
| --- | --- |
| Distinct actual products/tasks attempted | 200 |
| Codex attempts, including retries | 239; 161 tasks had one attempt, 39 had two |
| Successful literal-source outputs | 165/200; 35 failed after provider failures/timeouts |
| Failed invocation attempts | 65 unsuccessful-provider `ValueError` categories and nine `ProviderTimeoutError` categories; no invented answers substituted |
| Actual assignment | 189 stable / 11 candidate; no hash filtering to balance arms |
| Metric counts | 200 accepted, 239 calls, all 239 USD costs unknown; no free-cost claim |
| Unique live spans | 439: 200 agent roots and 239 invocation spans |
| Export completion | Failed: six Phoenix records reached dead letters; an observed later API query showed 872/878 exports verified |
| Terminal campaign result | Failed at the 180-second complete-export wait; JUnit retains the failure |
| Closed canary decision / rollback in this run | Not reached; not claimed passed |
| Cleanup | Owned API/worker stopped; exact API/backend ports independently returned `ECONNREFUSED` afterward |

Retained evidence:

- `releasefence-live-cohort-20261022-r2/report.json` and a partial executable archive:
  23 archived files match their recorded hashes. The absolute runner path incorrectly
  joined outside the archive, leaving its self-copy missing. Its recorded hash is
  retained, but the old source is not retrospectively reconstructed. A new observed
  red/green test fixes future absolute-path snapshots; this is a provenance limit
  of the failed campaign, not full immutable-source qualification.
- `releasefence-live-cohort-20261022-r2.xml` — **failed** campaign, 870.57s measured
  by the test runner; not a successful 14-minute performance result.
- `releasefence-cohort-read-only-checkpoint-20261022.json` — an independently
  authenticated, read-only API snapshot before cleanup. Its slightly earlier
  export counts are 868 verified / four retry / six dead-letter, not final counts.
- The attempted first fixture setup failed before any model call and is separately
  retained in `releasefence-live-cohort-20261022.xml`; no ledger reset occurred.

Wall timestamps contain large discontinuities: some invocation wall intervals
exceed 15,000 seconds while the runner reports about 871 seconds overall. The exact
host interruption/clock cause is not established. These durations **cannot**
qualify representative latency, a stable-host soak or an uninterrupted statistical
window. The source/output and call-count denominators are still retained.

## Zero-inference trace diagnosis

Read-only inspection of both retained backend databases found **439 matching span
IDs, trace IDs, parent relationships and release IDs**, with no cross-store identity
mismatches. A fresh actual-backend replay of that retained live metadata then
passed all **439 span read-backs in each backend**: 878 backend observations,
not 878 unique spans or model calls. This is a diagnostic replay, not new inference
or recovery of the original ReleaseFence dead-letter state.

Artifact: `releasefence-cohort-span-replay-20261022.xml` — one actual-services test,
143.00s. Reproduction is explicitly separate:

```sh
RELEASEFENCE_MLFLOW_PYTHON="$PWD/var/validation/releasefence-mlflow-venv/bin/python" \
RELEASEFENCE_PHOENIX_PYTHON="$PWD/var/validation/releasefence-phoenix-venv/bin/python" \
RELEASEFENCE_REPLAY_MLFLOW_DB="$PWD/var/validation/releasefence-live-cohort-20261022-r2/backend-lab/traces.db" \
  .venv/bin/python -m pytest -q tests/acceptance_releasefence_span_replay.py
```

The exact in-run cause of the six Phoenix read-back dead letters remains
unresolved; later data presence does not prove read-back succeeded at the original
verification time. The singular REST `trace_id` parameter was checked against the
installed upstream server/client and is correct; the plural Python `trace_ids`
argument must not be mistaken for the wire name. No speculative parameter change
was installed. Existing one-owner-replay limits/backlog promotion holds remain.

## Statistical interpretation and remaining work

A 100-session-per-arm admission minimum is not a power guarantee. Under the
unchanged conservative failure bound, even **100/100 perfect, known-cost samples**
are inconclusive. A deterministic zero-failure bound crosses the 2-point margin at
403 observations per arm, versus 402 insufficient, assuming the other gates pass.
Those are controlled mathematical checks, not a required production sample-size
recommendation or real-cohort qualification. The actual 11-candidate cohort and
unknown billing costs cannot support a promotion pass.

New test-first checks bind the new ledger without expanding the old grant and
reject incomplete cohort summaries, missing decisions, dead letters, provider
failures and discontinuous timing. Original failed reports are not rewritten.
Final full regression: **850 passed, five pre-existing unrelated skips**, six
upstream warnings, 99.12s; `releasefence-followup-final-monorepo-20261022-r2.xml`.
The final zero-inference source-bound process campaign also passes all its scoped
checks, with three organizations, both backends and signed/probed rollback:
`releasefence-followup-integration-20261022/report.json`. Independent verification
checks all 12 command/runtime signatures and 24 current executable-source hashes.
This controlled process pass is not the failed 200-product live campaign.

`releasefence-followup-independent-audit-20261022.json` binds the artifact hashes,
both separate ledgers, the failed cohort checks, cross-store identity comparison,
archive limitation, final regression and new no-inference process checks. The
failed cohort remains explicitly unaccepted in that summary.

Still required: resolve/recover original-run export failures under an uninterrupted
host campaign; sufficient authorized successful/provider/billing evidence for the
declared policy; Windows/Cloudflare host qualification; independent security and
semantic review; customer pilot acceptance. Additional inference beyond the new
grant needs a new explicit approval. **This remains not a 100% accepted MVP.**
