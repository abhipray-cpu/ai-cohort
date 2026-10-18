# Fresh real-world data validation

Report date: **18 October 2026, Asia/Kolkata**. Artifact timestamps retain UTC. **Workflow checks pass; full release remains blocked.** This validation changes harnesses/tests/docs only, not product behavior, credentials or existing product data. Original failed runs and unknown liabilities remain intact.

## Data and scope

Official WDC publisher records from the previously acquired, checksummed archives were used, not invented listings. Sources and original dataset caveats remain in the [first real-data report](real-data-validation-2026-10-17.md).

- **60 new pairs**, 30 positive and 30 negative, ten of each label at each publisher hardness level 20/50/80. Their 120 offer IDs are mutually unique and do not overlap prior pair diagnostics, prior retrieval records or the new HTTP queries. SHA-256 ordering, selection and inputs were frozen before answers. Gold remains evaluator-only.
- **400 new HTTP query IDs**, 200 seen-product and 200 no-match queries, against the existing **2,841-record** master. None overlap earlier query IDs or the master. Eight query offers previously appeared in pair diagnostics; thus these are 400 new retrieval queries, **not 400 entirely never-observed offers**. Pair-cohort offer disjointness is unaffected.
- The subsequent 12-case availability replay reuses selected cases from the fresh 60, not twelve additional independent examples. No training or threshold fitting occurred. Offer disjointness does not establish cluster, provider-pretraining or independent-truth separation.

## Fresh HTTP/worker results

The separate temporary API and worker completed all 400 queries. The main workflow has inference disabled to isolate retrieval/review/export; ten separately counted queries enable real inference.

| Check | Actual result |
| --- | --- |
| Positive retrieval recall@10 | **196/200, 98%**; original 95% retrieval target passes |
| Missed query IDs | `71942027`, `27758157`, `67017951`, `2078865` |
| Automated benchmark-derived review fixtures | 200 corrections/links, 200 rejects; **not independent humans** |
| Stale revision checks | 40 refused |
| Concurrent network checks | 300 analytics reads + 300 audit reads during 100 review updates |
| Cross-workspace denials | Five |
| Exports | Unreviewed export empty; reviewed CSV and coverage match the same snapshot |
| Worker restart | Durable review checkpoints preserved |
| Recovery | Real-data snapshot/restore invalidates reviews and quarantines dispatch |
| Live inference | Ten calls, **107,618 reported tokens**, ten manual-review rows, zero unknown usage |
| Additional guard run | One-token fixture refused before dispatch; strict mode refused; all ten paid restored batches refuse dispatch while quarantined |

The initial HTTP harness failed after successful retrieval/review/export because its stress assertion hardcoded 1,000 rows. That failed artifact is preserved. The assertion now uses the actual cohort length; a new output directory records the successful complete rerun. No product threshold or expected response was relaxed.

## Original 60-pair comparison: runtime-contaminated

All three modes processed the same frozen 60 cases, but later adapter invocations returned empty responses without audit confirmation or usage. The original harness did not retain enough provider error metadata to establish the root cause. This is **not proof of a quota error, network outage, or unauthorized tool execution**. The local diagnostic message “provider tools not audited” means audit confirmation is absent, not that a forbidden tool was observed.

| Mode | Benchmark-agreeing binary proposals / 60 | Unknown-usage attempts | Reported token subtotal |
| --- | --- | --- | --- |
| Router | 40 | 18 | 382,860 |
| Economy-only | 43 | 16 | 382,504 |
| Strong-only | 29 | 27 | 307,910 |

No observed binary proposal disagreed with its benchmark label; unresolved/failure rows remain in the denominator. This is not 100% product accuracy. Router states: 42 review drafts (two insufficient-evidence proposals) and 18 failed rows. It dispatched 60 economy attempts and two strong escalations; two validation-failure events were recorded. No automatic acceptance or calibrated confidence exit occurred.

There are **61 unknown-liability attempts**, retaining **732,000 advisory reserved tokens** in the original journals. Their actual usage is unknown, not zero. Known usage and journal entries reconcile. Because failure rates and missing usage differ across modes, their token subtotals **cannot establish a quality/cost comparison or savings**. The authoritative combined report marks the comparison ineligible and its gate verdicts unavailable. It supersedes the earlier exploratory subtotal ratio retained in `fresh-summary-v1.json`; v1 evidence was not overwritten.

