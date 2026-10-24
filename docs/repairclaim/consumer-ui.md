# Consumer experience — mobile-first, evidence-first

Implemented responsive React workspace for ordinary people; the interaction and
accessibility acceptance checklist below is still unverified because no browser
is connected. See [UI code](../../apps/repairclaim-web/src/main.tsx) and
[actual evidence](implementation-status.md). Use
plain language, readable type, generous spacing, restrained status colors and a
visible source/uncertainty hierarchy. No fabricated savings counters, refund odds,
animated “thinking” claims or pressure to postpone a safety-related repair.

## Navigation and main screens

1. **My garage:** vehicles, active cases, next action, monitoring status and supported
   scope. Explain unsupported scope before asking for sensitive uploads.
2. **Start a case:** estimate / paid repair / response, jurisdiction, vehicle details,
   upload or manual entry, privacy/egress explanation. No long mandatory questionnaire.
3. **Confirm facts:** original page beside extracted facts on desktop; Fact / Source
   tabs on mobile. Highlight uncertain OCR and conflicts. Keep current mileage separate
   from mileage at repair. Label user-reported facts and corrections.
4. **Coverage review:** potential programmes with search time/inventory and reason;
   condition checklist with evidence drawer. No certainty badge on a lead.
5. **Next step:** one important question plus full checklist, answer unknown/later,
   records-request preview and pause/resume controls.
6. **Packet studio:** enquiry versus reimbursement-request purpose, recipient, facts,
   attachments, redaction preview, unresolved conditions and exact-version approval.
7. **Case timeline:** manual-send entry, response upload, attributed reasons,
   follow-up, reminders and separate outcome categories.
8. **Monitoring inbox:** consent scope/expiry, successful versus failed source checks,
   old/new evidence, affected case and approvals needing re-review.
9. **Privacy/family:** invitations/grants, egress consent, retention, export, delete and
   explanation that already downloaded/external copies cannot be revoked.

## Smallest useful mobile layout

```text
RepairClaim                 My garage / Case
Vehicle · repair · last evidence checked

NEXT STEP
We need the mileage when this repair happened.
Why this matters · Upload record · I don't know

Coverage   Evidence   Timeline   Packet
Condition                    Status + explanation
Source / page / open original

Paused / source stale / approval needed, when relevant
```

Avoid squeezing a desktop evidence grid onto a phone. Preserve selection and
return focus after source drawers/modals. Critical distinctions never rely on color.

## Required language and states

- “Potentially relevant programme; confirmation needed,” not “You qualify.”
- “No match in our supported sources checked on [date],” not “No coverage exists.”
- “Could not complete this check,” not a completed negative result.
- “Payment recorded by you” versus “payment supported by uploaded evidence.”
- “Approved packet downloaded” versus “you reported sending it”; no delivered badge.
- “Suggested follow-up date” versus “documented programme deadline.”

Include loading/empty/bad-file/unsupported/OCR-needs-review/partial/cancelled/stale/
outage/conflict/permission-revoked/session-expired states. Keep safe accepted work
visible after faults and show exactly what failed. Deletion needs clear scope and
confirmation but no manipulative retention prompts.

## Disclosure approval

Owner sees the actual rendered pages and selected originals/derivatives, recipient,
amounts, private fields remaining and all unresolved facts. Editing anything requires
rerender/reapproval. Do not hide attachments behind a filename-only confirmation.
Unapproved review images are labelled by draft/rendered state in the packet desk;
the final approved bytes do not change at approval. Standalone draft-renderer
fixtures also carry an unapproved watermark. Finalized download is owner-scoped.
Preview/download errors must not change submission or outcome status.

## Accessibility and trust acceptance

Test keyboard-only completion, focus order/escape/return, labelled controls, screen
reader announcements, 200% zoom and 360/768/1440 px. Aim for WCAG 2.2 AA; require
automated checks plus manual critical-flow review. Error messages identify fields
and recovery. Financial/evidence tables remain readable without horizontal trapping.
Privacy-sensitive pages use no third-party session replay or advertising trackers.
Default overview never exposes complete VIN, address, bank details or document text.

Consumer usability target: 10 moderated participants, at least eight able to identify
the next useful action without assistance; zero participant left believing a lead
is guaranteed reimbursement after the explanation check. Record exact task outcomes,
failures and sample limits. These are proposed pilot gates, not demonstrated results.
