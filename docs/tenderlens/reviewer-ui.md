# Reviewer UI specification

The interface should feel like a procurement workbench: dense where comparison matters, calm everywhere else. The user should be able to answer “What is required, where does it say so, and what still needs review?” from one screen.

## Information architecture

| View | Main job |
| --- | --- |
| Opportunities | Find active tenders, deadlines, extraction/review status, and owner |
| Opportunity overview | See buyer, documents, amendment timeline, risk summary, and next actions |
| Review workbench | Inspect claims against source PDF, accept/edit/unresolve, handle conflicts |
| Run history | See attempts, validation failure stages, parser quality, and operational errors |
| Approved brief | Read and export a stable reviewed snapshot |
| Settings | Organization profile, users, retention, and integration status |

## Review workbench layout

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ TenderLens  /  Opportunity title       Draft · 8 of 12 claims reviewed │
├───────────────────┬──────────────────────────┬───────────────────────────┤
│ Claim navigator   │ Claim detail             │ Source PDF                │
│ Deadline       !  │ 29 Oct, 17:00 IST       │ Page 14 of 52            │
│ Eligibility    ✓  │ Source: amendment 2      │ highlighted exact quote   │
│ Documents      3  │ Original value struck   │ page thumbnails/search    │
│ Evaluation     !  │ [Accept] [Edit] [Unsure] │ OCR quality indicator     │
├───────────────────┴──────────────────────────┴───────────────────────────┤
│ Validation history  ·  reviewer activity  ·  approve and export        │
└──────────────────────────────────────────────────────────────────────────┘
```

Desktop uses three resizable panes; tablet collapses the navigator; mobile uses sequential claim/PDF tabs. No action depends on color alone. Use explicit labels such as `Verified`, `Needs review`, `Source conflict`, `OCR unclear`, and `Not stated`.

## Visual system

- Typography: highly legible sans serif for UI; tabular numerals for dates, amounts, and scores. Keep cited document typography native in the PDF viewer.
- Palette: restrained neutral surfaces, one strong accent for primary actions, semantic amber/red for uncertainty and failure. Contrast must meet WCAG AA.
- Density: compact tables for opportunity lists and requirement matrices; generous whitespace in claim detail and review decisions.
- Motion: only state feedback and pane transitions; respect reduced motion preferences.
- Copy: say exactly what failed, for example “Deadline quote does not match page 14” with a `View page` action, rather than “AI error.”
- Responsiveness: usable at 1440 px desktop, 1024 px tablet, and 390 px mobile. PDF review at narrow widths may use tabs but must keep the source one tap away.

## Key interactions

1. Upload shows file validation, page count, checksum, extraction progress, and whether OCR was used.
2. Claim click navigates the PDF to the cited page and highlights a matched quote. If exact coordinates are unavailable, show the page and quote text with a clear fallback.
3. Conflict cards show original and corrigendum claims side by side, with dates, pages, and explicit precedence reason.
4. Reviewer edit requires a reason and optionally a replacement citation. The original AI value remains in history.
5. Approval is disabled until all mandatory and deadline claims are reviewed, blocking conflicts are resolved, and export provenance is complete.
6. Run history is a practical troubleshooting view: stage, attempts, recoverability, time, and run ID. Do not show raw sensitive prompts by default.

## UI validation with real documents

Use the frozen public test pack, not lorem ipsum. Ask 5 representative bid reviewers to complete: find the true amended deadline, identify an unmet mandatory certificate, verify the citation, correct one extracted field, and export the approved brief. Observe without coaching. Target at least 4/5 successful completions for every task, median time under 2 minutes per task after onboarding, and no approval of an uncited mandatory claim. Record wrong turns and redesign the relevant interaction before release.

Automated browser tests cover the same path with at least one native PDF and one amended pack. Screenshot review checks layout at desktop/tablet/mobile widths, empty and error states, long requirement lists, and high zoom. Accessibility checks cover keyboard only use, visible focus, screen reader labels, and contrast. The premium standard is achieved when evidence and decisions are fast to inspect, not merely when the screen looks polished.
