# Actual implementation map

22 October 2026. The scoped API/worker/web application is implemented. This is
implementation evidence, not real-data, live-model, consumer or Windows acceptance.
The initial actual public-source integration checkpoint is now
[measured separately](real-data-validation-2026-10-22.md); full acceptance remains
open. Normal deployments still start with an empty programme inventory. Local unit
tests create authored fixtures; the isolated public-source replay uses frozen
official PDFs with explicitly authored case facts.

## Runtime modules

| Actual code | Responsibility |
| --- | --- |
| [Contracts](../../packages/contracts/src/contracts/repairclaim.py), [core](../../apps/repairclaim-api/src/repairclaim_api/core.py) | Bounded facts/anchors/programmes; explicit conditions, mile/km conversion, calendar-month anniversary clamp, VIN conflicts, unknowns, focused questions, separate Decimal outcome categories and reversals |
| [Store](../../apps/repairclaim-api/src/repairclaim_api/store.py), [features](../../apps/repairclaim-api/src/repairclaim_api/features.py) | SQLite scope, sessions/CSRF, revision history, per-case envelope encryption, durable documents/jobs, immutable source captures and reviewed programme activation |
| [Documents](../../apps/repairclaim-api/src/repairclaim_api/documents.py), [parser](../../apps/repairclaim-api/src/repairclaim_api/parser.py), [child](../../apps/repairclaim-api/src/repairclaim_api/parser_child.py) | PDF/JPEG/PNG extraction, OCR, unconfirmed proposals, burned-in redaction, pagination and preview; native macOS sandbox or unprivileged no-network container, parser admission and resource/timeout bounds; no unsafe fallback |
| [Sources](../../apps/repairclaim-api/src/repairclaim_api/sources.py) | Official HTTPS allowlist, public unicast DNS validation, pinned TLS, bounded bytes/redirects/retries and material versus cosmetic change classification |
| [Worker](../../apps/repairclaim-api/src/repairclaim_api/worker.py) | One global durable lease; parse/investigate/render; deterministic checkpoint before optional Codex advice; bounded retries, attempt receipts and validation events; cancellation/erasure/stale-result fences |
| [Jev boundary](../../apps/repairclaim-api/src/repairclaim_api/jev.py) | Optional native Choice/Noul advisory through a pinned gateway, distinct owner egress approval, durable 60-attempt/$0.60 journal, current-price checks, no automatic retries/fallbacks; actual live access blocked, not a quality pass |
| [Free proxy boundary](../../apps/repairclaim-api/src/repairclaim_api/jevmodel.py) | Separately approved jevmodel.org route, documented alias with returned-version check, 90,000-token/16-attempt ledger, honest non-USD receipts; eight-case API/worker smoke passed with three retained advisory disagreements; no UI or autonomous-eligibility claim |
| [Packets](../../apps/repairclaim-api/src/repairclaim_api/packets.py) | Recipient-specific drafts, response-linked follow-up, explicit attachment policy/order/redactions, queued rendering, PDF/manifest ZIP, exact fingerprint approval (24 hours), revoke and freshness-checked download |
| [Continuity](../../apps/repairclaim-api/src/repairclaim_api/continuity.py) | Separate retrospective consent, old/new findings, deduplicated in-app alerts, response reasons/frozen comparisons, manual-send attribution, outcomes and provenance-labelled reminders |
| [Privacy](../../apps/repairclaim-api/src/repairclaim_api/privacy.py), [operations](../../apps/repairclaim-api/src/repairclaim_api/operations.py) | One-use invitations/grants, export, case/account erasure, durable deletion ledger, key deletion, retention/orphan cleanup, managed backup expiry, encrypted backups and quarantined new-directory restore |
| [API](../../apps/repairclaim-api/src/repairclaim_api/api.py), [routes](../../apps/repairclaim-api/src/repairclaim_api/routes.py) | Same-origin UI/API; host/origin/session/CSRF checks, bounded JSON/binary uploads, authenticated casework, image-only previews and authorized ZIP downloads |
| [Web](../../apps/repairclaim-web/src/main.tsx), [UI rules](../../apps/repairclaim-web/src/domain.ts) | Responsive garage and workspace: Overview, Documents & facts, Coverage, Packet desk, Timeline, Privacy; empty/partial/stale/read-only handling |
| [CLI](../../apps/repairclaim-api/src/repairclaim_api/cli.py), [launcher](../../scripts/repairclaim_stack.py) | Explicit provisioning, capture/activation, backup/restore/quarantine release/maintenance; owned up/down/status, loopback binding and no borrowed credentials |

## Deliberate implementation decisions

- Programme acquisition/review is an operator action, not a consumer-controlled URL
  fetch or automatically invented coverage rule. Absent/stale sources cannot become
  a completed negative assessment or a finalized packet.
- Official PDF captures are supported. Arbitrary HTML/JSON ingestion, unrestricted
  discovery, authoritative VIN lookup and portal automation are not implied.
- Rules determine condition findings. Optional Codex is a structured advisory port,
  not coverage authority. Exact minimized egress needs owner approval. Installed CLI
  inference uses its configured authenticated service, not offline model weights.
  No model/authentication settings were changed.
- Correspondence uses constrained templates and attributed facts/conditions.
  Editing creates a new immutable draft, never inherited approval. No unconstrained
  legal/diagnostic letter is generated.
- ZIPs contain exact PDF bytes and a machine manifest. Originals require explicit
  selection. Review endpoints return images, not an unapproved final PDF download.
  Private case-data export is separately labelled, not approved correspondence.
- Documented outcomes require appropriate document type, literal amount/currency
  and positive payment/approval/coverage language. Ambiguity is rejected. This is
  evidence attribution, not bank or manufacturer authentication.
- Private object/fact/title payloads and blobs use per-case Fernet keys wrapped by a
  dedicated product key. Usernames, account IDs, generic garage metadata and minimal
  audit metadata remain under host ACLs. This is not full-disk encryption or
  administrator-proof evidence.
- Erasure is ledger-first, deletes private files and keys, and is replayed before
  restored access. Account tombstones erase owned cases even after a crash before
  individual case ledger entries. The current external erasure ledger is mandatory.
- Retention defaults to 180 days; fact/document/response/outcome edits can renew it.
  Background monitoring does not. Consents last at most 90 days. Only managed
  backups/repairclaim-*.rcbk files are pruned after 30 days; external copies cannot
  be recalled or promised deleted.
- Native macOS parsing has actual process and private-file/network denial evidence.
  Windows/Linux require the container image and host qualification. No fallback
  parses untrusted files inside the API.
- Container parsing explicitly uses the local Unix socket/Windows named pipe;
  inherited remote Docker contexts are not accepted, and Podman remote mode is off.
  This prevents an unrelated existing engine configuration from silently receiving
  private attachments. Host/container runtime verification is still a separate gate.
- Container base/dependency versions and PyMuPDF AGPL/commercial licensing still
  require deployment review. No license-clearance or supply-chain certification
  is claimed.

## Runtime boundary

All consumer routes use /api/repairclaim/v1. Liveness is separate from readiness,
which checks recent worker heartbeat, parser startup probe and quarantine state.
Neither health endpoint invokes a model or certifies coverage. Source freshness is
separate and empty inventory is explicit. See [API](contracts-and-api.md) and
[operations](operations.md).

No send/email/portal/settlement endpoint exists. Startup creates no default account,
source corpus, consumer case or Codex campaign. Real-data testing has not started.

## Verification boundary

[Current status](implementation-status.md) records measured results, failures,
process/PDF checks and the unavailable browser connection. Authored official-shaped
URLs and synthetic invoices are not actual-world evidence.
