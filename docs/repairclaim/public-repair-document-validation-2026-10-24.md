# Actual public repair-document validation — 24 October 2026

**Partial engineering checkpoint, not full product acceptance.** This campaign adds
original repair-document bytes to the earlier complaint-metadata track. It does not
turn the earlier 400 metadata records into 400 verified repair cases.

## Acquisition and privacy

The frozen [plan](public-repair-document-plan.json) contains seven distinct
NHTSA-hosted public complaint attachment packs. All seven downloaded and passed
the production restricted parser: **52 pages, 6,017,069 bytes**, no exclusions.
The packs include complaint forms, correspondence and historical repair records;
they are not seven clean standalone invoices. Archive publication is not consent
to participate in our pilot, permission to redistribute, or proof of the owner's
claims. Originals contain residual identifiers; raw PDFs, OCR, previews and packets
remain in ignored local evidence directories. No consumer document text, VIN,
customer identifiers or attachments were sent to any model or recipient.

Reviewed page previews distinguish invoice totals from estimates and payment
evidence. The Civic transmission pack includes a paid stamp on an invoice page;
that observation does not independently authenticate payment or determine a
refundable amount. The Kia pre-invoice has both Honda and Kia dealer branding:
the vehicle itself is a Kia. Consumer letters remain consumer assertions, not
manufacturer decisions. Historical dates and handwritten/scan ambiguity are not
silently repaired or promoted to authoritative facts.

## Actual API/worker workflow

The harness starts owned production API and worker processes with temporary
accounts and state, uploads the original bytes, waits for sandbox parsing, checks
hash binding and cross-owner denial, then recomputes the assessment. Packs are
classified **other** because mixed complaint/invoice packs are not single invoices.
Vehicle identity is human-entered, not claimed as automatically extracted.

Only the explicitly declared CR-V 2017–18 programme is active in this track.
Historical Honda identities fall outside that programme's conditions; this is
**not** a claim of ineligibility under every programme. The unsupported Kia must
return no coverage verdict and must refuse packet creation.

For six Honda cases the harness renders actual packets with rasterized original
attachments, verifies the downloaded PDF hash and manifest, denies download before
approval, approves the exact fingerprint, downloads, revokes, then verifies denial.
Nothing is submitted. This proves document transport and approval controls, not
correct financial extraction, comprehensive coverage search or useful outcomes.

## Retained failures and TDD correction

- Initial corpus parse produced **zero fact proposals across all seven packs**.
  Upload success was not invoice-understanding success. Broad extraction of dates,
  mileage, totals and payment remains an acceptance gap.
- The first HTTP campaign passed six flows but failed the Kia packet expectation.
  The product correctly rejected the unsupported make; the harness was corrected
  to require `unsupported_make`, no coverage verdict and HTTP 409 on packet creation.
- A failing authored regression reproduced the actual dealer label `dtc code`,
  lowercase code and OCR table separators. The parser now recognizes that bounded
  layout and normalizes the proposed code to uppercase while preserving its literal
  page quote. Exact quote/value validation and human-confirmation requirements
  remain in force. A subtotal/pre-invoice is not promoted to payment evidence.
- The harness now measures proposal counts from the actual worker response, not
  stale acquisition-time parse artifacts. Historical reports are not rewritten.

## Evidence and reproduction

Ignored local artifacts:

- `var/repairclaim-validation/repair-documents-20261024-a/`: frozen plan,
  acquisition manifest, original hashes, sandbox OCR and selected page previews.
- `var/repairclaim-validation/repair-document-e2e-20261024-a/`: first campaign,
  including the incorrect Kia expectation; six passes and one failure retained.
- `var/repairclaim-validation/repair-document-e2e-20261024-b/`: seven expected safety
  outcomes passed; six packet flows and one unsupported-make refusal, 35.90 seconds.
  Its proposal counters still refer to acquisition-time parsing; do not use them
  to assess the later parser fix.
