# Rigorous real-data validation — 18 October 2026

Historical failed baseline, preserved unchanged below. See the
[19 October corrective validation](fixes-and-validation-2026-10-19.md) for fixes,
new measurements and current acceptance boundaries.

## Verdict: not accepted

Accessible real-data and local E2E tests were executed, not just prepared. They
found **two release blockers**: inadequate failure-evidence retention and a worker
error-handler crash after lease expiry. No production-ready or full-E2E-acceptance
claim is made. Live external writes, browser interaction and target deployment
remain unexecuted for the reasons below.

## What actually ran

| Layer | Actual evidence | Result / scope |
| --- | --- | --- |
| Entire annotated corpus | 797 real Travis logs, 80 repositories, 29 languages | Production selector evaluated against human-annotated failure chunks; quality gate failed |
| Real-log AI campaign | One hash-selected log per repository: 80 cases, all 29 languages, 79 distinct gold-chunk hashes | 80 actual installed-Codex calls; no gold in prompts; all schema/exact-quote checks passed, relevance gate failed |
| Fresh GitHub acquisition | 36 real completed run records from 12 public repositories: 24 failed, 12 successful | Authenticated GET-only acquisition; 22 failure log archives obtained, two source-unavailable failures retained |
| Actual local E2E replay | Real loopback TCP API process, authenticated file-backed NATS, production inbox/workflow, actual installed Codex | 536 signed webhook requests, 10,000 queue envelopes, 25 poison envelopes; 36 canonical events, no pending ACKs/backlog |
| Triggered outcomes | 22 available failed-run logs, 12 successful runs, two unavailable sources | 22 AI calls/owned incidents, 12 no-incident successes, two visible dead letters; 34 workflow `done`, two `dead` |
| Handoff and isolation | Authenticated API reads/exports and client-scoped viewer | 22 exports labelled unapproved drafts; other-client export rejected with 404 |
| Crash/retry faults | Real abrupt child-process exits with recorded real data | Five passed, one failed; controlled proposer/external-effect stand-in, not more AI accuracy evidence |
| Final full regression | Actual local integrations enabled | **522 passed, one failed, zero skipped**, 56.81 seconds; known lease-expiry regression remains failing |
| Web code checks | Four domain tests, TypeScript/Vite production build, Python lint | Passed; these are not rendered-browser interaction tests |

The 10,000 queue envelopes are repeated deliveries of the 36 genuine source records,
**not 10,000 distinct real-world incidents**. The E2E webhook bodies were reconstructed
from unchanged actual GitHub identities; they were not original GitHub delivery traffic.
All 36 first arrivals in this replay were HTTP; the queue workload exercised cross-
transport duplicates. Queue-first inbox durability was exercised separately by the
real consumer-crash/redelivery test, not counted as additional live AI diagnoses.
Source evidence was replayed byte-for-byte from the live-read capture. The worker's
production `Workflow.once` ran under the acceptance harness; this is not a Windows
service deployment qualification. The broker and API were actual processes, not mocks.

## All five Day 8 concepts

| Concept | Validation | Status |
| --- | --- | --- |
| Webhooks and queue | Signed HTTP plus actual authenticated JetStream; invalid envelopes terminate after durable rejection audit | Passed exercised local/replay scope; native GitHub sender not tested |
| Workflow on trigger | 22 actual Codex analyses and owned incidents; successful-run controls avoid false incidents | Passed execution scope; interpretation quality not accepted |
| Idempotency | 10,536 valid deliveries collapse to 36 source events and 22 failed-run analyses/incidents | Passed this replay workload; not a universal exactly-once claim |
| Dead-letter handling | Two actual captured source-unavailable cases become visible dead letters; transient failure/replay fault case passes | Passed exercised cases |
| Retries | Four injected transient failures exhaust into dead letter; replay retains identity/checkpoints | Normal path passed; **lease-expiry failure path fails** |

External GitHub issue writes were disabled throughout public-data replay. Therefore
the zero-duplicate-incident result is not proof of zero duplicated real GitHub writes.
An external-effect stand-in with no unique-marker constraint was used in the separate
crash-after-accept test, which verified one durable stand-in issue after recovery.

## Blocker 1: the selector can omit the actual failure

The production implementation takes up to 6,000 trailing characters per file with a
32,000-character aggregate allowance. The evaluation reuses that exact selector,
without feeding gold chunks to selection or generation.

After correcting an annotation-format comparison issue, **450 of 765 literally
scorable annotated failure anchors were retained: 58.82%**, below the predeclared
90% diagnostic target. Thirty-two logs had no literal normalized anchor match in
their full source and were excluded from this anchor denominator, not labelled wins.
In the 80-case AI sample, 46 of 76 scorable anchors were retained.

