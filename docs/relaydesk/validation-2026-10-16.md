# Source feasibility observations — 16 October 2026

Historical pre-implementation snapshot: **research/source access only**. At that point no app, corpus freeze, embeddings, memory run, quality score or browser journey existed. Implementation and actual-data validation followed under explicit authorization; see [the subsequent engineering report](implementation-validation-2026-10-16.md). Source timestamps below remain UTC.

## What was checked

Primary vendor pages confirmed that existing products already advertise cross-conversation memory, account notebooks and customer-to-engineering issue links. Technical references were inspected for GitHub issue/comment acquisition, CPU semantic embeddings, SQLite and C4 notation. These establish feasible inputs/design options, not differentiation, demand or implementation correctness.

Public issue pages were read for two investigation seeds. The web-reading tool could not access the four GitHub API URLs, so that tool result was not interpreted as an API outage. A separate bounded HTTPS read using the existing trusted transport then returned JSON for all four URLs. The transport was used only as a research helper, not as a newly implemented RelayDesk connector.

## Actual API observations

| Public GET | Observed JSON metadata |
| --- | --- |
| [Elasticsearch issue 90216](https://api.github.com/repos/elastic/elasticsearch/issues/90216) | Issue ID `1382070206`; `comments=9`; created `2022-09-22T08:45:07Z`, updated `2025-06-10T01:29:11Z` |
| [First Elasticsearch comment sample](https://api.github.com/repos/elastic/elasticsearch/issues/90216/comments?per_page=1) | One record; comment ID `1255266253`; created/updated `2022-09-22T16:25:09Z` |
| [VS Code issue 255749](https://api.github.com/repos/microsoft/vscode/issues/255749) | Issue ID `3228002617`; `comments=33`; created `2025-07-14T09:13:16Z`, updated `2025-09-21T23:25:38Z` |
| [First VS Code comment sample](https://api.github.com/repos/microsoft/vscode/issues/255749/comments?per_page=1) | One record; comment ID `3068588841`; created/updated `2025-07-14T09:19:50Z` |

Four successful JSON reads, **not 42 captured human comments**. The issue counters were not reconciled against full pagination, bots, deleted/edited comments or quoted duplicates. Only one comment per issue was sampled; no source snapshot files/hashes were frozen. Future refreshes can differ.

The issue pages describe genuine reported technical investigations: [Elasticsearch](https://github.com/elastic/elasticsearch/issues/90216), [VS Code](https://github.com/microsoft/vscode/issues/255749). These are not private commercial customer histories. Their participants' claims/workarounds have not been independently verified, and their identities have not been linked into accounts.

Issue `updated_at` is not a body-only edit log. Historical replay cannot assume today's body or current closed state was visible at creation time. This observation motivates conservative source eligibility and explicit missing-history coverage in [contracts](contracts-and-evidence.md) and [evaluation](data-and-evaluation.md).

## Model and benchmark feasibility

The [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) provides a candidate English 384-dimensional semantic encoder and notes input truncation. No artifact was downloaded/pinned, model code installed, vector generated or Windows performance measured. CPU ONNX is an option to test, not a passed resource gate.

[LongMemEval](https://github.com/xiaowu0162/LongMemEval) is a separately labelled supplemental benchmark option with constructed-history components. It was not acquired or run. It cannot replace the real-thread technical-support cohort or actual multi-browser sync tests.

## Limits and next gates

| Area | What remains |
| --- | --- |
| Data volume | Acquire/freeze 200 threads across 20 repositories and >=5,000 deduplicated human messages, with exclusions and coverage |
| Data quality | Independent reviewed ledgers/questions, edit/cutoff handling, source rights/privacy and negative/contradictory examples |
| Product concepts | Genuine vectors, durable buffer, recall, compression, calibrated relevance and session consistency must all be implemented/tested |
| Commercial | Paid willingness-to-pay and handover-effort advantage versus existing tools are unknown |
| Operations | No service/port/model/Windows/tunnel/browser/resource acceptance |

No project installation, source script execution, credential change, external write, customer contact or dataset redistribution occurred. Only Markdown docs/catalogs were changed. Start engineering only after authorization, following [the TDD plan](implementation-plan.md). Study/blog stay deferred until real implementation evidence exists.
