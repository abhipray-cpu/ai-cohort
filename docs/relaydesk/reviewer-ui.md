# Premium investigation-continuity workspace

Status: React client implemented and built; frontend state/API/HTTP tests pass. Browser connection was unavailable, so visual/keyboard/viewport/accessibility and actual two-browser acceptance below remain unrun. [Current implementation](implementation-and-operations.md), [validation](implementation-validation-2026-10-16.md).

## Product layout

Desktop: compact account/case rail, central conversation and take-over handover, right contextual panel for memory/evidence. Header always shows account/case, source cutoff, latest memory revision, index readiness and whether the displayed handover is current/reviewed/partial.

Use deliberate spacing, readable dense typography and a restrained slate/neutral palette with labelled amber uncertainty and red conflict states. A premium technical workspace should emphasize trustworthy history, not decorative memory scores, fake progress or a generic full-screen chatbot.

Primary navigation: Conversation, Handover, Attempts, Memory, Sources and Activity. **Take over this case** is the main action; “What changed since my last session?” is a contextual entry point. A fresh engineer should see scope, current environment, unresolved questions and explicit next owner before any long prose.

Tablet/mobile: collapsible scope rail and explicit Conversation/Handover/Memory/Evidence navigation. Acceptance viewports: 1440×900, 1024×768, 390×844. These are future checks, not generated mockup proof.

## Screens and states

| View | Required interaction |
| --- | --- |
| Case list | Authorized cases only, latest activity/readiness and non-sensitive empty states; revocation removes metadata |
| Import | Source preview, public/private warning, consent, page/message counts, bots/duplicates/edits and completeness |
| Conversation | Persistent source-linked turns, bounded-buffer indicator, recall mode, no auto customer sending |
| Take-over handover | Current reported environment, attempts/outcomes, active/superseded workarounds, hypotheses, commitments and unknowns |
| Attempt timeline | Proposed/performed and successful/failed/unconfirmed outcomes visibly distinct; version/reporter filters |
| Memory drawer | Kind/status, source quote, attribution/date, applicability, revision, correction/rejection and why recalled |
| Relevance details | Named score components/rank policy, not a misleading confidence percentage |
| Corrections | Exact old/new preview, expected revision and dispute handling; no silent merge |
| Session freshness | Updated elsewhere, indexing pending, reconnect/reset and stale-draft states |
| Source reader | Exact quoted spans and original source metadata, safe text rendering, edited-body chronology caveat |
| Activity | Extraction/compression/index/recall coverage and failures; separate AI success from fallback persistence |
| Review/export | Exact revision, reviewer attribution, partial acknowledgment, source/coverage manifests retained |
| Forget workflow | Distinguish suppression from erasure, affected dependent artifacts, backup/download limitations and explicit confirmation |

Don't label a participant-reported fix “verified.” Don't show “all remembered” when data is unprocessed or a model summary omitted items. If semantic retrieval is unavailable, display that fact rather than present keyword results as vector recall.

## Two-session acceptance journey

Session A imports a real thread, reviews privacy/coverage and starts a conversation. Force buffer overflow, then ask a paraphrased question about an earlier source. Inspect vector-derived recall, source and ranking explanation. Restart API/worker and verify the same authorized history is recoverable.

Session B opens the same case under a separately authorized engineer. Correct one memory in A; verify B shows the new revision and pending/ready vector status. Submit simultaneous stale edits and verify conflict handling. Ask an as-of question; ensure the current correction is not leaked into a historical cutoff where it was unavailable.

Erase a selected source/derived item while a generation job is running. Verify no dependent stale answer/export is served; show clear limitation for previously downloaded exports. Revoke B's grant and verify case lists, events, suggestions, evidence and cached views no longer expose content. Test unrelated accounts with near-identical language.

Review/export a partial handover; limitations must survive Markdown/JSON and print. A source/model failure must leave successful durable evidence visible. Do not call this journey passed until actual browser interaction is recorded.

## Accessibility and visual QA

Keyboard navigation, labelled controls/errors, visible focus, focus-trapped dialogs, Escape/focus restoration, announced meaningful updates, reduced motion and non-colour state labels. Verify zoom/contrast, long logs/URLs, right-to-left/unicode inert rendering where encountered, small-screen overflow and source text escaping. Avoid announcing a large event stream on every poll.

Record actual screenshots and results for all viewports, keyboard/mobile checks and long/partial/conflicting cases. TypeScript build, HTTP API checks or mockups do not establish usability. If supported browser tooling is unavailable, leave the gate open; never fabricate screenshots or successful interactions.
