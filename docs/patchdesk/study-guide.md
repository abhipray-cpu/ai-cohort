# Study PatchDesk: multi-tool orchestration through a real product

Updated 16 October 2026, after [rigorous validation](validation-2026-10-16.md). This guide follows implemented code, measured failures and limitations—not an imaginary future architecture. You need basic Python functions/classes, JSON, HTTP and async/await; unfamiliar database concepts are explained below. The product is release-blocked despite passing regression tests.

## 1. Start with the customer decision

An agency maintains several client applications. A scanner can identify recorded dependency/advisory matches, but somebody still has to assemble source evidence, reconcile conflicting advice, assess candidate constraints and prepare a reviewable maintenance pack.

PatchDesk organizes that work. Its output is a cited, qualified plan—not a patch, compatibility certificate or exploitation verdict. The input is a captured npm manifest/lockfile pair; the agency's actual deployed runtime is not observed. Keep that distinction in every explanation.

Open the running app at http://127.0.0.1:8003/ with the configured account. Select the real Newman validation project, then inspect Maintenance, Inventory, Conversation, Activity and Tools. Read a finding's exact source snapshot, a pending candidate and a visible gap before reading code. Browser acceptance is still open; this is your manual exploration, not a recorded automated UI pass.

## 2. Trace one complete request

```text
paired files → captured inventory → scoped queued question
  → eligible readers in bounded parallel stages
  → immutable source checkpoints → deterministic reconciliation
  → structured capability plan → additional authorized reads
  → qualified narrative → revision-bound human review → export
```

Optional issue publication is a different branch after review: draft → exact approval → explicit dispatch → receipt or unknown outcome. Investigation itself never grants publication authority.

Read these files in order:

1. [Contracts](../../packages/contracts/src/contracts/patchdesk.py): shapes accepted at trust boundaries.
2. [Inventory](../../apps/patchdesk-api/src/patchdesk_api/inventory.py): package/location identity, graph support and range semantics.
3. [Store](../../apps/patchdesk-api/src/patchdesk_api/store.py): users, project grants, durable jobs and immutable objects.
4. [Registry](../../apps/patchdesk-api/src/patchdesk_api/registry.py): capability routing and current eligibility.
5. [Scheduler](../../apps/patchdesk-api/src/patchdesk_api/scheduler.py): bounded ready work.
6. [Adapters](../../apps/patchdesk-api/src/patchdesk_api/adapters.py): trusted endpoints, transport bounds and source normalization.
7. [Worker](../../apps/patchdesk-api/src/patchdesk_api/worker.py): `Investigation.investigate`, `batch`, `generate`, `report`.
8. [Reconciliation](../../apps/patchdesk-api/src/patchdesk_api/reconcile.py): deterministic decisions and citation/narrative checks.
9. [Publisher](../../apps/patchdesk-api/src/patchdesk_api/publisher.py): effect authorization and uncertain outcomes.
10. [API](../../apps/patchdesk-api/src/patchdesk_api/api.py) / [UI](../../apps/patchdesk-web/src/main.tsx): how the product exposes these boundaries.

## 3. The five requested concepts

| Concept | Where to inspect | What proves it is more than a prompt |
| --- | --- | --- |
| Dynamic tool registry | `Registry.register`, `snapshot`, `set_enabled`; `Investigation.live_registry` | Validated descriptors, duplicate rejection, pinned hash and live-disable negative tests |
| Capability-based routing | `Registry.route`, worker `batch` | Requests name a capability; router selects enabled compatible providers, records a reason and rejects unsupported identities |
| Permission scoping | `Store.scope`, registry `denied`, worker `check`/`allowed`, API session/CSRF, publisher | Cross-project IDs, denied egress, revoked tools and unapproved effects fail in executable tests |
| Parallel execution | `Scheduler.run`, worker stage batches | Dependency checks, global four/provider two bounds, actual overlapping activity and durable sibling results |
| Conflict resolution | `reconcile`, `osv_match`, `github_match`, `matches` | Deterministic identity/range comparisons, preserved assertions and explicit unresolved outcomes |

### Dynamic does not mean arbitrary

A registry is a collection of trusted descriptions of available implementations. It can change without rewriting the planner's capability requests. In this pilot, eight trusted adapters are installed in code; administrators enable/disable them at runtime. Registering a wholly new implementation is a trusted code/deployment step. There is no safe-by-assumption plugin download.

Each run pins a registry snapshot/hash so an old report can explain its selection. Live revocation still wins: pinning provenance cannot preserve permission to execute a now-disabled adapter. Follow `test_registry_revocation_is_live_across_store_configuration` in [hardening tests](../../tests/test_patchdesk_hardening.py).

