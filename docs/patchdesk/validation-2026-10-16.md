# Rigorous validation and release assessment — 16 October 2026

Verdict: **release blocked; implemented pilot only**. The regression suite passes and the larger actual-data assessment is complete, but report coverage and AI-plan reliability do not justify production readiness. All attempts, including outages and failed structured repairs, are retained.

This supersedes the current-readiness assessment in [initial implementation validation](implementation-validation-2026-10-15.md), without rewriting that historical record. Acquisition/cohort runs began on 15 October; completion, connector recovery, regression and documentation were verified on 16 October, Asia/Kolkata.

## 1. Data volume and selection quality

| Measure | Observed |
| --- | ---: |
| Real paired manifest/lockfile snapshots | 40 |
| Distinct public repositories | 20 |
| Distinct input hashes / repository-commit pairs | 40 / 40 |
| Recorded package-location entries | 33,909 |
| Smallest / largest snapshot | 205 / 2,116 entries |
| Distinct installed public package/version queries | 7,731 |
| Additional candidate-version queries | 58 |
| Successful captured advisory/release/threat responses | 778 |
| Full OSV advisory details | 370 |
| npm release records | 306 |
| EPSS responses | 100 |
| GitHub reviewed / publisher records | 1 / 1 |

Repositories: acorn, Axios, async, Express website, Reveal.js, highlight.js, http-server, Backbone, Underscore, jQuery, marked, TypeScript, PDF.js, nock, Node-RED, npm CLI, Newman, Rollup, Commander and JSON Server. The exact repository names, commits, hashes and payloads are in the immutable local freeze.

The first five repositories retain historical release pairs; 15 additional repositories contribute two commit-pinned snapshots selected from their latest root-lockfile commits. Discovery order was declared in the capture script; inaccessible/unsupported repositories were recorded as exclusions. Two snapshots with the same entry count still have distinct input hashes. There was no package installation, target-project script execution or invented input substitution.

Strata: 14 lockfile-v2 / 26 v3 snapshots; 8,650 nested entries; 40 workspace-link entries; 2,183 entries with peer metadata; 1,404 optional entries; 30,580 development entries. These are overlapping, repeated snapshot-level counts—not independent observations. The development-heavy public OSS cohort is not representative of confidential agency applications or deployed runtime exposure. Private registries and >5,000-entry inputs are not validated by this cohort.

Repository-level partition: 20 development snapshots / 8 calibration / 12 held-out, with no repository crossing partitions. However, 127 of the 165 advisory IDs occurring in held-out inputs also occur in development inputs. This is **not** an unseen-advisory generalization benchmark. Inventory conformance was inspected across the cohort; no pristine blind accuracy claim is made.

## 2. Reproducible evidence

Local ignored artifacts:

- Corpus: `var/patchdesk-corpus/20261015-quality40-v2/`; canonical payload SHA-256 `8b4931f95db7acfebed729eb41a2117093d8a83d899a44e57829a6b9613abefb`.
- Input-only checkpoint and failed initial acquisition: `20261015-quality40-inputs/`; the first aggregation exceeded the strict tool-record limit. The corrected evaluation collector preserves separately bounded batches rather than relaxing production limits.
- Source lookup checkpoints: `20261015-quality40-v2-lookup-*/`; all 7,731 installed queries were captured without the former 2,000-query acquisition cap. Each product investigation still has its own limits.
- Independent audit: `var/patchdesk-quality/20261016-final-audit/{report,cases}.json`, including distinct-decision denominators; prior zero-disagreement audit remains in `20261015-40-final-audit/`.
- Forty product runs: `var/patchdesk-evaluation/20261015-quality40-deterministic/`.
- Capture-relative coverage audit: `var/patchdesk-quality/20261015-deterministic-coverage-final/report.json`.
- Twelve actual-Codex runs: `var/patchdesk-evaluation/20261015-quality40-heldout-live/` and `var/patchdesk-quality/20261016-heldout-coverage/report.json`.
- Separate recovery probe: `var/patchdesk-evaluation/20261016-provider-recovery-probe/`.
- Regression JUnit: `var/patchdesk-quality/20261016-regression.xml`.