All 80 model outputs passed JSON/schema and exact quote-at-line checks, but only
**57/80 (71.25%)** had a meaningful lexical citation overlap with the annotated
failure chunk, below the 90% proxy target. This is **not 71.25% causal diagnosis
accuracy**. Multiple real errors, differing annotation boundaries and annotation
quality can affect the proxy. Independent diagnosis/next-step grading was not done.

All 80 benchmark inputs and all 22 available fresh GitHub inputs were partial under
the current selector. Confidence was capped by the existing production rule; all
22 fresh-run incidents were `needs_triage`. A nonfallback generated draft is not
an automatically resolved/accepted incident.

### Scorer correction, with no output replacement

LogChunks XML sometimes retains visible ANSI/SGR fragments after the ESC character
was removed. The first literal scorer therefore produced false negatives, e.g.
Scala's `[error]` text versus annotated `[0m[[0m[31merror[0m]`.
A failing evaluator regression was added, then the comparison normalized those
fragments symmetrically. **Generation evidence, source selection, thresholds and
all 80 saved model outputs were unchanged; no new model calls were made.**

Preserved v1 figures: 393/636 anchors (61.79%), 54/80 citation overlaps. Corrected v2:
450/765 anchors (58.82%), 57/80 overlaps. The anchor denominators differ because
more labels became literally scorable. Neither version passes its gate. Reports
retain both rather than overwriting the original result.

### Qualitative spot-checks

This agent inspected eight original mismatch examples and four overlap examples;
this is not an independent human review or a measured full-sample accuracy score.

| Repository / source build | Gold / observed behavior | Interpretation |
| --- | --- | --- |
| bitcoin/bitcoin / case `0065b39e0d5208ffda5f` | Include-guard evidence was cited precisely | Useful direct lint-failure handoff |
| technomancy/leiningen / case `0019877354dda15da691` | Missing Rakefile / rake abort was described | Observed failure supported; why Ruby tooling ran is still a hypothesis |
| discourse/discourse / case `0100f86bd372d76bcb82` | Prettier failure names the same file as annotation | Useful formatting-failure handoff |
| jlord/git-it-electron / case `0166d5b1b2742594e64a` | Syntax error in babel-eslint conversion code | Summary supported by captured errors; no verified fix inferred |
| neovim/neovim / 567681636 | Gold contains AddressSanitizer SEGV; selected tail exposes test failure summary | Agent explicitly could not identify the underlying test/error; missing evidence prevents a useful specific diagnosis |
| phoenixframework/phoenix / 565138076 | Gold contains CodeReloader argument error; tail exposes after-script reporting exception | Agent distinguishes uncertainty, but the annotated failure is omitted |
| luvit/luvit / 232600805 | Gold contains missing hash/codec failure; tail says tests passed and final build failed | Agent abstains from a cause; source selection is insufficient |
| electron/electron / 303191669 | Gold module-not-found error; tail exposes a separate apt HTTP 404 | A real secondary error can be cited while the annotated error is missed; not proof that the secondary error is fabricated |
| processone/ejabberd / 554568247 | Gold timeout differs from visible undef/setup failure | Multiple-error context; literal overlap is not a causal oracle |
| rabbitmq/rabbitmq-server / 572967302 | Gold RPC error omitted; tail shows skipped suites and make failure | Agent correctly says initiating error is not visible, but cannot provide a specific handoff |
| scala/scala / 567060744 | Summary identifies test and binary compatibility failures | Original literal scorer was affected by annotation formatting |
| Alamofire/Alamofire / 556020562 | Summary names a failing test with exact captured quotes; gold focuses on session diagnostics | Illustrates why proxy non-overlap alone cannot establish a false diagnosis |

## Blocker 2: expired-lease error handling crashes the worker

`test_expired_worker_network_failure_does_not_crash_supervising_loop` failed in
both the focused fault run and full regression:

1. A workflow claims an event.
2. The fault injection expires the lease while its source call is outstanding.
3. The source call raises a transient network failure.
4. `Workflow.once` catches that failure and calls `Store.fail`.
5. `Store.fail` correctly rejects the expired token, but its `ValueError` escapes
   the exception handler and terminates the worker loop.

This is a simulated lease state consistent with a long pause, **not an actual
Windows-suspend test**. The event remains reclaimable; the process should survive
without trying to mutate an expired/superseded job. A typed lease-loss path must
be handled around both normal execution and error recording.

The other five faults passed: crash after evidence commit, crash after triage commit,
crash after external stand-in acceptance, real queue-consumer death after inbox
commit/before ACK, and transient retry exhaustion followed by replay. Child workers
use one-second leases/ACK waits to accelerate recovery; retry schedules were advanced
explicitly in the retry test. Controlled proposers are clearly labelled and not
included in the 102 actual AI calls. Broker power loss/restart was not tested.

## Source provenance and runtime use

