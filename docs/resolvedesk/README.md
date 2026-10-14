# ResolveDesk delivery pack

Day 2: RAG agent with citation grounding. Status on 14 October 2026: implemented chat-first pilot; actual-document functional matrix passed 11 scenarios / 12 turns and all 16 source-page checks, including both live search-recovery paths. Human-adjudicated quality evaluation, browser acceptance, and Windows deployment remain open. The product name is provisional.

ResolveDesk is a conversational RAG product for PostgreSQL support: ask a question, inspect citations, and ask follow-ups in a persistent thread. Every answer retrieves fresh evidence; history supplies conversational context, not authority. The default UI is chat. A knowledge library and optional ticket review/export workspace remain secondary tools. The initial domain is PostgreSQL 16 and 17 backup, restore, connections, and upgrades. Customer demand and willingness to pay remain unvalidated. See [conversational implementation and acceptance](chat.md).

| Day 2 concept | Product responsibility | Detailed specification |
| --- | --- | --- |
| Retrieve context | Find relevant passages with product/version filters | [Architecture](architecture.md), [grounding contracts](contracts-and-grounding.md) |
| Generate answers with sources | Attach passage-level citations to material claims | [Grounding contracts](contracts-and-grounding.md) |
| Flag low confidence | Show evidence gaps, conflicts, and missing environment details | [Product](product.md), [reviewer UI](reviewer-ui.md) |
| Fallback to search | Search approved official sources when indexed evidence is insufficient | [Implementation plan](implementation-plan.md), [operations](operations.md) |

Read in order:

1. [Product](product.md): users, customer outcome, workflow, scope, and acceptance.
2. [Research and sources](research-and-sources.md): market evidence, concrete data sources, and unanswered questions.
3. [Architecture](architecture.md): C4 levels 1–4, runtime sequence, state flow, and deployment.
4. [Contracts and grounding](contracts-and-grounding.md): retrieval, claims, citations, uncertainty, search, and approval rules.
5. [Implementation plan](implementation-plan.md): TDD phases, interfaces, budgets, and gates.
6. [Data and evaluation](data-and-evaluation.md): actual-data acquisition, labels, splits, metrics, and end-to-end scenarios.
7. [Reviewer UI](reviewer-ui.md): premium workbench, evidence interactions, and browser acceptance.
8. [Operations](operations.md): Windows deployment, configuration, retry, backup, and failure drills.
9. [Implementation status](implementation-status.md): current evidence, open decisions, and release blockers.
10. [Latest validation](validation-2026-10-14.md): final concept matrix, real failures/fixes, counts and remaining gates.
11. [Study guide](study-guide.md): understand the concepts by tracing the actual product and tests.
12. [Blog draft](blog.md): a single evidence-based Day 2 narrative.

Product code: [API/worker](../../apps/resolvedesk-api/README.md), [chat UI](../../apps/resolvedesk-web/README.md), and [data](../../data/resolvedesk/README.md). See [current validation evidence](validation-2026-10-14.md), [earlier observations](validation-2026-10-13.md), and [the actual runbook](operations.md).
