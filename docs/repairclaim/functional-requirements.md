# Functional requirements — release-one baseline

All twelve requirements are mandatory for the scoped first release. Prior
discussion of monitoring as a signature feature does not defer it. Examples are
illustrative, not findings about an actual vehicle. AT IDs define acceptance scenarios;
actual code/local tests are linked in [traceability](requirements-traceability.md).

## FR-01: turn documents into a correctable repair case

Accept PDF, JPEG and PNG estimates, invoices, job sheets, receipts and responses;
accept a manual fact-entry path. Reject encrypted/unsupported/oversized files with
an explanation. Show extraction quality, page/source locations and original values
beside normalized facts: vehicle, repair, dates, mileage, diagnosis and charges.
Distinguish estimates, invoices, payment proof and user assertions. Ask whether
multiple repairs/documents concern the same case; never merge by name alone.
Users confirm/correct material facts with attribution; prior versions remain until
retention/deletion. A corrected value cannot silently overwrite its evidence.

**AT-01:** missing repair-time mileage stays unknown; OCR ambiguity and conflicting
VINs block a finalized assessment; manual correction creates a new assessment input.

## FR-02: discover potentially applicable official programmes

Search the supported, versioned official-source inventory for recalls, warranty
extensions, service/customer-support campaigns and reimbursement provisions.
Return candidate reasons, conditions, citations and explicit unknowns. Classify a
service bulletin without coverage language as a bulletin, not free-repair authority.
Record searched scope, time, exclusions and unavailable sources. Model/year
matching or VIN decoding alone cannot establish actual vehicle eligibility.

**AT-02:** a same-model wrong-component case is rejected as a supported lead;
unavailable retrieval does not return an unqualified negative or invent a programme.

## FR-03: explain each condition and the overall assessment

Show satisfied, not_satisfied, unknown, conflicting and confirmation_required per
condition, with facts and source anchors. Overall states: potentially_applicable,
missing_evidence, appears_outside_conditions, conflicting_information,
no_supported_programme_found. Display source-unavailable/unsupported scopes
separately, not as eligibility judgments. Unknown is not false; a failed required
condition cannot be averaged away by relevance scores. Only documented external
confirmation can populate manufacturer-confirmed status.

**AT-03:** boundary mileage/date values use the documented inclusive/exclusive
rule; absent in-service date or unresolved source conflict cannot become a pass.

## FR-04: ask the smallest useful next question

Prioritize material unresolved conditions, explain why a question matters, and
request one focused item at a time with an optional full checklist. Allow answer
later, unknown, upload, correction and a draft records request. Do not ask for a
fact already confirmed unless new evidence conflicts. Preserve progress on pause.

**AT-04:** given current mileage but unknown repair-time mileage, ask for the latter;
an answer updates only the correct event and reevaluates affected conditions.

## FR-05: prepare a factual, recipient-specific evidence packet

Create an editable enquiry or supported reimbursement-request draft, chronology,
programme references, attachment index and unresolved-fact list. Each material
claim binds evidence or is expressly user-reported. Reimbursement item selection
is explicit; estimates are not payments and totals do not imply recoverability.
Show exact recipient, content, redactions and attachment order before approval.
Support a readable downloadable PDF packet plus machine-readable manifest;
document originals are included only after explicit review. Draft preview is labelled
unapproved and not offered as a finalized correspondence download.

**AT-05:** unsupported diagnosis/phone calls never appear as facts; packet contents
and amounts agree with approved facts and the manifest; edited content loses approval.

## FR-06: process a rejection and prepare the next factual step

Accept a response, identify attributed reasons and distinguish missing evidence,
apparent condition disagreement, unsupported scope and unclear replies. Compare
each reason with the relevant frozen source and case facts; ask for clarification
where required. Draft a restrained follow-up or identify an appropriate official
contact/qualified-assistance route. Treat partial approvals separately from denials.
Do not promise that an appeal is available or invent a deadline or legal entitlement.

**AT-06:** a missing diagnostic-code rejection produces a records request, not a
fraud allegation; a genuinely excluded repair is explained without a false appeal.

## FR-07: revisit retained repairs when supported programmes change

Obtain separate, revocable consent per vehicle/history scope and retention period.
Check registered sources on a visible schedule, rematch material programme
additions/revisions against consented retained repairs, and create an in-app lead
with reasons, uncertainty and next evidence needed. No fresh consent is inferred
from an upload or family invitation. Revocation/deletion cancels pending work.

**AT-07:** a newly acquired historical programme can create a discovery lead but is
not labelled newly issued; duplicate captures do not generate duplicate alerts.

## FR-08: explain programme and assessment changes

Show old/new source versions, what was observed to change, publication/effective/
discovery dates when known, condition impacts, affected cases and required next
actions. Distinguish corrected extraction, user correction and actual source change.
Invalidate affected assessment/packet approvals while retaining labelled history.

**AT-08:** a substantive condition revision marks a related approved packet stale;
unrelated layout changes do not fabricate coverage changes; a 404 is not repeal.

## FR-09: user controls any external disclosure

Require review of exact facts, recipient, message and attachments before approved
download. Permit editing/cancellation; never send, sign, pay or accept a settlement.
Record manual submission as user-reported, with optional proof and channel/date.
If future delivery is implemented, a new explicit approval and delivery-evidence
contract is mandatory; approval for analysis is not approval for transmission.

**AT-09:** stale/revoked approvals cannot download a finalized packet; preparing or
downloading a packet never records it as delivered or creates external messages.

## FR-10: show a durable case timeline and useful next action

Record documents, corrections, assessments, consents, packet versions, user-reported
submissions, responses, reminders and outcomes. Home answers what happened,
who/what we await and the next useful action. Display deadline provenance,
timezone, uncertainty and stale-source warnings. Reminder suggestions are not
programme deadlines. Reopening a case preserves earlier history and authority.

**AT-10:** restart retains a paused case; unverified dates are labelled; cancelling a
reminder prevents later display as a fresh actionable notification.

## FR-11: report outcomes without inventing savings

Keep requested, confirmed-covered, approved-reimbursement, actually-received and
documented avoided-cost amounts distinct by currency and repair line. Record
source/actor/time for each; manufacturer response, payment evidence and user
assertion remain different evidence classes. Support partial payments, corrections,
reversals and case closure/reopen. Never double count approved and paid amounts.

**AT-11:** a draft is not a successful claim; an approval is not cash received;
unproven amounts are user-reported, unknown amounts stay null, mixed currencies
are not summed and reversed payments reduce the relevant received total.

## FR-12: protect, export and delete household information

Provide sensitive-field redaction and a rendered final disclosure preview; export
case data/history and delete cases/accounts with a visible deletion/backup policy.
Support distinct vehicles, explicit case-scoped family viewer/editor grants and
revocation. Only owners authorize disclosures, monitoring and grants in release one.
Use case-specific consent for any real-data pilot; service use is not research consent.

**AT-12:** another household cannot discover a case or attachment; revocation
immediately blocks future access; deleted data cannot reappear through queued
jobs, cached previews, monitoring or restoration. Explain external copies cannot
be recalled and downloads cannot be remotely revoked.

## Cross-cutting acceptance

Mobile 360 px through desktop, keyboard operation and readable evidence are
required. Show empty, running, paused, stale, partial, cancelled and failure states.
Never turn an inference failure into a negative coverage finding. User documents
must not appear in default telemetry, prompts to unauthorized destinations or
shared cross-household caches. See security, recovery and acceptance documents.
