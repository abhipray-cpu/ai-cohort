# Real data and evaluation protocol

Current evidence: [18 October runtime hardening](runtime-hardening-2026-10-18.md). The 60-pair and 400-query cohorts were replayed, not counted as new independent data; 240 new dispatches reconcile with zero new unknown usage. An independent offer-reuse audit rejected the fixed no-model exit candidate: only 19 selected qualification cases remain after strict offer disjointness. Operator attestations do not activate confidence exits. Full volume, independent truth and calibration requirements below remain unchanged.

Status: original acceptance protocol; [actual diagnostic findings](real-data-validation-2026-10-17.md) now record acquired sources, full offline audit, 1,000 real query workflow and 200 real calls. The documented 4,500/600 live targets and independent adjudication below remain **incomplete and unchanged**. Do not equate offline volume or a bounded diagnostic to full model acceptance.

## Acquisition and provenance

Acquire authorized official WDC Products hardness archives and earlier manually verified WDC gold material. Record final URL, download time, terms/notices, raw SHA-256, extracted member hashes, parser version, record/pair counts and rejected rows. Enforce safe archive paths, Windows reserved names, expanded-size/member limits and immutable raw retention. Do not assume headline counts equal acquired counts. Keep raw/gold/manifests outside runtime-accessible inputs. No customer data or external publication is authorized by this protocol.

For each variant preserve official training/validation/test roles. Threshold fitting uses development only. Strip labels, entity/cluster IDs, unseen/hard-negative flags and filenames from application inputs; separately map evaluator-only IDs to input rows. Report exact record/text/pair overlap across variants and earlier gold. Never aggregate overlapping presentations as independent cases. Missing labels/schema mismatches block the relevant cohort rather than shrinking its denominator silently.

## Distinct evaluation tracks

1. **Mechanical full corpus:** parse and validate all acquired official splits; hash duplicates and inspect conflicting labels, empty fields and overlap. Full corpus checks do not imply full corpus live inference.
2. **Pairwise matching:** evaluate every published test variant with deterministic baselines. Preselect three primary conditions (hard/unseen, middle difficulty and easy/seen) and a deduplicated live cohort of at least 4,500 unique pairs from their union, with recorded class/difficulty mix. Freeze before inference. Run the actual router on every live-cohort pair; unfinished calls stay in the denominator.
3. **Paired model comparison:** preselect at least 600 unique pairs, stratified by positives/negatives/difficulty, drawn from that cohort. Run rules-only, economy-only, stronger-only and router with identical input allowance rules. Cost and quality comparisons use this same cohort, not the full router cohort against a small easy baseline.
4. **Candidate retrieval/end-to-end:** at least 1,000 distinct supplier query records against a frozen master gallery, including positive/no-match/ambiguous queries. Construct disjoint query/gallery offer records using evaluator cluster truth only for scoring, never candidate generation. Freeze gallery membership, no-match definitions and retrieval parameters before scoring. Report recall@k, correct row resolution, conflicting candidates and review coverage separately from preselected pair accuracy.
5. **Independent challenge truth:** at least 1,200 real-source pairs, provisionally balanced same/different, independently annotated by two qualified catalog reviewers blinded to model outputs, then adjudicated. Preserve original benchmark labels and disagreements. Where insufficient evidence exists, retain that label rather than force binary truth. This requires actual people and can remain blocked; model-generated labels do not replace it.
6. **Workflow/operational acceptance:** real imported records through authenticated HTTP and browser review/export, plus separately labeled replicas for load and mutations for adversarial tests. Fixtures do not become new natural-data truth.

These are minimum planned volumes, not acquired counts or authorization to spend unlimited quota. Estimate/publish token/call costs and complete within explicitly approved evaluation allowance. Any volume shortfall is reported as incomplete; never silently reduce the acceptance target to match completed work. Public pretraining exposure limits “unseen to model” claims even for official held-out records.

## Scoring

Report same-product precision/recall/F1, per-class confusion, calibrated risk–coverage, false automatic links, incorrect auto-rejections, candidate recall, row-level correct links, review/unresolved/failure rates and latency distributions. Binary benchmark disagreement is distinct from adjudicated correctness. Do not remove noisy labels post hoc to improve numbers; publish raw and independent-adjudicated metrics with separate denominators and frozen correction rules.

Costs include all routing/repair/escalation/failure attempts. Compare fixed-point costs and measured tokens, not just prompt length. Unknown usage is explicit; confidence intervals and savings cannot hide it. Report per correctly resolved row and review burden, not only cost per completed model call. Use paired differences/bootstrap where appropriate, clustered by product/row to avoid treating repeated offers as independent. Publish seed, interval method and denominator.

## Proposed quality/economics gates

On independently adjudicated evidence, automatic same-product precision must have a 95% Wilson lower bound of at least 99%, with at least 500 automatically accepted same-product decisions. If too few qualify, the gate is inconclusive/blocked, not a pass. End-to-end candidate recall@10 target ≥95% on positive queries, with its interval reported. Never infer catalog-wide absence from retrieval misses.

On the paired comparison cohort, target ≥20% lower measured total tokens than stronger-only at no more than one percentage point lower adjudicated decision accuracy and no more than five percentage points lower automatic-decision coverage. These are proposed go/no-go targets, not promised savings. Also report reference/actual applicable cost and reviewer time; stronger-only itself may be below safe quality. Passing comparative savings does not waive the absolute false-link gate. If independent truth is unavailable, benchmark comparisons remain exploratory and semantic release stays blocked.

Every requested concept needs a real observable test: distinct effective models, row/batch reservation before calls, no stronger call after an accepted economy exit, and exact ledger-to-report reconciliation. Strict hard-token enforcement and advisory budgets have different verdicts; advisory runs cannot pass the strict gate.

## Reproducibility and corrective runs

Freeze source/product/adapter hashes, CLI/model identities, prompts/schemas, policy/calibration/rate cards, gallery, cohorts, allowance and scoring code before evaluation. Save sanitized requests/results, source-linked decisions, usage events, failures and gate report. Keep original failed artifacts. Corrections create a new run ID with explicit changed hashes; tuning against a test cohort makes it development evidence thereafter. Preserve a fresh held-out challenge before another release claim.
