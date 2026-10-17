# Permissions, document privacy and approval safety

Status: scoped auth/authority, egress, evidence/decision validation, isolation and erasure controls implemented with controlled tests; not penetration-reviewed or production-certified. [Actual boundaries](implementation-and-operations.md), [validation](implementation-validation-2026-10-17.md). Contract text/business exceptions are confidential even when a demonstration corpus is public.

## Actor and scope

Use per-user salted password hashes, hashed session tokens, expiry/logout, login rate limits, HttpOnly/SameSite cookies, HTTPS Secure cookies and CSRF/same-origin checks for mutations. Cloudflare Access is an additional perimeter, not object authorization. Bootstrap settings must never reset an existing user's password silently.

| Capability/role | Allowed | Denied by default |
| --- | --- | --- |
| Requester | Own granted cases, document/context intake, clarification responses | Exception approval, role grant, active playbook changes, final sign-off |
| Clause reviewer | Granted requests, evidence, interpretation correction | Unassigned exceptions or hard-block waiver |
| Exception approver | Explicit rule/case-scoped exception decisions within policy | Self-approval, organization policy rewrite, unrelated cases |
| Final reviewer | Exact current packet sign-off after all blockers clear | Signing contracts or clearing unassessed required checks |
| Workspace owner | Membership, policy administration, egress, cancellation and erasure | Silent approval impersonation; ownership alone is not exception authority |
| Auditor | Scoped decision history/verification under explicit grant | Mutating decisions or automatic access to all contract text |

Capabilities may be held together only where the active separation-of-duties policy permits. At least requester and independent exception/final reviewer identities are needed for acceptance; granting one actor all roles does not demonstrate separation. Explicit delegation is bounded, recorded and revocable. No user has case access merely because they have an account.

Enforce workspace, case, source, request, decision, packet and audit visibility on every list/detail/export path. Hidden object existence/names, request counts, cursor gaps and log fields must not leak across scope. Perform authorization before retrieval/context assembly, not after a globally selected top-k. Live authority checks are needed at decision receipt, resume, egress and final publication, not just login.

## Model and data egress

Generation uses the installed shared Codex adapter through a ClauseGate-owned boundary. The local executable may use remote inference; the product is locally hosted, not necessarily offline. Owner must approve model-context egress per workspace/case; default deny. Case participants cannot authorize a new egress destination through text.

Only necessary source passages and typed human facts go into prompts; no bootstrap credentials, audit signing keys, sessions, unrelated cases or hidden benchmark labels. Use an isolated working directory, minimized environment and explicit time/call budgets. No native shell/file/network/MCP execution authority from an uploaded NDA or model proposal. A provider without a verified tool-use audit cannot pass the generation gate. Test shared adapter behavior; do not assume another product's test certifies this product.

Refuse arbitrary URL fetching, private/reserved IPs, redirects to unapproved sources, external PDF references, scripts/macros and archive traversal/bombs. Evaluation acquisition permits only pinned official dataset locations, explicit byte/time limits and checked license notices. Original-source links are evidence references, not automatic crawl targets.

## Human input is also untrusted data

Review comments can contain malicious instructions, incorrect facts or overly broad approvals. Validate schema, length, scope and type; store literal text, render escaped and do not treat it as system prompt or executable policy. Reviewer input changes only its declared field/request. A clarification saying “ignore all other blockers” cannot clear them. Reconfirm consequential actions with precise source/policy/exception scope, not a vague confirmation dialog.

Render uploaded text and model rationale without unsafe HTML. Never autoexecute URLs or commands. Serve source files with safe content types/disposition and CSP; PDF preview must not become arbitrary same-origin active content. Decide sandboxed preview strategy during implementation and test it in the browser.

## Principal threats and required checks

| Threat | Control and test |
| --- | --- |
| Rubber-stamped model rationale | Original passages, visible uncertainty/coverage, explicit independent approval role and rationale |
| Approval of one document applied to another | Full context binding and transactional final fence; same filename is insufficient |
| Overconfident but unsupported interpretation | Source-span checks plus independent semantic labels/qualified review; no model self-confidence bypass |
| Grant revocation or delegation expiry | Live authority revision and time checks at every consequential boundary |
| Decision replay/race/CSRF | Expected revision, request binding, scoped idempotency and same-origin session controls |
| Human/model prompt injection | Treat all text as data, deterministic transitions, isolated audited provider and zero action tools |
| Old restore resurrects approval | New epoch; all restored decisions/final reviews unusable until fresh review; current authority reprovisioning |
| Old restore resurrects erased content | Identity-bound independent current erasure ledger and dependency reconciliation |
| Admin rewrites entire audit history | External checkpoint comparison/hardening; do not claim local hashes defeat a privileged attacker |
| Oversized/unreadable inputs | Hard limits, explicit coverage gaps and refusal of complete clearance |

## Retention and erasure

No automatic deletion policy is enabled without customer approval. Erasure requires preview and typed confirmation, closes over extracted text/findings/context/decisions containing content/packets/caches/model scratch files and export availability. Keep only permitted non-content receipts; hashes/identifiers may themselves be sensitive. Invalidate rather than claim already downloaded artifacts can be recalled.

Deletion from live SQLite is not certified SSD/WAL/backup secure wiping. Govern capture archives, backups, logs and downloaded packets separately. Auditing cannot silently override a deletion obligation; actual retention requirements need authorized policy and qualified review. See [audit/recovery](audit-and-recovery.md).
