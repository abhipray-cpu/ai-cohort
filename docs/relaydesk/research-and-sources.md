# Research and primary sources

Checked 16 October 2026. Observations below describe vendor documentation/source accessibility, not independently measured customer outcomes. No market-size, revenue or uniqueness claim is made.

## Market evidence and implication

| Primary source | Observed offering | Implication for RelayDesk |
| --- | --- | --- |
| [Intercom memory announcement](https://www.intercom.com/changes/en/154444-fin-now-remembers-past-conversations) | Past conversation context can follow returning customers across channels | Generic cross-session memory is not differentiation |
| [Pylon account intelligence](https://support.usepylon.com/articles/9584856925-pylon-101-setting-up-account-intelligence) | Account notebooks, structured AI fields and account summaries, including handoff uses | Account summaries alone are not a defensible wedge |
| [Linear customer requests](https://linear.app/docs/customer-requests) | Customer feedback is linked to engineering issues/projects and originating conversations | Coexist with existing workflows; do not rebuild a helpdesk or claim issue linking is novel |

Inference, not established demand: a narrow engineering-handover product could compete on inspectable attempts/outcomes, supersession and environment-aware continuity. Validate through paid pilots against the buyer's actual incumbent, not feature checklists. The proposed $99/team pilot price is our hypothesis, not a competitor quote.

## Actual conversation sources

| Source | What is available / useful | Limitation |
| --- | --- | --- |
| [Elasticsearch issue 90216](https://github.com/elastic/elasticsearch/issues/90216) | Reported upgrade environment, failure and workaround discussion | Participant reports are not independently verified operational facts |
| [VS Code issue 255749](https://github.com/microsoft/vscode/issues/255749) | Remote-connection investigation, related reports and follow-ups | Contributors can describe different environments; do not merge into one customer |
| [GitHub issues API](https://docs.github.com/en/rest/issues/issues) | Issue identities, timestamps, bodies and metadata | Listings can include pull requests; filter explicitly; edits/current status can leak future knowledge into historical replay |
| [GitHub comment API](https://docs.github.com/en/rest/issues/comments) | Attributed message IDs, bodies and creation/update timestamps; pagination | A first page or issue comment counter is not a full human-conversation capture |
| [GitHub API limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) | Primary/secondary limits and response guidance | Acquisition must checkpoint/rate-limit; token rotations must not bypass restrictions |

These are real public technical investigations. They are domain-relevant validation data, not private paying-customer histories. Repository licenses do not automatically license every contributor's comment for unrestricted redistribution. Preserve source attribution and inspect applicable terms/privacy before freezing or sharing fixtures; keep raw payloads ignored initially.

Never infer an organization/account from a GitHub author, profile or repository contributor role. A public repository is not a customer, and a participant returning to another issue does not authorize cross-case memory.

## Supplemental memory benchmark

[LongMemEval official repository](https://github.com/xiaowu0162/LongMemEval) supplies 500 evaluation items with evidence-session labels and question types covering temporal reasoning, updates, preferences and multi-session memory. Its histories include constructed/simulated components. Use it as a separate benchmark, not natural customer evidence. Verify dataset-version terms and evaluation code before acquisition. Its labels do not establish technical support usefulness or real multi-browser consistency.

Do not mix a supplemental benchmark's score with the proposed real-thread product score. LLM judges are optional evidence, not independent human gold. No benchmark has been acquired or run for RelayDesk.

## Technical references and proposed choices

- [all-MiniLM-L6-v2 model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2): candidate English semantic encoder with 384-dimensional output. The card notes truncation above 256 wordpieces; chunk before encoding and record coverage. This is a candidate, not installed/pinned or validated on our host.
- [Sentence Transformers inference backends](https://www.sbert.net/docs/sentence_transformer/usage/efficiency.html): CPU ONNX is an option; pooling/normalization outside the high-level library must match the model. Measure accuracy/resource changes after quantization; vendor throughput examples are not our laptop measurements.
- [SQLite WAL](https://sqlite.org/wal.html): proposed local transactional store on a local disk, not a network-share coordination mechanism.
- [SQLite FTS5](https://sqlite.org/fts5.html): optional lexical retrieval alongside vectors; verify availability in the pinned Python/Windows build.
- [C4 diagrams](https://c4model.com/diagrams): architecture notation in this pack; diagrams are targets, not a deployed service.

Initial vector design: normalized float32 embeddings in product SQLite with exact per-scope cosine search, backed by CPU array operations. This is genuine semantic vector retrieval, not a renamed keyword/hash lookup. It avoids requiring a separate vector service for the bounded pilot. ANN/vector extensions remain optional later optimization; exact-search latency and memory must be measured.

Existing shared provider interfaces can be assessed for reuse: [StructuredProvider](../../packages/agent-core/src/agent_core/provider.py), [local runtime adapter](../../packages/agent-core/src/agent_core/codex_local.py) and [service runner](../../scripts/run_product_service.py). Their existence does not implement RelayDesk memory or prove Windows compatibility. Keep earlier products' stores/orchestrators isolated.

## What this research has not established

No acquired 200-thread corpus, exact embedding artifact pin, Windows inference performance, independent gold labels, full comment-history reconstruction, customer effort savings, acceptable commercial inference cost or willingness to pay. [Source feasibility](validation-2026-10-16.md) distinguishes observations from these open gates.
