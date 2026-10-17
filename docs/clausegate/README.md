# ClauseGate delivery pack

Day 6: **human-in-the-loop approval agent**. Status, 17 October 2026: **implemented pilot; engineering checks pass, semantic/release gates still blocked**. Latest regression: 346 Python tests and four frontend tests/build. All **61 official development NDAs** complete analysis: **790/1,037 labels match, macro-F1 0.6995, evidence-token F1 0.5370**. Of 637 supported proposals, **162 are wrong**. Actual HTTP stress passes 600 reads during 100 updates; 300 real-source workflow fixtures pass 3,314 assertions. Start with [complete development validation](development-validation-2026-10-17.md), [study guide](study-guide.md), [single blog draft](blog.md) and [runbook](implementation-and-operations.md). Not production/legal-quality accepted.

ClauseGate is a provisional name for an NDA exception-approval desk. It helps an authorized reviewer resolve a specific uncertainty or policy deviation, then resumes only against the exact context approved. The commercial outcome to test is less reviewer effort and approval waiting without increased missed exceptions—not autonomous legal advice or signing.

| Requested concept | Required observable behavior | Design |
| --- | --- | --- |
| Uncertainty detection | Evidence gaps, ambiguous interpretations, conflicting clauses and missing business facts produce explicit reasons; high certainty never bypasses mandatory policy review | [Uncertainty and policy](uncertainty-and-policy.md) |
| Pause | Durable waiting checkpoint releases the worker; dependent finalization stays blocked across restart | [Approval lifecycle](approval-lifecycle.md) |
| Request human input | Scoped request contains a precise question, exact evidence, permitted decisions and authorized assignees | [Lifecycle](approval-lifecycle.md), [UI](reviewer-ui.md) |
| Resume with validated context | Check document, playbook, findings, grant, request/decision revisions, expiry and restore epoch before scheduling and committing continuation | [Contracts](contracts-and-evidence.md), [lifecycle](approval-lifecycle.md) |
| Full audit trail | Transactional domain events connect input, finding, pause, request, decision, resume and export; integrity limitations remain explicit | [Audit and recovery](audit-and-recovery.md) |

## Read in order

1. [Product](product.md): buyer, paid outcome, scope and commercial experiment.
2. [Research and sources](research-and-sources.md): competitors, primary sources, dataset suitability and limits.
3. [Architecture](architecture.md): C4 levels 1–4, sequence, state and Windows deployment.
4. [Uncertainty and policy](uncertainty-and-policy.md): detection, escalation, calibration and safe degradation.
5. [Approval lifecycle](approval-lifecycle.md): durable pause, input, validated continuation and races.
6. [Contracts and evidence](contracts-and-evidence.md): strict typed boundaries and proposed API.
7. [Permissions and security](permissions-and-security.md): roles, egress, prompt injection and authority.
8. [Audit and recovery](audit-and-recovery.md): evidence lineage, tamper evidence, restore and erasure.
9. [Data and evaluation](data-and-evaluation.md): real corpus, held-out labels, baselines and release gates.
10. [Reviewer UI](reviewer-ui.md): premium review workbench and actual browser acceptance.
11. [Implementation plan](implementation-plan.md): dependency-ordered test-driven phases.
12. [Operations](operations.md): resource ceilings and Windows/Cloudflare target.
13. [Implementation status](implementation-status.md): what exists and what is unverified.
14. [Source feasibility — 17 October](validation-2026-10-17.md): inspected documentation, not a product test.

Primary source acquired: ContractNLI, verified as 607 IDs/606 distinct texts and 10,319 labelled pairs. Full-primary mechanical checks pass; lexical screening flags 28 high-overlap pairs, 12 across official splits. Held-out semantic quality and qualified review remain pending. Company playbooks, reviewer authorities and approval histories are **not** supplied by that dataset. CUAD is secondary out-of-domain/extraction material, not another NDA-only approval oracle. See the source and evaluation documents before making any data-volume claim.

Implemented: separate Python API/worker, React web UI and SQLite on macOS loopback **8005**. The old Windows service host remains the deployment-acceptance target. Generation through the shared installed Codex adapter, not a direct model API. The CLI may use remote inference; document/model-context egress needs explicit permission. `make clausegate-up/down/status/test/validate/acceptance` and additive launcher/Windows task/example-route support exist. No actual Windows task or external tunnel was installed.

Current handoff: [implemented runbook](implementation-and-operations.md), [complete development validation](development-validation-2026-10-17.md), [repair campaign](fixes-and-validation-2026-10-17.md), [rejected validation](rigorous-validation-2026-10-17.md), [earlier implementation baseline](implementation-validation-2026-10-17.md), [study guide](study-guide.md) and [single blog draft](blog.md). Original specifications remain targets where broader than the pilot. No external publication/customer outreach was performed.
