# Research, sources and evidence boundaries

Inspected 17 October 2026. Primary publisher/vendor material supports the external observations below. Product differentiation, architecture, budgets and thresholds are our proposals, not source claims.

## Commercial category

| Source | Supported observation | Consequence / limit |
| --- | --- | --- |
| [Price2Spy product matching](https://www.price2spy.com/product-matching-service.html) | Offers matching with AI-enhanced methods and expert review | Commercial matching workflow exists; this is vendor evidence, not proof of unmet demand |
| [Channable product feeds](https://www.channable.com/products/product-feed-management-tool) | Markets feed management and product-data cleanup | Broad competing suites already exist; avoid a generic feed-tool clone |
| [Channable AI attributes](https://www.channable.com/products/ai-product-listing/attributes) | Offers attribute enrichment and approval controls | Attribute generation alone is not a defensible differentiator |

Commercial inference: a narrow matching-and-exception workflow could be useful to a retailer/agency that wants reviewable exports and predictable processing effort. Budget transparency is a proposed wedge; buyer interviews and paid use must establish whether it matters. Do not repeat vendor accuracy or uplift claims as our own evidence or claim competitors lack budgeting without a feature audit.

## Real-data feasibility

[WDC Products](https://webdatacommons.org/largescaleproductcorpus/wdc-products/) publishes 11,715 offers for 2,162 entities, nine pairwise test sets of 4,500 pairs, and downloadable hardness variants. Labels are identifier-derived; its manual sample estimates roughly 4% label noise. These are historical real web offers, not current supplier inventory. The linked sample JSON was opened in the preceding research turn. Archive hashes, actual imported counts and rights are not verified yet.

The [earlier WDC corpus/gold standard](https://webdatacommons.org/largescaleproductcorpus/) provides separately manually checked matching material. Its page has differing count descriptions, so acquisition must resolve actual file counts rather than select a headline. Cross-corpus duplication and web-pretraining exposure remain possible. Neither resource supplies operational reviewer time, buyer outcomes or complete variant truth.

The matching input must exclude labels, cluster IDs and sampling metadata. Published overlap across variants is not additional independent evidence. [Evaluation](data-and-evaluation.md) defines manifests, split isolation, separate benchmark and adjudicated scores, and candidate-search testing. Public download does not by itself establish redistribution/commercial-training permission; capture terms/attribution and block unverified reuse.

## Routing and cost foundations

[RouteLLM paper](https://arxiv.org/abs/2406.18665) studies choosing stronger versus weaker models to trade cost against quality. It supports testing a router, not assuming transferred performance or reusing chat-preference thresholds for catalog identity. Our initial policy should be an explainable tested cascade; a learned router is optional only after sufficient held-out task-specific evidence.

[Official OpenAI usage/pricing documentation](https://learn.chatgpt.com/docs/pricing) distinguishes included subscription usage from API pricing and applicable credit billing. Therefore store measured usage, reference-price estimates and actual reconciled charges as separate facts. Model/account availability and enforced output-token controls must be verified on the installed CLI before implementation acceptance. No current model identity or price is hardcoded by this research pack.

[SQLite WAL](https://www.sqlite.org/wal.html) supports same-host local-disk deployment with one writer. This is a proposed persistence choice, not proof of backup correctness or old-laptop throughput.

## Existing repository evidence

Read-only inspection: `packages/agent-core/src/agent_core/provider.py` exposes `StructuredGeneration` with text, exit code, elapsed time, stderr and audit flag. `codex_local.py` runs the installed executable and checks restricted events, but its returned contract does not expose structured usage/model identity. The proposed router therefore needs an additive, regression-tested adapter capability; the current contract alone cannot substantiate cost analytics or verified model routing. An output-byte limit is not an output-token limit.

No adapter was changed, CLI launched, credential inspected, dataset acquired, customer contacted or deployment performed during this docs stage. See [source feasibility](source-feasibility-2026-10-17.md).
