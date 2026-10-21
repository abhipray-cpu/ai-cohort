# Validation, acceptance and honest completion criteria

The implementation engineering gate passed (785 repository tests, 104 ShelfProof
tests, no skips); actual-data acceptance follows it. See
[status](implementation-status.md) for measured artifacts. Do not revise targets
after seeing a locked result to manufacture a pass. Source fidelity is not
food-safety or legal certification.

## Gate matrix

| Gate | Required evidence | Current status |
| --- | --- | --- |
| G0 feasibility/authority | Published source basis, applicable customer rights, exact payload/destination and finite campaign approval | Public USDA basis and bounded six/96 approval; customer pilot absent |
| G1 deterministic core | Contracts, fact/reference validation, nonregression selector, limits, scope and export correctness | Engineering checks passed; not independent semantic quality |
| G2 durable real processes | Actual API/worker/SQLite/journal, child crashes, cancellation, leases, recovery/restore | Real child/HTTP and recovery checks passed on macOS; target-host/load scenarios still separate |
| G3 real corpus | Measured acquisition/eligible groups, hashes, field mappings, splits and label review | Acquired/audited; 1,000 candidate GTINs, 533 heuristic owner groups; independent labels absent |
| G4 actual provider | Bounded installed-Codex runs, receipts, all requested stages and failed/pending denominators | Bounded fixed-code pass: 6/6 review-ready, all concepts observed, 23 new audited calls, zero new unknowns; cumulative 34/96, original unknown retained; not broad quality acceptance |
| G5 improvement quality | Frozen baseline comparisons, human labels, judge-error analysis and coverage/uncertainty | Not run; reviewers not secured |
| G6 user acceptance | Actual browser intake-to-review/export, responsive/accessibility and two-client isolation | Not run |
| G7 target operations | Actual Windows identity, resource bounds, restart/outage, protected tunnel and restore | Not run |
| G8 commercial evidence | Authorized customer pilot, review time/error tradeoff, cost and willingness to pay | Hypothesis only |

An implemented supervised MVP needs G0–G7 for its declared scope, including a small
qualified quality assessment. Broad held-out statistical claims and commercial
validation need the larger G5/G8 studies. Do not conflate three paid customers or
a 1,000-row benchmark with the definition of every engineering milestone.

## TDD and deterministic invariants

Write and observe the relevant failure before implementation. Use authored providers
for orchestration, never present them as actual inference. Required tests include:

- Unknown/duplicate keys, oversized fields, nonfinite numbers, invented facts,
  invalid references, Unicode quote offsets and missing-source handling.
- Decimal units/bases, serving-versus-pack quantity, null-versus-zero, GTIN leading
  zero preservation and brand-name/owner mapping conflicts.
- Ingredient ordering/omission, hidden numeric claims, prohibited phrases,
  source/draft prompt injection, incomplete claim maps and judge uncertainty.
- Fixed rubric calculation, invalid ratings, forged finding identities, missing plan
  coverage, hard-gate precedence, ties, higher-scoring factual regressions and early exits.
- Maximum two revisions, 16 calls, two attempts/stage, cumulative batch/campaign
  limits through crashes, restart, cancellation and separately authorized resume.
- Owner/producer/reviewer/viewer isolation, maker denial, CSRF/origin checks,
  changed-source/brief/profile invalidation, idempotent retries and conflicting keys.
- Spreadsheet-formula injection, quoting/newlines/Unicode and machine patch round trips;
  draft artifacts cannot be mistaken for approved upload patches.

Use property/permutation tests where appropriate: fact order should not alter
meaning, a higher judge score cannot cancel a blocker, and unavailable calls never
become free/known usage. Report skipped integration checks as incomplete.

## Fault and process tests

Run actual disposable API/worker/provider-child processes. Crash after import commit,
reservation, producer result, judge checkpoint, plan, candidate selection, human
review and export intent. Verify no duplicate invocation/effect, no lost incumbent,
unchanged usage liability and deterministic repeat selection.

Test late success/failure from a stale lease, partial subprocess streams, child timeout,
cancel during generation, parser crash, locked/full disk, journal fsync failure,
fsync-before-DB-commit mismatch and old-snapshot restore. Recovery must preserve
unknown receipts and warnings. Test active-runtime fencing across real processes,
not only a mocked lock. A Windows branch needs real Windows execution.

Controlled reliability target: 1,000 source-backed test-provider row workflows,
2,000 duplicate start/status requests and 100 cancellation/revocation races. These
are engineering workloads, not independent semantic sample sizes.

## Proposed locked quality targets

Measured only after sufficient independent products and actual model execution:

| Measure | Provisional acceptance target |
| --- | --- |
| Tested hard-gate violations in approved patches | Zero; any known violation blocks export |
| Independently observed critical new factual errors | Zero on the locked reviewed subset; disclose uncertainty |
| Material error rate among reviewed eligible patches | <=2% observed and 95% case-level upper bound <=5%; at least 100 independent products, larger sample if needed |
| Eligible source-complete row coverage | >=80% review-ready; publish all manual/needs-data/provider failures separately |
| Required-attribute preservation | 100% for accepted patches in tested cases; no omission-based score improvement |
| Judge critical/material defect detection | >=95% recall on labelled faults; report false positives and uncertainty, separate natural and injected errors |
| Reflection benefit | At least one predeclared paired benefit below, with no critical safety regression |

Reflection must either reduce independently assessed materially erroneous products
by at least five percentage points with a paired 95% interval excluding zero, or
reduce blinded human review effort by at least 20% with no more than +2 percentage
points added material error at the 95% upper bound. Compare against one-shot and
the same-maximum-budget resampling baseline; report cost differences and coverage.
If baseline errors are already rare or the study is underpowered, report insufficient
evidence—not a judge-score surrogate or a post-hoc metric substitution.

These are planned thresholds, not guarantees the product will meet them. A small
development smoke only establishes a narrower operational result.

## Browser-to-export scenarios

Use actual UI and service: login, create isolated client, import/map/freeze a real
record, inspect egress, run the actual provider, inspect all versions/quotes/findings,
review as a different user, export the patch and unresolved summary, then change
source/profile and prove the old approval cannot remain current. Repeat with a
missing required fact, score regression, source injection, partial failure, wrong
workspace, Unicode values and cancelled batch. Test 360 px/mobile keyboard flows,
focus trapping/return, contrast, screen-reader labels and no clipped tables.

Browser absence is a blocker to this evidence, not permission to call API tests
browser E2E. Never use synthetic avatars, fake success metrics or an automatic human
approval to create the appearance of a live accepted product.

## Reporting and final learning cadence

Every report records code/input/rubric/prompt hashes, actual rows and independent
groups, attempted/completed/review-ready/approved counts, baseline arms, all failures,
pending IDs, skips, known/unknown usage and exact commands. Keep mechanical checks,
actual provider execution, independent semantic quality and physical-host acceptance
separate. A batch terminal count is not a pass count.

After implementation and measured validation—or a later explicitly accepted
checkpoint—write the study guide and single blog with measured outcomes, defects
and open limits. No “production-ready” story is part of this docs-only phase.
