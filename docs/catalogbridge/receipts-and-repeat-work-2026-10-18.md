# Timeout receipts and repeat-work cost control

18 October 2026, Asia/Kolkata. Additional implementation and bounded real-data validation after [runtime hardening](runtime-hardening-2026-10-18.md). **Full release remains blocked; acceptance thresholds are unchanged.**

## Runtime fixes: red, then green

Regression tests first reproduced lost timeout stdout/usage, missing thread correlation, accepting one completion despite a later unfinished turn, and missing durable success receipts. Further tests reject truncated streams, malformed extra completions and ambiguous later failures. These now pass.

The CatalogBridge-owned adapter captures `TimeoutExpired` partial output before the shared adapter wraps the exception. Bytes and text are supported. Byte counts and SHA256 hashes describe the actual captured bytes, including invalid UTF-8. Diagnostics never retain raw streams, credentials or source text. Only UUID-shaped IDs from runtime `thread.started` events become correlation metadata; generated messages cannot supply them. Thread correlation is **not effective-model attestation**.

A single complete, valid usage record can survive a later process timeout. The invocation still fails and opens the runtime circuit. Missing/truncated/ambiguous usage remains unknown. Multiple completions, a later unfinished turn or incomplete JSON cannot be settled using only the first completion. These accounting checks do not create a provider-side hard token cap.

`Store.settle(..., runtime_evidence=...)` writes a whitelisted `runtime_receipt` audit event in the same **application SQLite transaction** as settlement, including successful calls. Diagnostics are whitelisted again when persisted. The independent liability journal retains its existing write-ahead/fail-closed behavior; this is not a distributed atomic transaction. Known settled-call retries remain idempotent. An actual subprocess timeout regression verifies usage survives termination, worker settlement and reopening the store while the circuit stays open. That injected process test is not paid inference.

## Opt-in draft reuse

`BatchSpec.reuse_validated_drafts` defaults to `false` and requires an actual boolean. The setup UI exposes the option and labels reused drafts. This is **draft reuse, not calibrated early exit or automatic acceptance**.

The exact key includes the complete supplier record, entire immutable master-feed hash, ordered retrieved candidates and existing code/prompt/instruction/model-policy binding. Even price-only changes invalidate it. No fuzzy matching or cross-workspace reuse. Expiry is 24 hours from creation, not renewed on hits; writes prune expired entries and bound storage to 5,000 entries per workspace.

Entries reference original tasks. The source must remain unreviewed, non-cancelled and in a supported review state. Human-reviewed drafts, including corrections/rejections, are not reused. Schema, candidate membership, literal quotes and variant checks run again. Uncertain, degraded or invalid drafts do not seed the cache. Cache insertion shares the successful lease-fenced checkpoint transaction; stale/cancelled workers cannot seed entries.

A hit produces `attempts=[]`, `calibrated=false`, `needs_review` and `cached_from` provenance. Reviewed export excludes it until separately reviewed. Original usage stays on the original attempt; no refunds, fabricated model calls or negative costs. Zero additional inference tokens does not mean hosting/review or an account bill is free. Runtime holds and denied egress are not bypassed.

This helps unchanged repeated feeds, **not unseen rows**. A future router/strong comparison must give both modes equivalent cache policy/warm state and report fresh versus repeated rows separately. The original >=20% quality-constrained fresh-row routing-token gate remains unmet.

## Actual real-data API/worker replay

The existing 400-query cohort was replayed against 2,841 master records. These are repeated records, not additional independent examples.

| Check | Result |
| --- | --- |
| Retrieval | 196/200 positive hits; recall@10 98%, four original misses retained |
| Review workflow | 400 benchmark-derived actions, 40 stale-form checks; zero actual human adjudications |
| Concurrent access | 300 summary + 300 audit reads during 100 review writes |
| Isolation/recovery | Five scope denials, worker restart and quarantined restore checks pass |
| Live seeds | Three actual model calls, **20,355 reported tokens**, all settled, zero unknown usage |
| Receipts | Three durable runtime receipts; all three have thread correlation; independent journal agrees |
| Repeats after worker restart | Three repeated rows: **two eligible cache hits, zero new calls/tokens** |
| Uncertain repeat | Not cached; its one-token replay budget blocks inference, leaving an explicit failed/unresolved row |
| Acceptance | All proposals remain review drafts; no automatic acceptance |

