# Permissions, privacy and runtime safety

Threat model and requirements, not security acceptance. Inputs can contain personal,
financial, health-related, legally sensitive or malicious material. The system must
not process live customer files before the customer approves purpose, authority,
data handling, retention and model-context egress. Qualified privacy/legal review
is a release dependency, not a checkbox supplied by this document.

## Capability and scope model

| Role | Default capability |
| --- | --- |
| Workspace owner | Manage workspace membership, approved policy/resource/egress settings and operational recovery |
| Analyst | Create/edit granted cases, upload permitted material, request a bounded run, inspect results and draft exports |
| Reviewer | Inspect granted evidence, correct/override and review exact packet revisions within assigned authority |
| Viewer | Read granted redacted case/packet material; no run, policy, review or membership changes |

Every operation also requires current workspace/client/case grants. Ownership is not
automatic permission to read unrelated clients' original artifacts. Raw original
download, reviewed export and sensitive-source access are separate capabilities.
Default maker/checker policy prevents the producing handler from granting a reviewed
label to their own case. Distinct accounts do not prove distinct humans or independent
expert review; benchmark review has additional reviewer qualification requirements.

The policy cannot be edited by a model or a document. Policy activation is an
attributed owner action and cannot retroactively validate old packets. Grant changes
take effect at every read, stage dispatch, result commit, review and download boundary.
Use scoped 404/denial behavior without revealing another client's case existence.

## Source rights and data minimization

The [source-rights gate](data-and-evaluation.md) precedes acquisition and ingestion.
Preserve purpose restrictions and expiry in each source revision. Do not bundle
restricted PDFs, benchmark gold or live customer material in git/test fixtures.
Redaction preview must distinguish raw original, extracted text and redacted model
context. Masking names is best effort and is not proof of legal anonymisation.

Collect only review-relevant material. No claims of universal “seven-year retention”
or other blanket period; customer/source-specific retention is approved separately.
Source expiry/withdrawal fences future processing and export. Erasure previews
include derived spans, proposals, packets, caches and backup retention implications.
Routine logs contain safe identifiers/error codes, not raw complaints or prompts.

## Application and edge boundaries

- Explicit per-user credentials; password hashing, bounded login throttling, hashed
  session tokens, expiry and immediate revocation. No demo/default password in production.
- Same-origin/CSRF protection for mutations, HttpOnly/SameSite cookies, Secure on HTTPS,
  safe upload/download headers and text escaping. No model-generated HTML execution.
- Bind API to loopback. Cloudflare Access protects every application route; unlike
  BuildRelay there is no public webhook exception for this product.
- Download/read authorization is checked at request time, not encoded only in a
  long-lived bearer URL. Artifacts are not a public static directory.
- Bound file bytes, pages, text, collections and parsing time. Reject active/unsupported
  formats, embedded archives and path traversal. Do not execute PDF scripts, attachments,
  shell snippets, URLs, HTML or content referenced by a document.

## Model boundary

Before each call: verify current authority, source rights, exact snapshot, approved
egress grant, remaining call/time allowance and complete serialized input size.
The grant covers a purpose/snapshot, not every future case revision.

Use a restricted installed-Codex adapter with tools/web/MCP/agent spawning disabled
and audited, an isolated working directory and an allowlisted environment without
application credentials. The model gets permitted redacted spans and peer proposals
as data, not evaluator directories, raw originals or access tokens. No extra provider
keys or direct LLM API integration are required by the design.

Prompts are not the enforcement mechanism. Reject unavailable tool auditing or any
observed tool action; stop the run and preserve safe evidence. Source/peer injection
tests attempt secret exfiltration, forged policy, voter impersonation, hidden web
requests and instructions to overwrite consensus. Multiple compromised/agreeing roles
must not acquire authority that one role lacks.

Revocation during inference cannot unsend context already delivered to a remote
model service. Stop future calls, request process cancellation and fence publication;
record the egress event and residual exposure. Local hosting must not be described
as offline inference or a guarantee that customer text never leaves the laptop.

## Threat cases to test

- Cross-tenant case/span/candidate/packet IDs, stale signed downloads and enumeration.
- Candidate/ballot forgery, duplicate role voting, tool-output prompt injection and
  synthesis laundering a party assertion into an unsupported fact.
- Oversized/decompression-intensive PDFs, malformed encodings, Unicode offset confusion,
  duplicate quotes, text corruption, source substitution and unsafe download names.
- Policy/authority changes during a model call or between review and export.
- Snapshot rollback, backup replay, audit editing and a stale worker publishing after restore.
- Accidental full-outcome PDF upload during a supposedly blind benchmark.

Workspace audit chains are not protection against an administrator who controls the
host and rewrites both data and hashes. Disk encryption, service identity/ACLs,
encrypted backups and independently anchored audit retention are production controls
to evaluate; this single laptop is not assumed to provide high availability or
regulatory-grade tamper-proof storage by itself.
