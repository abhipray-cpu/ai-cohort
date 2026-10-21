# Product, buyer and commercial scope

Status: proposed product, not a deployed or commercially validated offering.

## Buyer and job to be done

Start with grocery-commerce agencies managing English-language packaged-food
listings across client brands. The paying sponsor is the agency owner/content lead;
operators are catalog specialists; a brand-authorized reviewer approves changes.
Manufacturers with an internal ecommerce team are a secondary buyer, not another
MVP persona to implement in parallel.

The job is: take an approved product-data revision and inconsistent/unfinished
listing copy, produce a clearly reviewed patch, and show what was changed and why.
New products, packaging updates and copy refreshes create recurring batch work.
Frequency, budgets and willingness to pay must be established with actual customers.

Hypothesized value: less manual checking/rework without more unsupported product
statements. Neither improved conversion, fewer returns nor retailer approval is
an established outcome or a promise.

## Initial paid workflow

1. Agency creates an isolated client workspace and records data/egress authority.
2. Upload a bounded approved fact CSV/JSON and optionally existing listing drafts.
3. Map fields, inspect incomplete/conflicting records and freeze the input revisions.
4. Preview exact model context and authorize a bounded batch.
5. Produce/evaluate/critique/revise copy, retaining version 0 and every later version.
6. Reviewer inspects factual changes, findings, remaining issues and comparison history.
7. Explicitly approve selected current patches or request data/reject them.
8. Download patches, evidence/metrics and a separate unresolved-row report.

No customer review decision is prefilled as approved. No background process pushes
the patch into a storefront, retailer account, source CSV or PIM.

## MVP scope

- English/US text for ordinary shelf-stable packaged foods and nonalcoholic drinks.
- One versioned Google Merchant text profile, agency/client isolation, CSV/JSON
  import, title/description repair or generation, exact fact references and batch review.
- A frozen source fact pack is the authority *within the task*, not a certification
  that the real package or current formulation matches that record.
- Source-backed identity, literal ingredients and numeric values retain provenance.
  Missing package size is not filled from serving size. Brand owner is not assumed
  to be the consumer brand. Unknown attributes stay unknown.
- Generate only nonregulated descriptive copy from supplied facts and allowed brief.
  Dietary, allergen-free, organic/certification, medical and performance claims are
  not generated in the first release, even if a model thinks them plausible.
  If such a phrase is embedded in the source product's official name, do not
  silently rename it to evade a rule: preserve the raw identity and mark the row
  outside v1 automatic scope for explicit human/source handling.
- Review CSV is spreadsheet-safe; machine patches preserve exact typed semantics.
  Export is a partial content patch, not an upload-ready complete merchant feed.

Out of scope: printed nutrition labels, recipe/formulation calculations, label OCR,
images/PDF ingestion, infant/clinical nutrition, supplements, alcohol, price/stock/
shipping edits, medical advice, legal certification, live retailer APIs, autonomous
publishing, cross-language translation and replacement of an enterprise PIM.

The first channel profile does not make the product a complete Google policy engine.
Jurisdiction/channel additions require new source research, contracts and validation.

## Illustrative product behaviour

Authored example, not an acquired record: a source says 400 g net quantity and
8 g sugar per 100 g. The draft adds an unsupported certification and changes the
sugar basis to per serving. Evaluation should identify both errors independently.
Revision may remove the unsupported phrase and correct/remove the numeric sentence;
it cannot alter the source nutrient or invent serving mass to justify the draft.

If the source conflicts or lacks a required field, end with `needs_data`. A polished
but ungrounded sentence is not a successful repair.

## Positioning and commercial experiment

Salsify/Akeneo already compete in content enrichment and validation. The proposed
entry point is a low-integration, CSV-first review layer with evidence-linked
before/after patches and visible regressions. It must earn that position; the
reflection algorithm itself is not a durable competitive moat.

Pilot hypothesis: $250 for a bounded 100-product batch with approved facts and
existing copy. This is not a quote from competitors or proven willingness to pay.
No pilot, customer interviews, outreach, payment or procurement commitment exists.

Measure reviewer minutes per product, material errors before/after, unresolved
coverage, observed model usage and delivery effort. Compare against the agency's
current workflow and one-shot generation. A paid pilot needs explicit authority
and safe data handling; do not invent a buyer or outsource verification to the judge.
