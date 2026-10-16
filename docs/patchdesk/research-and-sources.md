# Research and source registry

Research date: 15 October 2026. See [measured source checks](validation-2026-10-15.md) for the difference between reachable endpoints and an implemented/validated product.

## Competitive evidence

[Dependabot security updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-security-updates) already support grouped update PRs. [Snyk Open Source](https://snyk.io/product/open-source-security-management/) already offers dependency detection, prioritization and remediation. These sources establish competing workflows, not demand for PatchDesk. Proposed agency-specific review/approval/reporting must earn its value against them.

## Primary technical/data sources

| Source | Capability / role | Access and design boundary |
| --- | --- | --- |
| User-authorized manifest/lockfile snapshot | `inventory.read`, `dependency_graph.read` | Authoritative for recorded project inputs; must not be replaced by a generic registry dependency graph |
| [npm lockfile format](https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json/) | Parser specification | Preserve version/location identity, dev/optional/link/workspace semantics; metadata is not proof of deployed runtime use |
| [OSV query/batch API](https://google.github.io/osv.dev/post-v1-querybatch/) | `advisories.lookup` | Batch returns IDs/modified fields, not full advisory detail; retrieve details and follow per-query pagination |
| [OSV advisory record](https://api.osv.dev/v1/vulns/GHSA-jr5f-v2jv-69x6) | Full ranges, aliases and references | Direct GET returned 200; preserve raw JSON and timestamps in future capture |
| [GitHub Advisory Database](https://github.com/advisories/GHSA-jr5f-v2jv-69x6) | `advisories.detail`, reconciliation | Reviewed record and publisher record can differ; this is not independent confirmation when one feed imports the other |
| [Axios publisher advisory](https://github.com/axios/axios/security/advisories/GHSA-jr5f-v2jv-69x6) | Publisher assertion / conflict seed | Its currently displayed range/severity differs from reviewed GitHub record; preserve both |
| [npm registry version metadata](https://registry.npmjs.org/axios/1.8.2) | `releases.lookup`, engine/deprecation metadata | Direct GET returned 200; release existence/integrity is not compatibility or security proof |
| [deps.dev API v3](https://docs.deps.dev/api/v3/) | Optional published dependency/release context | Documentation inspected, endpoint execution not yet tested here; published graph may differ from exact project lockfile |
| [FIRST EPSS API](https://api.first.org/epss/) and [FAQ](https://www.first.org/epss/faq) | `threat.epss` | Free public API; direct CVE query returned a dated record; forecast is not deployment-specific risk |
| [CISA KEV catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) | Optional `threat.known_exploitation` | Catalog identified, JSON retrieval/schema not yet verified in this task; absence is not evidence of no exploitation |
| [GitHub Issues API](https://docs.github.com/en/rest/issues/issues#create-an-issue) | Optional `work_items.publish` | Authenticated external write requiring app approval/policy; docs specify Issues write permission for fine-grained tokens; no issue created |

The [GitHub REST rate-limit reference](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) documents 60 unauthenticated requests/hour for that API. Respect response headers, secondary limits and bounded retries; do not apply that number to every host or assume authenticated access is unlimited.

## Actual project data already accessible

The public [npm CLI v10.8.2 lockfile](https://raw.githubusercontent.com/npm/cli/v10.8.2/package-lock.json) returned HTTP 200 and parsed as lockfile v3 with **1,204 package entries**. Entries include root/workspace/link locations; this is not 1,204 unique vulnerable packages. It is a historical real project input, not evidence of current npm security posture.

This tag URL is a feasibility seed, not an immutable evaluation pin. Resolve to a commit and preserve content hashes before using it as a frozen fixture. Expand to real projects and historical versions selected by documented criteria; do not rely only on a deliberately vulnerable training application.

## Natural conflict suitable for evaluation

For `GHSA-jr5f-v2jv-69x6` / `CVE-2025-27152`, the publisher page displayed 1.x affected versions `<=1.7.9` and Moderate severity. The reviewed GitHub entry displayed `>=1.0.0, <1.8.2` and High severity. Both listed `1.8.2` and `0.30.0` as patched branch releases for this advisory. This makes version `1.8.1` a useful affected-range disagreement case; it is not a recommendation to deploy either historical fixed release today.

The planned policy must distinguish range disagreement from different metrics or version branches. CVSS severity and EPSS likelihood answer different questions; different values are not inherently contradictory. Alias normalization must deduplicate imported copies without claiming a majority of independent sources.

## Data use, privacy and provenance

Preserve repository file licenses, source attribution, terms and acquisition times. Public access is not a blanket redistribution license. [deps.dev terms](https://github.com/google/deps.dev#terms) distinguish generated data and upstream-source terms; FIRST requests attribution. Keep raw fixtures ignored until publication rights and sensitive fields are reviewed.

Private package names, repository paths, internal registry URLs and dependency inventories may themselves be sensitive. Outbound queries must use explicitly approved project/package identities, not arbitrary strings supplied by source text or the model. Do not send complete lockfiles, credentials or private names to public advisory services by default. See [permission/egress policy](permissions-and-security.md).

No package install, project script, exploit execution, repository mutation, CI dispatch or external publication has been performed for this research. Four GET checks establish sample access, not sustained quotas, complete matching, correction accuracy or sellability.
