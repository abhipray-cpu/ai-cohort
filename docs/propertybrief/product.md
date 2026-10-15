# Product specification

Status: implemented pilot, updated 15 October 2026. Name and positioning remain provisional. Commercial outcomes below are hypotheses, not measured results. See [implementation status](implementation-status.md) and [actual-data validation](validation-2026-10-15.md) before interpreting this product specification as release acceptance.

## Buyer and purchase trigger

The initial buyer is a small residential property acquisition team or buyer's broker researching NYC rental buildings. The user is the analyst assembling a pre-offer diligence pack. The purchase trigger is a property advancing from an initial shortlist to detailed investigation, when the team needs a defensible account of public records and unresolved questions.

Proposed promise: enter an address and receive a reviewable public-record investigation, with the evidence and follow-up tasks needed to progress diligence. Measure analyst effort and missed material findings against a manual workflow. Do not promise avoided losses, an accurate repair budget, or guaranteed discovery of every issue.

Start with a per-investigation offer and test whether frequent users prefer team subscriptions. No price, revenue estimate, market size, or willingness-to-pay result has been established. Validate paid demand with prospective buyers after a working sample pack is available; no customer outreach is authorized by this document.

## Customer workflow

1. Create a property case with address, borough, optional known BIN/BBL, and a question such as “What recorded issues need clarification before we progress this purchase?”
2. Confirm the intended building if matching returns multiple candidates. The UI explains building-level and parcel-level scope.
3. Start an investigation. See completed checks, next planned check, action count, and source availability as the worker proceeds.
4. Inspect findings alongside exact source fields, timestamps, source IDs, and the agent's concise decision summaries.
5. Review a proposed follow-up plan grouped by seller, inspector, and attorney. Each task explains its evidence, purpose, and unresolved question.
6. Ask a follow-up in the same conversation. A new scoped run reuses pinned evidence or refreshes it explicitly and records its own budget and report revision.
7. Edit or accept findings, record review decisions, and export an immutable reviewed pack. A partial pack carries its gaps into every export.

## First-release scope

NYC residential building investigations using official HPD and DOB structured records. Support all five boroughs for these sources, subject to actual property coverage. A single case selects a single building; parcel records must be distinguished from records for that building. Resolve HPD building IDs, BINs, and BBLs using source relationships, preserving ambiguity.

Required checks cover housing violations and complaints, repair/vacate orders, underlying-condition and alternative-enforcement program participation, DOB complaints, DOB violations, and DOB ECB violations. These eight source checks form the initial coverage profile. Building records resolve identity; registrations are registered for later identity assistance but not automatically queried in this version. See [source registry](research-and-sources.md#source-registry).

The agent may choose the order and depth of these checks and follow up on relevant records. Application code controls whether coverage is sufficient to finish. A report always records the state of every required check, including incomplete and unavailable sources.

ACRIS record/image analysis is a later extension: coverage excludes Staten Island and automated access, schemas, document rights, and interpretation have not been validated. The first release explicitly marks ownership/title/recorded-document checks outside its coverage. Permit, zoning, tax, flood, physical inspection, repair-cost, market-value, and investment-return analysis are also future scope.

## Report contract from the user's perspective

| Section | Required content |
| --- | --- |
| Property identity | Address, borough, selected building/parcel identifiers, match method, ambiguity |
| Investigation coverage | Each required source, query scope, retrieval time, completeness, gaps |
| Findings | Recorded facts, source status, dates, citations, interpretations clearly attributed |
| Conflicts | Conflicting dates/statuses/identifiers and the effect on interpretation |
| Follow-up plan | Prioritized tasks, intended recipient, evidence, prerequisites, verification/closure criteria |
| Limitations | Unsupported checks, unavailable sources, truncation, stale records, unresolved questions |
| History | What was checked, what changed, critique outcomes, stop reason, review revision |

Use “recorded open as of retrieval” where appropriate. A closed violation is historical evidence; it does not prove present physical condition. A complaint is a report of a condition, not an independently verified violation. A zero-result query describes the exact checked dataset and filter. It does not establish a problem-free property.

Priorities describe investigation urgency, not a numerical investment-risk score. Model confidence cannot establish legal status, current building safety, or a probability of loss. Regulatory descriptions require the current applicable official source; source record text alone is not a verified current legal rule.

## Example product scenario

Illustrative workflow: the agent observes repeated water-related records, checks the relevant enforcement-program dataset, and finds conflicting status dates. It preserves both records, asks for a current agency record and inspection evidence, and adds a seller-document request. It does not infer that a historical condition still exists or price the repairs.

## Acceptance and commercial measurement

Functional acceptance requires a browser journey from real address to matched identity, adaptive tool execution, visible evidence, critique, a reviewed report, and a stable export. A follow-up must operate on the same selected property and show when evidence was refreshed. Cancellation and source/model outages retain completed work.

Compare manual and assisted research on the same frozen records, with independent reviewer labels. Record time to a reviewer-accepted pack, material omissions, incorrect property matches, and correction effort. The initial commercial hypothesis is at least 30% less median active analyst time without reduced finding recall, measured over at least ten paired tasks with reviewer order counterbalanced. This is a target, not a result or a statistically established benefit. Customer trials and pricing validation remain separate gates.