Exercise: disable a reader in a disposable project and inspect eligible capabilities. Predict whether an already pinned run may dispatch it. Answer: no; live eligibility is checked again. Do not disable tools needed by another person's current run.

### Ask for a capability, not a vendor

“I need advisory detail for this known package/advisory” is a capability request. “Always call OSV” is a concrete provider instruction. PatchDesk has OSV and GitHub detail implementations with the same purpose; safe read failover can choose another eligible provider within the original scope/budget.

Eligibility is semantic too. The publisher-advisory adapter knows Axios; it is not a generic fallback for lodash. Its descriptor has a package allowlist. Read `test_provider_specific_package_support_is_not_a_generic_fallback` in [registry tests](../../tests/test_patchdesk_policy_scheduler.py).

Current ranking is configured priority/stable ID, not learned optimization or health/cost-aware planning. Typed arguments are validated against captured known identities. A syntactically correct request can still be denied.

### Permission is checked at every boundary

Authentication answers “who are you?” Project membership answers “which client's data may you see?” Role grants answer “which operations?” Egress policy answers “which identities/evidence may leave this host?” Publication approval answers “may this exact external effect happen now?” These are different questions.

New projects deny public/model egress. A token existing on the host is not permission for every project. Public-looking package names can still be private; explicit grants govern queries. Server-owned scope is injected; model output cannot select another actor, repository, token or unrestricted URL.

Read `test_disabled_repository_connector_cannot_bypass_registry` in [API/publication tests](../../tests/test_patchdesk_publication_api.py). The test first exposed a real bypass: direct repository import did not consult disabled adapters. The fix routes that operation before dispatch. This is why policy must apply to every path, not just the main agent loop.

### Parallel work needs more than gather

A DAG is a directed acyclic graph: tasks have dependencies, and ready independent tasks may overlap. Advisory details depend on lookup identities; EPSS depends on known CVEs. Release metadata for unrelated packages can overlap.

`Scheduler.run` validates the graph, bounds global/provider concurrency, converts failures to typed outcomes, and saves siblings independently. Extra per-provider gates cover fallback routes so changing the actual upstream does not multiply its quota. The controller reserves counters before work; cancellation and live scope checks happen during dispatch.

Run the scheduler tests. They inject controlled delays/timeouts to prove overlap/limits and survivor persistence. The final real service trace reached four active nodes; no serial benchmark was collected, so “parallel” does not imply a measured speedup percentage.

### Resolve only what evidence can resolve

First normalize package identity, ecosystem and advisory aliases. Different nested versions remain separate installed instances. Imported GitHub data in OSV is not a second independent vote. Unioning aliases prevents duplicate findings; range evaluation determines whether a particular recorded version matches each applicable assertion.

When membership differs or semantics are unknown, preserve assertions and mark investigation required. The model does not average ranges or choose the more persuasive description. Declared/engine metadata checks inform candidates; peer solver/build/test verification remains pending.

Real Axios boundary: publisher says `<= 1.7.9`; reviewed says `>= 1.0.0, < 1.8.2`. Version 1.8.1 is false/true respectively. This is a probe of real source semantics, not a fabricated installed dependency. [Actual-data tests](../../tests/test_patchdesk_actual_data.py) preserve this distinction.

## 4. What makes this an agent?

The deterministic controller performs mandatory source stages, then a real installed-Codex call produces `AgentPlan` with up to four bounded additional capability requests. The application validates identities/arguments/permissions, executes eligible reads and generates a strict `Narrative`. The model chooses useful additional evidence and explains the plan; it does not control networking, credentials or approval.

It is neither a fully autonomous repair bot nor just one unvalidated chatbot reply. Most safety-critical work deliberately stays deterministic. The shared provider runs an isolated workspace with native tools disabled/audited; environment filtering excludes unrelated product/connector secrets. This is not proof of a complete OS sandbox or offline inference.

Schema validation answers “does this object fit the contract?” Citation validation answers “does this field/value exist in this run's snapshot?” Neither proves a paragraph is true. Narrative checks reject unknown finding IDs and selected unsafe guarantees; human review is still necessary for meaning and usefulness.

## 5. Durability, idempotency and partial results

SQLite WAL supports short concurrent transactions; no network request holds a database transaction open. Each operation uses a closed per-operation connection. Immutable objects contain canonical-hashed payloads. The run tracks counters and node snapshots.

A lease gives one worker temporary ownership. A fencing token rejects an old worker after ownership changes. An idempotency key maps repeated client submissions to one operation; it does not promise exactly-once remote writes. Counters are reserved before calls so crashes cannot secretly reset the budget. Resume grants are explicit and bounded; the original deadline remains.

Read [late-timeout tests](../../tests/test_patchdesk_worker.py). A later model failure cannot delete earlier source evidence. The deterministic fallback preserves a partial pack and validation/stage history, continuing the lesson learned in TenderLens.

