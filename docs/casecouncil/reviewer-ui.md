# Premium reviewer workbench

20 October: synthesis is labelled an internal advisory summary, not a customer
letter. The response editor starts from the handler's draft, not the AI voting
summary. Accepted runtime incidents remain visible and require review resolution.
See [measured continuation and limits](real-data-continuation-2026-10-20.md).

Workbench implemented and production build verified; browser interaction and
accessibility acceptance remain open because no browser connection was available.
See [current evidence](implementation-validation-2026-10-19.md).
“Premium” means a fast, legible evidence-review workflow, not decorative
charts, fabricated activity or a wall of agent chat.

## Information architecture

- **Case queue:** workspace, client/case reference, product, owner, source coverage,
  review stage, blockers and last meaningful update. Search/filter by authorized
  fields; no cross-client counts or empty demo metrics.
- **Intake:** document list with immutable revisions, extraction status and page
  gaps; attributed facts, issue list, proposed-response editor and missing-evidence checklist.
- **Egress preview:** redacted excerpts, coverage, model-service boundary, purpose,
  call/time ceiling and explicit authorization before a run starts.
- **Review desk:** issue-level comparison, source highlights, critic findings,
  ballots/consensus and a revised-response diff.
- **History:** revisions, stage attempts, corrections, votes, human decisions and safe receipts.
- **Policy/access:** approved policy versions and capability-scoped administration,
  distinct from the analyst workflow.

## Desktop layout

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Case / client · snapshot · DRAFT / STALE / DEGRADED · Review actions   │
├────────────────┬───────────────────────────┬─────────────────────────┤
│ Issues         │ Decision comparison       │ Evidence reader         │
│ Coverage       │ Current draft vs proposals│ Exact excerpt + source  │
│ Blockers       │ Critic and disputed facts │ Revision / page mapping │
│ Stage progress │ Ballots and retained dissent│ Coverage warnings      │
├────────────────┴───────────────────────────┴─────────────────────────┤
│ Computed recommendation · confidence reasons · usage · human review   │
└──────────────────────────────────────────────────────────────────────┘
```

Desktop starts with three resizable regions, bounded line lengths and an anchored
case header. On narrower screens, use Issues / Decision / Evidence tabs with stable
selection, not three squeezed columns. At 360 px, critical actions, exact evidence
and blockers remain reachable without horizontal page scrolling. Long quotations,
filenames and case references must wrap safely.

Proposed visual language: warm neutral surface, restrained navy/slate typography,
one blue action accent, amber uncertainty and red blocked/error states. Never use
green unanimity styling to imply legal correctness. Use consistent spacing, readable
body type, clear focus rings and sufficient contrast. No brand/logo asset is required
for the documentation stage.

## Decision display

For each confirmed issue, show the proposed resolution and alternatives, separating
policy facts, party assertions, proposed remedy and unverified hypothesis. Proposal
cards have equal visual weight; do not privilege the most verbose/confident role.
The critique panel links each finding to the exact challenged assertion and source.
Accepted, contested and unresolved responses stay visible after revision.

The ballot matrix shows each of three named roles, candidate selected or explicit
abstention/unavailable, and the fixed denominator. A 2/3 majority, missing participant
and no consensus have distinct labels. Dissent is part of the main pack, not buried
behind an export-only appendix. Confidence uses low/medium plus coverage and reasons,
never a pseudo-precise correctness percentage or a “three experts agree” badge.

Clicking a citation opens the authorized redacted-source revision and server-resolved
highlight. Repeated quotes resolve to their stored span, not the first browser text
match. If original page mapping is unavailable, say so. The user's original response
is visibly a proposal, not a source of authoritative policy facts.

## User states and actions

| State | What the user sees / can do |
| --- | --- |
| Empty workspace/case | Honest zero state, supported formats and setup instructions |
| Extraction incomplete | Named unreadable pages/files; replace source or continue as explicitly partial where permitted |
| Awaiting egress grant | Exact preview and data boundary; no background inference |
| Running | Named stages, completed work and actual elapsed/call usage; cooperative cancel |
| Material source changed | Stale banner, source comparison and new-run action; no implicit reanalysis |
| Required role unavailable | Degraded pack with completed work; no false consensus spinner |
| No consensus / unresolved critique | Alternatives and precise evidence/reviewer questions |
| Ready for human review | Findings/dissent, source check, proposed response diff and review form |
| Reviewed historical packet | Reviewer identity and old revision; cannot export as reviewed-current |
| Rights expired / access revoked | No further source/analysis/export access; safe explanation without leaking data |

Actions: save context, replace source revision, authorize run, cancel, mark a
finding reviewed/corrected, record an override with reasons, request evidence,
download an unapproved draft, or approve/download an exact-current reviewed pack.
No button sends a response, pays a claim, clears automated blockers or manufactures
consensus. A human override is clearly separate from the automated result.

## Browser acceptance scenarios

1. Sign in, create a client-scoped case, upload an authorized text PDF and plain-text
   source; inspect coverage and confirm the issue list.
2. Review redaction/egress preview and authorize exactly one run despite double-click/retry.
3. Follow actual stage status; reload during critique/balloting without losing state.
4. Inspect a cited source, disputed critique and a 2/3 result with retained minority view.
5. Trigger partial extraction, explicit abstention, missing role, timeout and unavailable
   synthesis; earlier work remains visible without a false success badge.
6. Correct a recommendation; require a qualified, scoped human review and attribution.
7. Change a source after review; immediately block reviewed-current export and show why.
8. Verify draft versus reviewed downloads, vote history and exact revision provenance.
9. Revoke access in a second authenticated session; source/API/download requests stop.
10. Keyboard-only intake/review/export, visible focus, labelled controls, screen-reader
    stage changes and mobile/tablet/desktop layout; no motion-dependent information.

Test accessible names, focus restoration on source drawers, async status announcements,
error recovery and contrast against the chosen accessibility target. Automated checks,
manual keyboard/screen-reader checks and screenshots have different roles. A build
or frontend-domain test is not browser acceptance. If the supported browser connection
is absent, report that gate unexecuted, not passed by screenshots from a mockup.
