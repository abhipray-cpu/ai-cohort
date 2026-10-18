# A cheaper model did not make our agent cheaper

*Day 7 of our AI product challenge: building CatalogBridge, a cost-aware supplier-catalog matching agent. Engineering notes, 18 October 2026. Draft for publication; not published externally.*

“Send easy tasks to a small model and difficult tasks to a stronger one.”

That sounds like a cost-aware agent. It is also an easy architecture to overclaim.

We built CatalogBridge to help catalog operators decide whether supplier listings refer to products already in their master catalog. The intended value is less repetitive matching work at controlled error and processing cost. A wrong link between an 8GB memory module and its 16GB variant is not a harmless chatbot mistake.

The workflow now imports real feeds, retrieves candidates, generates source-backed drafts, supports review and exports reviewed mappings. But the harder question is whether the router earns its place: does it reduce spending without degrading decisions?

Our measurements did not initially support that claim.

## Model price, token consumption and customer value are different things

An economy model may have a different reference token price. That does not mean it consumes fewer tokens for the same task. It also does not establish the marginal charge on an installed CLI account.

Both routes were paying much of the same context overhead. When the economy response was uncertain, escalation meant paying for another context-bearing call. The supposedly cheaper path could therefore consume more tokens than going directly to the stronger model.

We reduced prompt overhead with compact classifier instructions. That helped absolute usage, but it helped the stronger baseline too. Comparing an optimized router with an unnecessarily bloated baseline would have manufactured a win.

The lesson was to change the execution graph, not just the model name.

## A local stage can avoid a call—but must earn that decision

We added an opt-in local pair scorer ahead of the installed Codex adapter. It uses small boosted trees over lexical overlap, identifying numbers/codes, brand information and variant-conflict indicators. It runs locally from bounded JSON, without another model service or a generative call.

The fitting, tuning and qualification partitions have disjoint product entity groups. Product IDs and benchmark labels do not become runtime features. Thresholds are chosen on tuning data and frozen before the separate qualification check.

The result was deliberately asymmetric.

One negative band selected 1,077 offer-disjoint qualification pairs, with 1,073 agreeing with publisher labels. The positive band performed much worse: 717 agreements among 775 selected pairs. It failed and stayed disabled.

Even the negative result needs a qualification: product groups repeat within those 1,077 cases. Its pair-level Wilson calculation is not a defensible guarantee of independent 99% production safety. We restrict the artifact to benchmark review drafts. It does not authorize automatic linking.

For a row with several retrieved candidates, every candidate must satisfy the negative band before that local route can stop inference. Rejecting one easy candidate does not resolve the whole row. Rejecting all retrieved candidates also does not prove that no matching product exists elsewhere in the catalog.

## A draft, a confidence exit and a cache hit are not the same result

This distinction became central to the product.

A valid binary draft can stop further spending while still requiring review. An unchanged earlier draft can be reused under exact source and policy bindings. A genuinely qualified automatic recommendation would need stronger evidence and authority.

All three can avoid a later model call. Only one is intended to authorize an automatic recommendation—and real automatic acceptance is still unqualified in this product.

The local scorer therefore produces `needs_review`, keeps its score/profile/source evidence, and makes zero model attempts when it exits. Reviewed export still excludes that row until someone separately reviews it. A cached draft follows the same authority boundary.

Human review does not make the original proposal correct. It does make clear who is responsible for deciding whether that particular draft can be applied.

## We tested fresh pairs, not just remembered successes

We froze a 600-pair challenge with no development-entity overlap, balanced across three hardness levels and both labels. Selection used deterministic ordering, not model scores. A 60-pair live pilot was selected in advance.

On the complete offline challenge, the local stage produced 101 drafts without an LLM call: 100 agreed with benchmark labels and one did not. That is 16.83% local-exit coverage, not a measured 20% token-saving result.

The disagreement matters. It shows why a high-confidence band from one partition is not a license to stop observing mistakes elsewhere.

A second research candidate was tested against a separate legacy-source qualification partition. It did not collect enough reliable cases to qualify either band. We emitted no profile for that candidate and left its reserved challenge unscored. More training data and a more elaborate experiment did not automatically produce a deployable policy.

## The live comparison stopped on quota

The actual three-way run compared router, economy-only and strong-only on the same frozen pilot, with the same compact instruction profile and caches disabled.

It stopped after the installed runtime returned quota errors.

There had been 123 dispatches: 120 with known usage totaling 640,523 reported tokens, plus three calls with unknown usage. The shared campaign guard stopped new work across all modes. Their unresolved liabilities remain held; we did not infer that a quota error meant zero charge.

The router processed 45 rows, economy-only 43 and strong-only 35. Dividing those whole-mode token totals would compare different amounts of work. The campaign is marked ineligible for a savings conclusion, and the original 20% target remains unproven.

The local stage did make five genuine no-call draft exits before the stop. That establishes an execution path, not commercial acceptance.

This is the uncomfortable but useful result: the containment mechanism worked, while the quality–cost experiment remained incomplete.

## Unknown usage is part of the cost model

Cost-aware agents need more than counters on successful answers.

Before dispatch, CatalogBridge reserves advisory row and batch allowance. Afterwards it settles reported usage or retains an unknown liability. Cached input and reasoning output are subsets of their respective totals, not extra tokens to double-count. Timeouts and failures are included.

The adapter also preserves usable completion telemetry received before a later timeout. A truncated stream, multiple completions or a later unfinished turn cannot be silently settled using only the first receipt. Sanitized diagnostics retain error categories, hashes and thread correlation without storing raw logs or credentials.

The [documented Codex JSON event stream](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable) gives the adapter a machine-readable boundary. It does not establish hard-token enforcement, recover missing historical receipts or independently attest the effective served model.

A workspace circuit prevents later batches from continuing to spend through an unresolved incident. Restarting, increasing a budget or acknowledging a failure cannot erase unknown usage. Old liabilities remain separate from new successful runs.

## What we can honestly say today

The implemented engineering checks pass: 476 Python tests, eight frontend tests and the production web build. Real-data workflow checks have also exercised retrieval, revisions, review/export boundaries, concurrent reads/writes, isolation and recovery.

Those are useful achievements. They are not proof that the product is a sellable cost-aware MVP.

The fresh-row savings target remains unmet or unestablished in eligible live evidence. Automatic confidence acceptance remains unqualified. Independent customer adjudication, target-Windows operation, browser/edge checks and buyer value still require evidence.

Our most important design change was making those distinctions visible—in the controller, the ledger, the UI and the evaluation reports.

A cost-aware agent should be able to explain not only why it selected a model, but why it spent anything at all, what it knows about that spending, and what authority its answer actually has.

Until the completed quality–cost comparison supports the commercial promise, the right conclusion is not “production-ready.” It is “implemented, measured, and still under validation.”

---

Implementation and experiment details: [study guide](study-guide.md), [local-routing validation](local-routing-validation-2026-10-18.md), [architecture](architecture.md), [data/evaluation protocol](data-and-evaluation.md) and [runtime receipts/repeat-work evidence](receipts-and-repeat-work-2026-10-18.md). Benchmark agreement is not independently adjudicated customer truth, and reported tokens are not an actual bill.
