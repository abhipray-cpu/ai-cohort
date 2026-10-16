# PatchDesk implementation validation — 15 October 2026

Conclusion: working **implemented pilot**, not production ready. Validation used actual public project/source data and the installed Codex CLI. All five Day 4 concepts exist in application code. Functional checks do not establish finding accuracy, complete coverage, application security or customer value.

## Environment and evidence provenance

macOS 15.7.3 ARM64, Python 3.12 virtualenv, Node 24, loopback API/static UI 8003 and separate worker. Earlier products retain separate stores/processes. Product code uses shared `LocalCodexProvider`, not a direct LLM API. Native alternate tools are disabled/audited; subprocess environment is minimized. This is not OS-level sandbox certification.

Ignored local evidence:

- `var/patchdesk-corpus/20261015-first/`: first four-repository acquisition, preserved.
- `var/patchdesk-corpus/20261015-expanded/`: ten-snapshot freeze, manifest SHA-256 `b3a3da8c41dd868d8021c7e4d992e2df5f615e89688c2269e5b7370ed390b4d5`.
- `var/patchdesk-evaluation/20261015T163429088734/report.json`: final ten-case deterministic frozen replay, current code hashes.
- `var/patchdesk-evaluation/20261015T163445573848/report.json`: final actual-Codex/frozen-source Newman run, current code hashes.
- `var/patchdesk-http-smoke/report-1792082244586296000.json`: final authenticated live-source two-turn workflow, backend code hashes.
- `var/backups/patchdesk-20261015-final/` and `var/patchdesk-restore-20261015-final/`: verified live-store backup and separate restore.

Earlier evaluation/smoke attempts are retained, not overwritten or relabelled as final-code results. Freeze hashes cover canonical parsed JSON, not original HTTP wire bytes. Evaluation hashes cover source files, not a clean committed release; no commit was created. Raw corpus is not committed pending rights/privacy review.

## Actual corpus

| Repository | Ref | Package-location entries |
| --- | --- | ---: |
| npm/cli | v10.8.2 | 1,204 |
| npm/cli | v10.9.0 | 1,336 |
| axios/axios | v1.7.9 | 2,116 |
| axios/axios | v1.8.2 | 2,116 |
| typicode/json-server | v0.17.4 | 1,064 |
| postmanlabs/newman | v6.2.1 | 614 |
| hakimel/reveal.js | 5.1.0 | 896 |
| hakimel/reveal.js | 5.2.1 | 763 |
| postmanlabs/newman | v6.1.2 | 618 |
| typicode/json-server | v0.17.3 | 1,053 |
| Total | Ten snapshots, five repositories | **11,780** |

Each pair records a resolved 40-character commit and canonical input hash. The cohort is convenience-selected public npm/Node tooling, not a representative agency/customer sample. Entry counts include nested/dev/optional dependencies and are not vulnerability or unique-package counts. Six attempted node-semver/npm-package-arg/pacote refs failed acquisition; typed OSError records are retained.

Acquisition recorded 3,524 distinct name/version pairs but queried only the first 2,000 and captured at most 60 full details. There are 67 source captures, including actual Axios OSV/reviewed/publisher records, three release versions and dated EPSS. Missing frozen release/detail/context queries remain unavailable. Replaying does not silently fetch missing evidence or invent no-match responses.

## Regression and test-first fixes

Full Python regression: **215 passed**, including **61 PatchDesk cases** and previous-product/provider tests. Frontend: **4 passed**. Ruff passes; TypeScript/Vite production build passes (JS 274.52 kB / 84.37 kB gzip; CSS 31.63 kB / 7.57 kB gzip). Deprecation warnings remain in PDF/Starlette dependencies; no test failure is hidden.

TDD work began with missing-contract/parser/policy/worker tests and progressed through red → implementation → regression. Real data and negative tests exposed and fixed:

- npm spaced/comma comparators, uppercase legacy names, workspace-link identities and captured graph gaps;
- live registry disablement during a pinned run, wrong adapter identity and provider-specific package support;
- duplicate advisory findings linked by GHSA/CVE aliases;
- source/model sampling incorrectly eligible for complete status;
- repository snapshot API bypassing disabled registry adapters;
- password whitespace normalization, SQLite connections left open and subprocess inheritance of unrelated product secrets;
- remote receipt with wrong content/repository identity and generic retry of ambiguous writes.

Failure injection is labelled simulation, not an actual outage. Tests verify late model timeout preserves sibling snapshots and logs a stage event; invalid model requests get one repair; denied egress never invokes the provider; concurrency/dependencies/cycles/cancellation/fencing/budgets are enforced; private/cross-project access fails; stale/expired/unapproved writes fail; accepted-but-timeout writes become unknown, not resent; restored approvals are quarantined.

## Final ten-case frozen replay

