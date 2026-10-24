# Retrospective monitoring and change explanations

FR-07 and FR-08 are mandatory release-one functionality, not optional future work.
Their first notification channel is the authenticated in-app inbox. No email/SMS
delivery or real-time external-source SLA is implied.

## Consent and scheduling

Owner opts in for selected vehicles and retained case IDs, with an explicit end
date and permission to compare retained repair facts against supported public
programme updates. Default proposed duration: 90 days; show the exact expiry and
allow earlier revocation or explicit renewal. Document retention is separately
chosen; expired retention stops matching even if consent otherwise remains active.
An invitee cannot enable monitoring. No upload, packet approval or login implies it.

One daily source-check schedule is proposed, with visible last successful check,
last attempt, next due time and sources unavailable. Operator enables acquisition
only for registered reviewed hosts/paths. Cap each sweep at 25 registered URLs,
100 MiB transferred, three attempts per URL and one rematch job at a time. Larger
inventories require a reviewed paginated schedule and explicit freshness policy,
not hidden unbounded work. No expensive catch-up storm after sleep/restart.

Monitoring uses the consented purpose and minimum facts. External analysis, if
needed, also requires current provider-egress authority and finite budget. Exhaustion
creates a pending/manual review item; it never silently changes matching to a fake
provider or calls paid services beyond the allowance.

## Source update protocol

1. Fetch with HTTP validators when supported; validate final host/IP, bytes and type.
2. Persist capture/hash/status. Identical bytes are a check result, not a new programme.
3. Compare source identifiers/content, publication/effective dates and supersession.
4. Quarantine newly discovered or changed programmes for registry review. Previously
   relied-on sources with potentially material changes mark affected outputs stale
   immediately, before the new interpretation is accepted or any rematch completes.
5. Reviewer distinguishes substantive change, formatting-only change, extraction
   correction, unknown materiality and unrelated document. Preserve review attribution.
6. Activate a reviewed immutable registry revision; rematch only current consented
   retained cases. Notifications link exact before/after conditions and next actions.

An HTTP error, removed page or changed layout is not proof that a programme ended.
Uncertain materiality retains a visible review hold. Newly acquired old material is
labelled newly discovered, with its historical publication/effective dates if known.
Never label an archive upload as a new reimbursement opportunity without evidence.

## Change impact and alert semantics

Classify impacts: candidate_added, condition_changed, evidence_interpretation_changed,
confirmation_needed, candidate_no_longer_supported, or no_material_change. Retain
previous findings/packets as historical and explicitly show approval invalidation.
Do not claim a benefit was withdrawn without source support. Notification states:
pending, available, read, acknowledged, superseded, cancelled and expired.

Dedup key: household + case + programme family + reviewed revision + impact type.
Durable transaction writes impact, invalidation and outbox intent. Inbox materializes
idempotently; retries cannot create repeated “new money” alerts. Acknowledgement
is not a claim submission or renewed consent. Closing a case does not reopen it
automatically; a relevant lead offers an owner-controlled reopen action.

## Revocation, erasure and races

Check consent/retention/grant/deletion epoch at scheduling, job claim, before provider
egress, before writes and before notification display. Revocation cancels pending
jobs/alerts and suppresses already materialized private alerts. A stale worker cannot
recreate them. Public-source acquisition can continue independently of a deleted
household, but no private rematch can. Account erasure removes private links from
global public records. Restore reconciles revocations/tombstones before scheduling.

## Required proofs

Use controlled HTTP receivers and distinct genuine source revisions where available:
duplicate capture, previously unseen historical programme, substantive revision,
cosmetic revision, parser correction, source outage, changed URL, misleading dates,
expired consent, deleted case, grant revocation during inference, restart at every
commit boundary and stale packet download. A synthetic revision tests mechanics;
it must not be reported as an actual manufacturer change observed live.
