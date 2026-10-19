# BuildRelay corrective validation — 19 October 2026

This follows the [failed baseline](real-data-validation-2026-10-18.md). Raw captures,
failed reports and model outputs were preserved; this is a new derived campaign,
not a replacement of the original evidence. The source captures were acquired on
18 October; the corrective run uses those same bytes, not a new live GitHub sample.

## Changes under test

### Lease-loss handling

`Store.fenced` now raises typed `LeaseLost` (a `ValueError` subtype for compatible
callers). `Workflow.once` handles it around both normal processing and failure
recording. It records `lease_lost` without altering event state/checkpoints, resetting
attempts or renewing an expired/replacement token. Analysis propagates the type
instead of treating it as malformed model output. Ordinary contract errors are
classified by type, not by whether their text contains "lease".

The original real-record regression now passes. Added tests cover a replacement
worker's token on both normal and error paths, audit-time lease loss without model
calls/schema repair, and an unrelated `ValueError` containing "release".

These are simulated lease-state faults and actual local child-process tests, not
physical Windows suspend, power loss or a distributed multi-host protocol.

### Evidence selection and proposal instructions

The old selector kept 6,000-character file tails in alphabetical order, within
32,000 total characters. The new selector retains complete archives that fit;
otherwise it ranks early diagnostic clusters, bounded terminal slices, recent
diagnostic windows and heads across files, deduplicating overlapping lines.

The final aggregate content bound is **64,000 characters**. This is an explicit
resource-policy increase, not merely a ranking improvement and not a token-saving
claim. Prompt numbering/JSON/instructions add overhead. Existing download,
expansion, member-size, path-safety and file-count limits remain. Generation still
has a 90-second timeout and at most two schema attempts.

Unsafe/oversized skipped files mark coverage partial. Partial evidence still caps
confidence at 0.49; the manual-review threshold was not relaxed. Window ranges are
in redacted-source lines, not falsely advertised raw archive lines. Exact citations
address the selected text supplied to the model.

Proposal instructions now prefer concrete initiating diagnostics over generic exit
status or cleanup errors, request supporting citations where available, and require
multiple visible failures to be distinguished rather than invented into one chain.
Gold annotations, project-specific rules and expected categories are not inputs.

## TDD and regression results

The new middle-failure and multi-file crowd-out tests failed before the selector
change; the existing expired-lease regression failed before the handler change.
The instruction-contract test also failed before the prompt refinement. All pass
after their changes. Source-provenance, size, secret-redaction and partial-coverage
checks were added alongside them.

- Final full Python suite: **533 passed, zero failed, zero skipped**, 59.88 seconds.
- Dedicated real-record fault suite: **6 passed**; actual child exits, actual broker
  redelivery, controlled proposer/external-effect stand-ins and accelerated test
  leases/ACK waits. No broker power-loss/restart claim.
- Frontend domain suite: **4 passed**; TypeScript/Vite production build passed.
- Scoped Ruff checks/format checks and tracked diff whitespace check passed.
- Six dependency deprecation warnings remain; these were not test failures.

Real local integration flags were enabled with the checksum-verified NATS 2.15.1
binary. This was not a default test run that silently skipped broker/socket tests.
Frontend domain/build checks are not browser-interaction acceptance.

## Frozen selector comparison

All iterations use the same 797 LogChunks logs, 80 repositories and 29 languages.
Scoring uses symmetric redaction/visible-ANSI normalization, as established by the
baseline's metric regression. The first sufficiently long gold line is an anchor;
only anchors literally present in the normalized complete log are scorable.

| Revision | Evidence allowance | Retained / scorable | Retention |
| --- | ---: | ---: | ---: |
| Original failed baseline | 32,000; 6,000/file tails | 450 / 765 | 58.82% |
| Corrective iteration 1 | 32,000; diagnostic windows | 533 / 765 | 69.67% |
| Corrective iteration 2 | 32,000; terminal coverage plus recent diagnostics | 653 / 765 | 85.36% |
| Corrective iteration 3 | 32,000; also initiating diagnostic cluster | 661 / 765 | 86.41% |
| Corrective iteration 4 / frozen final | 64,000; larger terminal/context allowance | **690 / 765** | **90.20%** |

