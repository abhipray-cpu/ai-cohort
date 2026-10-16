# Product specification

Status: implemented pilot, 15 October 2026. Name, positioning, pricing and buyer benefit remain hypotheses. Source access and functional workflows are validated; independent product quality and commercial demand are not established. See [implementation evidence](implementation-validation-2026-10-15.md).

## Buyer, job and purchase trigger

Initial buyer: the engineering/maintenance lead of a small software agency responsible for multiple client Node.js applications. The operator is the engineer preparing recurring maintenance work; the reviewer approves scope and client communication. The first pilot is a private agency instance, not a public multi-tenant SaaS launch.

Trigger: a new vulnerability alert, a scheduled client-maintenance window, or preparation of a maintenance proposal. The desired answer is: which recorded dependencies need attention, what change candidates exist, what evidence/constraints conflict, and what needs approval or verification?

Proposed value: reduce repeated advisory research and preparation of evidence-backed client work, while preserving project boundaries and review. Charge by active maintained project/client, potentially with an initial paid assessment. No price, revenue, paid demand or measured time saving is claimed. Customer outreach/publication is not part of implementation authorization.

## Differentiation and competitive test

Do not position this as a novel vulnerability scanner. Dependabot already produces grouped security update PRs; Snyk already offers prioritization/remediation. PatchDesk's hypothesis is that agencies value a client/project-specific review and approval workspace that converts alerts into coherent maintenance deliverables, regardless of which data tools are available.

Compare against an agency's existing Dependabot/Snyk workflow plus a report template, not only an artificially weak manual baseline. If the workflow does not save meaningful review effort or improve evidence/approval clarity, revise the product claim rather than declaring an AI wrapper sellable.

## First-release scope

- npm ecosystem, paired `package.json` and `package-lock.json` v2/v3 snapshots. Parse exact recorded package identities/versions, locations and declared constraints without installing dependencies or running project code.
- Uploaded files or explicitly authorized repository snapshot reads, pinned to input hashes and repository commit when known.
- Multiple logical clients/projects, with server-enforced project membership and per-project connector/egress grants. A shared pilot login alone cannot demonstrate different-user isolation.
- Mandatory inventory/advisory/release-metadata capabilities; optional enrichment from additional advisory, threat and dependency-metadata sources. Missing required capabilities produce a partial plan; missing optional context is visible, not a clean result.
- Cited affected-version matches, dependency paths, candidate release metadata, constraint blockers and a maintenance plan. Candidate generation is conservative and deterministic where possible.
- Conversational follow-ups attached to one project/snapshot, reviewable report revisions, Markdown/JSON exports, and an optional approved GitHub issue publisher scoped to one configured repository.

Workspaces, aliases, links, optional/platform-specific dependencies, peers, bundled packages and private/git/file dependencies must be recognized. Fully resolve supported cases or explicitly mark their graph/matching gaps. Do not silently flatten an unsupported graph and report complete coverage. Lockfile v1, pnpm, Yarn, PyPI, full dependency solving, automated code patches/PRs, merges, deployments and arbitrary test execution are outside v1.

## User journey

1. Select client/project, confirm authorized repository and import manifest/lockfile snapshots. Display inventory hash, provenance and parser coverage.
2. Ask a maintenance question, e.g. “Prepare this project's next security-maintenance batch; explain blockers and client decisions.”
3. Inspect which capabilities are available, permission-limited or unavailable. Start a bounded investigation.
4. See independent tool checks progress in parallel, with dependency stages, outcomes, route reasons and partial evidence.
5. Review findings and conflicting source assertions beside exact evidence. View direct/transitive paths and role labels; a development dependency is not automatically harmless.
6. Review proposed change candidates and verification tasks. Separate advisory fix status from application compatibility, exploitability and deployment status.
7. Edit/approve an exact report revision, export a client pack, or approve an exact issue draft and target. Publishing is never implicit in “investigate.”
8. Ask a follow-up using pinned evidence or explicitly refresh. A new client/project requires a separate context, not a chat instruction that bypasses permissions.

## Output and status semantics

| Section | Required meaning |
| --- | --- |
| Scope | Client/project, input commit/hash, ecosystem/parser coverage and acquisition times |
| Findings | Exact installed version/location, advisory IDs/aliases, affected-range result and evidence |
| Context | Threat signals, source timestamps, environment facts attributed to their source; unknown exposure remains unknown |
| Candidates | Published versions relevant to recorded advisories, engine/declared-range checks, transitive-parent constraints and unresolved blockers |
| Maintenance batches | Proposed work, rationale, impacted findings, owner role and approval/verification requirements |
| Conflicts | Source assertions, policy/reviewer decision, unresolved effects and provenance |
| Limitations | Unsupported graph portions, missing capabilities, caps, source failures and unperformed verification |
| History | Routing, attempts, permission decisions, report review and external publication receipt |

Use `needs_action`, `needs_investigation`, `awaiting_approval`, `verification_pending`, and `verified_for_defined_check` at the appropriate item level. A run's `completed` means defined evidence processing finished, not that the application is secure or patched. A file change or closed issue does not prove remediation.

An advisory-matched installed version establishes a recorded dependency concern, not reachable exploitability. A version patched for one advisory may have other advisories. EPSS is not this client's compromise probability. No unsupported numerical business-risk score or legal/compliance certification is promised.

## Acceptance and commercial measurement

Functional acceptance: actual files → permission-scoped registry/routing → observable parallel checks → reconciled evidence/conflicts → reviewed plan/export; explicit publisher approval is enforced separately. Unavailable providers, revoked permissions or interrupted parallel work retain completed evidence and show gaps.

Proposed commercial experiment: at least ten paired maintenance-preparation tasks with prospective agency users, comparing their normal workflow against PatchDesk on the same evidence. Measure active preparation/review time, missed material advisories, incorrect recommendations, correction effort and willingness to pay. Target at least 30% lower median active effort without worse support/coverage. These are future thresholds, not demonstrated benefits.
