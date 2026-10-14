# Reviewer UI specification

**Primary interface is RAG chat.** `/` opens conversation history, a follow-up composer and per-turn evidence. Citation chips show exact quotes and stored passages; weak evidence is labelled low confidence and progress reflects real worker events. Enter sends; Shift+Enter adds a line. Threads persist at `#chat/{id}`. General questions need no environment form. See [chat design](chat.md). The specification below now describes the optional secondary review/export surface (`#workspace`); source management is at `#knowledge`. Browser acceptance remains open.

The welcome disclosure names and explains all four concepts. Completed answers expose whether indexed context was retained and whether search fallback was unused, fetched evidence, empty, unavailable or failed. These strings are driven by actual events and evidence origins, not optimistic UI defaults. Presentation unit tests check low-confidence and fallback labels; no screenshot or keyboard-interaction acceptance is claimed without a connected browser.

Interface specification. The core workbench is implemented; actual browser acceptance remains open. The primary task is to prepare a correct customer reply while checking its evidence and limitations. The user can inspect the ticket, draft, and source passage together.

## Views

| View | User job |
| --- | --- |
| Case queue | Find active cases, missing details, escalations, and reviewed replies |
| Investigation workbench | Compare ticket/environment, reply, and evidence |
| Clarification/escalation | Ask for precise missing details or package an unresolved investigation |
| Knowledge sources | Inspect approved source versions, freshness, visibility, and refresh status |
| Investigation history | Understand evidence additions, search attempts, failures, and revisions |
| Approved reply | Copy/export exactly the revision that was reviewed |

## Desktop layout

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ ResolveDesk / Backup fails          Partial evidence · Needs review     │
├───────────────────┬───────────────────────────┬──────────────────────────┤
│ Customer question │ Customer reply draft      │ Evidence                 │
│ Exact error       │ Claim text [1]            │ PostgreSQL 17 / pg_dump  │
│ Server: 17        │ Qualification [2]         │ Section and exact quote  │
│ Client: unknown ! │ Missing detail callout    │ Indexed / Found by search│
│ OS: Windows      │ [Edit] [Approve]          │ Version and snapshot date│
│                   │ Internal investigation tab│ [Open official source]   │
├───────────────────┴───────────────────────────┴──────────────────────────┤
│ Clarification: Which pg_dump version is used?   Investigation history   │
└──────────────────────────────────────────────────────────────────────────┘
```

Use three resizable panes at 1440px; at 1024px collapse the case detail pane; at 390px use ticket/reply/evidence tabs. Preserve the selected claim and evidence while switching tabs. Keep the evidence one action away. A screenshot must never hide an uncertainty state simply because another pane has focus.

## Visual and interaction system

Use restrained neutral surfaces, a clear accent for primary actions, legible typography, and monospace styling only for errors/commands. Long URLs and stack/error text wrap without breaking the layout. Status always has a textual label and explanation. Keep loading indicators tied to meaningful stages: searching saved knowledge, checking evidence, searching official docs, preparing reply.

Target WCAG AA contrast, visible focus, semantic controls, keyboard navigation, reduced-motion support, and useful screen-reader names. Do not communicate evidence strength by green/red alone. Product users see actionable limitations rather than parser, schema, or provider internals; detailed diagnostics belong in history.

## Required behaviors

1. **Environment:** show server/client versions separately. An unknown value is visually distinct from a selected default. A required missing fact offers a focused question the engineer can copy.
2. **Inline evidence:** selecting a citation opens the stored passage with heading, version, exact supporting quote, and source provenance. An optional external link is secondary to the pinned snapshot.
3. **Support labels:** show supported/partial/conflicting/insufficient with concrete reasons. Never display unsupported numeric certainty. A label must not look like human approval.
4. **Search:** visibly indicate why fallback was needed and whether it succeeded. Found-by-search sources are labelled. If search is unconfigured or unavailable, explain the remaining evidence gap and retry/escalation options.
5. **Conflicts:** display conflicting passages together, including version and authority differences. Conflicts and open questions sit above approval controls rather than in a collapsed audit section.
6. **Editing:** distinguish customer text from private investigation notes. Material edits create a revision and invalidate approval. The final preview contains the exact customer-facing content.
7. **Approval:** require review of the current revision and its limitations. Conflicting/insufficient cases lead to clarification or escalation, not a resolved-answer export. No automatic send action.
8. **Export:** approved reply text and authorized public citations export to Markdown/JSON. Internal URLs and excerpts require explicit authorization; the preview shows precisely what will leave the workbench.
9. **Failure/recovery:** preserve a validated candidate and fetched evidence across operational errors. Show failed stage, safe explanation, and bounded retry; incomplete model output is not displayed as an approved reply.

## Browser acceptance

Use actual acquired cases, including the public backup mismatch and a reproduced restore error. Five representative support engineers perform: identify missing client version, verify a cited rule, inspect conflicting guidance, correct a draft, export a reviewed reply, and escalate an unanswerable case. Target at least four of five completions per task without coaching. Compare time to a manual investigation baseline; log wrong turns and corrections.

Automated browser coverage follows case creation → investigation → evidence click → correction → reload → approval → export. Add search-failure, source-refresh, private-evidence, and revision-conflict cases. Visually inspect 1440px, 1024px, 390px, 200% zoom, long content, loading, empty, and error states. Build and API tests are prerequisites, not substitutes for browser acceptance. If the browser is unavailable, leave the visual gate open and record why.
