# Permission scoping and security design

Status: implemented pilot controls with automated negative tests, not a completed security review. The orchestration agent must not infer authority from a user question, source text, available token or model suggestion. See [validation](implementation-validation-2026-10-15.md) for observed evidence versus open deployment gates.

## Identity and project boundaries

Keep actor identity distinct from client/project identity. Resolve project membership and granted actions server-side on every request, object lookup and tool dispatch. Use immutable object ownership keys: a caller supplying another project's snapshot/report/run ID must receive denial/not-found, even if the artifact exists or is cached.

Proposed roles: administrator (trusted registry/connector setup), analyst (authorized project import/investigate/draft), reviewer (authorized report review/export), publisher (authorized target-specific publication). Roles are project-bound grants, not global powers by default. One actor may hold multiple roles if policy allows; do not falsely claim two-person control unless enforced/configured.

HTTP Basic with one shared password can protect a private instance but cannot demonstrate different-user project isolation. The implementation must add real actor resolution and project membership enforcement for this product, using per-user pilot credentials or a verified identity provider. Store password hashes/secret references appropriately; a client/project selector is not authorization. Do not trust arbitrary proxy identity headers without validated edge/origin setup.

## Capability/permission matrix

| Operation | Required checks |
| --- | --- |
| Import files | Project input-write grant; size/type/path limits; raw-data storage consent |
| Read repository snapshot | Read grant for exact configured repository and allowed paths/ref; resolve/pin commit |
| Query public advisory/release APIs | Investigate grant plus allowed package-identity egress to that provider |
| Send evidence to Codex/model | Separate model-egress consent for minimized project evidence; redact credentials/private fields |
| Read cached source/result | Project access rechecked; cache hit is not a permission bypass |
| Review/edit | Reviewer membership, expected report revision, revalidate material edits |
| Export | Reviewed exact revision; export permission; partial limits retained |
| Approve publication | Publisher grant, exact draft hash/revision/destination, expiry and current policy |
| Dispatch publication | Recheck all grants/approval/policy/connector/destination immediately before effect |
| Configure adapters/credentials | Administrator-controlled allowlist/config change; no model-driven registration |

## Egress is permission too

Private inventories can reveal package names, internal domains and architecture. Do not assume package names are public because they look npm-like. Determine allowed public-query identities from explicit project policy and trusted metadata; unknown/private/git/file/local identities stay local unless separately approved.

Never send a complete lockfile, `.npmrc`, access token, private registry URL, credentials embedded in resolved URLs, arbitrary file content or unrelated project conversation to external providers/model by default. Query payloads are minimized; model context is separately minimized/authorized. Egress-denied matching is `not_checked`/partial, not “no vulnerability.”

Use a strict provider-host allowlist, bounded redirects (prefer none), HTTPS, safe query encoding and explicit endpoint builders. Validate DNS/redirect/IP behavior to prevent SSRF, including loopback, link-local, metadata/private-network addresses and host-rebinding risks. Do not follow arbitrary advisory/repository/registry URLs supplied by a model. Approved repository adapters derive endpoints from configured repository identities, not prompt strings.

No dependency downloads/install scripts or project command execution in v1. `npm audit fix` is not a harmless read: npm documents that it invokes installation behavior. Even `--ignore-scripts` does not make explicitly requested `npm test` safe. See [npm audit documentation](https://docs.npmjs.com/cli/v11/commands/npm-audit/). External test-runner integration is later scope with its own sandbox/network/secret policy.

## Approval-bound publication

Publication intent includes: project ID, immutable repository ID plus current owner/name, connector identity reference, report/draft revision, exact title/body hash, approved labels if any, actor, approval expiry, policy revision and operation UUID. The UI shows destination, content and effect before approval.

Any material edit, destination change, stale report revision, policy/grant revocation, connector replacement or approval expiry invalidates dispatch. Labels/assignees are omitted unless explicitly supported/approved; do not expand the operation after approval. The model cannot mint approval, choose credentials or request a broader OAuth/token grant.

GitHub's [create-issue documentation](https://docs.github.com/en/rest/issues/issues#create-an-issue) specifies Issues write permission for supported fine-grained tokens. Upstream token scope is defense in depth, not the application's authorization policy. A token may have powers beyond the intended operation; the application still enforces exact repository/action/payload limits. Never use a personal broad token to infer authorization for all repositories it can see.

An internal idempotency key prevents duplicate local approvals/outbox rows but does not guarantee GitHub exactly-once writes. Reserve an outbox operation before sending; use an approved operation marker in the body for reconciliation. If the response is lost, mark `outcome_unknown`, inspect the configured repository for the marker and reconcile; do not blindly resend. Secondary duplicates or incomplete search remain unresolved for human review. Revocation prevents unsent work but cannot undo an already accepted remote issue; record the dispatch point and any observed race.

A restored backup must not revive dispatch rights or automatically republish pending/unknown writes. Require reconciliation/reapproval and credential rebinding before enabling the publisher. No deletion/closure of remote issues is automatically authorized as rollback.

## Untrusted text and model isolation

Manifests, package descriptions, advisories, release notes and chat messages are data. They cannot add tools, disable validation, change project identity, access another client or approve a write. Prompts state this boundary, but enforcement lives in contracts/router/policy/scheduler and the restricted provider adapter.

Reuse existing shared isolated-Codex controls only after verifying the chosen CLI version: disable alternate native tools, audit tool-free completion, bound subprocess lifetime and keep secrets out of its environment/prompt where possible. The model receives a sanitized capability view, not an administrative registry or credentials. Runtime restrictions are not a claim of complete OS-level isolation.

## Audit and secret handling

Record actor/project, action/capability, selected adapter/version, safe allow/deny reasons, policy/registry revision, approved payload hash, attempts, outcome, timestamps and external receipt. Redact tokens, authorization headers, resolved-URL userinfo, full private inventories and raw provider stderr from routine logs. Detailed source evidence belongs in authorized storage, not telemetry.

Secrets must live in protected environment/Windows-managed storage with per-service ACLs or an approved secret store. Persist references, not raw tokens, in descriptors/exports. Do not copy personal Codex authentication into source control. Backups containing project evidence require protected storage; they exclude secret material and disable publication on restore.

## Threat/acceptance matrix

| Threat | Required prevention / test |
| --- | --- |
| Cross-client object ID or cache access | Server-side ownership/grants on API, snapshots, reports, exports and cached tool results |
| Capability request broadens permissions | Inject server-owned scope; deny unauthorized fallback |
| Private identity sent to public API/model | Separate provider/model egress grants and observable query redaction tests |
| Permission revoked while queued | Recheck before dispatch and before new dependent operations |
| Source prompt injection | Malicious text cannot alter registry, destination, scope, counters or approval |
| Stale approval reused after edit | Exact content/revision/destination binding and expiry |
| Remote write accepted but response lost | Unknown-outcome state, reconciliation marker, no blind retry |
| Backup replays write | Restore disables publisher/requires reconciliation/reapproval |
| Unexpected native CLI tool | Fail closed on audited unexpected tool events; no acceptance of apparently valid final JSON |
| Host/path/URL injection | Allowlisted endpoint builders, path normalization, no archive traversal or arbitrary fetch |

This matrix remains the release requirement, not a blanket claim that every attack/deployment scenario has passed. Tested simulations and actual scoped integration observations are listed separately in [validation](implementation-validation-2026-10-15.md).