No model egress and no fresh HTTP in this cohort: zero model calls and zero HTTP attempts per case. All exact finding/candidate references validate. All ten runs are **partial**, intentionally—not ten completed-run passes.

| Snapshot | Findings | Gaps | Actions |
| --- | ---: | ---: | ---: |
| npm/cli v10.8.2 | 83 | 64 | 97 |
| npm/cli v10.9.0 | 86 | 63 | 98 |
| Axios v1.7.9 | 66 | 65 | 98 |
| Axios v1.8.2 | 66 | 65 | 98 |
| json-server v0.17.4 | 23 | 55 | 69 |
| Newman v6.2.1 | 28 | 52 | 69 |
| Reveal 5.1.0 | 25 | 56 | 65 |
| Reveal 5.2.1 | 22 | 60 | 70 |
| Newman v6.1.2 | 29 | 52 | 70 |
| json-server v0.17.3 | 27 | 55 | 69 |

These are captured, capped installed-instance/advisory matches—not independently confirmed counts. All ten frozen reports had zero candidate records because required npm metadata for their requested package targets was not captured. That is a dataset coverage gap, not evidence that upgrades do not exist. Source disagreement testing is separately described below.

## Actual model and live service

Frozen-source Newman v6.2.1 with real installed Codex: **50.32 seconds**, 73 actions, two model calls, zero HTTP, 28 findings, zero candidates/conflicts, 55 gaps; partial with exact references valid. Four additional planned capability requests ran within the captured/authorized scope; unavailable evidence stayed unavailable.

Final fresh-source authenticated HTTP journey:

- Unauthenticated project access: 401; invalid CSRF: 403. Built assets served successfully.
- Real Newman manifest/lock imported; scoped package/model egress explicitly enabled in a dedicated validation project.
- First run `ffc086ff474a4ba3a6a145b9142f92c3`: **102 actions, two model calls, 104 HTTP attempts**, 102 saved snapshots; 93 finding records, two affected-range conflict records and 169 finding/target candidate assessments across 16 distinct package/target pairs.
- Independently reran exact reference resolution: **527 finding/candidate references valid**.
- Real node activity reached four simultaneous nodes and ended at zero. Controlled scheduler tests separately assert the two-per-provider limit. No serial timing baseline exists, so no speedup claim is made.
- Partial reasons: 60-detail cap, 12-pair installed-metadata sampling and unresolved ranges. All candidates retain pending verification; 141 assessments reported other advisory IDs at the target. None is called a secure/compatible upgrade.
- Reviewer acknowledged limitations; Markdown and JSON exports retained gaps and hashes.
- Follow-up `0ae1cb9d307f472d985996c9a882e554`: **zero actions, two model calls, zero HTTP**, pinned successful evidence reused. This observation does not promise every future follow-up needs no new reads.

Live adapters exercised: OSV, npm, EPSS and model-selected deps.dev. Reviewed/publisher GitHub records were genuinely acquired and tested in frozen boundary checks; optional repository-input/KEV and live GitHub issue publication are not accepted by this live workflow. No third-party issue/PR was created.

## Conflict evidence, not majority voting

Captured Axios `GHSA-jr5f-v2jv-69x6`: publisher range `<= 1.7.9`, reviewed range `>= 1.0.0, < 1.8.2`; the 1.8.1 boundary evaluates false/true respectively, while 1.8.2 is outside the captured OSV range. This is a **version probe**, not a claim that an Axios dependency at 1.8.1 exists in these ten inputs. Axios's own repository lockfile does not establish that it depends on itself.

The live Newman pack additionally retained aliased lodash source records with differing affected boundaries. Imported/common aliases are deduplicated, but contradictory source membership is not erased. Range disagreement/unknown remains `needs_investigation`; CVSS and EPSS are different metrics, not votes about the same quantity.

## Recovery drill

Online backup passed SQLite integrity and all object/publication payload hashes. Separate restore preserved **214 objects**: two inputs, 204 snapshots, four reports and four exports, plus two projects/four runs. Sessions dropped from two to zero; publisher quarantine became true. No live publication rows existed. A separate controlled test restores an approved draft and verifies its status becomes quarantined; tampered backup restore and existing-target overwrite are rejected.

## What has not passed

Independent gold/held-out precision and recall, expert maintenance usefulness, complete large-pack coverage, actual package install/build/test or reachability, customer time savings, browser/keyboard/contrast/screenshots, Windows/Cloudflare/resource/coexistence drills, live approved issue publishing and full security/load review. Browser bootstrap returned no available browsers after the documented troubleshooting procedure; no screenshots or successful UI journey are fabricated.

The browser skill required leaving visual acceptance unverified when no supported browser was available. Build/HTTP checks were completed without substituting an unsupported browser driver. See [current status](implementation-status.md) and [runbook](operations.md).
