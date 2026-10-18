# Local routing redesign: implementation and measured limits

18 October 2026, Asia/Kolkata. This amends the [previous runtime and repeat-work report](receipts-and-repeat-work-2026-10-18.md). **The new stage is implemented; the fresh-row savings gate and full product acceptance have not passed.**

## Architecture change

The opt-in `routing_policy="local_review_v1"` adds a small local lexical pair scorer before Codex. It evaluates source-text similarities, identifying-number/code overlap and variant conflicts using bounded, depth-three boosted trees. Training uses NumPy; inference evaluates JSON trees without pickle, a model API, external tools or a new inference service.

The runtime validates profile structure, finite parameters, tree depth/size, source/feature version and declared band counts/statistics. It does not authenticate dataset provenance or independently re-adjudicate those labels. Profiles come from a trusted service-configured path, not a user-supplied request path or upload endpoint. Results are explicitly scoped to `benchmark_review_drafts_only`.

`CATALOGBRIDGE_ROUTER_PROFILE` selects that JSON file. Authenticated `GET /api/routing-profile` exposes availability, canonical hash and band counts, not file paths or tree weights. Batch setup offers an opt-in checkbox and binds the exact hash through `local_router_sha256`. The default remains `llm_only`. Missing, invalid or changed profiles produce an audit event and ordinary budgeted LLM fallback; they never authorize a local exit.

A negative draft requires every retrieved candidate to fall in the enabled negative band. It does not establish that no matching product exists outside retrieval. A positive draft requires a unique qualified candidate, all alternatives resolved and source/variant validation. **The real profile has no enabled positive band.**

Local exits make zero model attempts and remain `needs_review`, `calibrated=false`, with source quotes, profile/score provenance and `local_route_exit` audit. They cannot enter reviewed export without a separate review. Runtime holds and denied egress precede the local stage. Uncertain cases retain the existing economy/strong routing, reservations, validation, failure receipts and fail-stop behavior. Profile and new code participate in existing policy/cache binding.

## Development and qualification evidence

`train_catalogbridge_local_router.py` reads only official training/validation development members, never published test members. Product entity IDs are evaluator-only partition controls, not model features. Cross-partition pairs are excluded, pair presentations deduplicated, and official validation records never fit model parameters.

| Partition | Unique pairs | Product entity groups |
| --- | --- | --- |
| Fit | 12,233 | 295 |
| Threshold tuning | 3,186 | 106 |
| Qualification | 20,381 | 399 |

There is no offer/entity-group overlap between these partitions. Seventeen invalid development presentations and 6,619 duplicate presentations are recorded. The fixed scorer has 96 trees. Threshold candidates are chosen on tuning data, then frozen before qualification. Qualification retains the >=500 accepted-case and >=99% pair-level Wilson-lower-bound numeric checks; no target was reduced.

The negative band selects 1,077 offer-disjoint qualification pairs, 1,073 agreeing with publisher labels: the pair-level Wilson lower bound is **99.0489%**. However, 385 entity groups are reused within that subset. The independence assumption is therefore not established. This is a benchmark draft-band measurement, **not a defensible independent 99% safety guarantee or qualified automatic acceptance**.

The positive band selects 775 offer-disjoint pairs, only 717 agreeing; lower bound **90.45%**. It fails and is disabled. No constant owner score or model self-confidence substitutes for this result.

The preserved development v1/v2 runs produced no qualifying tuning bands. V3 used tuning point precision to choose candidate thresholds, leaving the unchanged numeric qualification gate to the separate partition. V4 retains those learned weights and outcomes while binding the integrated runtime feature version and canonical profile identity. All versions remain separate artifacts.

## Fresh, frozen challenge

`prepare_catalogbridge_local_comparison.py` freezes **600 pairs**, 100 per hardness/label stratum, with 636 distinct entity groups. There is no development-entity overlap, no internal offer reuse and no overlap with prior recorded live-pair offer IDs. The 60-pair pilot is selected in advance, ten per stratum. Selection uses SHA order and round-robin strata, never model scores. These are publisher-held-out inputs, not independently adjudicated customer truth or a claim of absence from pretraining.

Offline scoring of all 600 pairs yields:

- 101 local draft exits, **16.83% coverage**.
- 100 benchmark agreements and one disagreement among those exits.
- One incorrect different-product draft on a positive-label pair remains recorded.
- The naive selected-pair lower bound is 94.60%, not 99% independent qualification.
- Median local latency approximately 0.089 ms, p95 0.189 ms on this Mac; not Windows performance evidence.

