# Premium batch review workbench

Workbench code is implemented and built; actual browser/accessibility acceptance
is still pending because no browser connection is available. This is the target
UX specification, with actual implementation mapped in
[implementation notes](implementation-notes.md). Premium means an honest evidence
workflow, not decorative charts or fabricated activity.

## Information architecture

Client workspace -> imports/mapping -> batch authorization -> row review -> version
comparison -> evidence/findings -> exact-version approval -> export manifest.
Show client scope at all times; no global cross-client names/counts to unauthorized users.

```text
┌ Client / batch / source revision ───── remaining calls · hold state ┐
│ Rows                         │ Version comparison                  │
│ search / filters / status    │ original | candidate | incumbent     │
│                              │ title and description diff          │
│ needs data / review ready    ├─────────────────────────────────────┤
│ manual / approved / stale    │ Evidence and findings               │
│                              │ quote → source field / rule          │
├──────────────────────────────┴─────────────────────────────────────┤
│ Adoption reason · score detail · defects · current review/export   │
└────────────────────────────────────────────────────────────────────┘
```

Desktop uses a bounded row queue and a readable comparison/evidence area. On small
screens use Rows / Compare / Evidence / History tabs with stable selection, not
three squeezed columns. Real keyboard, contrast and 360 px acceptance is required.

## Intake and authorization

- File preview displays encoding/mapping errors, exact row count, excluded rows and
  required/optional columns. Do not silently auto-approve a guessed mapping.
- Facts show literal source and normalized value, unit/basis, source date and unknown
  fields. Ingredient and numeric provenance are visible before starting.
- Separate approved facts from existing draft copy and brand-tone instructions.
  Source contradictions/unsupported scope block freeze with actionable reasons.
- Egress modal shows exact redacted fields, destination boundary, purpose, requested
  rows, deadlines and maximum calls. Activation is explicit and owner-authorized.
- No hidden model request on upload, hover, dashboard refresh or health check.

## Row comparison and explanation

Always preserve original/imported or generated version 0, every candidate and current
incumbent. Identify imported versus generated originals. Show rejected/worsened
candidates as history, not erase them to display a monotonic improvement story.
Diff additions/deletions and unchanged facts; color must not be the sole indicator.

A version card shows deterministic blockers first, required coverage next, then five
judge ratings and computed score. Explain “80/100 rubric score, not correctness
probability.” Unassessable is not zero; a failed judge has no valid score.
Score gains, factual errors fixed and new defects are distinct indicators.

Click a finding/claim to open its precise text range and literal source field. Display
GTINs as text and per-serving/per-100-g units explicitly. The correction plan lists
the finding, proposed operation and constraint in plain language. Do not display
private chain-of-thought or claim the system learned a new truth through reflection.

## States and human actions

Queued/running is not complete. `needs_data` lists missing fields; `manual_required`
preserves a useful draft and safe failure reason; `review_ready` is not approval.
Cancelled/failed/stale rows never look like still-running spinners or green successes.
Batch totals separately show selected, attempted, terminal, review-ready, approved,
excluded and pending rows, with original denominators retained.

Reviewer can accept current eligible text with a rationale, reject it, request source
changes or submit a new attributed edit for separately authorized reevaluation.
An edited/source-changed artifact cannot inherit an old score or approval. Review
must not waive numeric/reference/prohibited-claim hard gates. A different authorized
reviewer is required from the row's producer/editor; an owner role does not bypass it.

## Exports and history

The export preview lists approved row IDs, machine-patch fields, provenance labels,
all exclusions/reasons and stale rows. Mark incomplete review artifacts `UNAPPROVED`.
Do not label a CSV review sheet a complete retailer-ready feed. Confirm no price,
stock or unrelated metadata changes and no automatic publication.

History shows per-stage attempts, adoption/rejection, call/known usage, holds,
incident acknowledgements, source/profile revisions and review attribution. Unknown
usage is never displayed as zero/free. Owner-accepted incidents retain a visible
warning in the row and exports, not a green “verified” badge.

Use warm neutral surfaces, clear type hierarchy, restrained accent colors and
amber/red for uncertainty/blocking. Charts are appropriate only for real comparable
data and denominators; do not show an empty “accuracy uplift” dashboard before
independent evaluation exists. Loading/empty/error states need copy and focus handling.
