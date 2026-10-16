# Contracts, dependency identity and evidence

Status: implemented pilot, schema `patchdesk-tool-1`, prompt `patchdesk-1.0`. Strict Pydantic ingress/tool/agent models forbid unknown fields; generated agent schemas are independently validated. Upstream records remain bounded raw snapshots with explicit adapter checks.

The table below is domain vocabulary, not one Python class per row. Scope, inventory, evidence, findings and reports are deterministic JSON objects persisted by `Store`; strict ingress/agent/tool classes live in `packages/contracts/src/contracts/patchdesk.py`. Exact reference validation checks ownership/field/value; narrative validation checks known finding IDs and selected unsafe phrases, **not general entailment**. Material reviewer edits create a new partial revision requiring acknowledgment; a human owns the accuracy review.

## Domain contracts

| Contract | Minimum meaning |
| --- | --- |
| `ProjectScope` | Server-owned client/project/actor IDs, grants, configured repository ID and policy revision |
| `InputRevision` | Manifest/lockfile hashes, uploaded/authorized origin, commit/ref, parser version and coverage |
| `PackageInstance` | Ecosystem, canonical package name, exact recorded version, installation location, source type, role flags and path edges |
| `ToolDescriptor` | Trusted adapter/version, capability/semantic contracts, schemas, permissions, effects, host/health/rate metadata |
| `CapabilityRequest` | Allowlisted capability, approved input artifact/package/CVE IDs and dependency task IDs; no arbitrary code/URL/token |
| `RouteDecision` | Eligible selection/rejections, scope/registry/policy version, safe reason and credential reference hidden from model/UI |
| `TaskResult` | Task/attempt/tool identity, typed outcome, source snapshot refs, completeness, validation warnings and safe error category |
| `SourceSnapshot` | Approved request fingerprint, dataset/provider/upstream lineage, raw payload hash, source-modified/retrieved interval, completeness and adapter version |
| `SourceAssertion` | Subject identity, exact source field/value, range/metric semantics, timestamp and lineage |
| `Conflict` | Category, assertions, affected instances, policy result, unresolved effects and reviewer rationale |
| `EvidenceRef` | Run-owned snapshot ID, bounded JSON field path/row identity and exact value/hash; server-resolved source link |
| `Finding` | Installed instance/path, advisory aliases, deterministic match state, qualified claim and supporting references |
| `UpgradeCandidate` | Published target, advisory checks, declared/engine constraints, other known matches, blocked/unknown verification state |
| `MaintenanceTask` | Purpose, affected findings/candidates, owner role, priority rationale, approval/verification requirements |
| `ReportRevision` | Scope/input/registry/policy/adapter/prompt versions, findings, conflicts, tasks, coverage, limits and stop reason |
| `Review` / `PublicationIntent` | Exact report/draft revision, actor, expected revision, limits acknowledgment; exact approved effect/payload/destination hash |

Scope and credential fields are never accepted as authority from model output. Dynamic generation schemas allow only captured artifact/package/advisory IDs and eligible capabilities. Independent validators check all references and object ownership; schema membership is not authorization.

## Recorded dependency identity

The identity key includes ecosystem, actual package name, exact version and installation location. Do not deduplicate different nested versions into one package row. Preserve root declarations, aliases, workspaces/links, optional/platform flags, peers, bundled/development metadata and source protocol. Distinguish package-entry count, distinct names, distinct name/version tuples and vulnerable installed instances.

For npm aliases, a declared alias is not necessarily the registry package's name. Source-specific scoped-name encoding and semver/prerelease interpretation must be tested. Git/file/private/unresolved versions are not force-matched to a public npm name/version. Workspaces/link resolution cannot escape the captured project scope. Unsupported/missing graph edges remain gaps; they must not yield invented transitive paths.

Manifest constraints and recorded lock versions can disagree; flag staleness rather than silently regenerate the lock. A generic published dependency graph is supplementary context, not proof of this project's actual resolved/deployed dependencies. Repository role/deployment exposure are separate facts; `dev=true` does not prove unreachable runtime impact.

