# Real-data end-to-end validation — 17 October 2026

Verdict: **release blocked**. Actual real-source HTTP/worker/review/export, retrieval and operational checks pass, but the bounded model comparison does not meet the proposed quality/coverage/token targets. This is not completion of the full 4,500-pair/600-comparison acceptance campaign.

The product, contracts and shared runtime hashes remained unchanged throughout these runs. Changes in this task are validation tools, four harness tests and documentation, not silent product fixes. No threshold was tuned against observed model answers. No existing `.env`, credential, Windows task, Cloudflare configuration or earlier product process was changed.

## Scope and reproducible artifacts

Artifacts remain local/gitignored; source content was not published or added to Git:

| Artifact below `var/validation/` | Purpose |
| --- | --- |
| `catalogbridge-real-corpus-v1/` | Preserved partial acquisition after publisher HTTP 429 |
| `catalogbridge-real-corpus-v2/manifest.json` | Eleven acquired resources, URLs, bytes and SHA-256; source-page snapshots |
| `catalogbridge-real-audit-v1/` | Original frozen primary/diagnostic/query/gallery inputs; initial legacy adapter issue preserved |
| `catalogbridge-real-audit-v2/` | Corrected evaluator adapter for legacy string labels, without changing runtime contracts |
| `catalogbridge-real-audit-v3/audit.json` | Full pair/multiclass audit and source/split-quality findings |
| `catalogbridge-real-models-v1/` | Frozen 60-pair router/economy/strong comparison, outputs and separate durable ledgers |
| `catalogbridge-real-http-v1/` | Actual 1,000-query HTTP workflow plus ten live complex rows |
| `catalogbridge-real-http-stress-v2/` | Same real-source cohort replayed for concurrency, scope and recovery; not extra unique data |
| `catalogbridge-legacy-cohort-v1/`, `catalogbridge-legacy-live-v1/` | Sixteen balanced, four-category legacy-gold cases, economy profile only |
| `catalogbridge-real-guards-v1/` | Real-input tiny-budget refusal and restoration of actual paid-state counters |
| `catalogbridge-real-summary-v1.json` | Reconciled totals, paired descriptive comparison and explicitly hypothetical rate scenario |

The publisher rate-limited initial parallel acquisition. Sequential downloads/backoff and reuse of the completed archive succeeded; the failed initial artifacts were retained. Public benchmark download is not a blanket redistribution/commercial-training license. Framework software licensing was not applied to dataset content. These runs are private evaluation, not commercial-training or legal clearance.

## Acquired data and quality checks

