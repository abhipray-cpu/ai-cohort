# The judge gave it 100. We still blocked the draft.

*Day 10 of our 14-day, 12-product challenge: building ShelfProof, a self-reflecting
packaged-food listing review agent.*

One result from ShelfProof explains the product better than a perfect demo could.
An LLM judge gave a generated listing a score of 100. Our deterministic checks
still found four blocking reference-annotation defects.

The draft did not become review-ready because the model liked it. It entered a
bounded correction loop. A revised version resolved the blockers without
introducing new ones, and the application selected it. The judge score stayed 100.

That was a useful improvement—but it was not a higher score, four independently
proven factual corrections or evidence that the judge was reliable. It was a
reminder of the distinction we wanted this product to preserve: **models can
propose improvements; they do not own the acceptance rules.**

## A buyer problem, not an invitation to generate more copy

ShelfProof is aimed at grocery-commerce agencies managing packaged-food listings
for multiple brands. Its proposed job is to turn approved facts and draft copy
into a clearer review handoff: show unsupported claims, propose supported repairs
and retain an explanation of what changed.

That is narrower than generating “better marketing.” The first profile requires
literal brand and product identity, package quantity/unit and the complete ordered
ingredient list. It does not infer dietary claims, certify food safety, generate
regulatory labels or publish listings to a retailer.

The intended commercial value is a more accountable review workflow. We have not
yet demonstrated customer time savings, willingness to pay or production readiness.
Those claims cannot be created by adding an agent loop.

## Give reflection an observable job

The Day 10 concepts were execute, evaluate with an LLM judge, critique, regenerate
with constraints and log improvement metrics.

In ShelfProof, execution either creates version zero from a frozen fact pack or
starts with an imported draft. Deterministic checks inspect the copy, then a
separate judge context returns structured ratings and findings. If the draft needs
repair, a correction planner names the findings it intends to address, the allowed
operations and the facts supporting those edits.

Only then does regeneration produce a candidate. The candidate is checked and
judged again. Code decides whether it replaces the incumbent.

“Critique reasoning” here means a short, inspectable finding-and-edit rationale.
It is not a request to expose hidden chain-of-thought. “Self-reflection” means
another bounded inference step, not an update to model weights.

There are at most two revisions. Missing source data leads to a data request,
not a more persuasive guess. Sufficient initial output can exit early without
spending calls on unnecessary reflection.

## A score is one signal, not permission

The judge returns five ratings: fidelity, coverage, channel adherence, clarity
and brand. Code weights them into a score. An unassessable dimension leaves the
aggregate unavailable; it is not silently dropped from the calculation.

Review-ready requires a score of at least 80 and no blocking findings. A candidate
cannot win by introducing a new blocking-defect family or losing required coverage.
Selection considers blocker counts and coverage before accepting a sufficient
score gain. Ties keep the incumbent.

This explains the draft that scored 100 while still failing reference checks.
The model's broad assessment did not validate the claim annotations. The
controller kept that distinction visible and allowed a correction to improve
the evidence mapping without pretending the score had risen.

Separate producer and judge contexts help limit anchoring, but they do not make
two invocations of the same provider independent experts. Their errors can still
be correlated. A rubric score is not a calibrated confidence probability.

## Real data made the assumptions harder to hide

We used the official USDA FoodData Central branded-food release. Public data made
source-backed validation possible, but it did not make every record usable.

A bounded scan of 50,031 records produced 1,000 distinct-GTIN candidate fact packs.
Missing literal brand names and ambiguous package quantities were major exclusion
reasons. We did not substitute brand owner for brand or serving weight for package
weight simply to increase the denominator.

We also corrected our grouping before model calls after finding brand aliases
under shared owners. The derivative contains 533 heuristic owner groups—not
independently verified product families. Preserving raw records, hashes and the
parent inventory made that correction explainable without rewriting history.

The 1,000-record workload used a controlled provider. It completed 2,131 controlled
calls, with 869 fixture review-ready tasks and 131 needs-data tasks. That exercised
engineering paths against real source records. It did **not** measure real-LLM
quality, prove reflection gains or supply human labels.

