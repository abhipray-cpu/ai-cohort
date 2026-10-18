# Runtime safety, cost investigation and confidence qualification

Subsequent work is recorded separately in [timeout receipts and repeat-work cost control](receipts-and-repeat-work-2026-10-18.md). Measurements and runtime hashes below remain historical; the new phase does not overwrite or reconcile them.

18 October 2026, Asia/Kolkata. **Engineering safety fixes implemented and tested; full release remains blocked.** The original [fresh-data failure report](fresh-real-data-validation-2026-10-18.md) remains intact. No production data, credentials, account settings or earlier-product source logic was changed.

## What changed

Failing regression tests reproduced missing failure evidence, cross-batch spending after unknown usage, missing provider-failure events, a campaign continuing across failed modes, unsafe recovery acknowledgement, missing instruction-profile binding, and acceptance of unverified calibration scores. Fixes were then verified without lowering acceptance thresholds.

| Area | Implemented behavior |
| --- | --- |
| Runtime evidence | Nonzero exits, missing audit/usage and invocation exceptions become provider failures, not parse errors. Retain safe category, exit status, byte counts and stdout/stderr hashes; never raw logs, tokens, email addresses or source text. Generated answer text cannot impersonate a runtime error category. |
| Reported usage on failure | Retain valid runtime usage even when a later exit/audit fails. Missing/ambiguous usage remains unknown, never guessed as zero. Multiple completion payloads are not silently treated as one complete bill. |
| Cross-batch hold | A durable workspace circuit and historical unknown-attempt query fence new reservations across batches, surviving restart. Later rows remain manually reviewable without additional inference. Other workspaces do not receive tenant details. |
| Campaign stop | First runtime/usage/audit failure opens a shared guard across all evaluation modes. Only already-authorized in-flight calls may finish (at most three concurrent workers). Stopped dispatches are distinguished from dispatched, unknown-liability calls. |
| Workbench | Workspace-wide warning and disabled continuation when a circuit is open, including a hold caused by a different batch. Manual review/export remains available. |
| Recovery | Authenticated runtime status; owner-only, reasoned retry authorization. Unknown/in-flight usage, divergent journals and restore quarantine cannot be acknowledged away. Retry authorization does **not** assert provider health or trigger a call. |
| Preflight | Check serialized envelope and installed command availability before reservation; no fabricated unknown charge for a known pre-dispatch refusal. |
| Confidence | Legacy/operator-attested profiles cannot authorize confidence exits. Owner API uploads cannot claim empirical verification. Qualified test fixtures are explicitly labeled fixtures; no real verified profile exists or is activated. |
| Optional compact instructions | Explicit `instruction_profile="compact_classifier_v1"` uses a fixed packaged classifier instruction file; default remains `legacy`. Tools stay disabled, schema/quotes/attributes stay validated, and missing evidence still abstains. |
| Provenance | Bind profile, instruction asset and relevant code into calibration identity. Future campaigns archive whitelisted backend/provider sources and assets, not credentials or data. The final runtime has an archived source snapshot. |