Two bounded, isolated runtime probes later succeeded, one per requested model, with 17,840 reported tokens. They capture exit status, event types and safe error categories without publishing raw stderr or credentials. Both still lack independently observed effective identity. Recovery of availability does not explain or settle the original failures. Official [non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable) describes completion/failure/error events and reported usage; it does not establish what caused this particular incident. OpenAI Docs was used for this narrow diagnostic check; no model, authentication or account settings were changed.

## Bounded availability replay

Before replay answers, six positives and six negatives at hardness 80 were chosen by SHA-256 order from the original frozen 60. The same twelve cases ran through all three modes with a separate 48-call cap. **36 calls actually ran**, all with known usage and reconciled journals.

| Mode | Benchmark-agreeing binary proposals / 12 | Abstentions | Tokens |
| --- | --- | --- | --- |
| Router | 12 | 0 | 107,853 |
| Economy-only | 12 | 0 | 107,739 |
| Strong-only | 10 | 2 | 115,995 |

All are manual-review drafts, not automatic matches. The router used **7.02% fewer tokens** than strong-only: descriptive improvement, but still below the original **20%** target. Twelve selected replays cannot qualify confidence calibration, prove broad model superiority or erase the failed 60-pair run. Original unknown liabilities were not reset or refunded.

## Totals, evidence and verification

The original paired campaign records 182 adapter invocations, HTTP records ten, probes two and replay 36: **230 invocations**, of which **169 have known usage** and **61 remain unknown**. Known reported usage totals **1,530,319 tokens**; this excludes unknown usage and is not a bill or complete total consumption. Paired/replay/probe calls total 220, within the announced 240-call allowance; ten HTTP calls are separately bounded. No further live calls were made after the replay.

Evidence under local/gitignored `var/validation/`:

- `catalogbridge-fresh-cohort-v1/`: source hashes, 60 label-separated pairs, 400 queries and reused master.
- `catalogbridge-fresh-models-v1/`: original 60-case three-mode answers, frozen runtime, failed cases and liabilities.
- `catalogbridge-fresh-http-v1/`: preserved hardcoded-size harness failure; no live inference reached.
- `catalogbridge-fresh-http-v2/`: successful HTTP/worker/stress run, review/export snapshots and ten paid queries.
- `catalogbridge-fresh-guards-v1/`: tiny-budget/strict-mode guards and paid-state restore.
- `catalogbridge-fresh-runtime-probe-v1.json`: two bounded diagnostic observations.
- `catalogbridge-fresh-replay-cohort-v1/`, `catalogbridge-fresh-replay-models-v1/`: frozen 12-case replay and all mode journals.
- **`catalogbridge-fresh-summary-v3.json`**: authoritative combined report, verified source/runtime/report hashes, freshness checks, per-hardness results, missing-usage eligibility guard and replay totals. v1/v2 summaries are preserved intermediate analyses.

Commands used include `python -m scripts.prepare_catalogbridge_fresh_validation`, the existing real-model/HTTP/guard runners, `probe_catalogbridge_runtime_failure.py`, `prepare_catalogbridge_availability_replay.py` and `python -m scripts.summarize_catalogbridge_fresh_validation`. Always choose new output paths. Repeating live commands consumes allowance; never overwrite a failed artifact to manufacture a pass.

Verification: **416 Python tests**, seven frontend tests/build, Ruff and whitespace checks pass; existing dependency deprecation warnings remain. Product/contract/shared-runtime hashes are identical across the original run, HTTP and replay and remain unchanged after validation. Temporary API/worker processes shut down. No browser/visual, Windows, protected Cloudflare or buyer acceptance was performed.

## Remaining work

Runtime error diagnostics and campaign-wide stop-on-repeated-failure behavior need a separate implementation pass; the per-batch unknown-usage fence does not stop this harness's subsequent isolated batches. Resolve and independently reconcile unknown liabilities before resuming those original batches. Do not repeatedly retry them as if free.

The stable 4,500/600 live campaign, independent adjudication, verified effective model identity, empirical calibration/confidence exits, >=20% quality-constrained savings, and Windows/edge/browser/buyer acceptance remain open. Hard token enforcement remains unavailable; strict mode stays refused. `make catalogbridge-acceptance` intentionally reports blocked. No release-success study/blog claim follows from this run.
