# Our AI agent passed its tests. The larger evaluation still blocked release.

Day 4 of our 12-products-in-14-days challenge was multi-tool orchestration. We built PatchDesk: a maintenance desk for software agencies managing multiple client applications.

The product hypothesis is simple. Dependency scanners and update bots already produce alerts. Agencies still need to turn those alerts into a defensible client-specific maintenance plan: recorded dependencies, supporting sources, contradictory advice, candidate constraints, review and approval.

PatchDesk now implements that workflow. But after expanding validation, we are not calling it production-ready. The most useful outcome was discovering why green tests were insufficient.

## The five concepts became application boundaries

The model requests a capability; it does not choose credentials or arbitrary endpoints. A trusted dynamic registry describes available readers and pins their versions per run. Live disablement still wins over historical pinning.

Capability routing selects an enabled compatible provider. OSV and GitHub can provide advisory detail, but semantic eligibility matters: the publisher-advisory adapter currently supports Axios, not every npm package.

Permission scoping separates actor identity, project membership, analyst/reviewer/publisher roles, public-package egress, model egress and exact external-write approval. A token existing on the laptop is not authority for every client.

Parallel execution overlaps independent reads with four active nodes globally and two per actual provider. Dependencies remain ordered, attempts are reserved before work and each successful result is persisted separately.

Conflict resolution is deterministic. Package identity, aliases and affected-version ranges are evaluated in code. Imported advisory copies are not independent votes, and unresolved disagreements remain visible. The model explains a qualified plan; it cannot vote uncertainty away.

The API, worker and SQLite store run locally, with a React workbench. AI generation invokes the installed Codex CLI through our shared adapter, not a direct product LLM API. Local hosting still requires authenticated network inference.

## We expanded the evidence, not just the test counter

The initial ten snapshots from five repositories were feasibility evidence. The larger assessment contains **40 distinct, commit-pinned manifest/lockfile pairs from 20 repositories**, with **33,909 recorded package-location entries**.

The cohort includes npm CLI, Newman, Axios, Node-RED, PDF.js, TypeScript, Rollup, jQuery, marked and other real public repositories. It includes lockfile versions 2 and 3, nested installations, workspace links, peers and optional dependencies. The input hashes are distinct; repeated entry counts are not used to disguise duplicate inputs.

We queried **7,731 distinct installed public package/version pairs**, plus 58 candidate-version pairs. The freeze contains 778 successful advisory, release and threat responses, including 370 complete OSV advisory records.

This is still a development-heavy OSS cohort, not a representative customer deployment sample. Repository partitioning exists, but advisory IDs overlap across partitions. We make no unseen-vulnerability generalization claim.

## An independent implementation found a real parser bug

Production uses Python's semantic-version library. The audit uses npm's independently implemented Node semver library and a separate interval interpreter. Neither installs or executes captured projects.

The larger inputs exposed eight mismatches around tilde prerelease ranges such as `~5.9.0-0`: stable versions that npm accepts were rejected by the Python library's expansion. We wrote a failing regression test, corrected that form and advanced the parser version.

The final audit found zero disagreements across **58,590 dependency-edge comparisons and 6,270 advisory-version comparisons**. Those include positive, negative and explicitly labelled boundary checks. They are repeated observations: there are 4,686 distinct version/constraint decisions and 4,007 distinct advisory/package/version decisions.

Independent implementation agreement is valuable. It is not human-adjudicated vulnerability truth, application exploitability or verified upgrade compatibility.

## Citation integrity passed. Coverage did not.

Across 40 deterministic product runs, all **14,814 exact references**, including conflict assertions, resolved to captured values. The reports contained 2,309 finding records and 5,085 finding/target assessments.

That sounds reassuring until we inspect what was absent.

The provider queries reported 3,387 installed-instance/advisory pairs. After accounting for aliases, the reports represented 2,342: **69.15% capture-relative representation**. The other 1,045 lacked a directly captured detail ID in their run, despite the larger source freeze containing the installed-query details.

This is not an independently adjudicated recall score; upstream query IDs can themselves be disputed or aliased. But it is a material release blocker. The current fixed detail-selection policy omits too much captured evidence. Seventeen runs reached the detail cap, and every run reported metadata sampling. All 40 correctly remained partial.

A citation proves where a presented assertion came from. It says nothing about an important assertion the controller never retrieved. Using the report's own finding count as the only evaluation denominator would have hidden that problem.

## Durable failure is not successful AI completion

We also ran the installed Codex on 12 preselected real snapshots using the frozen sources. All 12 retained durable partial reports. Only five completed both planning and narrative generation. Two exhausted their structured repair allowance; five recorded provider unavailability.

A separate recovery probe on 16 October succeeded with two actual model calls. It did not replace those earlier failures or fix the structured-plan failures by declaration.

The live HTTP journeys made this distinction concrete. Newman, TypeScript and http-server passed through login, explicit egress, source retrieval, review/export and follow-up persistence. But TypeScript's follow-up exhausted structured repair, and http-server's follow-up hit provider unavailability. Both retained qualified fallback reports. API success and AI-stage success are different measurements.

## Scope and recovery needed their own tests

Expanded validation found another real issue: revoked actors could no longer read project artifacts but still saw project names in the project list. Metadata is data. A failing test preceded the fix, and 60 live multi-actor checks across three actual-data projects now verify boundaries, role restrictions, revocation and logout.

We also verified commit-pinned public repository import, actual deps.dev and EPSS reads, and a valid KEV no-match response for a selected CVE. A labelled injected OSV outage routed to a genuinely live GitHub detail response. The secondary read was real; the outage was a controlled simulation.

A fresh backup/restore drill preserved 457 evidence/input/report/export objects, invalidated restored sessions and quarantined publishing. Controlled tests cover restoring approved drafts and rejecting tampered backups.

## The release decision

The full regression now passes **229 Python tests and four frontend tests**, with lint and the production UI build passing. Twelve fault tests exercise real input shapes under injected late timeout, malformed JSON and wrong tool hashes.

PatchDesk is nevertheless **release-blocked**. Required next work includes bounded complete-coverage continuation, safe diagnosis of structured failures, corrective revalidation and independent reviewer labels. Browser acceptance remains unverified because no supported browser connection was available. Actual Windows laptop, protected Cloudflare and resource/reboot acceptance also remain open.

No packages were installed or project scripts executed to claim upgrade verification. No third-party issue was created. Optional publishing remains disabled until separately authorized live acceptance.

The lesson from Day 4 is not that tests are unhelpful. They caught and preserved important boundaries. The lesson is that a live product needs several kinds of evidence: implementation correctness, source completeness, model reliability, human usefulness and operational acceptance.

Green tests can coexist with a red release decision. Reporting that clearly is part of building the product.

---

Local blog draft, updated 16 October 2026; not externally published. [Measured validation](validation-2026-10-16.md), [study guide](study-guide.md), [C4 architecture](architecture.md), [runbook](operations.md). All counts refer to retained evaluation artifacts, not promises about future provider data.
