# Corrective implementation and targeted real-data validation

17 October 2026. **Named engineering fixes verified; full release remains blocked.** Original failed evidence is preserved in [the first real-data report](real-data-validation-2026-10-17.md). No existing product data, credentials, source labels or release thresholds were changed.

## Fixes and red/green evidence

New tests first failed for punctuation-sensitive retrieval, title-versus-marketing conflicts, unconditional escalation on uncalibrated decisive drafts, identity-gated uncertainty escalation and lost partial-draft state. All five then passed after implementation. A sixth accounting check subsequently failed because an oversize prompt created an unknown usage liability despite no dispatch; pure adapter preflight before reservation fixed it. Existing citations, variant mismatches, calibrated acceptance fences and unknown-usage guards remain enforced.

| Observed problem | Implemented correction |
| --- | --- |
| `AB-123`/`AB123` and punctuation segmentation lose candidates | Unicode/punctuation normalization with compact identifier tokens; bounded ranking and deterministic ID tie-break |
| No shared words in a single-record master suppress assessment | Sole master record remains a candidate; no automatic identity acceptance |
| LaCie 2TB title conflicts with description advertising a 5TB product range; “used” in prose becomes condition | Title capacity/form-factor/pack take precedence, description fallback only when absent; condition from title; brand punctuation/case normalization |
| Unknown effective identity prevents a useful stronger opinion | Unknown identity still blocks acceptance, but does not block budgeted escalation on uncertainty |
| Missing calibration alone causes another paid opinion | Valid binary proposal stops as manual-review draft; this is **not confidence early exit** |
| Later failure hides usable draft / missing per-attempt proposal lineage | Validated `proposal_history`; later failure retains draft as degraded/manual review with `partial_proposal_retained` event and incurred liabilities intact |
| Known oversized serialized input becomes fictitious unknown usage | Complete prompt/schema envelope preflight before reservation; `preflight_refused`, no dispatch/attempt |
| Model copies a normalized/translated quote or supplier ID | Prompt explicitly requires unchanged single-field substrings and selected candidate ID; literal validation stays strict, no quote rewriting |

Policy, prompt and retrieval versions are v2; calibration bindings include code hashes and invalidate older profiles. This is still heuristic retrieval/attribute extraction, not a trained multilingual matcher. Description contradictions not represented by deterministic constraints require source-aware model/reviewer scrutiny. No brand-alias guessing, gold-derived retrieval features or automatic calibration was introduced.

## Targeted real-model comparison

Before dispatch, the harness froze 20 real publisher pairs: 12 previous router abstentions and eight previously resolved controls, selected by SHA-256 order within those groups. These contain **four positives and 16 negatives**. This deliberately corrective sample is **not held-out or balanced acceptance**, and is not representative market accuracy. Gold stays evaluator-only; the product receives supplier/master fields without labels. All three modes receive the same 20 pairs.

| Mode | Binary proposals / 20 | Benchmark agreements / 20 | Calls | Actual tokens |
| --- | --- | --- | --- | --- |
| Original router on the selected cases | 8 | 8 | 12 | 104,366 |
| Fresh router v2 | 19 | 19 | 22 | 192,499 |
| Fresh economy-only | 18 | 18 | 20 | 173,828 |
| Fresh strong-only | 17 | 17 | 20 | 187,392 |

The router recovered **11 of 12** selected prior abstentions and retained all eight resolved controls as benchmark-agreeing proposals. Its two escalations followed real `insufficient_evidence`: one became `different_product`, the other stayed unresolved. These are actual observed transitions, but not calibrated confidence decisions. Historical differences also include model nondeterminism, prompt changes and cache/timing effects; they are not a causal estimate of one individual fix.

Router token use is **2.73% higher**, not lower, than the fresh strong-only baseline. Thus the proposed >=20% token-reduction gate still fails on this diagnostic. Better coverage is useful evidence but does not make the savings claim pass. Economy-only uses fewer tokens with one fewer resolved proposal; no winner is inferred from 20 failure-enriched cases. All 60 mode results are `needs_review`; **zero automatic acceptances**, zero unknown attempts, zero journal mismatches. No actual-charge or statistically established quality/savings claim is made.

## Actual HTTP/worker and operational rerun

The separate temporary API/worker replayed the frozen **1,000 real queries against 2,841 master records**. These are the same query IDs as the first report, not additional independent examples. The main run disables model egress to isolate retrieval and workflow.