Follow-ups reuse successful/partial evidence and retain scope. The observed second live turn used zero HTTP and two model calls. Refresh is distinct and intentionally reacquires; new capabilities or retryable failed evidence may need more authorized reads.

## 6. Publication and the uncertain-write problem

Imagine GitHub accepts an issue, then the response is lost. A generic retry might create a duplicate. PatchDesk saves an exact operation marker/body hash before dispatch, disables generic POST retries, and records `outcome_unknown`. Reconciliation checks the configured repository's immutable ID plus exact marker/title/body before recognizing the receipt. It never blindly resends.

Approval binds report/draft revision, payload, target, policy, actor, expiry and connector identity. Changes invalidate it. Restore quarantines pending approvals and invalidates sessions. [Publication tests](../../tests/test_patchdesk_publication_api.py), [transport test](../../tests/test_patchdesk_transport_effect.py) and [backup tests](../../tests/test_patchdesk_operations.py) prove these controlled scenarios. No live issue was created; publisher remains disabled by default.

## 7. Reproduce the evidence

```bash
make patchdesk-test
.venv/bin/python -m pytest tests/test_patchdesk_policy_scheduler.py tests/test_patchdesk_hardening.py -q
.venv/bin/python scripts/validate_patchdesk.py --all
```

The last command requires the ignored actual corpus; see [runbook](operations.md) to acquire a new freeze. Corpus tests skip explicitly when absent. `--live` calls installed Codex and consumes usage; the HTTP smoke also retrieves real public data and creates a dedicated local validation project. Do not enable live writes to learn the concepts.

Current results: 229 Python/four frontend tests; 40 distinct real snapshots/20 repositories/33,909 entries; 64,860 semantic comparisons with zero disagreements after fixes; all 40 deterministic reports partial. The 12-case actual-Codex cohort had five planning/narrative successes, two structured failures and five provider-unavailable outcomes. Live journeys cover Newman, TypeScript and http-server; 60 live multi-user checks pass. These are not held-out accuracy scores. Raw hashes and unsuccessful attempts are retained.

## 8. Check your understanding

- Can a disabled adapter still run because an old registry revision is pinned? **No.** Reproducibility does not override live revocation.
- Does a valid `CapabilityRequest` authorize public egress? **No.** Server-owned grants still apply.
- Does an empty OSV result after a timeout mean unaffected? **No.** Timeout is unavailable/partial, not no-match.
- Are two imported advisory copies two votes? **No.** Preserve lineage and deduplicate aliases.
- Does a published target outside one captured range prove a safe upgrade? **No.** Other advisories and compatibility/reachability remain separate.
- Does a reviewed partial report become complete? **No.** Review acknowledges limitations; it cannot delete them.
- Does a locally installed Codex mean offline inference? **No.** Local service/adapter, remote authenticated inference.
- Does an HTTP/build pass prove premium UI usability? **No.** Browser/accessibility acceptance remains open.

You understand Day 4 when you can explain where the model has discretion, where application policy wins, what survives a failed sibling, and why an honest partial report is more useful than an unsupported all-clear.

## 9. Learn to evaluate the product, not just its code

The larger validation exposed a distinction that every agent engineer needs: **correct presented evidence is not complete evidence**.

The 40 deterministic runs presented 2,309 findings and 5,085 finding/target assessments. All 14,814 exact references, including conflict assertions, resolved. Yet the provider queries reported 3,387 installed-instance/advisory pairs, and only 2,342 were represented when aliases were accounted for:

```text
capture-relative representation = 2,342 / 3,387 = 69.15%
unrepresented pairs            = 1,045
```

All 1,045 lacked a directly captured advisory detail ID in their run. The expanded source freeze contains the installed-query details; the product's fixed selection is the bottleneck. Seventeen runs hit the detail cap. This is not independently adjudicated recall—source IDs can themselves be disputed, aliased or withdrawn—but it is strong evidence that the current workflow misses too much captured source material for release.

Read [audit_patchdesk_runs.py](../../scripts/audit_patchdesk_runs.py). It derives its denominator from captured queries, expands presented aliases and validates references recursively through conflict assertions. It does not accept the report's own finding count as proof of completeness. If the report were the only denominator, omitted findings would disappear from the evaluation too.

Exercise: compare the source-query count, detail count and represented pair count for one npm CLI run and one smaller TypeScript run. Explain why 98 successful source tasks can coexist with incomplete coverage. A successful task says its own query completed; it does not prove the controller asked every required question.

## 10. Understand the independent oracle

