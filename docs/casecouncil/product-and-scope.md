# Product and scope

Status: implemented engineering pilot; not real-data accepted or commercially
validated. See [implementation evidence](implementation-validation-2026-10-19.md).

## Buyer, user and paid outcome

Initial buyer: head of complaints/quality at a specialist UK motor insurer or a
complaint-handling consultancy serving insurers. Daily users are complaint handlers,
senior reviewers and quality analysts. Do not assume every broker has authority to
decide claims or access the evidence required for this workflow.

Job to be done: before issuing a final complaint response, identify whether the
reasoning overlooks the customer's strongest supported argument, contradicts the
case record, depends on missing evidence or mixes up contractual coverage with
service failures. Produce a reviewable pack, not merely a fluent letter.

Value hypothesis: fewer avoidable senior-review iterations and unsupported final
responses, with no increase in missed consumer harm. Measure reviewer effort and
quality jointly. Do not optimize for rejecting complaints, reducing legitimate
redress or discouraging referral rights. Market evidence and competitors are in
[research](research-and-sources.md); neither establishes willingness to pay.

## Product workflow

1. A handler creates a client-scoped case, identifies jurisdiction/product and
   uploads authorized complaint material, correspondence and relevant policy terms.
2. The UI shows extraction coverage, redaction preview, missing items and the exact
   material that would leave the laptop for inference. Egress is an explicit grant.
3. The handler supplies a proposed resolution/draft, or requests an independent
   issue review. This draft is labelled as a party position, never source truth.
4. Three role-bound agents propose independently; a critic tests the proposals.
   One bounded revision cycle is allowed before a frozen candidate ballot.
5. The deterministic controller computes agreement and blockers. A synthesis stage
   prepares an evidence-backed pack without changing votes or erasing dissent.
6. A human reviews issue-level recommendations, corrections and missing evidence.
   Only an exact-revision reviewed pack can receive a reviewed export label.

## Pilot deliverable

A workspace-scoped desk with case queue, immutable source revisions, evidence
coverage, proposed-response comparison, role proposal cards, critic findings,
ballot matrix, consensus result, dissent, usage receipts, review history and local
JSON/print-friendly HTML export. Export is download only. A visible draft export
is permitted to authorized users; it must say unapproved and list unresolved items.
Reviewed exports require current dependencies and appropriate human authority.

First input formats: text-bearing PDF and UTF-8 plain text; manual typed case facts
must be attributed separately. Scanned/encrypted/unreadable PDFs are explicit
unsupported/partial inputs, not silent empty documents. No OCR, email archive,
audio, video understanding or remote link fetching is included initially. A case
that references inaccessible photographs/video must disclose that evidence gap.

Issue dispositions are `uphold`, `partial_uphold`, `do_not_uphold`, `undetermined`.
Routing is separate: `ready_for_human_review`, `request_evidence`, `escalate`.
A firm can be contractually right but still owe a service remedy; one case may have
several issues with different dispositions. Monetary calculations require supplied
facts, a versioned approved rule and deterministic arithmetic; agents cannot invent
policy terms, interest rules, settlement authority or amounts.

## Commercial experiment

Pricing hypothesis: £300–£750 per team/month with a bounded case allowance; no
claim this is a validated market price. First experiment: three paid design partners,
an agreed authorized case cohort, baseline senior-review time and a blinded quality
rubric. A proposed success target is at least 20% lower median review effort without
material quality regression; see [acceptance](validation-and-acceptance.md).

Sell a second-review layer that can initially work through uploads/exports rather
than demand replacement of a customer's case-management system. “Uses debate” is
an implementation detail, not a moat. If the feature does not beat a simpler review
baseline on utility relative to cost, change the mechanism or reject the hypothesis.

## Explicit exclusions

- No binding legal/FOS decision, regulatory certification or prediction guarantee.
- No automatic claim rejection, payout, policy amendment, customer contact or referral.
- No impersonation of an independent ombudsman; the fairness role is an AI reviewer.
- No fabricated missing evidence, live investigation, accident reconstruction or fraud accusation.
- No all-jurisdiction legal engine, current-rule advice inferred from historical cases,
  clinical/legal specialist decisions or motor-finance commission complaints.
- No bulk FOS ingestion before source-rights clearance; no raw customer logs sent to
  a model merely because the application runs on the customer's laptop.
- No SSO, billing automation or CRM integration in the first pilot.

Name, niche, demand, permissions and useful debate lift remain assumptions to test.
Scope expansion needs an explicit decision, not a larger prompt.
