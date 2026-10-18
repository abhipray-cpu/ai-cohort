# Product definition

Status: proposed scope, 17 October 2026. No customers, revenue, measured accuracy or savings claimed.

## Buyer and job to be done

Initial buyer: catalog operations lead at an electronics retailer, distributor or small e-commerce agency handling recurring supplier lists. Start with text-described branded electronics, where model, capacity, form factor and pack quantity can determine identity. Do not promise equivalent reliability for fashion, furniture, refurbished goods or multilingual catalogs without separate evidence.

Job: map a new supplier's listings to an existing master catalog without attaching price/availability to the wrong variant, while avoiding repeated manual inspection of obvious cases. Existing matching/feed vendors establish a commercial category, not an underserved segment; see [research](research-and-sources.md).

Value proposition to test: **verified catalog mappings with explicit processing budgets, clear exceptions and cost per usable decision**. The router is internal machinery; the customer-facing deliverable is an evidence-linked mapping file and a manageable review queue.

## Workflow and example

1. Owner creates a workspace, grants roles, chooses an approved model/egress profile and budget.
2. Operator imports a master catalog and supplier list, previews field mappings and validation errors, then freezes immutable revisions.
3. System retrieves a bounded candidate set per supplier row; search is independent of evaluator labels.
4. A deterministic identity check or selected model proposes a pair decision with literal supporting fields and conflicts.
5. A calibrated accept policy can stop early; uncertain cases may escalate within the remaining allowance. Exhaustion preserves earlier decisions and produces explicit unresolved rows.
6. Reviewer inspects evidence and candidates, accepts/corrects a link or leaves it unresolved. Changing a source or rule invalidates dependent recommendations.
7. Authorized exporter downloads a version-bound file with reviewed and unreviewed status distinguished; analytics show the full batch denominator.

Illustrative fixture, not a measured result: an incoming “8GB DDR4 3200 SODIMM” listing must not map to an existing “8GB DDR4 3200 UDIMM” merely because most title words agree. Missing form factor should normally prevent automatic identity acceptance; a confident model cannot invent it.

## Decision semantics

Pair outcomes: `same_product`, `different_product`, `insufficient_evidence`. Row outcomes: `recommended_match`, `no_verified_match`, `needs_review`, `failed`, `cancelled`. Review status is orthogonal: `unreviewed`, `accepted`, `corrected`, `rejected`, `stale`.

`no_verified_match` means no safe link was established among searched candidates; it is **not** proof the item is new or absent from the entire catalog. The default export contains only current explicitly reviewed links. An optional separate recommendations export must be conspicuously labeled unreviewed and never ready-for-import by default. Multiple supplier rows may refer to one master product; one supplier row must not silently link to several incompatible variants.

## Release scope

Required: bounded CSV/JSON text feeds; strict field mapping and immutable revisions; candidate retrieval; deterministic attribute checks; real two-model routing; cumulative token/call/time allowances; calibrated exits; review UI; scoped authentication; durable worker/checkpoints; lineage and audit; safe mapping export; reconciled cost/quality analytics; real-data evaluation and Windows acceptance.

Excluded: arbitrary website crawling, image matching, executable spreadsheet uploads, marketplace credentials, stock/price writes, automatic SKU merges/deletions, repricing advice, inferred missing specifications, autonomous purchasing and claims of full offline inference. Supplier prices are evidence attributes, not commands to update commerce systems.

## Commercial experiment

Offer a paid onboarding pilot using the buyer's authorized catalog, then consider a recurring workspace subscription with processing allowance and clear review responsibilities. No fixed price or willingness-to-pay is established. Meter resource units transparently; do not sell fabricated per-token subscription invoices.

Before scaling, recruit consenting buyers under separate authority, measure their current minutes per 1,000 rows, double-check a blind error sample, and compare assisted workflow time including review/corrections. Record processor/model costs, hosting and support time separately. Proposed usefulness target: at least 30% lower median hands-on time without worsening independently reviewed incorrect-link rate. This is a hypothesis requiring actual users, not a dataset metric.

## Non-negotiable behavior

No lower cost obtained by hiding failed rows, discarding retries or shifting all work to reviewers. No automatic match from price/title similarity alone. No new model or increased batch budget without authorized configuration. No silent reset after retry/restart. Documentation completeness is not implementation, benchmark agreement is not correctness, and a good macOS run is not Windows release acceptance.
