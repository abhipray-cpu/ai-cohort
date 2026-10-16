# Source feasibility observations — 15 October 2026

Scope: read-only research before implementation. These observations establish actual data access, not a PatchDesk product test, frozen corpus, security assessment or production-readiness result. No app code, source acquisition script, database or service was created by these checks.

## Direct endpoint checks

Four public URLs were requested with Python's standard HTTPS client, a 25-second timeout and a bounded response read, using a small concurrent pool. All responses parsed as JSON. No API credentials were supplied. Tool results recorded the summaries below; raw responses were not saved/checksummed as a frozen dataset.

| Endpoint | Actual outcome | Observed fields |
| --- | --- | --- |
| [npm CLI v10.8.2 package-lock](https://raw.githubusercontent.com/npm/cli/v10.8.2/package-lock.json) | HTTP 200 | `name=npm`, `version=10.8.2`, `lockfileVersion=3`, **1,204 entries** in `packages` |
| [OSV GHSA record](https://api.osv.dev/v1/vulns/GHSA-jr5f-v2jv-69x6) | HTTP 200 | ID `GHSA-jr5f-v2jv-69x6`, alias `CVE-2025-27152`, **2 affected entries** |
| [npm Axios 1.8.2 metadata](https://registry.npmjs.org/axios/1.8.2) | HTTP 200 | `name=axios`, `version=1.8.2`, distribution integrity field present |
| [EPSS CVE query](https://api.first.org/data/v1/epss?cve=CVE-2025-27152) | HTTP 200 | `status=OK`, **1 record**, score date **2026-10-15** |

The advisory's affected-entry count is not a project vulnerability count. Lockfile entries are not distinct package names or affected instances. The historical Axios release exists; these checks do not recommend it as a current secure/compatible upgrade. EPSS score availability is not evidence of this application's exposure.

The browser/search tool could not retrieve some JSON URLs directly, but the approved standard HTTPS client succeeded. That is a tooling-path observation, not an upstream outage. No sustained quota/parallel speed measurement or complete dependency/advisory match was performed.

## Actual source disagreement inspected

The [Axios publisher advisory](https://github.com/axios/axios/security/advisories/GHSA-jr5f-v2jv-69x6) displayed the 1.x affected range `<=1.7.9` and Moderate severity. The [GitHub reviewed record](https://github.com/advisories/GHSA-jr5f-v2jv-69x6) displayed `>=1.0.0, <1.8.2` and High severity. Both listed patched branches `1.8.2` and `0.30.0` for this advisory.

This supplies a real range disagreement affecting classification of version `1.8.1`, plus a displayed severity disagreement. It does not authorize selecting a winner by source count, treating different feeds as independent, or running an exploit. Original HTML/API snapshots and modification times must be captured before this becomes a durable reproducible fixture; future live pages may change.

## Primary documentation inspected

[OSV batch query](https://google.github.io/osv.dev/post-v1-querybatch/): results include IDs/modified fields, with per-query pagination; full detail retrieval remains separate. [deps.dev API](https://docs.deps.dev/api/v3/): optional public metadata/dependency context, not exact project resolution. [FIRST FAQ](https://www.first.org/epss/faq): public scores and the distinction from organization-specific risk. [npm lockfile format](https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json/): location/version/role/link semantics. [GitHub Issues API](https://docs.github.com/en/rest/issues/issues#create-an-issue): permission-sensitive external write. [GitHub rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api): bounded access required.

Competitor sources: [Dependabot grouping](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-security-updates), [Snyk dependency workflow](https://snyk.io/product/open-source-security-management/). These show existing functionality, not PatchDesk demand.

## Not yet tested

OSV POST batch/pagination at corpus scale; complete package/range/graph reconciliation; npm v2/workspace/alias handling; deps.dev live API; CISA KEV JSON; private-package egress policy; dynamic registry/routing; application parallel scheduling/cancellation; permission enforcement; real Codex generation; report quality; GitHub connector reads/writes; browser UI; Windows/tunnel/reboot/resources; backup/restore; customer effort/pricing.

No publication, repository edit, package install, code execution or customer contact was performed. The next engineering gate is immutable source acquisition and failing contract/parser/policy tests in [implementation plan](implementation-plan.md). Study/blog content is deferred until implementation and validation evidence exists.
