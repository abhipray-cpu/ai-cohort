# Actual data and evaluation plan

Status: larger-cohort functional/conformance assessment completed; **release blocked** by coverage and AI reliability. Forty commit-pinned snapshots across 20 repositories are frozen, with 7,731 installed-version queries and 778 source captures. Independent-implementation checks cover 64,860 comparisons, not human-adjudicated accuracy. See [16 October assessment](validation-2026-10-16.md). No adjudicated gold or browser acceptance is claimed; earlier feasibility/implementation evidence remains historical.

## Phase 0: acquire and freeze real inputs

1. Select ten historical/current project snapshots across at least five real public npm repositories for feasibility. Include lockfile v2/v3, direct/transitive versions, nested duplicates, workspaces/links, dev/optional flags and varied sizes. Record selection criteria; missing strata remain gaps.
2. Start with the reachable npm CLI v10.8.2 lockfile, resolve its tag to a commit, acquire paired manifests/allowed workspace metadata and hash raw bytes. Verify expected graph edges independently. A package-entry count is not a vulnerability count.
3. For approved public package/version identities, capture OSV query/batch pages and full advisory details, npm release metadata, reviewed/publisher advisories for conflict cases, and dated optional EPSS/KEV context. Preserve per-query mapping/pagination; batch IDs alone are not full ranges.
4. Save raw response bytes and parsed content hashes, approved request fingerprints, acquisition intervals, upstream modified fields/ETags when available, adapter/schema versions, completeness and error records. Retry only within explicit budgets.
5. Capture both sides of the Axios advisory discrepancy and related branch/range values. Verify source lineage and independently label the expected handling. Do not fabricate an advisory conflict if a future refresh reconciles it; retain the earlier hashed snapshot if legally reusable.
6. Publish a manifest only after verifying all file references/hashes and scope. Acquisition uses a new directory, never overwrites a freeze. Partial captures remain partial, with unavailable/denied queries separate from no matches.

Target richer evaluation layout (not all implemented):

```text
data/patchdesk/
  manifests/       dataset/source/terms and split metadata
  gold/            independently adjudicated expected identities/findings/conflicts
  adversarial/     labelled mutations/fault descriptions
var/patchdesk-corpus/<capture>/
  inputs/          original project snapshots and provenance
  responses/       raw upstream responses and acquisition failures
  manifest.json    hashes, versions, counts and coverage
var/patchdesk-evaluation/<session>/
  store/           isolated product database
  report.json      metrics, code hashes, traces and outcomes
```

Keep raw source fixtures ignored until rights/privacy review. Repository/project licenses and data-provider terms govern reuse; public retrieval is not automatic unrestricted redistribution. The task does not authorize customer uploads, token discovery or private-repository inspection.

## Quality cohort and independent labels

After feasibility, target forty project snapshots from at least twenty repositories: twenty development, eight calibration and twelve held-out snapshots. Split by repository, not file, and analyze advisory-family overlap. For claims about generalization to unseen vulnerabilities, group related advisory families across splits or report the leakage limitation; do not pretend holding out one lockfile eliminates advisory leakage. Freeze selection before tuning on held-out results.

Two reviewers independently label a stratified set of package/version/instance decisions, including all critical/conflicting cases. Resolve disagreements with evidence. Record sample denominators/coverage; a single-reviewer evaluation leaves the independent-quality gate open. Model output, agreement between imported feeds, or a second call to the same API cannot be the gold answer.

Gold fields: exact package/location identity, dependency path support, supported/unknown parsing, affected-range membership, alias grouping, source coverage, range/constraint conflict handling, candidate release existence, blocked/unknown checks and acceptable verification tasks. An actual vulnerable dependency match does not supply an exploitation/reachability label for the application.

The corpus must contain real affected and unaffected/control versions. Synthetic version swaps or source outages are labelled robustness tests, never naturally occurring project outcomes. Independent expected version boundaries come from captured advisory semantics and reviewed range logic, not a fabricated “safe” package set.

## Baselines and metrics

Compare: deterministic inventory/advisory checklist, one-shot AI on identical frozen evidence, capability-orchestrated agent, and the agency's normal Dependabot/Snyk/report-template workflow where users can provide it. Keep evidence access and budgets equal or explicitly describe differences. Measure parallel scheduling and model-plan benefit separately; network timing alone does not prove agent intelligence.

