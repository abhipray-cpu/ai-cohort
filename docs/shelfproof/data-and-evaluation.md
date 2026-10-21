# Real data, independent labels and improvement evaluation

The implementation gate passed and source acquisition/curation has begun. Read the
[actual validation log](real-data-validation.md) and [status](implementation-status.md)
for measured counts, hashes and discrepancies. Cohort sizes/thresholds below remain
targets until measured. Do not report generated mutations as authentic errors.

## Source and acquisition

Use the official [USDA Branded Foods downloads](https://fdc.nal.usda.gov/download-datasets/),
starting with a frozen listed release rather than scraping retailer product pages.
The [FDC API guide](https://fdc.nal.usda.gov/api-guide/) records the public-domain
CC0 basis. Archive acquisition requires explicit implementation/data-work authority;
no third-party outreach or customer file is assumed. Keep source attribution and
do not imply USDA endorsement of the product or output.

Record archive URL/release, retrieval UTC, byte count, SHA-256, license reference,
schema/dictionary hash, acquisition/parser/mapping versions and all exclusions.
Download to a new-only location with finite transfer/disk limits; validate archive
entries against path traversal, symlinks, expansion ratio and allowed filenames.
Never load the multi-GB release into RAM. Stream selected rows or build a bounded
temporary on-disk index, preserving the raw record and every joined table reference.
Resume acquisition by exact archive hash, not an untracked replacement release.

Proposed storage under gitignored `var/validation/shelfproof-.../`: `raw/`,
`normalized/`, `manifests/`, `gold/`, `fault-injections/`, `runs/`. Do not commit the
archive, customer rows or misleading placeholder labels. The normal app never
downloads the corpus or reads gold. Raw releases are not forwarded to the provider.

## Eligibility and normalization

Target 1,000 distinct eligible product-family records; count scanned, excluded,
duplicate, conflicting, incomplete and eligible records separately. Main positive
cohort: English/US, in-scope packaged foods, known identity, interpretable ingredients
and at least one unambiguous supplied numerical attribute. Preserve a separately
reported incomplete/conflicting cohort rather than testing only clean rows.

Read the actual field dictionary before mapping. The downloaded April 2026 JSON
archive was found to omit its advertised bundled guide; a pinned official external
guide is recorded explicitly, not passed off as bundled/current. Keep FDC IDs, GTINs,
brand owner/name, raw ingredients, nutrient IDs/units/bases, serving metadata,
publication/modification dates and status. Reject ambiguous joins and malformed IDs.
Do not assume serving size is package size, infer density, fill null nutrition with
zero or invent brand claims. Missing optional package quantity means no package-size
claim; missing profile-required facts means `needs_data`.
Restricted claims embedded in an official name are excluded from automatic v1
handling with a recorded scope reason, not stripped to manufacture a positive case.

These are source-snapshot fidelity tests. The [Branded Foods documentation](https://fdc.nal.usda.gov/GBFPD_Documentation/)
identifies provider-supplied data and distinct reporting bases. A source record
does not prove current packaging accuracy; that requires authorized current brand
evidence/review. Product images and regulatory label generation are outside scope.

## Grouping, splits and leakage

Proposed 600 development / 200 calibration / 200 locked-test product-family groups.
All revisions of a GTIN and clearly related variants must stay together; report
family/group counts, not just rows. Detect normalized exact duplicates and near
duplicates before splitting. A declared brand-held-out subset is desirable only
where independently sufficient brand/category coverage exists; do not promise it
without the inventory. Frozen split assignment precedes model output inspection.

Include several food categories, short/long ingredients, mixed numeric units,
missing attributes and realistic copy lengths. Source dates/brand families may
create temporal/domain bias; document it. Tune prompts/thresholds on development,
judge calibration on calibration, and freeze code/rubric before locked test calls.
After test-driven tuning, the touched set is development, not untouched holdout.

Gold labels, corrected reference copy and seeded error descriptions are evaluator-only.
Audit serialized prompts, metadata and repair contexts for label canaries. Do not
send hidden clean answers as judge context. Public-record model pretraining exposure
cannot be ruled out; this is not an unseen-knowledge benchmark.

## Three separate cohorts

1. **Authentic source, generated copy:** actual approved records become model tasks.
   Measure naturally produced errors and revisions without claiming preexisting
   customer defects or proven commercial demand.
2. **Authentic source, injected faulty copy:** deliberately change a unit/basis,
   identity, quantity or unsupported phrase. Track injection IDs and expected
   failures separately. Many variants do not increase independent product count.
3. **Authorized customer workflow:** real drafts, approved facts, current brand brief
   and independent customer review. This is needed for claims about actual editing
   effort or operational value; no such partner is secured.

## Independent labels

Annotate factual claim spans and references as supported, contradicted, unsupported
or uncertain. Mark available/required attributes, claim prohibitions and error
severity. Label readability/tone separately from fact support. First annotator
must not be the producing agent; a second trained catalog reviewer independently
labels the proposed 100-product locked quality subset. Adjudicate disagreement;
record reviewer expertise, time, agreement and ambiguity.

Deterministic fact/reference tests are necessary but not labels for every semantic
claim. Independent reviewers judge source consistency, not medical/legal safety.
Any prospective safety/compliance claim requires a different expert protocol.

## Comparison arms and spend staging

| Arm | Behaviour | Normal / absolute invocation maximum per row |
| --- | --- | --- |
| A: one-shot | Initial producer and evaluator; no revision | 2 / 4 |
| B: equal-budget resampling | Up to four independent producer/judge pairs, same hard gates and selector; no feedback between samples | 8 / 16 |
| C: reflection | Initial pair, then up to two plan/producer/judge triples | 8 / 16 |

All arms share facts, scope, rubric, validator, channel and independent labels.
Report actual calls/latency/known usage and outcome coverage; an early-exit arm
need not spend its maximum. Equal maximum is not equal observed cost. If an exact
initial artifact is reused, retain its receipt and disclose shared versus marginal
cost; do not invent additional observed calls or independent samples.

Proposed stages, **not standing authorization to spend**:

- Audit target 1,000 source records locally and exercise deterministic/test-provider
  workflows; report actual eligible count and execution denominator.
- Six development products, reflection only: at most 96 cumulative invocations
  including repairs. Confirm privacy, actual receipts, cancellation and all stages.
- Separately approve paired development baselines. Six products across all three
  arms have a maximum 216 invocations including the prior reflection calls—not
  three fresh grants that forget earlier usage.
  This reuse assumes exactly frozen artifacts/code/context. If tuning requires a
  fresh reflection arm, the new authorization must also account for every earlier
  call outside the new comparison; do not describe the combined spend as 216.
- Review findings, then authorize larger development/calibration and the locked
  evaluation with explicit IDs, modes, deadline and cumulative allowance. A proposed
  200-product locked comparison can require up to 7,200 calls including repairs;
  do not silently run it because the source corpus is large.

Stop on unknown usage, unsafe tools, quota/auth/privacy/integrity faults or exhausted
grant. Preserve all attempted/pending IDs and invalid judgments. A hold or incomplete
arm cannot be counted as a quality pass. [Recovery policy](audit-and-recovery.md)
does not itself authorize another campaign.

## Improvement metrics

Report initial, each candidate, incumbent and final values with explicit denominators:

- Products with critical/material factual errors; errors per assessed claim.
- Required-attribute coverage and eligible/review-ready/manual/needs-data coverage.
- Findings resolved, unresolved and newly introduced; rejected/worsened candidates.
- Judge rating/score changes and independently judged correctness/preference changes.
- Revision/early-exit distribution, source omissions and unassessable evaluations.
- Calls, wall time, known usage lower bounds, unknown attempts, observed rate basis
  for any monetary estimate, and reviewer minutes on the customer cohort.

Use paired product-family comparisons and product-clustered confidence intervals;
do not count ten claims or injected variants from one product as ten independent
successes. Report category/brand/missing-data strata and failed runs. Never combine
judge score gain with human accuracy into one unqualified improvement percentage.
