# Complete requirement traceability

Actual-data/consumer/host acceptance remains **open**. All twelve rows now have
implementation surfaces mapped below and in [implementation notes](implementation-notes.md).
Local fixture passes do not establish actual-world acceptance. FR IDs
are stable. AT IDs identify executable acceptance scenarios to be implemented;
they are not existing test filenames. Gates are defined in
[validation](validation-and-acceptance.md). All rows are first-release obligations.

| Requirement | Design responsibility | Consumer surface | Planned proof | Gates |
| --- | --- | --- | --- | --- |
| FR-01 intake/correction | ingestion, facts/provenance repository | Upload → confirm facts | AT-01: actual parsers, bad/OCR/conflicting files, fact revision | G1, G2, G3 |
| FR-02 coverage discovery | source registry, candidate retrieval | Coverage search and searched-scope panel | AT-02: real-source positives/hard negatives/outage | G1, G2, G3, G5 |
| FR-03 condition explanation | versioned conditions, deterministic evaluator | Condition checklist and evidence drawer | AT-03: boundaries, unknowns, conflicts, external confirmation | G1, G2, G3, G5 |
| FR-04 focused clarification | question policy, case state | Next-action card and records-request preview | AT-04: repair/current mileage distinction, unknown/resume | G1, G3, G5 |
| FR-05 evidence packet | evidence validator, packet renderer | Recipient/content/attachment review | AT-05: independent PDF render review, provenance, totals | G1, G2, G3, G5 |
| FR-06 rejection follow-up | response mapper, bounded casework controller | Response upload, reasons and follow-up | AT-06: missing evidence/valid exclusion/partial approval | G1, G2, G3, G5 |
| FR-07 retrospective monitoring | consent scheduler, rematcher, notification outbox | Monitoring settings and new-lead inbox | AT-07: new/versioned programme, dedup/revocation/restart | G1, G2, G3, G4 |
| FR-08 explain changes | source lineage, impact analysis, stale invalidation | Old/new conditions and affected packets | AT-08: material/cosmetic/missing-source distinctions | G1, G2, G3, G4 |
| FR-09 disclosure control | exact-artifact approval and scoped download | Approval preview, download, manual-send record | AT-09: stale/hash/grant/replay denial; zero outbound messages | G1, G3, G4 |
| FR-10 timeline/reminders | event ledger, reminder service | Case timeline and home next action | AT-10: restart/clock/deadline labels/cancellation | G1, G3, G4 |
| FR-11 honest outcomes | attributed outcome ledger, decimal aggregates | Outcome receipts and separate totals | AT-11: approval/payment/reversal/currency distinctions | G1, G3, G5 |
| FR-12 household privacy | auth/grants, redaction, erasure/export | Privacy, family access and case export | AT-12: two-household IDOR, revoke/erase/restore, burned-in redaction | G1, G3, G4, G5 |

## Design consistency checklist

- States cover no supported lead, incomplete investigation, contradictions,
  confirmed external response and cancelled/failed work without conflating them.
- Every condition/follow-up/packet has an evidence lineage and revision identity.
- All twelve rows have happy-path, abstention and failure tests; monitoring is not
  an after-launch item and consent is not represented by a decorative checkbox.
- Download approval is not delivery proof; confirmed coverage is not reimbursement.
- Private pilot evidence, public-source accuracy and Windows deployment are
  different gates. No aggregate test count can substitute for any row.
- Study/blog are later evidence-based learning deliverables, not acceptance proof.

Implementation PRs must add actual code/test/artifact links and measured status
without removing the original requirements or rewriting failed results as passes.

## Implemented surface and local proof (22 October 2026)

