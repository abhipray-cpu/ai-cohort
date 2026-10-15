# Conversation and reviewer experience

Status: implemented React/TypeScript workbench; browser/visual acceptance remains unverified. The product's primary screen is a persistent investigation conversation for a selected property, with the report and evidence one click away. Technical agent internals remain secondary to the user's diligence task. Build and HTTP asset checks are recorded in [validation](validation-2026-10-15.md), not substituted for browser interaction tests.

## Layout and visual direction

Use a restrained editorial style: warm neutral surfaces, dark readable text, a single accent for navigation/actions, and distinct labelled warning/error states. Dense record tables use tabular numerals and comfortable row spacing. Typography, spacing, focus states, and loading transitions should be consistent with a paid research workspace. Avoid decorative charts or fabricated risk scores.

The implementation uses a case sidebar, central conversation/report area, and source/activity side panel with an overlay evidence drawer. It has responsive navigation and a mobile case selector. The header shows address, selected building/parcel identity and investigation status. The precise mobile tab layout proposed here was not shipped; responsive behavior still needs actual browser acceptance.

## Screens and interactions

| Screen / component | Required behavior |
| --- | --- |
| Case list | Search address, recent activity, report state and unresolved checks; meaningful empty state |
| Start investigation | Address/borough/question form, optional known identifier, example intent; no implementation jargon |
| Candidate confirmation | Side-by-side source addresses/identifiers and ambiguity reasons; accessible selection |
| Conversation | Persistent messages, scoped follow-ups, source timestamp on answers, explicit refresh action |
| Live investigation | Completed checks, current check, brief decision summary, remaining action allowance, cancel control |
| Report | Findings, conflicts, source coverage, prioritized follow-up checklist and limitations |
| Evidence drawer | Exact rows/fields, original status/dates, source catalog link, row key, snapshot time and scope |
| Follow-up checklist | Recipient role, reason, supporting findings, prerequisites, completion evidence; analyst may add notes |
| Review/export | Exact revision, reviewer attribution, material edits revalidated, gap-preserving export |
| Run history | Action/results, changed hypotheses, critique and failures; optional technical detail expansion |

The conversation must visibly drive an investigation and answer follow-ups about the same property. A generic chat bubble containing a generated report is insufficient. The source coverage matrix remains available throughout the conversation.

## Status language

Use “Investigation complete for listed sources”, “Partial investigation”, “Needs property confirmation”, “Source unavailable”, “Results capped”, “Conflicting source fields”, “Critique not assessed”, and “Cancelled; observations saved”. Complete means the defined process finished. Avoid visual cues suggesting legal clearance or building safety.

Display source severity exactly as a source field, with a separate explanation of investigation priority. Mark recorded facts, interpretations, analyst notes, and follow-up tasks distinctly. A closed record remains available in historical findings. A source that returned no records and a source that failed must never share the same empty state.

## Degradation and review

Partial preview appears after the first validated observation. If generation stops, show source-derived observations and checks still needed. Include the stop reason and an explicit resume action when permitted. Reload must recover from server state rather than losing the report or restarting the run.

A reviewed partial pack is exportable with its gaps attached. Warn only about concrete unresolved coverage/review state relevant to export. A reviewer cannot hide machine-detected gaps by editing prose. No email, seller contact, agency submission, or autonomous financial decision is part of the workflow.

## Browser acceptance

Validate at 1440×900, 1024×768, and 390×844. Complete the full actual-data journey: sign in, address input, resolve ambiguity, start, inspect progress/evidence, ask follow-up, cancel/resume, review/edit, export, reload, and reopen a historical revision.

Check keyboard navigation, visible focus, labelled forms/errors, screen-reader announcements of significant progress, readable contrast, text zoom, and non-color status cues. Escape source descriptions and preserve formatting without executable markup. Test long addresses, long evidence text, hundreds of records, zero records, stale sessions, failed downloads, and source/model outages.

Capture screenshots and record actual interaction results for premium-UI acceptance. TypeScript/build success alone does not prove visual or interaction quality. If browser tooling is unavailable, report the gate as untested and preserve the rest of the validation evidence.