Repeat batches deliberately have one-token row/batch budgets, so a miss cannot unexpectedly spend another call. The uncertain row is not counted as a successful cached answer. Runtime hashes were frozen, archived and unchanged during the run.

An injected-outage replay uses the same 60 real pairs in separate batches. One broken boundary call blocks the next 59 batches, persists across restart and prevents owner acknowledgement of unknown usage. The separate multi-mode campaign stops after one injected boundary call. These are safety tests with **zero actual model calls**, not semantic quality evidence.

Regression: **455 Python tests**, eight frontend tests, production web build, Ruff and whitespace checks pass. Six existing dependency deprecation warnings remain. No browser visual, old-Windows, protected-edge or buyer acceptance was performed.

## Historical incident investigation

The existing Codex diagnostic SQLite database was opened read-only. Only incident-window aggregates were inspected; no raw log bodies, auth files, conversations or credentials were printed. The original run spans approximately 16:46:22–16:51:49 UTC on 17 October. Retained logs contain 35 entries: 18 DEBUG, eight INFO, nine TRACE; **zero WARN/ERROR and zero usage/completion-like records**. This does not establish coverage of the failed child invocations, their cause or their charges.

Official [Codex log-directory documentation](https://learn.chatgpt.com/docs/config-file/config-basic#log-directory) describes local logging configuration, not a guarantee of recoverable billing receipts. No global Codex configuration, account settings or credentials were changed. Authoritative historical usage was not found.

The six original application/journal files were independently checked read-only and unchanged: **61 unknown attempts / 732,000 advisory reserved tokens remain held**. New successful receipts cannot settle those old calls. Authoritative account/provider usage attributable to the original invocations is still required; there is no safe application-only substitute.

## Commands and evidence

```sh
.venv/bin/python -m pytest -q
npm --prefix apps/catalogbridge-web test
npm --prefix apps/catalogbridge-web run build

# New output path required. Three seed rows may escalate; each has a two-call ceiling.
.venv/bin/python scripts/run_catalogbridge_real_http.py \
  --cohort var/validation/catalogbridge-fresh-cohort-v1/retrieval \
  --output var/validation/catalogbridge-receipts-cache-http-NEXT \
  --live-rows 3 --stress --repeat-drafts \
  --instruction-profile compact_classifier_v1

# Injected boundary, no paid inference.
.venv/bin/python -m scripts.check_catalogbridge_runtime_faults \
  --cohort var/validation/catalogbridge-fresh-cohort-v1/pairs \
  --historical var/validation/catalogbridge-fresh-models-v1 \
  --output var/validation/catalogbridge-receipts-cache-faults-NEXT
```

Local/gitignored evidence: `var/validation/catalogbridge-receipts-cache-http-v2/` (`report.json`, `live-results.json`, `repeat-results.json`, archived sources and ledgers), and `catalogbridge-receipts-cache-faults-v1/report.json`. Initial HTTP v1 used an incorrect cohort directory and stopped before services or inference; its empty output directory is preserved. Direct-file execution of the fault utility failed import before running; the documented module command succeeded. Failed invocations are not relabeled passes.

Temporary API/worker processes were shut down. Earlier artifacts remain intact. These three calls are additional to the previous 240-call hardening phase, not replacement or independent-volume claims.

**Still blocked:** authoritative historical settlement, effective identity verification, qualified empirical confidence/independent adjudication, the original fresh-row routing savings gate, full live volumes, and deployment/buyer acceptance. Safer receipts and repeat-work savings are implemented improvements, not completion of those gates.
