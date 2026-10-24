# Permissions, sensitive documents and security

Target design, not a security certification. Household records, VINs, addresses,
receipts, payment details and correspondence are private even when programme
sources are public. Local hosting does not remove confidentiality obligations.

Implementation checkpoint: scoped sessions/CSRF, encrypted per-case content,
restricted parsing, owner-only approval/download, one-use invitations, revocation,
export and ledger-first erasure/restore are implemented and tested locally. See
[actual details](implementation-notes.md) and [evidence](implementation-status.md).
Host ACLs, edge policy and comprehensive security/privacy qualification below
remain acceptance work, not implied certifications.

## Identity and household boundaries

Separate product account sessions from the Cloudflare pilot gate. Use a maintained
password-hashing library with current reviewed settings, rate-limited login,
HttpOnly/Secure/SameSite cookies, CSRF protection, session expiry/rotation and
logout revocation. No inherited TenderLens password or shared portfolio sessions.
Initial pilot enrollment is operator-provisioned, not open public registration;
account recovery requires verified identity and revokes existing sessions. No
unverified email reset or operator bypass granting access to arbitrary documents.

Owner controls grants, deletion, monitoring, egress and disclosure approval. Viewer
can read explicitly granted cases; editor may add attributed facts/documents and
request investigations but cannot create owner correspondence packets,
approve/download finalized packets, change grants or renew consent. Invitations
are one-use hashed tokens, case-scoped and expire within 24 hours. Revocation is
checked on each request/job result; a signed-in session is not permanent authority.
Service-operator source administration does not grant a consumer-data browsing role.

Every private route and repository operation derives household/actor scope from
server identity, not request-supplied household IDs. Prevent IDOR through attachments,
search/counts, jobs, notifications, exports and guessed URLs. Shared caches contain
only reviewed public-source facts; private caches are household-scoped and erasable.

## Uploads, parsing and redaction

Quarantine files outside web roots. Validate magic bytes/type, page/image limits,
decompression, parser time/memory and attachment count. Isolate parser/OCR children
with OS-level restrictions and no network or provider credentials; a subprocess
alone is not a sandbox. Determine practical Windows restrictions in a security
spike and block uploads of risky types until demonstrated. Reject active content,
archives and embedded executable attachments; sanitize names and download headers.

Redaction creates a new derivative; originals remain private unless selected.
Burn redactions into final pages and remove recoverable text layers, annotations,
metadata and embedded attachments. Verify final bytes by text extraction and visual
rendering, including image-only sources. A black rectangle or hidden CSS is not
redaction. Owner reviews all attachments after transformation. Redaction failure
blocks disclosure, never silently falls back to the original.

## Network and provider egress

Only registered official hosts/path patterns can be fetched. Revalidate every
redirect/DNS resolution and block loopback/private/link-local/metadata IP ranges,
userinfo, unexpected ports and non-HTTP(S) schemes. Respect source terms, robots,
traffic limits and validators. A document hyperlink is not an approved fetch target.
No arbitrary URL fetch, portal credential use or CAPTCHA bypass.

Analysis approval lists destination/purpose, fields and retention implications.
Default minimum context excludes complete VIN, account/payment identifiers, home
address and unnecessary names. Pass only required vehicle attributes and redacted
repair evidence. Need for any sensitive field requires explicit per-purpose review.
No provider call on upload, login, hover, startup or health probe. External decision
providers require separate credentials/egress approval; another product's approval
does not carry over. Hide private inputs from normal logs, traces and crash reports.

## Storage, retention and deletion

Use restricted service-account file ACLs, full-disk encryption and encrypted backups;
secrets stored outside repo and user content, never in prompts. Backup key recovery
must be tested, not assumed. Proposed case retention defaults to 180 days from last
user activity with a visible exact date; owner may delete earlier. Warn before expiry,
do not extend retention through background monitoring. Monitoring consent lasts at
most its separately selected period and never overrides document deletion.

Deletion immediately tombstones scope, revokes access/consent/approvals and fences
jobs. Purge live private blobs/derivatives/cache within 24 hours; backups expire in
30 days. A separate minimal deletion ledger must survive restores and be reconciled
before serving. Explain these windows and operator access honestly; external copies
cannot be erased by the service. Keep only non-content minimal audit references
for a documented, time-bounded operational purpose; no raw VIN or persistent
document fingerprint as a substitute for deleting the document. The runtime retains
minimal action/ID audit rows and restore barriers; a legally reviewed final audit
retention schedule is not implemented or claimed. Erase content keys
and private hash references when retention expires. Final policy needs privacy review.

## Mandatory abuse/security tests

Two-household access matrices for every endpoint and blob; helper escalation;
stale invite/session/grant; CSRF; upload bombs; PDF embedded content; prompt
injection; path traversal; HTML/script in descriptions; SSRF/rebinding/redirects;
secret/log leakage; incomplete redaction; poisoned source; approval replay; job
completion after deletion; restore resurrection and denial-of-service admission.
No critical/high unresolved finding can be waived by a good model benchmark.