Fresh repositories: pytest-dev/pytest, pallets/flask, astral-sh/ruff, cli/cli,
nodejs/node, microsoft/TypeScript, dotnet/runtime, rails/rails, laravel/framework,
spring-projects/spring-boot, rust-lang/cargo and vitejs/vite. Each supplied two actual
failed runs and one success control. GET-only acquisition used existing local GitHub
authentication, held in process memory; no tokens/signed log URLs were saved in reports.

Unavailable captures: cli/cli run
[38894745982](https://github.com/cli/cli/actions/runs/38894745982) and spring-boot run
[39069820611](https://github.com/spring-projects/spring-boot/actions/runs/39069820611).
Their original source errors are retained, not replaced with synthetic logs.

**102 actual Codex calls**: 80 LogChunks analyses + 22 available fresh failed-run
analyses. All returned audited no-tool completions, with usage receipts for all 102:
1,439,784 input tokens, 41,562 output tokens; 322,560 cached-input tokens are a subset
of the input count, not extra tokens. This is runtime telemetry, not a monetary-cost
or independent billing statement. No quota/unknown-usage failure occurred in these runs.

## Artifacts and reproducibility

All raw records, logs, generated drafts and SQLite files remain gitignored under
`var/validation/`. These are public-data evaluations, not redistributable app fixtures.
Manifests retain source URLs, sizes and hashes; do not include raw credentials.

- `buildrelay-github-2026-10-18-v1/manifest.json`: 36 actual source records and per-artifact hashes.
- `buildrelay-selector-2026-10-18-v1/manifest.json`: all-corpus selection, fixed case IDs, original scoring.
- `buildrelay-semantic-live-2026-10-18-v1/`: frozen 80 IDs, per-call receipts, outputs, audit, original report.
- `buildrelay-real-e2e-2026-10-18-v1/`: scope, TCP/broker logs, real app database, call receipts, E2E report.
- `buildrelay-faults-2026-10-18-v1.xml`: five passing faults and one real failing regression.
- `buildrelay-real-validation-summary-2026-10-18-v2/`: original and corrected scoring, 797 per-case rescoring records, full-regression results, source-identity/audit checks and current code hashes. The earlier v1 summary is preserved; v2 clarifies that broker **redelivery**, not broker crash/restart, was tested.
- `buildrelay-rigorous-regression-2026-10-18-v1.xml`: full 522-pass / one-failure result.

The final summary verifies every stored event payload against the frozen GitHub
capture: exact set match. Its ingress audit records 36 accepted events, 10,500
ignored duplicates and 25 rejected poison envelopes. No stale success banner or
test-double analysis is used to manufacture a real-data pass.

Use **new output directories** on rerun; do not replace failed artifacts:

```sh
.venv/bin/python scripts/capture_buildrelay_github.py --output var/validation/buildrelay-github-new
.venv/bin/python scripts/validate_buildrelay_semantics.py prepare --corpus var/validation/buildrelay-capture-2026-10-18 --output var/validation/buildrelay-selector-new
# Explicit real model usage, bounded at 80 cases / two attempts per case; stops scheduling on runtime errors.
.venv/bin/python scripts/validate_buildrelay_semantics.py live --corpus var/validation/buildrelay-selector-new --output var/validation/buildrelay-semantic-new --limit 80 --workers 2
.venv/bin/python scripts/validate_buildrelay_e2e.py --live --capture var/validation/buildrelay-github-new --output var/validation/buildrelay-e2e-new --nats-binary /path/to/nats-server
BUILDRELAY_NATS_BINARY=/path/to/nats-server BUILDRELAY_PROCESS_TEST=1 \
  .venv/bin/python -m pytest -q --junitxml=var/validation/buildrelay-regression-new.xml
```

This turn added evaluation harnesses/tests and extracted the existing production
selector/triage into shared pure ports to avoid benchmark-only behavior or fabricated
Travis-as-GitHub identities. It did **not** repair the selection algorithm or expired-
lease error handler; the observed failures remain explicit, not patched out of tests.

## Still blocked / next work

1. Repair expired-lease failure handling; retain and pass the failing regression.
2. Improve evidence selection with failure/job context and source offsets; compare
   against the frozen baseline without gold leakage or weakening the gates. Re-run
   real-data evaluation and obtain a genuinely independent causal/next-step review.
3. Live GitHub issue operations require an authorized owned test repository. One
   was requested asynchronously; none was supplied during this validation. Public
   dataset repositories were not used as write targets.
4. Browser skill connection failed with “No browser is available”; supported discovery
   returned `[]`. Rendered flows/accessibility/responsive acceptance remain blocked.
5. Actual old-Windows-host startup/reboot/ACL/backup/power behavior and Cloudflare
   path-specific access/downtime tests remain unexecuted. A Mac replay is not proof.
