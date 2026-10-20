# CaseCouncil — Day 9 multi-agent review desk

Learning cadence: [study guide](study-guide.md) and [single blog draft](blog.md).
Prepared at the user's request after acceptance of this delivery checkpoint;
the recorded browser/domain/Windows release limits remain unchanged.

Latest: [20 October real-data continuation](real-data-continuation-2026-10-20.md)
completed all six artifact sets: five fully audited histories and one explicitly
accepted unknown incident; 71 citations rechecked. Browser, domain and target-host
acceptance remain open. Earlier two-complete/one-partial descriptions below are
the historical pre-recovery result, not the current artifact count.

19 October 2026. **Implemented engineering pilot; real-data/release acceptance open.**
Start with the [implemented map and runbook](implementation-and-operations.md) and
[verification record](implementation-validation-2026-10-19.md). Design documents
remain the requirements baseline; implemented interface differences are recorded.
Alternative source: [actual Irish FSPO corpus and local checks](fspo-source-and-validation-2026-10-19.md)
— 132 decisions, 122 usable excerpts. [Approved real-model run](approved-real-data-run-2026-10-19.md):
two full protocols, one partial packet, three pending; unknown-usage hold, not a six-case pass.
The [20 October recovery fix and operator commands](recovery-fix-2026-10-20.md)
are implemented and tested; they do not invent the old missing receipt or clear its hold.
The [MVP readiness record](mvp-readiness-2026-10-20.md) records the latest checks,
strict campaign completion reporting and the operator-policy decision. The user
subsequently approved [bounded irrecoverable incident closure](incident-closure-2026-10-20.md);
the same-store continuation preserves unknown usage rather than fabricating a receipt.
CaseCouncil is a provisional name; trademark/domain availability is not established.

An evidence-backed, adversarial second-review desk for UK motor-insurance complaint
teams. It challenges a proposed complaint resolution before an authorized handler
approves a response. It is not an insurer, ombudsman, legal adviser or autonomous
claim-denial system. Customer value and pricing remain hypotheses.

**UK data feasibility is conditional.** UK FOS reproduction/storage clearance and
authorized customer case files have not been obtained. An alternative Irish
retrospective corpus is now available under its published reuse conditions, but
does not validate UK/prospective performance. Read [research and sources](research-and-sources.md) and
[data and evaluation](data-and-evaluation.md) before promising real-data acceptance.
Irish research acquisition has been performed; no UK clearance request or customer
outreach has been performed.

## Every requested concept is implemented

| Day 9 concept | Required observable behaviour | Specification |
| --- | --- | --- |
| Multiple agents propose solutions | Three isolated, role-bound proposals with alternative issue resolutions and source citations | [Debate protocol](debate-protocol.md) |
| Critique evaluates | Separate, non-voting critic identifies contradictions, missing evidence and unsupported conclusions; findings retain provenance | [Debate protocol](debate-protocol.md) |
| Voting | Three structured, snapshot-bound ballots over a frozen candidate registry; explicit abstention and unavailable states | [Consensus and confidence](consensus-and-confidence.md) |
| Consensus logic | Deterministic fixed-denominator quorum, issue-level agreement, blocker checks and no-consensus outcomes | [Consensus and confidence](consensus-and-confidence.md) |
| Aggregate synthesis with confidence | Source-validated review pack preserves recommendation, dissent, conditions, uncertainty and confidence limitations | [Contracts](contracts-and-evidence.md), [reviewer UI](reviewer-ui.md) |

## Read in order

1. [Product and scope](product-and-scope.md): buyer, workflow, value hypothesis and exclusions.
2. [Research and sources](research-and-sources.md): evidence, competition, source rights and uncertainty.
3. [Architecture](architecture.md): C4 levels 1–4, execution sequence and deployment boundary.
4. [Debate protocol](debate-protocol.md): isolated proposals, critique, revision and resource ceilings.
5. [Consensus and confidence](consensus-and-confidence.md): ballots, dissent, abstention and synthesis gates.
6. [Contracts and evidence](contracts-and-evidence.md): typed boundaries, exact citations and proposed API.
7. [Data and evaluation](data-and-evaluation.md): permission gate, leakage controls, labels and baselines.
8. [Validation and acceptance](validation-and-acceptance.md): engineering, real-data, UI and commercial gates.
9. [Reviewer UI](reviewer-ui.md): premium workbench, accessibility and browser scenarios.
10. [Permissions and security](permissions-and-security.md): tenant isolation, egress and human authority.
11. [Audit and recovery](audit-and-recovery.md): durable checkpoints, stale-context fencing and restore.
12. [Implementation plan](implementation-plan.md): dependency-ordered TDD phases and deliverables.
13. [Operations](operations.md): old Windows laptop, installed Codex and protected Cloudflare deployment.
14. [Implementation status](implementation-status.md): facts versus plans, blockers and next authorization.

Implemented stack: Python/FastAPI/Pydantic, React/TypeScript, independent SQLite
with source BLOBs, a separate usage-authority journal, durable serialized worker,
and an adapter to installed Codex. Loopback port **8008**, with additive Make,
service packaging and protected tunnel configuration. Packaging is not deployment acceptance.
Local hosting is not offline inference; approved model-context egress is required.

The study guide and blog use measured implementation, replay and recovery outcomes,
including unresolved acceptance limits rather than a production-ready success claim.