| FR | Actual web/API surface | Executable local evidence |
| --- | --- | --- |
| 01 | Documents & facts: classified upload, page preview, confirm/correct/remove, preserved provenance/history | [Documents](../../tests/test_repairclaim_documents.py), [workflow](../../tests/test_repairclaim_workflow.py), [hardening](../../tests/test_repairclaim_hardening.py), [actual parser/process](../../tests/test_repairclaim_process.py) |
| 02 | Coverage: operator-reviewed versioned inventory, source status, candidate/exclusion findings; no automatic fake inventory | [Core](../../tests/test_repairclaim_core.py), [sources](../../tests/test_repairclaim_sources.py), [workflow](../../tests/test_repairclaim_workflow.py) |
| 03 | Coverage: per-condition status, quote/hash/page and frozen source image; explicit unknown/conflict/confirmation | [Core](../../tests/test_repairclaim_core.py), [rule extensions](../../tests/test_repairclaim_rule_extensions.py), [HTTP](../../tests/test_repairclaim_http_workflows.py) |
| 04 | Next-action card, focused question, unknown/later/answered, fact revision, paused/reopen controls, records request | [Workflow](../../tests/test_repairclaim_workflow.py), [agent](../../tests/test_repairclaim_agent.py), [continuity](../../tests/test_repairclaim_continuity.py) |
| 05 | Packet desk: recipient/purpose/notes/new immutable draft, attachment policy/order/redactions, queued render, review images, manifest | [Documents](../../tests/test_repairclaim_documents.py), [workflow](../../tests/test_repairclaim_workflow.py), [HTTP](../../tests/test_repairclaim_http_workflows.py), [real local processes](../../tests/test_repairclaim_process.py) |
| 06 | Response upload/reasons, frozen condition comparison, quoted factual follow-up linked to latest response | [Continuity](../../tests/test_repairclaim_continuity.py), [HTTP](../../tests/test_repairclaim_http_workflows.py) |
| 07 | Privacy: explicit case/vehicle monitoring consent up to 90 days; revocation; garage update inbox | [Workflow](../../tests/test_repairclaim_workflow.py), [continuity](../../tests/test_repairclaim_continuity.py) |
| 08 | Old/new revision findings in update details; material/cosmetic source classification; stale job/packet approvals | [Sources](../../tests/test_repairclaim_sources.py), [hardening](../../tests/test_repairclaim_hardening.py), [workflow](../../tests/test_repairclaim_workflow.py) |
| 09 | Exact owner-only fingerprint approval, 24-hour expiry, revoke, freshness-checked ZIP download; no outbound submission | [Workflow](../../tests/test_repairclaim_workflow.py), [HTTP](../../tests/test_repairclaim_http_workflows.py), [actual process](../../tests/test_repairclaim_process.py), [frontend guards](../../apps/repairclaim-web/tests/domain.test.mjs) |
| 10 | Persistent timeline/manual-send attribution, sourced/user/suggested reminders, due/cancel, close/reopen | [Continuity](../../tests/test_repairclaim_continuity.py), [hardening](../../tests/test_repairclaim_hardening.py), [HTTP](../../tests/test_repairclaim_http_workflows.py) |
| 11 | Timeline outcome ledger: requested/confirmed_covered/approved/received/avoided_cost, currencies, evidence classes, reversals and independent totals | [Core](../../tests/test_repairclaim_core.py), [continuity](../../tests/test_repairclaim_continuity.py), [HTTP](../../tests/test_repairclaim_http_workflows.py) |
| 12 | One-use invitations, scoped grants/revoke, private export, case/account erase, retention, encrypted backup and tombstone-safe quarantined restore | [Store](../../tests/test_repairclaim_store.py), [continuity](../../tests/test_repairclaim_continuity.py), [recovery](../../tests/test_repairclaim_recovery.py), [hardening](../../tests/test_repairclaim_hardening.py), [API](../../tests/test_repairclaim_api.py) |

These links prove local mechanics only. Browser interaction could not run because
no browser was connected. Real-source correctness, actual private consumer data,
model quality, outcomes and Windows/tunnel deployment remain unvalidated. No AT
scenario is labelled a real-world pass solely because it has a local test.