Those 600 rows make **zero LLM calls** in this offline check. Coverage is not measured token savings. The profile is not tuned against these challenge outcomes.

## Actual live comparison: quota-stopped, not a pass

Router, economy-only and strong-only received the frozen 60-pair pilot, the same compact instruction profile, disabled draft caches and existing allowance rules. The call cap was 240. Router alone had the experimental local stage; the controls remained actual single-model baselines. Source snapshots were frozen and remained unchanged.

The installed runtime reported **quota** errors. The shared guard stopped new work across all modes; already-authorized in-flight calls finished or failed. No automatic retry or account/configuration change followed.

| Mode | Processed / 60 | Known reported tokens | Attempts | Unknown attempts | Local exits |
| --- | --- | --- | --- | --- | --- |
| Router | 45 | 234,641 | 45 | 1 | 5 |
| Economy-only | 43 | 224,195 | 43 | 1 | 0 |
| Strong-only | 35 | 181,687 | 35 | 1 | 0 |

There were **123 actual dispatches**, 120 with known usage, **640,523 known tokens** and **three unknown-usage liabilities**. Their 36,000 advisory reserved tokens remain held. All three errors have sanitized quota diagnostics and runtime thread correlation. Journals reconcile; automatic acceptance is zero. The original 61 historical unknown liabilities remain separate and unchanged.

The report has `comparison_eligible=false`, with only 35 shared processed IDs. Whole-mode token totals cover different row sets and cannot establish a fair savings ratio. The generated raw `benchmark_tradeoff` ratio must not be interpreted as an eligible result. Missing/failed/unstarted cases remain in the full 60-case denominator. **Neither a >=20% savings result nor full 600-pair live validation is established.**

The safe failure classification and campaign containment worked; the commercial target did not become a pass merely because those controls worked.

## Additional research candidate, rejected

A second, separately recorded experiment fit 40,928 WDC development pairs across 694 entity groups and tuned on the original separate 106 groups. The previous WDC qualification partition was explicitly reclassified as development. Six predeclared model configurations were chosen using tuning data only.

Fresh qualification used a SHA-partitioned portion of the separate legacy source, excluding literal offer-ID/exact-title-brand overlaps. The remaining **974 challenge pairs were frozen but not scored**. Cross-source physical-entity independence remains unverified.

On 1,902 qualification pairs, the negative band retained only **47** offer-disjoint cases, all agreeing: too few, with a 92.44% lower bound. The positive band retained **155**, with **140** agreeing: insufficient sample size and quality. **No profile is emitted or activated.** This records both domain shift and inadequate qualification, not an alternative way to claim the savings gate.

## Engineering evidence and operating boundaries

**476 Python tests**, eight frontend tests, production web build and Ruff pass. New tests cover finite/bounded profiles, feature symmetry and ID/price exclusion, per-candidate ambiguity, conflict refusal, no-call local exits, hash drift, workspace holds, default-policy preservation, authenticated profile status and campaign accounting. These fixtures are not real-data qualification. Six existing dependency deprecation warnings remain. New UI controls compile but are not browser/visual acceptance evidence.

The official [Codex JSON event documentation](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable) was checked for the live boundary. The product continues to use the installed CLI, not a direct model API; CLI inference may still be remote. No credentials, subscription/billing settings, tunnel or Windows deployment were changed.

Local/gitignored artifacts:

- `catalogbridge-local-router-development-v1` through `v4`: development evidence and the v4 draft-only profile.
- `catalogbridge-local-routing-cohort-v1/`: frozen 600 pairs and 60-pair pilot.
- `catalogbridge-local-router-offline-v1/`: all 600 local decisions, including the disagreement.
- `catalogbridge-local-router-models-v1/`: stopped live campaign, runtime source snapshot, per-mode ledgers/receipts.
- `catalogbridge-cross-source-router-development-v1/`: failed cross-source qualification and unscored legacy challenge.

Do not resume paid inference while quota is unavailable or clear unknown usage by acknowledging a circuit. A later campaign needs a fresh run directory and an explicit allowance; it does not erase these attempts. The opt-in profile can be exercised in review-only mode after trusted service configuration, but no deployment or paid-MVP acceptance is claimed.
