# Implementation status — 16 October 2026

Stage: **implemented pilot; release blocked**. Rigorous larger-cohort validation is complete, with measured coverage and AI-workflow failures. The suite passing does not remove those blockers. [Current assessment](validation-2026-10-16.md) supersedes readiness conclusions from the initial feasibility/implementation phase.

## Delivered

- Strict Pydantic contracts; npm v2/v3 recorded inventory/graph parser, explicit unsupported/gap handling and canonical input hashes.
- Separate SQLite WAL store, per-user salted password hashes, opaque expiring sessions, CSRF, login throttling and project-bound analyst/reviewer/publisher roles.
- Trusted versioned registry, live disablement, capability/provider routing, safe detail failover and provider-specific package eligibility.
- Bounded parallel stages/DAG scheduler, durable per-node evidence, leases/fencing, cumulative budgets, cancellation and explicit bounded resume.
- HTTPS allowlisted/IP-pinned transport, bounded OSV/GitHub/npm/EPSS/KEV/deps.dev readers and configured-repository snapshot input. No project installation/execution.
- Deterministic advisory membership, alias union, source disagreements, candidate constraints, exact citation checks and coverage-preserving partial reports.
- Installed Codex capability planning/narrative generation; restricted native tools, minimized context/environment, validation/repair and deterministic fallback.
- React workbench: project settings/import, scoped conversation, findings/conflicts/evidence, tool/activity views, review and Markdown/JSON/print exports.
- Exact approval-bound optional issue publisher with unknown-outcome reconciliation and no generic write retry. Disabled by default; controlled-transport tests only.
- Independent port/data/processes, Make targets, Windows task installer, rotating service logs and verified SQLite backup/restore with publisher quarantine.
- Forty distinct real snapshots across 20 public repositories, 33,909 entries and 7,731 installed package/version queries; 778 source captures, 64,860 conformance comparisons, 40 deterministic runs and 12 actual-Codex cases.
- 229 Python/four frontend tests pass; three live actual-data API journeys, 60 live multi-user scope checks and actual optional/repository/secondary-provider reads are recorded.

See [rigorous validation](validation-2026-10-16.md) for counts, failures and evidence. [Initial implementation evidence](implementation-validation-2026-10-15.md) remains historical.

## Release gates still open

| Area | Remaining gate |
| --- | --- |
| Quality | Independent two-reviewer gold, precision/recall, task usefulness and analyst-effort baseline remain open; repository split exists but shares advisory IDs |
| Full-size coverage | **Blocked:** 2,342/3,387 captured provider instance/advisory pairs represented (69.15%); all 40 deterministic reports partial |
| AI reliability | **Blocked:** 12-case cohort has five planning/narrative successes, two repair failures and five provider-unavailable outcomes; separate recovery succeeds but does not erase them |
| Candidate verification | No install/build/test/deployment/reachability checks or globally safe/compatible upgrade claim |
| UI | Build/presentation tests passed; browser unavailable, so screenshots, interaction and accessibility acceptance remain unverified |
| Windows/Cloudflare | Actual laptop reboot, service-identity Codex auth, Access/tunnel isolation, resource/coexistence drills not performed |
| External writes | Live owned-repository publication needs separate authority/credentials; none used or created here |
| Optional sources | Live deps.dev/EPSS/KEV reads, exact pinned repository import and live GitHub detail failover verified; primary outage explicitly injected |
| Operational security | No penetration test, full OS sandbox, disk-full acceptance or sustained load/SLO measurement |
| Commercial | Pricing, customer usefulness and willingness to pay remain hypotheses |

Study/blog explain actual implementation and limitations. They are local Markdown, not externally published. No earlier product data or credentials were migrated or replaced.
