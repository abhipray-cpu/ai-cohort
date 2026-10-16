# PatchDesk delivery pack

Day 4: multi-tool orchestration agent. Status: **implemented pilot; release blocked**, 16 October 2026. The larger assessment covers 40 real snapshots/20 repositories/33,909 entries. Regression and evidence integrity pass, but captured-source representation is only 69.15% and AI failures remain. See [rigorous validation](validation-2026-10-16.md), [initial implementation evidence](implementation-validation-2026-10-15.md) and [remaining gates](implementation-status.md).

PatchDesk is a provisional product name for a security-maintenance workspace for agencies managing multiple client applications. It turns dependency evidence into client-specific maintenance plans, reviewable reports and explicitly approved work items. It does not promise automatic secure upgrades or replace expert security review.

| Requested concept | Implemented observable behavior | Design |
| --- | --- | --- |
| Dynamic tool registry | Register/disable trusted adapters and schema versions; pin a registry revision per run and recheck live disablement | [Orchestration](orchestration.md) |
| Capability-based routing | Request a capability and select a compatible authorized provider, not an arbitrary hardcoded tool name | [Orchestration](orchestration.md), [contracts](contracts-and-evidence.md) |
| Permission scoping | Client/project/repository/data-egress constraints checked before every dispatch; exact approval for publication | [Permissions](permissions-and-security.md) |
| Parallel execution | Execute independent DAG nodes with bounded concurrency, durable results and deterministic reduction | [Architecture](architecture.md), [orchestration](orchestration.md) |
| Conflict resolution | Reconcile identities, advisory ranges and upgrade constraints using provenance and deterministic policy; retain unresolved conflicts | [Contracts](contracts-and-evidence.md), [evaluation](data-and-evaluation.md) |

Read in order:

1. [Product](product.md): buyer, workflow, differentiation, first-release scope and commercial hypotheses.
2. [Research and sources](research-and-sources.md): primary sources, competitors, data access and limitations.
3. [Architecture](architecture.md): C4 levels 1–4, parallel sequence, state and Windows topology.
4. [Orchestration](orchestration.md): registry, capability routing, DAG scheduling, budgets and conflict reduction.
5. [Permissions and security](permissions-and-security.md): project boundaries, data egress, approvals, revocation and publication safety.
6. [Contracts and evidence](contracts-and-evidence.md): typed boundaries, dependency identity, citations, conflicts and reports.
7. [Data and evaluation](data-and-evaluation.md): actual-data capture, independently reviewed labels, baselines and end-to-end validation.
8. [Reviewer UI](reviewer-ui.md): premium client-maintenance workbench and browser acceptance.
9. [Implementation plan](implementation-plan.md): dependency-ordered TDD phases and implementation mapping.
10. [Operations](operations.md): Windows service target, configuration, credentials, backups and recovery drills.
11. [Implementation status](implementation-status.md): what exists and what remains unverified.
12. [Source feasibility — 15 October](validation-2026-10-15.md): actual HTTP observations, natural advisory disagreement and limits of those checks.

13. [Implementation validation — 15 October](implementation-validation-2026-10-15.md): regression, actual-data, live service and recovery evidence.
14. [Study guide](study-guide.md): learn the five concepts through actual code and experiments.
15. [Single blog draft](blog.md): implementation story, measured evidence and limitations; not externally published.
16. [Rigorous validation — 16 October](validation-2026-10-16.md): larger cohort, independent semantic oracle, coverage denominators, failed model cases and release decision.

Start locally with `make patchdesk-up`, visit http://127.0.0.1:8003/, and sign in with the configured bootstrap account. Use `make patchdesk-down` to stop. [Runbook](operations.md) covers setup, data validation and credentials without exposing their values.
