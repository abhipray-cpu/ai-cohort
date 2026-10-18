# CatalogBridge delivery pack

**Latest, 18 October:** [local-routing redesign and validation](local-routing-validation-2026-10-18.md). Optional local review-draft scorer, profile-hash binding and UI are implemented; 476 Python tests and eight web tests/build pass. A frozen 600-pair offline challenge yields 101 local exits/one disagreement. The 60-pair live comparison stops on quota after 123 dispatches, with three new unknown liabilities; it is not eligible for a savings claim. The original savings, independent confidence and release gates remain open. Earlier measurements below are historical.

Learning cadence: [study guide](study-guide.md) and [single blog article](blog.md). Both distinguish implemented mechanisms, measured evidence and unpassed acceptance gates.

**Latest, 18 October:** [timeout receipts and repeat-work cost control](receipts-and-repeat-work-2026-10-18.md). Timeout usage preservation, ambiguous-turn guards and durable sanitized receipts; opt-in exact-context draft reuse with UI/provenance and mandatory review. 455 Python tests, eight web tests/build. Three new live calls settle 20,355 tokens; two eligible repeats require zero new calls after worker restart. The original fresh-row savings gate and other release blockers remain open. Earlier paragraphs preserve historical measurements.

**Current implementation, 18 October:** [runtime hardening, cost investigation and confidence qualification](runtime-hardening-2026-10-18.md). Workspace/campaign fail-stop, safe diagnostics, constrained recovery and unverified-calibration rejection are implemented. 432 Python tests, eight web tests/build; 240 new real dispatches, zero new unknown usage. The optional compact profile reduces prompt overhead but does not meet the original routing-token gate. Original liabilities, empirical qualification, identity and full deployment acceptance remain blocked. The paragraphs below are historical milestones.

**Latest, 18 October:** [fresh real-data validation](fresh-real-data-validation-2026-10-18.md). Sixty new offer-disjoint pairs, 400 new query IDs and a bounded 12-case availability replay. Fresh retrieval is 98%; workflow/stress/recovery checks pass. The original model run has 61 unknown-liability attempts; the clean replay gives 12/12 router agreement but only 7.02% token reduction, below target. 416 Python tests and seven web tests/build pass. **Release remains blocked.** The dated paragraphs below retain historical measurements.

Day 7: **cost-aware agent router**. Status, 17 October 2026: **real-data diagnostic executed; release blocked**. Start with [real-data findings](real-data-validation-2026-10-17.md): 40,500 test-pair presentations audited, 1,000 real HTTP queries, 200 actual model calls; retrieval recall@10 98.375%, but the 60-pair router comparison misses the proposed trade-off targets and confidence early exit is unvalidated. Fresh regression: 408 Python tests, seven frontend tests/build. [Original implementation evidence](implementation-validation-2026-10-17.md) and [actual runbook](implementation-and-operations.md). CatalogBridge is a provisional name, not a cleared trademark.

**Latest:** [corrective implementation and targeted validation](fixes-and-targeted-validation-2026-10-17.md). Six red/green behavior checks; 413 Python tests and seven web tests/build pass. Fresh 20-pair comparison yields 19 benchmark-agreeing router proposals (previously eight on the same corrective cases); 1,000-query HTTP replay yields 98.625% retrieval. The 65 fresh real calls reconcile 585,827 tokens. Router token savings still fail; confidence acceptance, effective identity and external release gates remain open. Earlier numbers above are preserved historical evidence, not current runtime results.

CatalogBridge is a supplier-catalog matching desk for electronics retailers and catalog agencies. It recommends which supplier listings refer to an existing catalog product, distinguishes conflicting variants, and leaves unresolved cases for review. The paid outcome to test is less catalog-processing effort at a controlled incorrect-match rate and predictable processing cost. No automatic repricing, inventory updates or product merging in the first release.

| Requested concept | Required observable behavior | Specification |
| --- | --- | --- |
| Token budgeting per task | Reserve allowance before dispatch; include context/schema, retries and escalation; preserve cumulative usage through restart | [Budgets and analytics](budgets-and-analytics.md) |
| Model routing by complexity/cost | Choose between at least two verified available model identities using complexity, measured quality, allowance and applicable rates | [Routing and confidence](routing-and-confidence.md) |
| Early exit on confidence | Stop before another model call only when calibrated acceptance and evidence checks pass; otherwise escalate or abstain | [Routing and confidence](routing-and-confidence.md) |
| Cost per decision analytics | Reconcile attempt costs to batch totals, including failures; compare quality, coverage and review burden alongside cost | [Budgets and analytics](budgets-and-analytics.md) |

## Read in order

1. [Product](product.md): buyer, workflow, scope and commercial experiment.
2. [Research and sources](research-and-sources.md): commercial evidence, dataset suitability and limitations.
3. [Architecture](architecture.md): C4 levels 1–4, sequence, states, deployment and decisions.
4. [Routing and confidence](routing-and-confidence.md): candidate retrieval, complexity, real model selection, calibration and safe exits.
5. [Budgets and analytics](budgets-and-analytics.md): reservations, unknown usage, rate cards and honest unit economics.
6. [Contracts and evidence](contracts-and-evidence.md): strict schemas, proposed API and export lineage.
7. [Permissions and security](permissions-and-security.md): tenant isolation, ingestion, egress and model boundaries.
8. [Data and evaluation](data-and-evaluation.md): actual public data, split hygiene, volume and independent correctness.
9. [Product acceptance](product-acceptance.md): explicit release gates and reproducible evidence.
10. [Reviewer UI](reviewer-ui.md): premium workbench, accessibility and browser journeys.
11. [Implementation plan](implementation-plan.md): dependency-ordered red/green/refactor phases.
12. [Operations](operations.md): old Windows service host, protected Cloudflare entry and recovery.
13. [Implementation status](implementation-status.md): evidence versus plans and current blockers.
14. [Dated source feasibility](source-feasibility-2026-10-17.md): what was inspected, not a validation report.

Original design documents preserve targets where broader than this pilot. The [runbook](implementation-and-operations.md) and [local-routing amendment](local-routing-validation-2026-10-18.md) describe actual interfaces and limits. WDC resources are acquired and tested as recorded; no independently qualified automatic calibration or proven business savings exists. The larger 4,500/600 live campaign and independent adjudication remain incomplete. Earlier product business logic/data remain unchanged. The linked study guide/blog document these limitations rather than claiming acceptance.

Generation must use a port/adapter to the installed Codex CLI, not a direct product model API. The Windows laptop hosts the service; the CLI may still use remote inference. API token-price estimates must not be presented as subscription charges. If two genuine model choices or reliable usage telemetry cannot be verified, the corresponding concept remains blocked—not simulated into a pass.
