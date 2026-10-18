# Routing, complexity and confidence

Latest amendment: [local review-draft routing](local-routing-validation-2026-10-18.md). An opt-in JSON-tree scorer precedes the LLM route and requires an exact service profile hash. Its negative band is benchmark-scoped; the real positive band failed and is disabled. Correlated qualification entities prevent independent automatic-confidence claims. All local exits remain `needs_review`, `calibrated=false`; every retrieved candidate must qualify for a negative exit. A 600-pair offline challenge produced 101 exits/one disagreement. The live comparison stopped on quota and cannot establish the savings gate. See the [study guide](study-guide.md) for draft completion versus calibrated acceptance.

Latest implementation: [exact-context draft reuse and runtime receipts](receipts-and-repeat-work-2026-10-18.md). Opt-in reuse avoids repeated inference for unchanged context; revalidated proposals remain uncalibrated review drafts, not confidence exits. Invalidation covers source/master/candidates, policy binding, expiry, human review and cancellation. Fair evaluation must give baselines equivalent cache conditions and distinguish fresh-row savings from repeat-work hits. Qualified empirical confidence remains blocked.

Status: target behavior, not a trained or tested policy. No CatalogBridge model profile or calibrated threshold exists yet.

## Define the task before routing

A task is one supplier row against a frozen master/index revision. Retrieval returns up to 10 candidates initially; a row may compare several candidates but shares one cumulative allowance. Candidate-pair accounting must not masquerade as cost per supplier row. Store task, pair and attempt IDs.

Normalize formatting and explicit units without inventing attributes. Preserve originals and reversible evidence locations. Use normalized brand/model tokens, lexical retrieval and attribute filters first; optional learned retrieval must earn its added resource cost. Exact identifiers, when actually supplied, are useful but do not override conflicting variant/pack/condition evidence. Missing brand/model is missing evidence, not a wildcard.

Do not use benchmark `label`, `cluster_id`, `is_hard_negative`, `unseen`, split IDs or pair filenames as routing features. Candidate lists come from master records, not gold-provided positive pairs. Price proximity is not identity; price difference alone is not a contradiction. Model output cannot change the candidate index.

## Initial explainable route policy

Implementation v2 distinction: **draft completion is not calibrated early exit**. A validated binary proposal may stop spending while remaining `needs_review`; automatic recommendation still requires calibration plus verified identity. Missing identity blocks acceptance, not escalation after `insufficient_evidence`. Invalid output escalates once within remaining allowance. The implemented complexity gate remains candidate count >3, or missing brand with multiple candidates; the broader features below are design targets, not implemented learned routing. See [actual behavior](implementation-and-operations.md).

| Route | Admission | Possible exit |
| --- | --- | --- |
| Deterministic | Reliable supplied identity evidence and required variant checks; or an explicit incompatible attribute | Accept/reject pair only if this route's calibrated policy qualifies; otherwise continue |
| Economy model | Ordinary ambiguity, bounded candidates, supported domain, verified economy profile | Validated same/different proposal meeting route-specific acceptance policy; otherwise escalate |
| Stronger model | High candidate ambiguity, incomplete identifying evidence, model/check disagreement or out-of-calibration features | Validated decision if policy qualifies; otherwise review |
| Manual review | Missing capability, egress denied, budget unavailable, uncalibrated domain, failed evidence, unknown usage | Explicit unresolved row; no invented match |

Complexity features: missing identifying fields, competing candidate score gap, candidate count, contradictory capacity/form-factor/quantity/condition, input length and calibrated domain coverage. A cheap classifier may produce features; using another LLM just to route must be separately budgeted and benchmarked. Start deterministic to make overhead and decisions explainable.

An owner-approved profile contains actual configured model identity, allowed reasoning settings, verified effective identity evidence, runtime version, availability timestamp, usage-field support, enforced limits and rate-card basis. No hardcoded model names or assumptions about account entitlements. If observed identity is unknown/mismatched, retain incurred usage and reject acceptance. Two names pointing to the same effective model do not establish multi-model routing. Different reasoning levels are a separate experiment, not a substitute.

## Confidence is empirically qualified acceptance

**18 October implementation guard:** owner/legacy profiles default to `evidence_status="operator_attested"` and cannot activate confidence acceptance. The upload API rejects self-declared `empirically_verified`. No production empirical verifier/importer currently exists; explicit verified profiles used in unit tests are fixtures, not qualification evidence. Profile, instruction asset and relevant runtime/store code participate in binding. [Actual qualification audit](runtime-hardening-2026-10-18.md) rejected the no-model capacity shortcut; neither repeated benchmark entities nor a high point estimate can replace the frozen sample/uncertainty requirements.

Model self-reported confidence is diagnostic only. Acceptance requires schema/evidence validity, no hard identity conflict, sufficient field coverage, an applicable calibration profile and a route score meeting its frozen threshold. A strong model can still be wrong.

Build route scores from development data using appropriate calibration (for example a validated classifier or reliability bins); publish method, bin sample counts, reliability, precision/coverage and uncertainty. Keep threshold fitting and evaluation independent. Sparse bins/categories abstain by default. Changes to model, prompt, input mapping, retrieval, policy or scorer invalidate the applicable calibration until reevaluated. No production feedback is silently used to improve the score in place.

Auto-match thresholds prioritize false-link risk. Auto-nonmatch thresholds must also preserve recall; rejecting all pairs can otherwise look cheap and accurate on negative-heavy data. Report risk–coverage separately for same/different outcomes. A row match additionally requires resolution of conflicting accepted candidates; two incompatible accepted candidates force review, not a largest-confidence tie-break.

## Early exit and bounded escalation

Record `exit_stage`, policy version, evidence checks, calibrated score/band, threshold and next-stage calls avoided. Deterministic exits should consume zero model calls. Economy exits require observed evidence that a stronger call was not dispatched. Score low confidence before attempting escalation; choose stronger immediately when the economy attempt is predicted unlikely to help, rather than always paying for both.

Initial maximum: two normal model attempts per row plus one schema-repair attempt shared across all stages; repairs are never free and cannot bypass the remaining allowance. Row call/time/token limits override this maximum. A repair may fix formatting, not erase contradictory evidence. No endless retry on malformed JSON, refusals, timeouts or quota errors.

Budget shortage, unknown usage, provider timeout or unsupported domain leads to a typed unresolved reason. Preserve prior row results and every failed attempt. Do not downgrade quality thresholds to meet a cost target. Optional continuation requires explicit remaining/top-up authority and does not reset original usage or attempt history.

Implemented recovery: each validated proposal has an attempt-bound history entry. If a later attempt fails, the last valid draft remains reviewable with `degraded=true` and a `partial_proposal_retained` audit event; unknown usage still blocks further calls. No valid proposal means the row remains failed. Oversize serialized inputs are refused before reservation/dispatch and do not create fictitious unknown usage.

## Required tests

Verify deterministic exit dispatches no model; easy/complex profiles route differently; effective models are distinct; low confidence escalates once; trusted-looking self-confidence cannot clear missing evidence; conflicting variants block acceptance; candidate omission remains visible; unavailable model does not silently fallback to an unapproved one; calibration drift disables automatic acceptance; budget/restart/cancel races preserve accounting. Combine fixture routing checks with actual installed-model runs and the independent quality comparison in [acceptance](product-acceptance.md).