- Retrieval: **789/800** positive queries hit at 10 (**98.625%**), up from 787/800 (98.375%). Eleven misses remain, and the changed ranker has both recovered and newly missed cases; miss IDs are preserved in the report. The original 95% retrieval target passes, not perfect recall.
- 200 unseen/no-match queries; 400 benchmark-derived automated review actions, 40 stale revision refusals; default unreviewed export empty and reviewed CSV matches its snapshot.
- 300 actual summary reads plus 300 audit reads during 100 review updates; five cross-workspace denials; independent worker restart; real-data snapshot/restore quarantines dispatch and invalidates restored reviews.
- Three additional real queries run inference through the actual HTTP/worker path: **three calls, 32,108 tokens**, all manual review, zero unknown usage. This is three model answers, not 1,000.
- Separate actual-store/worker and API TestClient guards refuse a one-token operational fixture before dispatch (zero attempts), refuse unsupported strict mode, restore the paid 32,108-token state and refuse all three quarantined batch dispatches. Those guards are not browser journeys.

Total fresh targeted inference: **65 actual calls / 585,827 reported tokens**. The model-comparison cap was 80 calls, plus at most three separately authorized HTTP rows. Same product/contract/shared-runtime hashes were frozen across both campaigns and remained unchanged. All temporary HTTP/worker processes stopped after the runs.

## Evidence and reproduction

Local, gitignored evidence under `var/validation/`:

- `catalogbridge-repair-cohort-v1/`: source hashes, exact selected IDs and label-separated inputs.
- `catalogbridge-repair-models-v1/`: frozen runtime, per-mode answers, usage journals and paired report.
- `catalogbridge-repair-http-v1/`: retrieval misses, review/export snapshots, stress evidence and three paid rows.
- `catalogbridge-repair-guards-v1/`: paid-state restore, tiny-budget and quarantine checks.
- `catalogbridge-repair-summary-v1.json`: combined totals, original selected-case comparison and report hashes.

Use a **new output path** for each rerun; scripts refuse overwriting evidence. Live commands consume account allowance. Original publisher archives are reused rather than downloaded again.

```sh
.venv/bin/python scripts/prepare_catalogbridge_repair_diagnostic.py \
  --cohort var/validation/catalogbridge-real-audit-v1/diagnostic \
  --baseline var/validation/catalogbridge-real-models-v1 \
  --output var/validation/catalogbridge-repair-cohort-v2
.venv/bin/python scripts/run_catalogbridge_real_models.py \
  --inputs var/validation/catalogbridge-repair-cohort-v2/inputs.jsonl \
  --gold var/validation/catalogbridge-repair-cohort-v2/gold.jsonl \
  --output var/validation/catalogbridge-repair-models-v2 --call-cap 80
.venv/bin/python scripts/run_catalogbridge_real_http.py \
  --cohort var/validation/catalogbridge-real-audit-v1 \
  --output var/validation/catalogbridge-repair-http-v2 --live-rows 3 --stress
.venv/bin/python scripts/check_catalogbridge_real_guards.py \
  --cohort var/validation/catalogbridge-real-audit-v1 \
  --paid-http var/validation/catalogbridge-repair-http-v2 \
  --output var/validation/catalogbridge-repair-guards-v2
.venv/bin/python scripts/summarize_catalogbridge_repairs.py \
  --cohort var/validation/catalogbridge-repair-cohort-v2 \
  --baseline var/validation/catalogbridge-real-models-v1 \
  --models var/validation/catalogbridge-repair-models-v2 \
  --http var/validation/catalogbridge-repair-http-v2 \
  --guards var/validation/catalogbridge-repair-guards-v2 \
  --output var/validation/catalogbridge-repair-summary-v2.json
```

Regression: **413 Python tests** pass, including 67 CatalogBridge/campaign tests; seven frontend state tests, production build, Ruff and whitespace checks pass. Existing dependency deprecation warnings remain. This turn did not perform browser/visual or old-Windows/Cloudflare testing; no claim of premium UI acceptance follows from a build.

## Remaining release gates

Not everything is production-accepted. Eleven retrieval misses, the failed token-savings gate, absent independent effective-model identity, no qualified empirical confidence calibration, independent adjudication, full 4,500/600 live volumes, actual browser/Windows/edge and buyer acceptance remain open. Hard token enforcement cannot be manufactured by application-side estimates: strict mode stays refused. Real-data quality/cost observations do not qualify owner-attested constant calibration scores. The [acceptance command](../../scripts/accept_catalogbridge.py) intentionally remains nonzero. Study/blog claiming successful acceptance are not produced.