Production uses Python's `semantic_version`; [the audit](../../scripts/audit_patchdesk_quality.py) uses [a separate Node interpreter](../../scripts/patchdesk_semver_oracle.cjs) backed by npm's `node-semver`. It compares every recorded graph-edge constraint and real-source advisory range decisions. It never installs or executes a captured project.

There were eight disagreements before correction. Ranges such as `~5.9.0-0` should include stable `5.9.3` but exclude `5.10.0`; they admit prereleases on the specified patch, not arbitrary later prerelease patches. The Python library's tilde expansion was wrong for that form. A failing test preceded explicit expansion, and parser version advanced to 3. The fixed cohort has zero disagreement across 58,590 edge comparisons and 6,270 advisory comparisons.

Do not confuse repeated checks with distinct evidence: those comparisons contain **4,686 distinct version/constraint decisions and 4,007 distinct advisory/package/version decisions**. The advisory checks include actual installed versions and separately labelled boundary probes. A synthetic version probe of real advisory semantics is useful, but it is not an actual installed project instance.

The oracle checks agreement between independent implementations of documented semantics. It does not establish that the upstream vulnerability allegation is true, that every graph edge is independently correct, or that an application is exploitable. Two human reviewers and adjudicated labels remain a separate gate.

## 11. Data volume without inflated confidence

The expanded freeze has 40 unique input hashes and 7,731 distinct installed public version queries. These matter more than repeating one large lockfile many times. Versioned lockfile formats, nested installs, workspace links, peers, optional dependencies and positive/negative advisory membership supply different failure opportunities.

The 33,909 entry count is still development-heavy: 30,580 entries have the development flag. It is public OSS, not a representative paid-client deployment dataset. Snapshot sizes range from 205 to 2,116, so giant/unsupported inventories remain unvalidated. More rows do not compensate for missing data strata.

Repository partitioning prevents one repository crossing development/calibration/held-out groups. It does not prevent advisory leakage: 127 of 165 held-out advisory IDs also occur in development data. Therefore “held-out” names a partition here, not proof of unseen-vulnerability generalization. Report that limitation before claiming performance.

## 12. Failure preservation is a product capability, not a quality pass

The 12 actual-Codex cases all retained partial reports, but only five completed both planning and narrative. Two exhausted structured repair; five recorded provider unavailability. The later recovery probe succeeded separately. Replacing the earlier result with that successful retry would hide reliability evidence.

Separate these questions:

1. Did the job persist evidence and a report?
2. Did the planner satisfy schema, identity, scope and semantic constraints?
3. Did the narrative stage succeed?
4. Was required source coverage complete?
5. Was the result independently judged useful and accurate?

An HTTP 200 or reviewed export does not answer all five. Study the TypeScript follow-up: the API journey finished, but structured repair failed and a fallback report survived. That is correct degradation, not successful AI completion.

Twelve fault tests across actual npm CLI, Axios, Newman and Reveal inputs inject late timeout, malformed JSON and wrong tool hashes. Those are labelled simulations. They test resilience on real input shapes without pretending a naturally occurring outage happened.

## 13. Permission scope includes metadata and recovery

The larger tests found that an actor with all project roles revoked could not read reports, but still saw project names in the list. Confidentiality includes metadata; artifact denial alone was insufficient. The list query now excludes revoked memberships, with a failing test preceding the fix. Sixty live HTTP checks across three real-data projects verify role restrictions, snapshot/export boundaries, revocation and logout.

Likewise, a backup is not just bytes restored. The current recovery drill preserved 457 source/input/report/export objects, invalidated all restored sessions and quarantined publishing. An old backup must not revive an external write approval.

## 14. Reproduce the larger assessment safely

With the captured larger corpus available:

```bash
.venv/bin/python scripts/audit_patchdesk_quality.py var/patchdesk-corpus/20261015-quality40-v2 var/patchdesk-quality/my-new-semver-audit
.venv/bin/python scripts/validate_patchdesk.py --corpus var/patchdesk-corpus/20261015-quality40-v2 --all --session var/patchdesk-evaluation/my-new-runs
.venv/bin/python scripts/audit_patchdesk_runs.py var/patchdesk-corpus/20261015-quality40-v2 var/patchdesk-evaluation/my-new-runs var/patchdesk-quality/my-new-coverage-audit
```

Use new output directories; don't overwrite evidence. Source reacquisition and `--live` are explicit, usage-consuming steps in the [runbook](operations.md). The collector preserves individually bounded lookup batches; an evaluation-wide index is not permission to enlarge production tool responses. Review the previous failed acquisition checkpoint to see that distinction in practice.

Before release, the next engineering work is bounded complete-coverage continuation, safe structured-failure diagnosis and corrective revalidation, then independent labels and browser/Windows/tunnel acceptance. Do not simply increase every budget or remove partial flags to turn the dashboard green.