| Metric | Definition | Proposed release gate |
| --- | --- | --- |
| Package/path identity | Correct supported instances/edges versus reviewed inventory | 100% in tested supported cases; unsupported portions explicitly flagged |
| Affected-version matching | Correct true/false/unknown on reviewed version decisions | 100% deterministic boundary tests; publish held-out numerator/denominator, no critical false reassurance |
| Finding support | Supported material findings / presented material findings | At least 98%, with human assessment |
| Material finding recall | Recovered adjudicated matches/conflicts / expected material items | At least 95%; report capped/unsupported cases separately |
| Evidence integrity | Exact references resolving within run/project | 100% |
| Coverage honesty | Denied/unavailable/capped results never relabelled no-match | 100% required scenarios |
| Routing | Semantically compatible authorized provider selected; no unauthorized fallback | 100% policy scenarios |
| Parallel correctness | Bounded overlap, dependency readiness and order-independent outcomes | 100% deterministic schedules/fault scenarios |
| Conflict handling | Correct typed policy/qualification on adjudicated disagreements | 100% critical seeded conflicts; publish false-positive count |
| Permission/publication safety | No cross-project access, unapproved writes or stale approval dispatch | Zero violations in required tests; any violation blocks release |
| Maintenance usefulness | Reviewer-accepted actionable tasks / tasks assessed | At least 90%, rubric and denominators published |
| Narrative completion | Complete runs versus partial/failed, stratified by size/coverage | Publish all outcomes; select realistic threshold after feasibility, not after cherry-picking held-out runs |
| Active analyst effort | Paired preparation/review minutes to accepted client pack | Target at least 30% median reduction over ten paired tasks |

These thresholds are provisional, unmeasured and not security guarantees. Show raw counts, critical errors, corrections and uncertainty. Small held-out data cannot justify broad accuracy claims. No benchmark here measures zero-day detection, actual compromise probability, general compatibility or whether a paid customer will buy.

## End-to-end acceptance matrix

| Scenario | Data/setup | Expected result |
| --- | --- | --- |
| Ordinary project | Real pinned manifest/lockfile with supported graph | Evidence-backed matches/candidates, reviewed pack, no invented runtime exposure |
| Nested versions / alias | Real selected graph examples | Correct affected installation locations and actual package identity |
| Workspace/link/peer/optional | Real selected examples | Supported graph semantics or visible parser/constraint gap |
| Private/git/file dependency | Real allowed input or labelled mutation | No unauthorized public/model egress; unknown matching visible |
| Axios disagreement | Captured publisher/reviewed actual records | Both range/severity assertions retained; policy flags affected-range ambiguity |
| Withdrawn/modified advisory | Actual selected records | Status/versioning respected; refresh does not mutate old reports |
| Missing CVE | Actual advisory without published CVE | EPSS not applicable, not zero probability |
| Two detail providers | Actual payloads plus configured registry | Capability selection/failover preserves semantic contract/provenance |
| Registry change/revocation | Controlled trusted configuration | Old revision reproducible; disabled adapter/grant cannot dispatch |
| Parallel overlap | Bounded delayed adapters around frozen real payloads | Independent tasks overlap, limits respected, stable reduction regardless of order |
| One parallel sibling fails | Injected timeout/429/schema fault | Successful sibling checkpoints survive; dependent gaps explicit |
| Later AI timeout | Real-source checkpoints plus failure injection; separate live observations | Deterministic preview/report retained with stage event |
| Cross-project artifact access | Distinct test actors/projects over real public fixtures | Denied API/cache/export/model access, no data leakage |
| Stale/expired approval | Exact draft changed after approval | Dispatch blocked; new approval required |
| Publish response lost | Fake transport accepting request before timeout | Unknown-outcome state and reconciliation; no blind duplicate write |
| Approved live publication | Explicitly authorized owned test repository and credentials | One intended issue with receipt, exact scope/body and audit trail |
| Restore with pending publication | Backup restored to new store | No automatic remote replay; reconciliation/reapproval required |
| UI journey | Browser with real project and partial/conflict cases | Import, chat, routing/parallel evidence, review/export/reload/approval all usable |
| Windows/tunnel | Actual service laptop and protected hostname | Identity/secrets, reboot, cleanup, resource and access acceptance |

Live write acceptance requires a separately authorized test repository/connector. If unavailable, mocked policy/outbox tests can proceed, but the external-write integration gate stays unverified. No unsolicited public issue or upstream project PR is created to make testing easier.

## Reproducibility and reporting

Pin input commits/hashes, source snapshot hashes/terms/times, code commit plus dirty-file hashes, registry/policy/schema/adapter/prompt versions, grants/budgets, actor-role test configuration, provider/host versions and label/split revisions. Save full safe routing/node traces, validation failures, conflict reductions and publication receipts or unknown states.

Report deterministic tests, frozen-source actual-model runs, live-source integration, injected failures, real external writes and expert judgments separately. Preserve unsuccessful attempts. Do not tune prompts/limits until a favourable run and call that a held-out pass. A completed report needs independent quality assessment; a useful partial is not a complete-run pass.

Acquisition/evaluation utilities now refuse existing captures/sessions and bound usage. Actual freeze layout is `var/patchdesk-corpus/<capture>/{payload.json,manifest.json}`: canonical parsed-JSON hashes, not original HTTP-wire byte hashes or complete ETag archives. Evaluation stores `patchdesk.sqlite3`, per-run JSON and `report.json` together in its session directory. This is narrower than the richer archival target above. Commands are in [operations](operations.md); independent labels/metrics remain open.
