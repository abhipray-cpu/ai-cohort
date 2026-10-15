# PropertyBrief delivery pack

Day 3: ReAct planning agent. Status on 15 October 2026: implemented, locally runnable pilot, validated over 3,346 actual public records from 12 buildings. Final actual Codex case completed all eight checks with passing advisory critique; earlier partial/failing runs are preserved. This is not production-readiness or independent accuracy sign-off. PropertyBrief is a provisional name.

PropertyBrief helps small NYC residential acquisition teams investigate a building before progressing an offer. An analyst supplies an address and diligence question; the agent checks official public records, adapts its investigation to findings, challenges its conclusions, and produces a cited investigation pack and prioritized follow-up plan. The primary experience is a conversation attached to a persistent property investigation, with visible progress and evidence review.

| Required concept | Observable product behavior | Specification |
| --- | --- | --- |
| Observe | Ingest typed source results and update evidence and coverage | [Agent loop](agent-loop.md), [contracts](contracts-and-evidence.md) |
| Think | Select the next useful diagnostic check from current findings | [Agent loop](agent-loop.md) |
| Act | Execute an application-controlled read-only source tool | [Architecture](architecture.md), [contracts](contracts-and-evidence.md) |
| Reflect | Revise hypotheses and tasks after each result | [Agent loop](agent-loop.md) |
| Max iteration limit | Enforce action, provider-call, HTTP, and time budgets in code | [Agent loop](agent-loop.md), [operations](operations.md) |
| Self-critique | Challenge evidence, identity, status, completeness, and proposed follow-ups | [Contracts](contracts-and-evidence.md), [evaluation](data-and-evaluation.md) |
| Graceful degradation | Persist completed observations and present a qualified partial pack | [Architecture](architecture.md), [UI](reviewer-ui.md), [operations](operations.md) |

Read in order:

1. [Product](product.md): buyer, commercial hypothesis, workflow, scope, and acceptance.
2. [Research and sources](research-and-sources.md): evidence, competitors, source registry, and feasibility limits.
3. [Architecture](architecture.md): C4 levels 1–4, dynamic flow, state, deployment, and design decisions.
4. [Agent loop](agent-loop.md): adaptive planning, reflection, critique, budgets, and recovery.
5. [Contracts and evidence](contracts-and-evidence.md): tool boundaries, record provenance, interpretation, and review.
6. [Data and evaluation](data-and-evaluation.md): actual-data acquisition, independent labels, metrics, and end-to-end tests.
7. [Reviewer UI](reviewer-ui.md): premium conversation/workbench, evidence interactions, accessibility, and acceptance.
8. [Implementation plan](implementation-plan.md): dependency-ordered TDD phases and release gates.
9. [Operations](operations.md): Windows service target, resource budgets, configuration, backups, and drills.
10. [Implementation status](implementation-status.md): delivered features, explicit scope decisions and remaining gates.
11. [Source feasibility observations](validation-2026-10-14.md): exact sample checks and observed data-quality problems.
12. [Implementation and real-data validation](validation-2026-10-15.md): tests, corpus, actual model runs, failures, fixes and release limits.
13. [Study guide](study-guide.md): learn each concept by tracing the actual product code, tests and records.
14. [Single blog draft](blog.md): the product story, engineering lessons and honest measured outcomes.

Start locally with `make propertybrief-up`, open http://127.0.0.1:8002/, and use the configured credentials. `make propertybrief-status` and `make propertybrief-down` manage only this product. See [operations](operations.md) for Windows alternatives, credentials, backup and deployment acceptance. Implementation-plan targets and commercial/quality thresholds remain acceptance criteria, not measured achievements unless the validation report explicitly says so.
