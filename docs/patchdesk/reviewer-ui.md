# Conversation and reviewer workspace

Status: implemented React/TypeScript workbench with production build and four presentation tests passing. No browser was available in this session: screenshots, interaction/accessibility and viewport acceptance remain unverified. This specification remains the browser acceptance target, not a claim that every interaction has passed.

## Layout and visual language

Desktop: client/project sidebar; main conversation and maintenance plan; right-side coverage/activity panel, with an evidence/conflict drawer. A persistent header shows selected project/repository, input commit/hash, source dates and review state. Switching projects visibly resets the conversation/evidence scope.

Use a restrained dark-ink/light-neutral palette, deliberate typography/spacing, readable dense tables, tabular numerals and labelled warning states. No fabricated “security score,” decorative pie charts or all-green status based on zero returned matches. Integrate chat as a way to request/clarify maintenance work, not as the only access to findings.

Tablet: panels collapse with explicit controls. Mobile: accessible project switcher and Conversation / Plan / Evidence / Activity navigation, with persistent scope/gap indicators. Proposed acceptance viewports: 1440×900, 1024×768 and 390×844.

## Screens and key interactions

| Screen | Required behavior |
| --- | --- |
| Client/project list | Authorized projects only; last snapshot/review, unresolved work and empty state |
| Import | Paired manifest/lockfile, provenance/commit, size/format support, private data/egress choices and parser gaps |
| Capability view | Available/denied/unconfigured/stale tools with safe explanations, no tokens or sensitive hidden-project names |
| Conversation | Persistent scoped questions, pinned evidence date, refresh as explicit new acquisition |
| Running investigation | Capability stages and overlapping task lanes, selected provider, route reasons, attempt/budget state, cancel |
| Findings | Package instance/version/path, advisory aliases, source-matched/unknown status, evidence and qualification |
| Candidate comparison | Fixed-for-which-advisory, published release, declared/engine/peer checks, breaking-change uncertainty and verification pending |
| Conflict drawer | Side-by-side source fields/ranges/timestamps, lineage and policy/reviewer decisions; unresolved impact stays visible |
| Maintenance plan | Proposed batches/tasks, affected findings, rationale, owner role and concrete verification/approval requirements |
| Review/export | Exact report revision, material-edit revalidation, attribution and gap-preserving Markdown/JSON download |
| Publication approval | Separate destination/title/body/labels preview, exact approval/expiry, no preselected automatic publish |
| History | Input/registry/policy/report changes, source refresh comparison, prior failures, receipts/unknown publication outcome |

Source full records remain inspectable outside model context. “Not in prompt” is not “not in storage.” Package counts distinguish locations/names/versions/matches. An optional missing threat provider does not hide required advisory coverage gaps or fabricate a zero score.

## Status language

Use “Recorded dependency match,” “Version range unresolved,” “Source unavailable,” “Permission required,” “Candidate needs verification,” “Approved for this issue draft,” and “Publication outcome unknown.” Run completion is separate from security/remediation state.

Present denied egress as a deliberate boundary, with a scoped configuration/review path; never encourage granting broad credentials to remove an error. A different-client request must direct the user to a separately authorized project, not quietly merge evidence.

Partial results appear as nodes complete. Cancel/reload/reconnect restores server state, not a new run. A failed sibling leaves completed evidence intact. A stale report/changed destination invalidates approval visibly. An ambiguous remote write shows reconciliation guidance instead of a casual Retry button.

## Accessibility, safety and browser acceptance

Label forms and errors; announce meaningful progress; use visible keyboard focus, focus-trapped dialogs, Escape behavior and focus restoration. Do not communicate state only through colour. Verify text zoom, contrast, long package names/descriptions, large nested graphs and mobile overflow. Source fields render as text, never executable HTML; validate outbound links.

Required browser journey: sign in as scoped actor, select project, import real files, inspect parser gaps/egress, ask a question, observe parallel checks, open evidence/conflict, review candidates/tasks, ask follow-up, cancel/resume, edit/review/export, reload history, and test a publication approval without accidental effect. Test other-project IDs, denied sources, stale approvals and unknown outcomes.

Capture screenshots and actual interaction results at each viewport. A TypeScript build, HTTP asset check or generated mockup is not premium-UI/accessibility acceptance. If browser tooling is unavailable, leave that gate unverified and do not invent screenshots or user-test results.
