# Approved real-data development run — 19 October 2026

Later: [20 October user-approved continuation](real-data-continuation-2026-10-20.md)
completed all six artifact sets in the original store. Five histories are fully
audited; the failed call remains unknown under a separate owner incident record.
The incomplete-run findings below remain historical evidence, not erased or
retroactively declared a clean pass.

Subsequent authorized fix: [20 October diagnostics/recovery implementation](recovery-fix-2026-10-20.md).
The code path is implemented and tested, but the original missing receipt has not
been reconstructed; this live store remains unchanged and held. Earlier statements
below about the missing recovery code describe the original investigation.

Status updated 20 October 2026 (Asia/Kolkata): **incomplete — two full protocols,
one partial packet, three unstarted cases; unknown-usage runtime hold retained.**
The user explicitly approved the
previously described six prepared Irish FSPO development excerpts through the model
service configured via installed Codex, capped at 132 cumulative calls. This is
not authorization for additional cases, baselines or an unbounded campaign.

## Scope and preserved inputs

This is retrospective **Irish** motor-insurance evidence replay through an actual
loopback FastAPI process and a separate actual installed-Codex worker, not a
stand-in provider. It does not establish UK legal correctness, prospective file
completeness, independent semantic accuracy, browser usability or production readiness.
See the [source conditions/inventory](fspo-source-and-validation-2026-10-19.md).

The original 122-case manifest remains unchanged with external-model egress false.
A new subset, `var/validation/casecouncil-fspo-approved-six-v1/`, copies only the
six deterministically selected development inputs and their separate evaluator gold.
It records explicit approval, source-manifest hash, allowed IDs, model destination,
132-call cap and short-lived source/egress grant. No calibration/test inputs are
approved. Gold/outcome labels and full decision PDFs are not model context.

Selected opaque IDs:

```text
motor_c1fd2022d9c7185a
motor_e7dfd096e4839383
motor_fa378a29d52e24a4
motor_eb65fff90174d40f
motor_77cd1d18737e505a
motor_b5bbef04de32fe4a
```

## Execution and evidence paths

```sh
.venv/bin/python scripts/replay_casecouncil_http.py --live \
  --corpus var/validation/casecouncil-fspo-approved-six-v1 \
  --output var/validation/casecouncil-fspo-http-development-approved-v1 \
  --limit 6 --max-calls 132
```

This command has been started under the user's explicit payload/destination
approval. **Do not rerun it to consume a second allowance**: the approval is for
this campaign's cumulative usage, not 132 calls per launcher invocation.

The run directory retains frozen selection, code/module hashes, dirty repository
HEAD, CLI version (`0.160.0`), actual service store, audit/usage journal, receipts,
per-case packets and progress/report files. The upstream model build is not exposed
in stored receipts; CLI version is not a reproducible model-build guarantee.

Post-run `scripts/verify_casecouncil_replay.py` independently rechecks source quote
offsets/hashes, recomputes frozen registry/consensus, checks retained critic/evidence
blockers and inspects receipts without making additional model calls. These are
mechanical checks, not independent domain review.

## Observed result — 20 October 2026

Started 19 October at 22:15:45 Asia/Kolkata. The actual process exited after:

| Case suffix | State | Calls / known receipts | Observed route |
| --- | --- | --- | --- |
| `c1fd2022d9c7185a` | `draft_ready` | 8 / 8 | Agreement blocked by missing evidence; low confidence |
| `e7dfd096e4839383` | `draft_ready` | 8 / 8 | No consensus; low confidence |
| `fa378a29d52e24a4` | `manual_required` | 5 / 4 | First ballot provider exit; insufficient participation |
| `eb65fff90174d40f` | Unstarted | 0 / 0 | Dispatch held |
| `77cd1d18737e505a` | Unstarted | 0 / 0 | Dispatch held |
| `b5bbef04de32fe4a` | Unstarted | 0 / 0 | Dispatch held |

The collector's `completed: 3` means terminal stored packets, **not three passing
pipelines**. Full protocol completion is 2/6. The partial and three pending cases
remain in the six-case denominator. Zero qualified recommendations or human approvals.

**21 invocations, 20 known receipts, one unknown.** Known usage is a lower bound:
315,303 input and 16,131 output tokens, plus unknown failed-call usage. Do not call
the unknown call free or infer a dollar cost. The failure was `provider_exit` after
11,963 ms, not a 90-second timeout. Unused budget does not override the runtime hold.

The failed `ballot:customer` has an attempt-bound `validation_failed` event,
code `provider_audit_exit_or_usage`. The workspace hold is `unknown usage or unsafe
runtime`. The third packet retains three valid proposals and the critic, with no
invented ballots or synthesis. All unavailable stages are named. No hold, receipt,
journal hash or budget was reset; no additional model call was made on continuation.

Read-only verification rechecked **30 exact citations** (11/12/7), stored hashes,
registry and deterministic consensus. Negative HTTP checks passed on all three
packets: idempotent start, denied maker approval, denied anonymous access and draft
HTML/JSON export. These are mechanical checks, not independent semantic accuracy.
Case elapsed times were 160.733, 187.483 and 109.533 seconds.

Evidence under the run directory: `selection.json`, `run-provenance.json`,
`progress.json`, `report.json`, `verification.json`, per-case packet files, SQLite
and the independent `service/authority/usage.jsonl`. Final engineering regression:
**627 passed, zero skipped**, `var/validation/casecouncil-approved-regression-v1.xml`.
An earlier product-only run passed 92 tests; the two added verifier tests also passed.

### Recovery/observability finding

The [official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode)
documents JSON failure/error events and stderr diagnostics. The current adapter
returns bounded stderr for a nonzero exit, but the controller persists only a
generic failure category; the process-local event stream is not retained. Thus
the original exit code, error category and safe diagnostic are not available in
the stored run. This is a failure-observability/recovery gap, **not evidence that
quota, authentication or networking was the cause**.

Following the OpenAI Docs skill, a documented [read-only rate-limit query](https://learn.chatgpt.com/docs/app-server#auth-endpoints)
was attempted over local stdio with no model turn or complaint payload. It timed
out without establishing quota state. No credentials were printed, account/config
changed, credits/reset consumed or owner message sent. It does not reconcile the
failed invocation. Do not infer zero usage or automatically replay it.

Before safe continuation: add sanitized persisted failure diagnostics and an
audited reconciliation/resume path that preserves the unknown liability and all
21 attempts. Do not create a fresh workspace to evade the hold or rerun completed
proposals. No such runtime/reconciliation change was silently implemented during
this testing continuation. Full validation and study/blog completion remain open.

## Interpretation rules (requirements retained)

- Six selected cases remain the denominator even if inference fails or the usage
  circuit stops dispatch; retain failed/incomplete cases and pending IDs.
- A late failure must preserve prior valid work and its validation-history events.
- All three proposals and ballots, separate critic, deterministic consensus and
  synthesis are assessed separately; `draft_ready` is not human approval.
- Full original policy/case evidence is unavailable in these source summaries.
  Those explicit gaps must block qualified recommendations and preserve low confidence.
- Count unknown usage and failed calls; do not report them as zero cost or remove
  them from denominators. Do not reset a usage hold just to complete the cohort.
- No automated review represents an independent qualified human reviewer. No
  study/blog success story or release acceptance follows from a green mechanical check.
