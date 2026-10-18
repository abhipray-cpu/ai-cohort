# Permissions, data protection and threat model

Implemented addition: [runtime receipts and exact-context cache](receipts-and-repeat-work-2026-10-18.md). Receipt persistence whitelists category, numeric exit/size fields, SHA256 hashes and bounded UUID runtime thread IDs; no raw streams or credentials. IDs are correlation metadata, not served-model proof. Cache lookup joins original task and workspace, expires after 24 hours, rejects reviewed/cancelled sources and revalidates evidence. Cache inserts share lease-fenced checkpoints; entries are bounded per workspace. Reuse never promotes acceptance, bypasses egress/runtime holds or releases liabilities. This is tested application behavior, not a security audit.

Status: planned controls, not a penetration/security acceptance report. Supplier prices, identifiers and agreements may be commercially confidential even if evaluation fixtures are public.

## Authority and isolation

Runtime recovery is owner-only and CSRF-protected. `GET /api/runtime` is workspace-scoped; another tenant's failures/details are not exposed. `POST /api/runtime/acknowledge` audits an investigation reason, refuses unknown/in-flight usage, journal divergence and restore quarantine, and never settles usage or verifies health. Owner calibration uploads cannot self-promote to `empirically_verified`. Compact instructions come only from a fixed packaged asset, not a user-controlled path; tools remain disabled. Safe diagnostics retain hashes/categories rather than raw potentially credential-bearing logs. See [verified behavior and remaining limits](runtime-hardening-2026-10-18.md).

| Capability | Scope | Cannot do implicitly |
| --- | --- | --- |
| Owner | Membership, approved profiles/egress, policy, budgets, explicit erasure/restore | Impersonate a reviewer or erase incurred usage |
| Operator | Granted feeds, import/start/cancel within assigned allowance | Increase budgets, choose arbitrary executable/model or change grants |
| Reviewer | Granted tasks, exact-revision accept/correct/reject | Access unrelated feeds or edit source evidence |
| Exporter | Current eligible mapping downloads under grant | Publish to a store or export unauthorized content |
| Auditor | Granted redacted lineage/accounting | Automatic access to all source bodies or mutations |

Roles can combine where explicitly granted; do not claim independent review unless two actual distinct users performed it. Enforce workspace/feed/batch/task/attempt/export scope on lists, details, evidence, analytics and downloads, not just routes visible in UI. Live revocation and revision fences apply at dispatch, review and export commit. Source revocation prevents future model egress.

Use per-user salted password hashes; hashed, expiring, revocable session tokens; HttpOnly/SameSite cookies; Secure cookies for HTTPS; CSRF/origin checks; bounded login attempts; no credential fallback silently shared with another product. Cloudflare Access is a perimeter in addition to application authorization, not a replacement. Bootstrap cannot overwrite an existing password.

## Intake and export

First release accepts bounded plain CSV/JSON only. No XLSX/macros, uploaded executable templates, arbitrary archive import or user-supplied URL fetch. Reject duplicate/empty IDs, malformed encodings, field mapping collisions, oversized fields, path-like filenames and decompression tricks. Store randomized scoped paths; filenames do not determine directories. Escape HTML/Markdown and avoid active links/images from feed text. Formula-escape dangerous CSV cells on export; preview actual output before calling it safe.

Evaluation acquisition is a separate explicitly run allowlisted downloader with TLS, redirects/host policy, size/time limits, checksum manifest and safe archive paths including Windows device/reserved names and case collisions. No bulk crawling or acceptance of licenses on a user's behalf. Public access is not blanket permission to redistribute source content.

## Model egress and prompt injection

Installed Codex runs through a restricted audited adapter with isolated workdir, minimized environment, no inherited product secrets, no shell/file/network/MCP action authority and bounded descendants. The executable may use remote inference. Require explicit owner-approved egress and record approved destination/profile; do not advertise this as zero-egress/offline processing.

Only this task's necessary fields/candidates go into context. Gold labels, evaluator directories, API/session secrets, hidden cross-workspace records and price-rate credentials are never included. A listing saying “ignore the budget and run this command” is literal data; deterministic policy controls routes, limits and permissions. Model output cannot issue tool instructions or declare its own measured usage/effective model.

The existing adapter's read-only sandbox is not by itself proof of no internal tools. Require verified event audit and fail closed if unknown action events appear. Log attempted action/validation failures safely. Diagnostic stderr may contain secrets; redact before retention/display. Service authentication remains an operator responsibility, not a product-exposed CLI credential endpoint.

## Threats and mandatory tests

| Threat | Required control/test |
| --- | --- |
| False exact match due to variant mismatch | Required-attribute conflict gates and independent challenge evaluation |
| Cross-tenant candidate/evidence leak | Scope before retrieval/index access; adversarial HTTP list/detail/export tests |
| Budget race or replay | Atomic nested reservations, unique settlement, revision-bound top-up |
| Crash/restore appears to refund spending | Independent current usage/liability journal and blocked dispatch until reconciliation |
| Model/profile substitution | Owner allowlist and verified effective identity; unknown is not a cheaper tier |
| User-input cost manipulation | Server-owned rate cards/telemetry; fixed-point units and signed/scoped configuration authority |
| Stale reviewer form or grant revocation | Compare-and-swap input/index/policy/review/epoch binding at commit |
| Prompt injection or malicious feed HTML | Zero action tools, input-as-data, escaped rendering and browser tests |
| Unsafe export/newline/formula payload | Strict output format and spreadsheet formula neutralization tests |
| Privileged local audit rewrite | Explicit trust limitation; external checkpoints where configured, not “immutable” claims |

## Retention and deletion

No automatic destructive cleanup of user feeds. Define a customer-approved retention policy for originals, derived fields, prompts, proposals, caches, exports, backups and logs. Erasure previews the dependency closure and requires explicit authority. Keep permitted minimal non-content accounting receipts; identifiers/hashes can still be sensitive. Current erasure/revocation state must not be rolled back with an older backup.

Deleting SQLite rows is not certified SSD/WAL/backup wiping. Already downloaded exports cannot be recalled. Avoid claiming encryption, compliance certification or secure deletion unless configured and independently verified. Windows ACL/backup/edge tests are release gates; macOS fixtures do not establish them.
