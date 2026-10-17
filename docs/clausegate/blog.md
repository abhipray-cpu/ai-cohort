# The hard part of a human-in-the-loop agent is keeping approval valid

*Day 6 of our AI product challenge. Build and complete development-data evaluation, 17 October 2026. Draft only; not published externally.*

A reviewer accepts an NDA exception. The document changes before the workflow resumes. Does the old approval still count?

That revision problem became the design problem behind ClauseGate: preserve the meaning and authority of a human decision across time.

ClauseGate is an NDA exception-review workspace. Its proposed buyer is a team with approved contract positions and a queue of deviations awaiting review. The commercial hypothesis is less reviewer effort and waiting without more missed exceptions. We have not yet proved that outcome with customers.

It does not sign agreements, send messages to counterparties or certify legal safety.

## The model proposes; the system determines who must decide

A model can propose whether a passage supports, contradicts or does not mention a proposition. That interpretation is separate from the organization's policy.

A well-supported clause may still require an exception. An uncertain interpretation needs source review. Missing business context needs a clarification. An unreadable source needs a readable replacement, not someone clicking “accept risk.”

ClauseGate keeps those concerns separate. The model returns strict Pydantic-validated proposals with source references. Deterministic rules produce blockers and scoped requests. Current authorization determines who may respond.

That distinction matters because structured output is not truth. A schema-valid interpretation can be wrong; a real quotation can omit the exception that changes its meaning.

## Five concepts, one durable workflow

The product combines uncertainty detection, pause, targeted human input, resume with validated context and an audit trail.

Uncertainty is not a percentage invented by the model. Missing source coverage, conflicting proposals, unknown company facts and mandatory policy review can independently require a person. The model's own supported flag remains uncalibrated.

Pause means committing a source-bound checkpoint, request and audit before releasing the worker. It does not mean leaving a model process asleep until somebody returns tomorrow.

Human input is typed. A clarification supplies facts. An interpretation correction changes a proposed meaning. An exception response accepts only a permitted deviation. A final review acknowledges the exact internal packet. These are different decisions with different authority requirements.

Resume checks what changed while the person was away: source, playbook, business context, findings, role, assignment, expiry and restore epoch. The checks run again before the result can be used or exported.

The audit connects those transitions. It is an engineering record with explicit trust limits, not an automatic legal certificate.

## The failures made the design more concrete

Test-driven work exposed blank rationales, confirmations that could secretly change a label, expired authority and stale contexts. Another test showed why a readable PDF heading cannot establish that an image-only body was extracted. We now flag image content conservatively; even a logo can make a PDF partial. That is not OCR capability.

The most surprising failure involved a valid audit.

During 100 legitimate context updates, concurrent authenticated API reads returned 109 false integrity conflicts in 600 requests. The final audit verified correctly. Multiple SELECTs had observed different committed snapshots and mistaken the mismatch for tampering.

We reproduced the interleaving before fixing it. Short read fences now cover the relevant case/audit/source boundaries and ordinary anchor publication. Backup verification and copying use the same fence, with a separate SQLite source connection for the copy. Source downloads authorize and retrieve bytes atomically.

Fresh actual HTTP stress passes all 600 reads during 100 updates with a valid audit. The tradeoff is serialization: these short operations reserve the domain writer. This is a conservative consistency fix, not a claim of unlimited concurrency or proven performance on an older Windows laptop.

## We evaluated real documents, not generated success stories

The retained ContractNLI corpus contains 607 document IDs, 606 exact-distinct texts and 10,319 published document/hypothesis labels. One unsafe archive member was quarantined rather than extracted. Corpus integrity was verified, and annotations stayed outside model context.

For natural model evaluation, we retained a frozen 30-document development run and evaluated the other 31 documents under the same product code. The two cohorts have no overlap. Together they cover all 61 official development NDAs and 1,037 predictions.

All 61 analyses completed and stopped for human input. They matched 790 of 1,037 labels: 76.18%, with three-way macro-F1 0.6995. The training-only per-hypothesis majority baseline matched 706 labels, with macro-F1 0.6325.

Evidence-token micro-F1 was 0.5370 using our documented overlap scorer—not the official benchmark scorer or proof of complete support.

The uncomfortable result is the important one: 162 of 637 findings marked supported were wrong against the published annotations. That is a 25.43% error rate in the very subset a superficial demo might treat as trustworthy.

We cannot turn that flag into autonomous clearance.

## Completion, grounding and correctness are different achievements

The repairs improved stage completion and exact-source provenance. They did not solve semantic reliability.

An earlier paired comparison made this especially clear. Recovering provider failures increased total label matches, but correct answers on previously usable pairs fell from 341 to 331. A higher total concealed a conditional regression.

Exact quotations also improved evidence precision while reducing recall. A smaller genuine excerpt can still miss a relevant qualifier.

We therefore retained the failed/interrupted campaigns, scored original proposals before reviewer corrections, and pooled counts rather than averaging batch F1. Repeated development documents were not counted as additional independent contracts. The official test documents were not sent to inference.

Even the complete development set is not blind or qualified acceptance. Published template overlap, correlated hypotheses and possible model-training exposure remain limitations.

## A person in the workflow is not automatically independent evidence

Alongside semantic scoring, 300 workflow cases on distinct real texts passed 3,314 mechanical assertions. The company policies and reviewer responses were explicit automated fixtures, not actual organizational approval histories.

Fresh authenticated HTTP journeys exercised natural model output, interpretation review, exception response, worker continuation and exact reviewed export. Twelve original-PDF upload/download journeys passed 72 checks. An actual worker restart drill passed seven checks, and a concurrent backup/later-erasure/quarantine/fresh-authority drill passed eleven.

Those results establish controlled system behavior. They do not establish that a qualified person would approve the contract or that customers save time.

The corpus's 374 safely named original PDFs were also checked: 162 remain conservatively partial. Passing text integrity is not a complete visual extraction assessment.

## Implemented is not production-accepted

The final regression suite passes 346 Python tests, four frontend tests, the production UI build and lint checks. Six engineering/integration gates pass.

Four acceptance areas remain blocked: qualified held-out semantic quality, actual two-person browser/accessibility, the target Windows/protected-edge/resource environment, and customer usefulness. No browser was connected for visual acceptance, and no customer success or target-host deployment is claimed.

The service stores its workflow locally and uses an adapter to installed Codex; inference may still be remote and needs explicit egress permission. A local audit chain is not immutable against its administrator. Restore must apply current erasures and require fresh authority, rather than treating yesterday's memberships and approvals as valid today.

The lesson from ClauseGate is that a human-in-the-loop agent must preserve the meaning of a decision—not merely collect a click. Real-data validation should make it easier to see where that promise holds and where it does not.

[Study guide](study-guide.md) · [Complete validation results](development-validation-2026-10-17.md) · [Architecture](architecture.md) · [Research and sources](research-and-sources.md)