## Advisory matching and aliases

Use deterministic npm-compatible version-range logic for supported inputs, not LLM comparison of version strings. Record exact installed version, source range, matching policy and true/false/unknown result. Handle fixed/introduced/last-affected boundaries, prereleases, withdrawn records and modified timestamps. Unknown syntax/ambiguous package mapping produces unknown, not unaffected.

Normalize GHSA/CVE aliases with provenance; do not double-count a single advisory imported by OSV, GitHub and another aggregator. Distinct vulnerabilities can affect one package. A shared CVE alone must not merge unrelated ecosystem/package ranges or version branches.

The real Axios seed demonstrates different displayed affected ranges and severity. Preserve both assertions with source revision/hash and explain the policy decision. Do not resolve source disagreement by averaging severity or asking the model which page “sounds authoritative.” CVSS version/vector differences and EPSS likelihood are distinct dimensions, not necessarily conflicts.

## Candidate checks, not automatic remediation

Candidate assessment requires a published target version and deterministic checks against the relevant captured advisory ranges. Prefer supported lower-change candidates within declared/runtime constraints, but do not claim globally optimal resolution. Include known newly applicable advisories and unresolved source coverage. A fixed branch for one advisory does not make an old target release safe today.

Direct/transitive remediation differs: changing a nested version may require a parent dependency update, override or solver work. v1 produces proposals/blockers, not a guaranteed regenerated lockfile or solver result. Peer/engine/declared-range compatibility checks are necessary evidence, not proof of successful install, build, tests, runtime behavior or exploit prevention. Verification stays pending until attributable evidence from an authorized future runner/CI is available.

## Result and coverage semantics

`TaskResult.outcome`: success, no_matches, partial, unavailable, denied, unsupported, cancelled, failed. Separate completeness: complete_for_query, truncated, drift_detected, unknown, not_applicable. A provider outage/permission denial/unknown version cannot become `no_matches`.

Coverage is capability × package/version cohort × source, with queried counts, remaining identities and caps. A completed query with no matches is scoped to its provider, date and supported range semantics. An advisory without a CVE makes CVE-only enrichment not applicable, not zero probability. A failed EPSS call is unavailable, not score zero. Prompt omissions are tracked separately from acquisition coverage.

Cache keys include provider, normalized request, source/policy versions and privacy boundary where needed. Shared public raw advisory cache is possible, but project mappings/results remain project-scoped and authorization is rechecked. Freshness/expiry never mutates evidence used by an old reviewed report; explicit refresh creates a new revision and comparison.

## Citation and report validation

1. Validate result identity/schema/counts, request fingerprint and content hashes before checkpoint publication.
2. Resolve every reference to a captured snapshot available to this run/project and exact field value. Preserve evidence whitespace and raw ranges rather than text-normalizing away differences.
3. Independently check package/version/range/path assertions and candidate status using deterministic logic.
4. Validate task finding/candidate IDs and ensure material prose claims have adequate support.
5. Reject unsupported claims of exploitability, compatibility, full remediation or complete coverage. Exact citations alone do not prove natural-language entailment; human review remains required.
6. Keep missing/denied/capped capability coverage, conflicts and verification state attached through export/publication.

Report edits create a new immutable revision, revalidate material claims and preserve parent/source manifests. Review approval belongs to an exact revision, not a mutable project. Markdown/JSON plus printable HTML are first formats; PDF generation and external delivery are deferred. Escape source text; derived source links use approved identities, not model-supplied URLs.

## Events and recovery

Record registry/policy changes, run grants, capability requests/routes, per-node queued/start/finish/denied events, HTTP/model attempts, validation failures/repairs, conflict decisions, cancellation, review/export and publication approval/receipt/unknown outcome. Include safe reason categories, object/adapter/schema/policy versions, elapsed duration and reserved counters.

Later failure must not erase earlier successful sibling results. Run errors supplement, not replace, stage history. Storage failure may prevent new persistence; preserve the last durable checkpoint. Publication recovery follows [approval/outbox policy](permissions-and-security.md), not generic read retry logic.