- `var/repairclaim-validation/repair-document-e2e-20261024-c/`: final rerun against
  the corrected parser and actual worker proposal counters: **7/7 expected outcomes
  passed, six packet flows, 36.53 seconds**. One unconfirmed diagnostic-code proposal
  was extracted from the Kia pack; the other six packs still yielded zero proposals.
  This is deliberately not reported as successful general invoice extraction.
- `var/repairclaim-validation/repair-document-e2e-20261024-d/`: expanded real-document
  workflow, **7/7 expected outcomes passed, 44.27 seconds**. Seven reminder create/
  cancel and private-export checks passed, as did six monitoring consent/revoke
  flows, one actual DTC proposal confirmation and manual invoice-total entry with
  no inferred payment. Historical regulator correspondence was recorded twice
  idempotently, its page-two missing-evidence request remained review-required,
  and a follow-up packet rendered. This is not a reply to our unsent packet.

## Expanded acceptance and UI safety correction

A new frontend test first failed on an absent `documentReviewNotice` export. Its
implementation now warns in the actual document-review UI whenever no facts are
extracted, or proposals are incomplete/unconfirmed; the warning uses a status
region. Opening/parsing a PDF no longer silently implies invoice understanding.
The existing manual fact correction path remains attributed `user_reported`, not
anchored or independently confirmed. This fixes misleading presentation, **not**
general automatic extraction accuracy. Four frontend tests and production build
passed. Actual browser interaction remains blocked, so no visual/a11y pass is claimed.

The expanded `-e` campaign additionally tests rejection of a documented refund
based only on the historical invoice total, invalidation of an approved download
after a fact revision, and erasure of the owned temporary test account without
revoking the other owner's account. Consult its final report for results. Local
validation exports are deliberately retained as evidence outside application state;
account erasure is not claimed to erase previously downloaded copies.
Final `repair-document-e2e-20261024-e/report.json`: **7/7 expected case outcomes,
one account-erasure/isolation check passed, 43.49 seconds**, zero provider calls.
Final expanded-acceptance full regression: **1,040 passed / five existing optional
skips**, six upstream warnings, 114.78 seconds, native RepairClaim process checks
enabled. JUnit: `var/repairclaim-expanded-acceptance-regression-20261024.xml`.

```bash
.venv/bin/python scripts/validate_repairclaim.py acquire \
  --plan docs/repairclaim/public-repair-document-plan.json --out NEW_PRIVATE_CORPUS
.venv/bin/python scripts/repairclaim_public_e2e.py \
  --corpus var/repairclaim-validation/public-20261022-b \
  --repair-documents NEW_PRIVATE_CORPUS --out NEW_PRIVATE_CAMPAIGN \
  --families 1 --programme-index 3
```

The repair-document track refuses combination with live-provider mode. No model
calls were made in this campaign; the previously measured free-proxy balance of
33,372 tokens was not consumed by it. No new USD expenditure was initiated.

## Still required before “full E2E complete”

Earlier full monorepo regression after the parser change: **1,040 passed, five existing
optional skips, six upstream warnings, 115.79 seconds**. RepairClaim's three native
process checks were enabled and passed. JUnit:
`var/repairclaim-repair-documents-regression-20261024.xml`. Scoped build/frontend/lint
passed (latest frontend count is four); 187 scoped Python tests passed with three opt-in process skips in the normal
invocation. Green regression tests do not override the open product gates below.

1. Reliable invoice-field extraction, manual correction/confirmation and ambiguity
   handling measured against independently reviewed repair-document labels, with
   the volume and quality thresholds in [acceptance](validation-and-acceptance.md).
2. Reviewed programme inventory, positive real repair/programme matches, financial
   and negative-pair evaluation, specialist interpretation and rights review.
3. Actual browser/mobile/keyboard/accessibility journeys. Supported browser discovery
   again returned no browser after documented troubleshooting; no UI pass is claimed.
4. Actual target Windows laptop, isolated parser runtime, protected tunnel and soak.
5. Consented customer cases, real reply journeys and specialist/outcome review.

These are open gates, not successful tests. Public historical records cannot be
relabeled as consented users, and generated packets cannot be called sent claims.
