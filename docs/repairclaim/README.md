# RepairClaim — Day 12 consumer repair-coverage casework

22 October 2026. **Scoped implementation completed across API, worker and web,
following observed TDD cycles. Latest local checks: 187 tests plus actual process checks,
4 frontend tests, build/lint; latest full regression: 1,040 passed / 5 existing optional skips.
Public-source integration has started: 11 parsed official PDFs and 48 authored
boundary cases through actual HTTP/worker passed; full consumer acceptance is open.
Browser interaction, actual coverage,
consumer savings and Windows acceptance are not claimed.** RepairClaim is a provisional
name; name/domain clearance is pending.

Consumer promise: before or after paying for a car repair, discover potentially
applicable manufacturer coverage, understand missing evidence, prepare a factual
enquiry/reimbursement packet and progress the case. This is not an AI mechanic,
legal representative, warranty seller or guarantee of reimbursement.

Initial proposed scope is English-language US Honda passenger-vehicle cases for an
explicitly reviewed programme inventory. Supporting a make does not mean covering
every model, campaign or jurisdiction. Initial inventory acquisition is measured;
complete inventory and specialist review remain prerequisites. All twelve requested requirements,
including retrospective monitoring and change explanations, are first-release
acceptance requirements. See the coverage matrix; none are silently deferred.

## Read the delivery pack

1. [Product and scope](product-and-scope.md): consumer, proposition and boundaries.
2. [Functional requirements](functional-requirements.md): FR-01 through FR-12 and acceptance behaviours.
3. [Traceability](requirements-traceability.md): every requirement mapped to design, UI, tests and release gates.
4. [Research and sources](research-and-sources.md): verified sources, access limits and product hypotheses.
5. [Architecture](architecture.md): proposed C4 levels 1–4, deployment and repository boundaries.
6. [Casework protocol](casework-protocol.md): investigation, clarification, review, rejection and outcome states.
7. [Coverage and evidence](coverage-and-evidence.md): programme conditions, provenance, conflicts and uncertainty.
8. [Contracts and API](contracts-and-api.md): data model, proposed interfaces and approval bindings.
9. [Monitoring and changes](monitoring-and-changes.md): consent, source revisions, retrospective matches and expiry.
10. [Consumer UI](consumer-ui.md): mobile-first screens, evidence review and failure states.
11. [Permissions and security](permissions-and-security.md): household access, sensitive documents and egress.
12. [Audit and recovery](audit-and-recovery.md): durable jobs, fenced writes, retries and deletion.
13. [Operations](operations.md): proposed Windows service, backup, health and protected tunnel.
14. [Data and evaluation](data-and-evaluation.md): actual public documents, private-data gap and independent labels.
15. [Validation and acceptance](validation-and-acceptance.md): engineering, real data, browser, pilot and host gates.
16. [Implementation plan](implementation-plan.md): dependency-ordered TDD slices; not implementation evidence.
17. [Decisions and risks](decisions-and-risks.md): defaults, unverified assumptions and scope control.
18. [Implementation status](implementation-status.md): authoritative planned-versus-measured ledger.
19. [Implementation notes](implementation-notes.md): actual files, supported API and missing capabilities.
20. [TDD checkpoints](tdd-checkpoints.md): observed red/green cycles and test limitations.
21. [Public-source validation checkpoint](real-data-validation-2026-10-22.md): actual downloads, exclusions, socket workflows, defect correction and open acceptance gates.
22. [Jev free-access research](jev-free-access-research.md): first-party pricing, conditional credits and unofficial proxy limitations.
23. [Live Jev attempt, 24 October](jev-live-validation-2026-10-24.md): API/worker adapter, budget controls and actual 403 access blocker; no live pass.
24. [Free-proxy Jev checkpoint](jevmodel-validation-2026-10-24.md): eight-case actual API/worker smoke pass, token receipts and three retained advisory disagreements; not full acceptance.
25. [Actual public complaint metadata](public-complaint-validation-2026-10-24.md): 400 records / four unique minimized inputs, actual worker and packet controls, representative live calls; not invoice/narrative acceptance.

26. [Actual public repair documents](public-repair-document-validation-2026-10-24.md): seven mixed attachment packs, actual packet controls, unsupported-make refusal and an explicitly unpassed invoice-extraction gate.

## Design decisions to make scope concrete

- Consumer-controlled case preparation, not automated diagnosis or an eligibility certificate.
- Reviewable, approved downloads with user-managed external submission in release one.
  Recipient editing, exact attachment review and manual-send recording are included;
  integrated email, portal automation and settlement acceptance are excluded.
- Opt-in scheduled checks against registered official sources; notifications are
  in-app. A failed check is not evidence that nothing changed.
- Independent product API/web application, dedicated store and private files;
  no cross-product application imports, credentials or consumer-data sharing.
- Existing installed-Codex adapter is a proposed generation integration, not local
  model inference. Optional decision providers are capability-gated; no Jev account,
  paid call or experimental vision feature is required to read these docs or start
  deterministic development. Provider selection follows evaluation, not hype.
- [Study guide](study-guide.md) maps concepts to code, measured results and open
  acceptance gates. Blog drafts were removed at the user's request.

Use `make repairclaim-test repairclaim-lint` for local implementation checks, and
`make repairclaim-up`, `repairclaim-down`, `repairclaim-status` after explicit
account provisioning. [Operations](operations.md) has setup instructions. Startup
does not acquire programme data or invoke Codex. See the actual implementation map
and status before interpreting a design target as measured acceptance.
