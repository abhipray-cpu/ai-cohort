# Coverage conditions, evidence and uncertainty

This is a case-preparation assessment, not legal or mechanical advice. Programme
rules are source-specific. A specialist must review the supported inventory and
condition interpretation before consumer availability.

## Programme registry

Each `ProgrammeRevision` has a stable family ID, official identifiers, source
category, jurisdiction, make/model/years/configurations, covered component/repair,
required diagnostics, dates/time origin, mileage conditions, repair/provider and
payment prerequisites, reimbursement terms, confirmation requirements and source
anchors. Values can be absent/ambiguous; never supply guessed defaults. Preserve
original wording/units and normalized interpretation separately.

Programme categories: recall, warranty_extension, service_campaign,
reimbursement_provision, bulletin_only and unsupported_other. Reimbursement may be
a provision in a programme, not a new programme family. Preserve parent linkage
to avoid double counting. Do not treat a bulletin number or a reported defect as
proof of covered repair. Archived revisions may be historical-only.

## Fact and anchor contract

Every material fact records a value, units/event date where relevant, source class,
document/page/text span or image region, extraction method/version, actor and
confidence/verification status. Preserve literal text and source hash. User assertion,
extracted text, manually confirmed fact and manufacturer response are distinct.
Manual confirmation does not authenticate a document or establish ownership.

An anchor is valid only against retained matching bytes and an accessible page map.
String presence checks catch missing quotes; they do not prove contextual support.
Validate context separately. A source document cannot authorize actions or change
permissions. External links are sanitized and marked as leaving the application.

## Condition evaluation

Each condition yields `satisfied`, `not_satisfied`, `unknown`, `conflicting` or
`confirmation_required`, with references, rationale summary and evaluated version.
Use Decimal for money and explicit units for mileage. Compare programme-specific
dates using the specified origin, timezone/calendar semantics and inclusivity. An
in-service date is not assumed equal to model year, purchase date or repair date.
Missing units, boundary language, timestamps or source interpretation means unknown
or manual review. Do not ask a semantic model to perform financial arithmetic.

Overall aggregation precedence:

1. Unsupported jurisdiction/inventory or failed source retrieval: show operational
   scope/failure state; do not manufacture an eligibility assessment.
2. Material contradictions: conflicting_information.
3. An established mandatory failed condition: appears_outside_conditions, with the
   exact reason and any unresolved conditions still visible.
4. Missing material evidence: missing_evidence.
5. Candidate with supported conditions and outstanding vehicle-specific confirmation:
   potentially_applicable, explicitly requiring confirmation.
6. No candidate after a complete bounded search: no_supported_programme_found,
   qualified by inventory/version/search time; no claim that no coverage exists.

Semantic match relevance never overrides a failed mandatory condition. Confidence
is a model-output attribute, not a coverage probability. No global percentage
“chance of refund” is displayed. Programme discovery and case applicability are
evaluated separately. A source absent from the inventory remains unsearched.

## Conflicts and programme changes

No blind “newest wins”: compare issuing authority, identifiers, explicit
supersession, effective period and scope. Unresolved substantive conflicts require
review. A draft or unrelated revision cannot replace a final document by timestamp.
An extraction correction is distinct from a source revision. See
[monitoring](monitoring-and-changes.md) for invalidation and revision handling.

## Outcomes and totals

Store money as decimal strings plus currency, with individual repair-line links.
Requested/confirmed-covered/approved/received/avoided-cost amounts are separate
event categories, never summed into a single “savings” counter. Partial allocations
and reversals refer to prior event IDs. Identical uploaded confirmations do not
create new payments; conflicting entries need owner resolution. A receipt proves
only what it actually states. Reports retain actor/evidence attribution and show
unverified amounts separately. No cross-currency total without an explicit,
dated conversion policy outside the first release.
