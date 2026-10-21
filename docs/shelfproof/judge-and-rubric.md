# LLM judge, critique and score interpretation

Implemented rubric/protocol specification; actual judge quality is not yet measured.
An LLM judge is one evaluator, not ground truth or a food specialist.
Use [Self-Refine](https://arxiv.org/abs/2303.17651) as a research basis for the loop
and [judge-bias research](https://arxiv.org/abs/2306.05685) as a reason to measure its
limitations. Published benchmark gains are not projected ShelfProof results.

## Judge boundary

The judge receives the current draft, immutable fact references, declared source
limitations, profile/brief, rubric revision and deterministic findings. It does
not receive a desired score, previous score, model identity, iteration number,
gold labels or customer approval. Do not prompt it to justify a planned adoption.

Producer, judge and reflector use separate contexts through the same provider
port. Shared model/service use remains correlated; role isolation is not model
independence. An unavailable judge yields no score, not an invented zero or pass.

## Proposed rubric

Each dimension has integer rating 0–4 or `unassessable`, plus a brief rationale
and evidence/finding references. Code calculates the weighted score, not the model.

| Dimension | Weight | Full-credit anchor |
| --- | --- | --- |
| Factual fidelity | 30 | All assessed factual statements match identified facts, units and measurement bases |
| Required-attribute coverage | 25 | All profile-required and task-required available information appears correctly; no shortening away required facts |
| Channel/brief adherence | 20 | Text follows the frozen permitted style/profile and AI-provenance rules |
| Clarity | 15 | Readable, unambiguous text without obscured quantities or misleading relationships |
| Brand tone | 10 | Follows the supplied neutral/approved brief without invented experiential or certification claims |

Shared rating anchors: 0 = major unsupported/unusable content; 1 = material changes
needed; 2 = usable only after several corrections; 3 = minor corrections; 4 = meets
the stated dimension. Add task-specific examples on development data before freeze.

`score = sum(weight * rating / 4)` only when all dimensions are assessable. Otherwise
score is null and the row cannot pass automatically. 80/100 is a review-readiness
threshold, not 80% factual accuracy. Deterministic critical/material violations
block readiness regardless of score. Display ratings and blockers before the total.

## Findings and the correction plan

Each finding must contain controller-assigned identity after validation, category,
severity, target draft field/Unicode span, exact offending quote if present, relevant
fact/rule references, concise explanation, proposed constraint and whether source
input is missing. Judge-generated IDs cannot impersonate deterministic rule IDs.

Reject invented facts, out-of-range spans, unrelated source references, duplicate
finding keys, mismatched snapshot/version/rubric or explanations claiming authority
not present in the input. Bounds: at most 20 LLM findings, ten references per finding,
2,000 characters per explanation. Oversized lists cannot expand the agent loop.

Reflection maps each blocking finding to `remove`, `replace_from_fact`, `clarify_basis`
or `request_source`. `retain_with_reason` is allowed for nonblocking suggestions
only; it cannot waive a hard gate. Require every blocking finding to be addressed.
The brief plan is an inspectable edit rationale, not a transcript of internal reasoning.

After revision, findings are recomputed. A producer saying “fixed” or a reflector
relabeling “critical” as “minor” has no effect on stored severity or export eligibility.

## Prevent easy score gaming

- Never expose previous scores/desired threshold in the revision brief; expose facts
  and specific findings. Freeze the rubric throughout a row task.
- Validate required coverage so a model cannot achieve fidelity by deleting the title,
  every product attribute or the required ingredient information.
- Keep length-neutral clarity anchors; more words do not intrinsically earn points.
- Judge the whole text, not only the producer's selected claim annotations.
- Track newly introduced defects and rejected candidates, not only final score gains.
- Preserve version 0 and unchanged cases; do not exclude hard cases after seeing scores.
- In offline paired comparisons, randomize/blind order and include order-swapped
  repeat judgments on a declared subset. Report disagreement, not just mean scores.
- Source text claiming “ignore the rubric” is a prompt-injection case, not a rule update.

## Independent labels and acceptance

Human annotators mark supported/unsupported/contradicted/uncertain claims, required
facts and error severity without seeing version order or model scores. A second
reviewer independently annotates the locked quality subset; disagreements receive
adjudication. Deterministic checks cover explicit numeric/reference/profile rules,
not all semantic support. Report judge false-negative and false-positive rates
against the human labels separately from software validator performance.

Judge score gain, objective error reduction and human preference are three different
metrics. A quality claim needs the latter evidence, plus coverage and uncertainty;
neither a high score nor a plausible correction rationale establishes it alone.
See [evaluation](data-and-evaluation.md) and [release gates](validation-and-acceptance.md).