The pre-existing >=90% development target now passes **narrowly**. Seventy-five
scorable anchors are still omitted; 32 nonliteral anchors are excluded, not counted
as successes. All 797 cases were processed; 464 still have partial coverage.

The fixed 80-case model selection is byte-for-byte the same ID list as the baseline:
one source-path-hash-selected case per repository, 29 languages, 79 unique gold
chunk hashes. In that subset, 68/76 literal anchors are retained. Aggregate corpus
retention therefore must not be substituted for the smaller model-sample retention.

Development used the known corpus to compare generic selection revisions. This is
**not** a newly independent held-out benchmark or proof of unseen-project quality.
The final manifest records the selector module hash; preparation refuses a selector
file change during the run. The frozen final module SHA-256 is
`07c9d9ee6422e7a153161a146357fb8fda7a8c3801012d942c1f7cce341ed670`.

## Real-model and transport campaigns

The fixed 80-case interpretation campaign and the 36-record GitHub HTTP/NATS replay
are running through the installed Codex adapter. Final results are appended only
after their completion. No live GitHub issue writes are enabled.

The derived GitHub capture reselects unchanged ZIP archives and verifies every
source artifact hash before copying. Its manifest records the parent manifest hash
and selector hash. Of 22 available failed-run archives, 19 remain partial and three
fit completely. Two genuine unavailable-log records and 12 successful controls
remain in the 36-record acceptance denominator.

## Artifacts and reproduction

All raw/model artifacts are local and gitignored under `var/validation/`:

- `buildrelay-selector-2026-10-19-v1/` through `-v4/`: preserved development iterations.
- `buildrelay-selector-2026-10-19-final/`: final corpus evidence/manifest.
- `buildrelay-github-2026-10-19-final/`: source-hash-verified derived native capture.
- `buildrelay-semantic-live-2026-10-19-final/`: fixed 80-case model outputs/receipts.
- `buildrelay-real-e2e-2026-10-19-final/`: actual HTTP/NATS replay and model checkpoints.
- `buildrelay-faults-2026-10-19-v1.xml`: six-case fault evidence.
- `buildrelay-rigorous-regression-2026-10-19-final.xml`: 533-test full regression.

Use new output directories. Bounded live commands consume model quota:

```sh
.venv/bin/python scripts/validate_buildrelay_semantics.py prepare --corpus var/validation/buildrelay-capture-2026-10-18 --output var/validation/buildrelay-selector-new
.venv/bin/python scripts/reselect_buildrelay_capture.py --source var/validation/buildrelay-github-2026-10-18-v1 --output var/validation/buildrelay-github-new
.venv/bin/python scripts/validate_buildrelay_semantics.py live --corpus var/validation/buildrelay-selector-new --output var/validation/buildrelay-semantic-new --limit 80 --workers 2
.venv/bin/python scripts/validate_buildrelay_e2e.py --live --capture var/validation/buildrelay-github-new --output var/validation/buildrelay-e2e-new --nats-binary /absolute/path/to/nats-server
BUILDRELAY_NATS_BINARY=/absolute/path/to/nats-server BUILDRELAY_PROCESS_TEST=1 .venv/bin/python -m pytest -q --junitxml=var/validation/buildrelay-regression-new.xml
```

## Acceptance boundaries

Browser interaction, actual Windows sleep/reboot/service behavior, Cloudflare
deployment and live GitHub issue-write acceptance remain unexecuted here. No owned
write target was authorized. The prior Browser skill attempt returned no available
browser; domain tests and a build do not clear that gate. Independent causal and
next-step review also remains outstanding. Neither corpus text overlap nor the
maintainer's spot checks can be relabeled as that review.

This is still a single-host pilot, not a highly available or production-certified
deployment. The [study guide](study-guide.md) and [blog](blog.md) explain these
boundaries as part of the product rather than omitting them for a cleaner story.
