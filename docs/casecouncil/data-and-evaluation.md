# Real data and evaluation design

**Updated status:** 132 actual Irish FSPO motor decisions acquired under published
reuse conditions; 122 eligible retrospective excerpts passed local-only checks.
No actual-payload model inference or full-product acceptance has run. See the
[source report](fspo-source-and-validation-2026-10-19.md). The UK/FOS gate below
remains unresolved; Irish source rights do not imply UK or prospective validity.

## G0 — source authority before acquisition

The [FOS legal terms](https://www.financial-ombudsman.org.uk/legal-policy) restrict
reproduction/storage without permission unless specifically permitted. Before any
bulk capture or packet/index construction, record verified applicable permission
or another qualified reviewed legal basis covering intended storage, transformation,
evaluation, model egress and any redistribution. Public readability is insufficient.

Alternatively use a design partner's actual historical complaint files with written
authority, purpose limits, data-processing arrangements and explicit model-egress
approval. Customer possession alone does not clear third-party rights. If neither
route is available, report the real-data gate blocked and ask for a source/product
decision. Synthetic fixtures can test software but never substitute for real acceptance.
No permission request, outreach or bulk download is authorized by this docs task.

Keep a source register: publisher/customer, source URL or record ID, acquisition
time, document bytes/hash, permission evidence/reference, permitted operations,
retention/expiry, egress restrictions, withdrawal process and reviewer. Unknown
rights fail closed. Do not include restricted originals in the public repository.

## Conditional target inventory

After G0, target **500 eligible actual motor-insurance complaint records**, not 500
copies of the same template: 300 development, 100 calibration and 100 locked test.
These counts are goals, not acquired volume or a promise all examples are suitable.
Group near duplicates, same dispute/appeal, copied policy templates and closely
related incidents before splitting. Latest eligible groups should form temporal
holdout where possible; document any conflict with class/issue coverage.

Include policy interpretation, total-loss valuation, claim handling, delay,
communication, premium/refund disputes and mixed coverage/service outcomes, with
different firms, lengths, amounts and evidence completeness. Exclude motor-finance
commission disputes and out-of-jurisdiction products from the initial acceptance set.
Report eligibility exclusions, missing material, duplicates and class distribution.
Do not select only clean PDFs or comfortable outcomes after seeing model results.

If fewer independent cases are available, publish the actual denominator and
uncertainty; do not top up the accepted count with synthetic variants. Duplicate
clones/mutations are useful robustness tests but form a separate denominator.

## Two materially different evaluation cohorts

**A. Retrospective published-decision replay:** authorized published material
reconstructs a facts-only packet. It can test grounded argumentation against recorded
findings but is selected for escalated/finalized disputes and lacks many original
artifacts. It is not representative of all insurer complaints or a live investigation.

**B. Prospective-use case-file replay:** authorized actual case documents, the draft
response and only evidence available at that historical review time. Later outcomes
are evaluator-only. This is the stronger workflow test and is required for paid
pilot acceptance. An inferred narrative must not be marketed as raw case-file access.

Do not combine these cohorts into one unqualified “real-world accuracy” number.

## Leakage controls

1. Preserve source hashes and a separate restricted gold copy. Runtime receives
   only an approved label-free packet; it must not upload the full decision PDF.
2. Remove final/provisional decisions, investigator conclusions, remedy directives,
   appeal outcomes and explicit outcome metadata. Background sections can contain
   an investigator's conclusion: dropping only the last heading is inadequate.
3. Annotators separate pre-review facts, party assertions, later evidence and
   adjudicator reasoning. Do not smuggle policy facts from the reasoning section
   into a supposedly prospective packet. Record their provenance/time instead.
4. If pre-review facts are insufficient, retain the gap and expect abstention.
   Exclude unusable cases with recorded reasons rather than fabricate missing policy.
5. Hide decision reference/search labels from prompts unless necessary; use opaque
   benchmark IDs. Dates material to applicable rules remain, but no outcome-bearing filenames.
6. Disable web/tools in benchmark roles. Any permitted precedent index must exclude
   the current dispute, related cases and post-cutoff decisions. No gold text in
   prompts, retries, caches, critic context or synthesis.
7. Audit serialized egress, including schemas/metadata, for seeded outcome canaries
   and forbidden references. Human spot-check packets before freezing test IDs.

Even this cannot prove absence of model pretraining contamination. Record that
limitation; do not claim the public corpus is unseen to the underlying model.

## Ground truth is multi-dimensional

Do not collapse a published “not upheld” label into “no service error or payment.”
Annotate issue-level supported findings, contractual versus service issues, remedy
conditions, decisive evidence, missing facts and source outcome separately. A
current recommended next action is not identical to the historical final outcome.

Two qualified motor-complaint reviewers independently annotate the locked cohort;
an adjudicator resolves disagreement with a recorded rationale. Report agreement
and unresolved ambiguity. They must not be the producing agents or unblinded
maintainers using model self-scores. Review expertise and availability are not secured.

## Baselines and bounded model campaigns

Freeze source/split hashes, policy, prompts, schemas, provider profile, call/time
limits, scoring rubric and target thresholds before test calls. Compare:

- Strong single-agent evidence review; include a self-refinement/cost-matched arm.
- Three isolated proposals with voting but no inter-agent critique/debate.
- Full CaseCouncil critique/revision/ballot/synthesis protocol.

Use the same permitted evidence and evaluate at matched decision coverage. Report
call count, known/unknown usage, latency and human review effort for each arm. A
higher-budget debate win is not automatically an interaction benefit.

Stage actual inference: six development cases across arms first; review runtime and
quality, then an explicitly bounded expanded development campaign, calibration,
and finally the untouched 100-case test. Obtain quota/resource authorization for
each campaign. A test involving roughly 13–16 normal calls/case across the basic
three arms can require 1,300–1,600 calls for 100 cases before repairs and any extra
cost-matched arm. Do not promise unlimited inference from a local CLI subscription.

Stop on quota, provider-tool audit failure, privacy incident, unknown-usage circuit
or exhausted authorized campaign allowance. Preserve incomplete cases and pending
IDs. Reusing valid outputs is allowed only for exactly identical frozen inputs and
must retain receipts; never reuse gold-influenced outputs as a clean holdout.

Metrics and acceptance thresholds are in [validation](validation-and-acceptance.md).
Keep raw case counts, independent groups, assessed issues, qualified recommendations,
manual outcomes, stage failures and duplicate stress events as distinct denominators.