Sources: [WDC Products](https://webdatacommons.org/largescaleproductcorpus/wdc-products/) and [earlier WDC matching gold sets](https://webdatacommons.org/largescaleproductcorpus/v2/). Publisher benchmark labels, including their known uncertainty, are not independently adjudicated catalog truth.

Observed in the downloaded artifacts:

- Eleven resources, **76,948,459 bytes**, with raw hashes and safe archive-member checks.
- All **27 pairwise split files**: **155,957 pair presentations**, including nine test sets with **40,500 presentations / 37,776 distinct unordered test pairs**. These are not 155,957 independent products or live model calls.
- All **27 multiclass split files**: **33,921 offer presentations / 10,422 distinct offer IDs**. Use these acquired-file counts, not an unverified headline count from a webpage.
- Thirty-five pair presentations fail the product input envelope; five multiclass presentations refer to one unsupported offer. All newer test-pair inputs are schema-eligible. No silent truncation or suppressed denominator was used.
- The older combined gold file contains **4,398 raw pairs**, seven outside the product envelope. Individual category files total 4,399 presentations and substantially overlap the combined file; they are not additive independent evidence.
- The legacy publisher serializes labels as strings. Initial audit v1 rejected them; a tested, evaluator-only `0`/`1` conversion fixes that in v2/v3 without relaxing product inputs. Four validation-harness tests pass.
- No conflicting binary labels were found for the audited newer unordered pair IDs. Offer-ID overlap was observed between `train_large` and the **50%-unseen** test variant: 269 / 274 / 272 IDs for the three hardness families. The corresponding fully-seen and fully-unseen variants showed zero such overlap. Investigate that before learned-calibration evaluation; no training/fitting occurred here. The actual retrieval query/gallery set has **zero offer-ID overlap**.

The fixed title-similarity/conflict baseline was evaluated across all nine test sets. Its roughly 89% overall agreement conceals very low positive recall (0.4%–4.2%) on negative-heavy sets. It is not an acceptable identity matcher and was not used to declare product quality.

## Actual 1,000-query end-to-end workflow

Separate loopback API and worker processes imported **2,841 master records** and **1,000 supplier queries**: 800 queries whose entity exists in the gallery and 200 withheld-entity/no-match queries. Cluster/label metadata remained evaluator-only. All source records in this cohort were imported; none were dropped.

The main 1,000-query batch intentionally used manual mode, so it tests actual retrieval/checkpoints/workflow—not 1,000 live AI answers. It completed through the real worker to `review_ready`. Candidate retrieval hit **787/800 positives: 98.375% recall@10**, above the proposed 95% target. Thirteen misses are preserved. A product-cluster bootstrap over 481 positive clusters (2,000 resamples, seed 42) yields an indicative 95% interval of **97.49%–99.25%**. This is relative to benchmark entity labels, not independent catalog adjudication.

Actual HTTP checks include unauthenticated denial; separate owner/reviewer sessions; 400 benchmark-derived review actions (200 corrected links, 200 rejections); 40 stale-form denials; no unreviewed default export; reviewed CSV/coverage consistency; reviewer budget-change denial; and actual worker restart at durable review checkpoints. **These reviews are automated workflow fixtures, not 400 real people or independently verified human judgments.**

Ten preselected queries then ran through the actual API/worker with model egress enabled and the full gallery. All requested the stronger profile based on candidate complexity. They consumed **ten calls / 112,677 measured tokens**, no unknown usage, and stayed in `needs_review`; one produced no publishable proposal after validation. Three calls exceeded the 12,000-token reservation; maximum **13,153 tokens**. Those overruns were retained, demonstrating advisory—not hard—budget behavior.

## Real model comparison: same 60 pairs

The frozen diagnostic includes 30 positive and 30 negative pairs across three difficulty conditions. The actual router ran against its two real configured requested profiles; economy-only and strong-only baselines used the same source fields, prompt/schema and evidence/conflict validator. These baseline calls are comparison harnesses, not normal multi-candidate product workflows.

| Mode | Cases | Calls | Measured tokens | Binary proposals | Agreeing with labels / all cases |
| --- | ---: | ---: | ---: | ---: | ---: |
| Router | 60 | 54 | 473,744 | 36 | 34/60 |
| Economy only | 60 | 60 | 520,664 | 49 | 47/60 |
| Strong only | 60 | 60 | 561,030 | 46 | 44/60 |

Abstentions remain in the denominator. This table is **validated-proposal agreement/coverage, not final catalog accuracy**. Of resolved binary proposals, agreement is 34/36, 47/49 and 44/46 respectively. No mode automatically accepted a mapping. Twelve router cases retrieved no candidate; six other cases used a further model route after validation failure. Do not call either candidate omission or unverified-identity stop a calibrated-confidence early exit.

Against stronger-only, router token reduction is **15.56%**, below the proposed 20% target. All-row agreement and binary-proposal coverage are each **16.67 percentage points lower**. These exploratory proxies fail the intended trade-off; the actual adjudicated release criteria remain unmeasurable without qualified truth and larger samples. Do not turn abstention into an incorrect-link claim, but do count the manual workload it leaves.

The economy baseline had six validation failures; stronger-only had four. Across these ten cases, eight were source-attribute conflicts and two exact-quote mismatches. Conflicts require expert inspection; weakening a validator merely to agree with noisy gold is not a fix. Failed calls remain charged in usage totals. The separate legacy diagnostic completed 16 economy-only calls: **15 matching binary predictions, one validation failure**, using **138,881 tokens**. That is a small secondary check, not full legacy acceptance or a paired model comparison. Its original generic `paired_rows` field denotes a one-mode intersection and is explicitly ignored as comparative evidence.

## Accounting, cost and operational evidence

Total across newer comparison, complex HTTP rows and legacy check: **200 actual model attempts / 1,806,996 measured tokens**, including failures and retries. All measured attempt→batch totals reconcile; no unknown usage or journal mismatch was observed. Requested profile counts are 124 economy / 76 stronger calls. Response streams do not independently attest effective identity.

The summary separately applies the inspected [official Standard credit-rate table](https://learn.chatgpt.com/docs/pricing#token-rates) as a **post-hoc reference scenario keyed to requested model**. On the same 60 pairs, hypothetical totals are router **2.65154 credits**, economy **0.71584**, stronger **22.48582**. These are neither billed charges nor included-subscription/quota estimates. Cache/reasoning fields are counted once. Concurrent, non-counterbalanced baseline scheduling and a small sample limit economic inference. The router is not shown to improve on economy-only; lower reference price than stronger-only does not offset worse coverage.

The stress replay performs **300 actual summary reads + 300 audit reads during 100 review updates**, plus five cross-workspace denials. It also checks real-source backup/restore, invalidated restored reviews and blocked quarantined dispatch. The same 1,000 source queries and 400 review fixtures are replayed, not counted as new independent examples.

Additional guard checks use real records with a deliberately tiny allowance: refusal occurs **before any model dispatch**, with zero attempts, and strict-token mode is explicitly refused. A separate snapshot/restore of the genuinely paid HTTP state preserves **112,677 tokens** across ten batches and refuses all ten attempted dispatches while quarantined. These are actual store/worker plus API TestClient guard tests, not browser or separate-network-server journeys.

## Concept and release verdict

| Concept/gate | Evidence | Verdict |
| --- | --- | --- |
| Token budgeting per task | Reservations before calls, reconciled usage, real-input exhaustion refusal, actual overruns and paid-state restore | Advisory behavior demonstrated; hard enforcement unavailable |
| Routing by complexity/cost | Requested economy/strong selection on actual inputs; 48 economy/6 strong calls in router comparison, direct strong on ten complex queries | Requested routing demonstrated; effective identity and acceptable quality/cost trade-off unverified |
| Early exit on confidence | No qualified real calibration, no automatic acceptance | **Not validated**; do not substitute safe abstention for a pass |
| Cost per decision | Reconciled failures/retries, model-specific reference scenario, explicit denominators | Descriptive analytics demonstrated; actual billing and business savings unproven |
| Real retrieval/workflow/stress | Natural-data HTTP path, recall, review/export, scope/restart/recovery | Named checks pass, with exact limitations above |

Fresh regression: **408 Python tests**, no skips/failures, including 62 product/campaign tests; seven frontend tests and production build; Ruff/whitespace checks pass. Existing dependency deprecation warnings remain. Browser skill setup/discovery found no connected browser, so visual acceptance is blocked. No actual old Windows, protected Cloudflare edge or buyer usefulness test ran. Temporary API/worker processes shut down; earlier products were untouched.

**Still not completed:** 4,500 unique live router pairs, 600 paired baseline cases, 1,200 independently adjudicated pairs, qualified calibration/effective identity, browser and Windows/edge acceptance. The expensive live portion stayed at a 200-call diagnostic cap; it was not silently relabeled as the larger campaign. No synthetic labels, model-generated human decisions or lower replacement thresholds were used to manufacture acceptance.

Next: inspect the preserved misses/conflicts/abstentions; resolve runtime/calibration prerequisites; improve the measured quality/cost trade-off; then freeze a new campaign before expanding live volume. Product repairs require a subsequent implementation request. Original failed evidence and all original volume/quality targets remain intact. No study/blog claiming successful acceptance was created.
