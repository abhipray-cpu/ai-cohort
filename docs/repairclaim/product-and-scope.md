# Product and scope

22 October 2026. Scoped implementation exists; value, actual-world accuracy and
consumer/host acceptance remain unproven. See [status](implementation-status.md).

## Consumer and job

Initial consumer: a US used-Honda owner with a costly estimate, a paid repair or a
manufacturer/dealer refusal, who does not know whether a documented programme
might relate to the repair or what evidence to assemble. The job is case preparation
and continuity, not vehicle diagnosis or litigation. A family member can help only
under an explicit, revocable grant.

Value hypothesis: a source-linked explanation and complete case packet reduce the
effort of navigating a repair-coverage enquiry. This is not proven demand. Test a
free initial supported-scope screen and a disclosed one-time preparation fee in
consumer interviews before implementing billing. No subscription assumption,
success-fee collection, repair-shop kickbacks or payment wall hiding safety links.

## First release: all twelve requirements

Include intake/correction, coverage discovery, condition-level explanations,
focused clarification, evidence packets, rejection follow-up, optional retrospective
monitoring, exact revision comparisons, user control, case timelines, documented
outcomes, export/deletion/redaction and scoped family access. Formal requirements
are in [functional requirements](functional-requirements.md).

Programme support is an inventory, not a brand-level promise: each entry records
source version, geography, repair/component scope, applicable dates/mileage,
required confirmations, currency and source freshness. Launch with only reviewed
entries. Show unsupported scope before document upload where possible. Historical
programmes are labelled historical; expired or unknown windows cannot be marketed
as currently claimable. No arbitrary deadline is inferred from a document date.

The user can prepare an enquiry when applicability is uncertain; a reimbursement
request cannot invent conditions being satisfied. A source outage preserves a
previous assessment with a visible stale badge, not a fresh result.

## Explicit exclusions

- Mechanical diagnosis, repair instructions, roadworthiness advice or instructions
  to postpone repairs/payments while investigating coverage.
- Guaranteeing coverage/refunds, authenticating VIN ownership or certifying records.
- Insurance claims, aftermarket service-contract disputes, lemon-law litigation,
  class-action filing or settlement interpretation. A source of that kind is routed
  outside supported scope with a neutral explanation; it is not discarded silently.
- Automated manufacturer login, CAPTCHA bypass, portal scraping that violates
  terms, blind bulk VIN lookup, outgoing email, signatures or settlement acceptance.
- Global brands/jurisdictions, non-English advice and unsupported programme types.
- Pricing diagnosis or declarations that a workshop overcharged or committed fraud.
- Payments in the initial release. Pricing research is not a payment integration.

## Release-one external communication boundary

The product prepares correspondence and attachments. It does not send them.
Users review recipient, facts and exact bytes, approve a packet and download it;
they submit through their chosen permitted channel outside the product. They can
record a send date/channel and upload the response. The UI calls this
`user_reported_sent`, not `delivered`. Drafts remain preview-only/unapproved until
the approval gate. Future delivery connectors require a new permission/recovery
design and recipient verification; they are not an implicit implementation task.

## What makes the demonstration worthwhile

A user uploads an older paid-repair record, understands what is known, obtains
missing information, reviews a supported-programme enquiry, later processes a
response, and sees an opted-in programme revision explained against that same
case. Show at least one convincing non-match and one conflict as well as a positive
lead. This demonstration can use clearly labelled fixtures; only consented records
and observed outcomes establish a real consumer workflow or reimbursement.