Keeping that distinction explicit matters more than having a large-looking test count.

## The first live run did not pass

Our initial installed-Codex attempt returned no auditable completion. The system
stopped and retained an unknown usage charge instead of claiming zero usage or
retrying invisibly.

After an explicitly approved one-time recovery, ten additional audited calls
completed the six-product campaign—but every product still required manual work.
Five judges marked channel adherence unassessable. One product exhausted its judge
parse retries.

Inspection found a real product defect: the producer received the channel profile,
but the independent judge did not. Asking the judge to assess rules we had not
supplied was an orchestration failure, not a source-data problem.

We reproduced that omission with a failing test, then shared the same immutable
channel-profile constant across the appropriate contexts without passing producer
reasoning or desired scores to the judge.

Further red/green tests addressed two other gaps. Malformed responses now receive
bounded, actionable validation feedback without echoing rejected raw output.
And accepted-unknown history follows successor ancestry, so changing task ID cannot
erase the warning or its required reviewer acknowledgement.

The original failed runs stayed intact. Explicitly authorized fixed-code successors
kept the same facts, grant, parent linkage and consumed per-product call/claim
budgets. We did not manufacture a clean campaign by resetting the store.

## What the successful bounded run actually showed

The fixed-code run used the same six development products: three source-backed
generation cases and three drafts with deliberately injected quantity faults.
Those injected faults were not authentic customer mistakes, and the cohort was
not a held-out population-quality study.

All six reached review-ready. Four completed an adopted critique/regeneration
cycle; two exited early. Two malformed judge responses were successfully repaired
within their existing stage retry limits.

The three injected quantity-error cases moved from judge scores of 58.75 to 100,
100 and 96.25. The separate generated case resolved its reference blockers while
remaining at 100. All four adopted revisions recorded four resolved blocker
findings and no introduced findings. Those findings overlap in purpose; they are
not sixteen independently established factual errors.

The successful pass used 23 audited actual calls with no new unknown usage.
Including the earlier failed history, the original grant stood at 34 of 96 calls.
The original unknown charge and historical warning remained visible.

The frozen implementation also passed 785 repository tests, including 104
ShelfProof tests, with zero skips or failures. Four frontend tests and the
TypeScript/Vite production build passed. Selected-artifact checks confirmed current
source bindings, eligibility and stage/accounting limits for all six products.

These are meaningful, bounded results. They are not six human approvals or six
published listings. There were no human reviews and no exported patches.

## Local service does not mean offline inference

The implementation uses FastAPI, React, an isolated SQLite store and a separate
worker. A provider port calls the locally installed Codex CLI. Product logic does
not need to embed a direct model API client.

That deployment shape does not imply the model runs offline. Approved context may
reach the CLI's configured service. The old Windows laptop and protected Cloudflare
entry remain the target; deployment acceptance on that machine has not happened.

The durable parts are also agent behaviour: reserve calls before invocation,
checkpoint known stages, preserve a usable incumbent after later failure and
require an explicit decision for unknown usage. A polished comparison screen would
not compensate for silently repeating paid work or losing the best valid draft.

## The result worth keeping

The bounded live-workflow gate now passes. Broader acceptance does not. Independent
quality labels, visual/browser testing, actual Windows/tunnel qualification and
customer evidence remain open. Browser discovery returned no available browser;
we did not replace that missing evidence with a fabricated visual pass.

The lesson from ShelfProof is not that an agent becomes trustworthy by judging
itself. It is that a useful reflection loop needs explicit facts, separate
evaluation criteria, finding-bound edits, deterministic selection, durable limits
and an honest human handoff.

Self-reflection becomes a product capability when an improvement is observable,
constrained and auditable—not when the model says its second answer is better.

---

Implementation and measured details: [study guide](study-guide.md),
[validation log](real-data-validation.md), [current status](implementation-status.md)
and [architecture](architecture.md). This is a local blog draft, not a publication
or a claim of commercial validation.
