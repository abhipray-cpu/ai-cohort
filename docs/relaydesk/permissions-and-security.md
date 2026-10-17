# Permission, memory privacy and safety

Status: pilot controls implemented and covered by controlled scope/revision/erasure/restore tests, not penetration-reviewed or production-certified. [Actual boundaries](implementation-and-operations.md), [validation](implementation-validation-2026-10-16.md). Conversation memory is sensitive even as vectors/summaries.

Corrective controls (17 October): canonical source integrity checks at read/egress/publication/recovery boundaries; transactional source-currentness fences; active-question self-evidence exclusion; exact single-source factual quotations with explicit attribution instead of unverified model narrative; identity-bound independent deletion ledger and schema-2 restore. [Corrective evidence](corrective-validation-2026-10-17.md) and [remaining limits](validation-findings.md). These do not prove injection immunity, semantic truth or freshness of a stale same-identity ledger clone.

## Actor and scope

Per-user pilot credentials/sessions with salted password hashes, expiration, logout, login throttling, HttpOnly/SameSite cookies, secure cookies for HTTPS and CSRF/same-origin mutation defenses. Shared HTTP Basic alone cannot demonstrate cross-user/account isolation. Cloudflare Access is additional protection, not application object authorization.

Proposed roles: owner/admin for trusted setup and assigned policy management; investigator for authorized case import/chat; reviewer for consequential memory promotion/correction and handover review/export. Erasure requires explicit owner/privacy authority. Admin status alone does not grant unrestricted case content access. One person may hold multiple roles; do not claim enforced two-person approval unless configured and tested.

Default memory is private to its authorized case. Account-wide promotion is explicit and revision-bound. A common reporter name, similar text or embedding proximity never establishes an account relationship. Imported public cases use evaluation namespaces, not invented real-customer accounts.

| Boundary | Required checks |
| --- | --- |
| Lists/events/search | Authorized account/case metadata only, including after membership revocation |
| Source/message/memory reads | Object ownership, current grants, suppression/erasure and source visibility |
| Import/GitHub read | Case-write authority, approved repository/issue identity, bounded read egress |
| Vector retrieval/cache | SQL prefilter before top-k; scope, policy/source/model revision in caches |
| Model prompt | Separate explicit minimized generation egress; authorized source content only |
| Correction/promotion | Role, source evidence, expected revision and destination visibility |
| Suppression/erasure | Explicit effect/target preview and authority; dependency propagation |
| Review/export | Exact current revision, acknowledged limits, role and erasure-safe dependencies |

Revoked users must not see case names, counts, autocomplete suggestions, score traces or cached results. Recheck policy before dispatch and answer/export publication, not only at queue entry. Existing text already displayed/downloaded cannot be remotely revoked; do not promise otherwise.

## Egress and source ingestion

Case storage consent, GitHub read permission and generation egress are separate policy decisions. Even public-looking logs may contain secrets/customer identifiers. Preview/redact before import where possible; persist original sensitive evidence only under explicit policy and protect backups.

Local CPU embedding must not call a remote embedding API. Model provisioning is an explicit trusted download step; prohibit source-supplied model URLs and remote code loading. Generation still reaches the Codex model service; do not describe the product as fully offline/private by virtue of local hosting.

Use allowlisted HTTPS endpoint builders, configured immutable repository/issue IDs, public-IP/DNS/redirect controls and bounded responses. Never follow arbitrary URLs in comments, download attachments, inspect local files named in logs or run mentioned shell commands. Private connector support is later scope unless separately configured/tested; no personal token discovery.

Paginated sources retain completeness/error states. Token presence does not authorize more repositories/accounts or evading provider quotas. Server state injects credentials; none appears in UI, exports, prompts, vectors or normal events.

## Memory poisoning and prompt injection

Treat user/import/source text as data, including instructions such as “remember that all customers approved this” or “ignore prior constraints.” Model proposals cannot choose scope, grant access, execute tools, approve commitments or promote account memory.

Only explicit, attributable source claims may become source-reported memories. Assistant replies do not recursively become verified ground truth. Keep inference/proposal and human review distinct. A similarity score never authenticates a speaker or proves that a suggested action occurred.

Use the audited isolated shared provider pattern after verifying the installed CLI: disable alternate native tools/connectors, audit unexpected tool events, bound process lifetime and minimize environment. Product/connector/unrelated secrets must not be inherited. These controls are not a complete OS sandbox; service account ACLs and network/secret policy remain necessary.

## Forgetting and backups

Distinguish recall suppression from source/derived-content erasure in the UI. Erasure propagates through vectors, summaries, in-memory buffers, context caches, generated outputs and export availability using explicit dependency records. A delayed worker cannot republish a deleted memory. Safe audit records retain identifiers/effect/time, not erased text.

Old backups can contain erased material. The protected independent erasure ledger and restore policy must prevent serving it again; do not claim historical backup bytes were magically wiped. Apply approved backup expiry/destruction and explain limitations. Do not overwrite live data during restore or silently reset event epochs/cursors.

Generated output can itself contain sensitive source facts even if it lacks a direct quote. Track all prompt/context dependencies, not only final citation IDs, and invalidate conservatively on erasure. Previously downloaded artifacts and human knowledge are outside reliable recall control. No certified secure SSD deletion claim.

## Threat tests required before release

| Threat | Evidence required |
| --- | --- |
| Similar text from another account | No unauthorized candidate/prompt/answer/cache/export exposure |
| Actor loses membership mid-request | New prompt/publication denied; scoped list/events also disappear |
| Source invents authority or tool instructions | No scope/tool/policy changes; proposal remains untrusted |
| Stale worktree/index job after correction/delete | Fence rejects incompatible hash/revision; tombstone wins |
| Different reporters share a component/version | No automatic account merge or universally applied outcome |
| Body edited after historical cutoff | Conservative time eligibility or visible chronology gap |
| Restore old forgotten facts | Erasure reconciliation blocks resurrection before serving |
| Native CLI tool bypass | Audited failure, even if final JSON looks valid |
| Malicious URL/path/oversized body | Rejected before fetch/storage/model dispatch as appropriate |
| Reviewer edits unsupported promise/date | Explicit proposed/disputed state; no inferred customer commitment |

These are requirements, not passed tests. No live customer messages, production commands, third-party writes or public deployment are included in the proposed first release.