Hashes cover canonical parsed JSON, not original wire bytes. Run reports include dirty-source hashes and preserve raw captured evidence in scoped SQLite objects. No commit/clean release, external publication or independent human gold set was created. Raw captures remain ignored pending reuse/licensing/privacy review.

## 3. Independent semantic checks

The product uses Python `semantic_version`; the audit uses npm's separately implemented `node-semver` 6.3.1 already installed as a frontend dependency. No audited project's code is loaded. The independent interval interpreter follows the [OSV range specification](https://ossf.github.io/osv-schema/); constraint comparison uses [npm's semver implementation](https://github.com/npm/node-semver). This compares semantics, not the truth of upstream vulnerability allegations.

- **58,590 dependency-edge constraint comparisons:** 58,539 true, 33 false, 18 unknown in the oracle.
- **6,270 advisory-version comparisons:** 3,025 affected / 3,245 unaffected, including 4,213 actual installed-version decisions and 2,057 explicitly labelled boundary probes.
- **64,860 total comparisons; zero disagreements after the fix.** There are **4,686 distinct version/constraint decisions and 4,007 distinct advisory/package/version decisions**. Both edge and advisory comparisons repeat across captured contexts; these are not 64,860 independent samples.
- Zero raw version-identity mismatches in normalized inventory rows. This is narrower than independent verification of every package name/path/graph decision.

Before correction, eight actual tilde-prerelease constraints disagreed: stable versions under ranges such as `~5.9.0-0` were falsely rejected by the Python library's expansion. A failing regression test preceded explicit bounded expansion of that form; parser version is now `patchdesk-inventory-3`. The original eight-disagreement report and subsequent zero-disagreement audit remain separate.

## 4. Product coverage: the main release blocker

All 40 deterministic runs produced durable **partial** reports. They used zero model calls and zero fresh HTTP calls; frozen replay cannot establish provider availability or narrative quality.

| Aggregate | Count |
| --- | ---: |
| Finding records | 2,309 |
| Finding/target candidate assessments | 5,085 |
| Reserved tool actions | 2,778 |
| Exact finding/candidate references | 14,802 |
| Exact references including conflict assertions | 14,814 |
| Provider-reported instance/advisory pairs in supported captured queries | 3,387 |
| Those pairs represented, including aliases | 2,342 |
| Unrepresented pairs | 1,045 |

**Capture-relative representation is 69.15%, not an accuracy/recall score.** Every unrepresented lookup pair lacked a directly captured detail ID in its run. The source corpus itself contains the installed-query details; the product's bounded selection is the bottleneck. Seventeen runs explicitly reached the 60-detail cap, and all 40 reported installed-release metadata sampling. No run was relabelled complete to improve the metric.

Provider query IDs can be aliased, disputed or withdrawn, and unsupported/uncaptured identities are outside this denominator. Therefore this is not human-adjudicated recall. Nevertheless, omitting this much captured source evidence is a material release blocker. Valid exact references establish evidence integrity for presented items, not completeness of what is absent.

Six advisory IDs first encountered in candidate-target queries do not have full detail records in the freeze. They remain additional reported IDs, not fully assessed target safety. All candidates retain pending install/build/test/compatibility verification.

## 5. Actual Codex and repeatability

The preselected 12-case model cohort invoked the real installed Codex CLI against frozen actual sources: **22 calls**, 710 finding records, 1,784 candidate assessments and 4,992 exact references including conflict assertions. Every run retained a durable partial report.

| AI outcome | Cases |
| --- | ---: |
| Planning and narrative stages completed | 5 |
| Structured repair allowance exhausted | 2 |
| Provider unavailable | 5 |

Provider unavailability overlapped an observed usage-limit/review failure, but the product records a nonzero provider exit, not a definitive upstream diagnosis. Do not relabel those five as quality passes. Structured failures are also failures of the AI workflow even though deterministic evidence survives. Current safe logs record error type but not enough detail to independently reconstruct every invalid request; better safe error categorization is an open diagnostic task.

On 16 October a separately recorded http-server recovery probe completed planning/narrative with two real model calls in 46.43 seconds. It retained 147 findings, 596 assessments and 1,486 finding/candidate references. It remained partial. One recovery does not replace the original 12-case result or prove the two structured failures fixed.

## 6. Live API, scope and connectors

Three distinct repositories were exercised through the running API: paired upload, explicit egress, fresh official reads, installed Codex, revision-bound review, gap-preserving Markdown/JSON export and follow-up persistence.

| Real input | First-turn HTTP / model calls | Follow-up HTTP / model calls | Follow-up AI result |
| --- | --- | --- | --- |
| Newman | 104 / 2 | 0 / 2 | Narrative completed; partial |
| TypeScript | 18 / 2 | 0 / 2 | Structured repair exhausted; partial fallback retained |
| http-server | 105 / 2 | 2 / 2 | Provider unavailable; partial fallback retained |

An HTTP journey returning a durable report is functional persistence evidence, not proof that its AI narrative succeeded. The smoke reports preserve stop reasons so those outcomes cannot be collapsed into an all-green claim.

Artifacts: `var/patchdesk-http-smoke/report-1792083946586471000.json`, `report-1792084154367398000.json`, `report-1792084317380093000.json`.

**60 live multi-actor checks passed** across those three actual-data projects: cross-project run/report/snapshot/export denial; reviewer-only read/export permission; analyst/admin/publisher action denial; immediate revocation including project-list metadata; logout invalidation. Temporary audit actors have no remaining test-project roles and were logged out; their randomly generated passwords were not saved. One first attempt hit a validation-script logout-method error after revocation; the corrected runs are separately recorded, not a product outage.

Live connector evidence: `var/patchdesk-quality/20261016-connectors-live/report.json` plus its adjacent source freeze. Configured public GitHub repository import at the pinned Newman commit reproduced the expected input hash and 614 entries. deps.dev and EPSS returned success; KEV returned a complete no-match response for the chosen CVE, not a blanket clean bill. A **labelled injected OSV outage** selected GitHub detail as a secondary provider; the secondary response and snapshot were genuinely live. The outage itself was not naturally observed.

## 7. Regression, faults and recovery

**229 Python tests passed**, including 75 PatchDesk cases and previous-product regressions. Four frontend tests, Ruff and TypeScript/Vite build passed. Dependency deprecation warnings remain.

Twelve additional fault tests use real npm CLI/Axios/Newman/Reveal inputs with explicitly injected late model timeout, malformed model JSON and wrong tool hash. They verify durable sibling evidence, visible partial gaps and stage/validation events. They are robustness simulations, not additional naturally occurring outages or new project snapshots.

Test-first fixes from expanded validation:

1. Truncated frozen lookup could become complete on replay; replay now retains source completeness.
2. Tilde-prerelease expansion rejected actual stable versions; parser-3 tests cover stable bounds and prerelease rules.
3. Revoked membership denied artifacts but leaked project-list metadata; revoked projects are now excluded from lists.

Online backup/restore on 16 October preserved **457 objects**: six inputs, 427 snapshots, ten reports and 14 exports. Restored sessions fell from six to zero; publisher quarantine became true. No publication rows existed. Controlled tests separately cover quarantining approved drafts and rejecting tampered/overwrite restores.

## 8. Remaining gates and next actions

| Gate | Status / required next action |
| --- | --- |
| Complete captured advisory coverage | **Blocked:** replace silent fixed selection with auditable bounded continuation/prioritized coverage; retain unassessed identities and test full denominator |
| Reliable AI workflow | **Blocked:** diagnose the two structured failures with safe reason categories; verify provider availability/recovery separately; fresh corrective cohort must preserve prior failures |
| Independent quality | **Open:** two-reviewer labels, adjudication, task usefulness and supported precision/recall; the oracle is not human gold |
| Browser | **Unavailable:** browser skill setup/troubleshooting returned no browsers again on 16 October; no unsupported driver substitute or fabricated screenshot |
| Windows/Cloudflare | **Unverified:** actual laptop identity/reboot/resource/tunnel acceptance needs that host |
| Actual upgrade verification | **Out of current scope:** no package install/build/test/reachability/deployment performed |
| Live issue publishing | **Unverified and disabled:** requires separate explicit owned-target authority; no third-party issue/PR created |

The browser skill required keeping UI acceptance unverified when no supported connection existed. Build/API checks are not substitutes. Study material and the single blog draft now explain these findings without claiming release readiness.