The OpenAI Docs workflow informed the runtime diagnostics and instruction experiment. Official [JSON event documentation](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable) documents completion/failure/error events; the official [configuration sample](https://learn.chatgpt.com/docs/config-file/config-sample) documents replacing built-in base instructions with `model_instructions_file`. These mechanisms do not independently attest the effective served model or establish what caused the historical failure. CLI version observed locally: `0.160.0`.

## Actual real-data rerun: legacy profile

The preserved 60-pair cohort was replayed through router/economy/strong modes. It is the same real-source cohort, **not 60 additional unique cases**. No prompt/quality shortcut was introduced in this phase.

| Mode | Binary proposals / 60 | Benchmark agreements / 60 | Calls | Tokens | Unknown |
| --- | --- | --- | --- | --- | --- |
| Router | 56 | 56 | 65 | 569,867 | 0 |
| Economy-only | 56 | 56 | 60 | 523,286 | 0 |
| Strong-only | 53 | 53 | 60 | 563,919 | 0 |

All router rows remain review drafts; its four unresolved cases are positive-label abstentions, not silently counted as correct nonmatches. No observed binary proposal disagreed with a benchmark label; this does not establish general product precision or independent truth. There are zero automatic acceptances and zero journal mismatches.

The full comparison completed **185 real dispatches** without new unknown usage or a runtime-stop event. Router tokens are **1.05% higher** than strong-only, so the original >=20% routing-token target still fails. The successful run does not retrospectively establish the cause of earlier failures.

An actual separate API/worker replay of 400 query IDs against 2,841 master records again yields **196/200 positive hits, 98% recall@10**. It passes 400 automated benchmark-derived review fixtures, 40 stale revisions, reviewed/default export checks, 600 concurrent reads during 100 writes, five scope denials, worker restart and quarantined recovery. Five separately counted live rows settle **54,440 tokens**. These are five model calls, not 400 AI answers or human reviews.

## Fault containment using real input records

Explicit outage injection is a safety test, **not a real-model quality test**. Sixty genuine input pairs were placed in separate batches sharing a workspace. One injected boundary failure held its unknown usage; the other **59 batches** stayed manually reviewable with **zero additional attempts**, including after restarting the store. Owner acknowledgement was refused. A separate three-mode campaign injection invoked the broken boundary once and stopped globally; tests also cover the permitted in-flight bound.

The original six database/journal files were opened read-only and their byte hashes verified unchanged: **61 unknown attempts / 732,000 advisory reserved tokens remain held**. They were not refunded, overwritten, reconciled with invented zero usage, or hidden by a successful replay. An authoritative usage record is required to settle them. Starting a fresh production database is not a reconciliation procedure.

## Cost optimization: useful, but not a routing-gate pass

The eight-call instruction experiment held two real records and requested models constant while comparing legacy versus task-specific base instructions. All responses had known usage and validated evidence. Compact instructions used **34.26% fewer economy tokens** and **38.46% fewer strong tokens** in this small, non-counterbalanced diagnostic. This is prompt-overhead evidence, not customer billing or a quality acceptance result.

The explicit compact profile then ran the preserved 12-case replay through all three modes:

| Mode | Benchmark agreements / 12 | Abstentions | Calls | Tokens |
| --- | --- | --- | --- | --- |
| Router | 12 | 0 | 12 | 67,186 |
| Economy-only | 12 | 0 | 12 | 67,168 |
| Strong-only | 10 | 2 | 12 | 67,100 |

All are manual-review drafts, zero unknown usage and zero automatic acceptance. Relative to the earlier same-case legacy replay, router tokens are **37.71% lower**. Timing, caching, runtime changes and nondeterminism confound that historical comparison; it is not a causal or independent release claim.

Crucially, both models benefit from compact instructions: router tokens are **0.13% higher** than contemporaneous **compact strong-only**, not 20% lower. We do not keep an artificially bloated stronger baseline to declare success. The default is unchanged, and the optional profile is experimental/API-selectable; there is no claim of a completed premium-UI profile selector or broadly qualified rollout.

The compact API/worker replay performs the same named 400-query workflow checks with three live rows / **20,395 tokens**. After closing the unverified-calibration path, a final-code HTTP replay repeats those checks with three further live rows / **20,396 tokens**. These are repeated records, not extra independent cases. Source/contract/runtime hashes are frozen separately for each implementation phase and unchanged during each run; earlier phases are not falsely attributed to the final hash.

## Empirical confidence: rejected shortcut, not fabricated qualification

An offline qualification tool evaluates a fixed rule: differing single title capacities in the same GB/TB unit, abstaining on multi-capacity titles or unit conversion. It does not activate a runtime decision or fit thresholds against test gold.

- Development: **50,785** unique supported training pairs, 2,359 rule-selected, **37 benchmark disagreements**; diagnostic Wilson 95% lower bound **97.85%**, below 99%.
- The first audit exposed **835 pair overlaps** and **1,287 overlapping offer IDs** across combined training/validation variants. A point estimate based on repeated entities cannot qualify the route.
- Strict SHA-ordered qualification excludes training offers and reused qualification offers: **537** mutually offer-disjoint pairs remain; only **19** are rule-selected. All 19 agree with publisher labels, but the lower bound is **83.18%**, and the required 500 selected examples are unavailable.
- Seventeen invalid development presentations were excluded and recorded. Cluster independence and independent adjudication are still unverified. Test gold was not read by this qualification tool.

The rule is **not activated**. No sample padding, replacement confidence threshold, fabricated label or owner-declared constant score is used to manufacture confidence. `evidence_status` defaults to `operator_attested`; supported owner uploads cannot set `empirically_verified`. No production qualification verifier/importer is currently provided. Direct database edits or a privileged test fixture do not constitute empirical evidence.

## Exact totals and regression evidence

This hardening pass performs **240 new real dispatches / 2,020,716 reported tokens**, all reconciled with their independent usage journals and **zero new unknown usage**. This total includes the 185-call rerun, eight-call instruction experiment, 36-call compact replay and 5+3+3 live HTTP calls. It excludes injected faults and all historical runs. It is reported usage, not an actual bill or a guarantee of future provider availability.

Final regression: **432 Python tests**, **eight frontend tests**, production web build, Ruff and whitespace checks pass. Existing dependency deprecation warnings remain. A built wheel was inspected and contains the exact classifier instruction asset. The final-code HTTP and fault artifacts match current backend/contract/asset hashes. Temporary API/worker processes were shut down; no Windows, browser/visual, protected Cloudflare or buyer acceptance was performed.

Local/gitignored artifacts under `var/validation/`:

| Artifact | Evidence |
| --- | --- |
| `catalogbridge-runtime-hardening-models-v1/` | 60-pair legacy rerun, raw decisions and durable usage |
| `catalogbridge-runtime-hardening-http-v1/`, `...-guards-v1/` | HTTP/worker/stress and five paid-state recovery checks |
| `catalogbridge-runtime-hardening-summary-v1.json` | Reconciled first-phase totals; captured before later profile/qualification changes |
| `catalogbridge-runtime-faults-v3/` | Final-code injected-outage guards, original ledger hashes unchanged; v1/v2 retained |
| `catalogbridge-instruction-cost-v1/` | Eight actual calls comparing instruction styles |
| `catalogbridge-compact-models-v1/`, `catalogbridge-compact-http-v1/` | 12-case optional-profile comparison and compact API journey |
| `catalogbridge-final-safety-http-v1/`, `...-guards-v1/` | Final-code HTTP checks and three paid-state restore/quarantine refusals |
| `catalogbridge-exit-qualification-v2.json` | Offer-disjoint qualification audit; v1 overlap audit retained |
| **`catalogbridge-runtime-hardening-final-v1.json`** | Read-only combined accounting, phase report hashes, current source hashes and original liabilities |
| `catalogbridge-runtime-hardening-final-v1/runtime-source/` | Whitelisted final backend/provider source and classifier-asset snapshot |

## Safe operation and remaining blockers

`GET /api/runtime` is authenticated/workspace-scoped. `POST /api/runtime/acknowledge` is owner-only, CSRF-protected and requires a 12–2,000 character investigation reason. It returns `health_verified=false`. It refuses unknown/in-flight usage, journal divergence and restore quarantine; it neither settles usage nor dispatches/retries a task. A new provider failure opens the hold again. Manual review/export is available during a hold.

The compact profile can be selected explicitly in batch JSON or the evaluation runners:

```sh
.venv/bin/python scripts/run_catalogbridge_real_models.py \
  --inputs var/validation/catalogbridge-fresh-replay-cohort-v1/inputs.jsonl \
  --gold var/validation/catalogbridge-fresh-replay-cohort-v1/gold.jsonl \
  --output var/validation/catalogbridge-compact-models-NEXT \
  --call-cap 48 --instruction-profile compact_classifier_v1
```

Choose a genuinely new output path; reruns consume account allowance. Never rerun the original unknown attempts as if free. Diagnostic commands do not authorize changing account credentials or bypassing circuits. Budget increases, restarts and calibration uploads do not clear a runtime hold.

**Still blocking full release:** authoritative settlement of the old 61 liabilities; independently verified effective identity; qualified, independently adjudicated calibration; the original >=20% quality-constrained routing-token target; full 4,500/600 live volumes; and browser/Windows/edge/buyer acceptance. The safety engineering work is complete for the named failure modes, but the commercial acceptance objective is not. Independent adjudication and model-runtime attestation cannot be replaced by application-side claims. `make catalogbridge-acceptance` remains nonzero.
