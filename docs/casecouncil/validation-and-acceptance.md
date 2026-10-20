# Validation and acceptance plan

Updated 20 October 2026: [132 actual Irish FSPO decisions were acquired](fspo-source-and-validation-2026-10-19.md),
with 122 mechanically eligible excerpts. Explicit model-egress approval covered six
development excerpts only. The [actual-model campaign](approved-real-data-run-2026-10-19.md)
completed two full protocols, one partial packet and left three cases pending;
unknown usage/runtime audit initially held further dispatch. A subsequently
[user-approved incident closure](incident-closure-2026-10-20.md) and separate same-job
resume allow bounded continuation while retaining unknown usage. This is not a corpus or campaign
pass, UK/prospective validation, or independent semantic acceptance. The broader
corpus still denies model egress.

See the [current MVP readiness record](mvp-readiness-2026-10-20.md). Dataset/metric
thresholds below remain targets, not achieved measurements. Neither green tests
nor successful packet generation clear domain, browser or deployment gates.
Latest [continuation measurements](real-data-continuation-2026-10-20.md): all six
artifact sets now exist; five fully audited histories and one accepted unknown
receipt remain distinct. 71 citations rechecked; no independent semantic pass.

## Acceptance matrix

| Gate | Required evidence | Current status |
| --- | --- | --- |
| G0 source authority | Permission/legal-basis register or authorized partner cohort; egress/retention scope | Irish research reuse basis recorded; six-case egress approval only; UK/prospective rights unresolved |
| G1 deterministic engineering | Contracts, exact citations, scope, quorum/blockers, idempotency and call limits | Implemented; product engineering suite passed; not proof of semantic truth |
| G2 durable real-process integration | Actual API/worker/SQLite restart and fault recovery, resource accounting | Actual local HTTP/child-crash tests passed; physical target-host/disk/load acceptance remains open |
| G3 corpus integrity | Actual independent counts, hashes, extraction/coverage, labels, split/leak audit | 132 acquired / 122 usable; mechanical checks run; independence and domain labels not established |
| G4 semantic usefulness | Locked real-data comparison, independent expert review, uncertainty intervals | Six development artifact sets, five fully audited histories, one accepted unknown; no independent semantic assessment or baseline comparison |
| G5 browser UX | Actual login/intake/debate/review/export, accessibility and responsive checks | No available browser connection on 20 October; still open |
| G6 target deployment | Old Windows laptop, restart/sleep/outage, Codex, protected Cloudflare access | Not run |
| G7 paid product | Authorized prospective-use cohort, measured review effort/quality and paid pilot | Not established |

The broad held-out statistical targets and paid-pilot goals below are not evidence
that all such studies are needed before every supervised MVP. They remain the
requirements for the broader quality/commercial claims originally proposed.
Conversely, removing those claims does not establish usable browser UX, acceptable
domain drafts or safe operation on the promised host. MVP readiness must record
its narrower scope explicitly, not silently relabel missing evidence as a pass.

## Deterministic tests: zero tolerance in tested cases

- Unknown/forged/stale citations, votes, candidate IDs and role identities are rejected.
- Repeat start/review/export requests are idempotent; conflicting reuse returns conflict.
- Cross-workspace access and revoked access expose no source/packet/export metadata.
- Quorum remains three; unavailable is not abstention; dissent is not discarded.
- Model/synthesizer output cannot alter computed decisions, blockers or review status.
- No reviewed-current export from stale/cancelled/revoked/restored or incomplete context.
- No provider invocation beyond cumulative grant or deadline; invalid/timeout calls
  still receive receipts and usage settlement/unknown handling.
- Injected prompt instructions do not authorize tools, external messages or private-data access.
- Partial extraction and missing decisive evidence cannot be labelled full coverage.

Test tables exhaustively cover 3-role candidate/abstention/unavailable combinations,
conflicting conditions, same-disposition/different-remedy candidates and critique
resolution states. Property tests permute role arrival order: aggregation should
not change with scheduling or database row order. Fixed seeds plus minimized
counterexamples make failures reproducible.

## Real-process and failure acceptance

Use disposable stores and actual child processes; no production client data. Kill
workers after reservation, provider return, proposal checkpoint, critic checkpoint,
candidate freeze, one ballot, consensus, synthesis and review preparation. Restart
and verify checkpoint reuse, fixed roster, no duplicate ballot, accurate call grants,
retained unknown usage and no silent auto-review. Include an error after lease
expiry and after a replacement token has been installed.

Inject schema errors, invented/ambiguous quotes, critic outage, one missing voter,
unavailable synthesis, late results, cancellation, grant revocation, source/policy
changes, disk-full/locked database and restore. A blocked/partial result is acceptable
only when it is visible, attributed and cannot masquerade as completed acceptance.
Database corruption tests operate on copied test stores, never broad user paths.

Reliability workload target: 500 source-derived workflow fixtures after G0, 2,000
duplicate start/status interactions and 100 revision/revocation races. Controlled
proposers can test orchestration but must be labelled stand-ins, not actual-AI results.
Repeated delivery/fixture volume is not independent semantic sample size.

## Locked real-data quality targets

Report confidence intervals, all attempted cases and source/cohort strata. On the
planned 100 independent held-out case groups, provisional targets are:

| Measure | Proposed target / interpretation |
| --- | --- |
| Structured grounded packets | 100% of accepted generated claims satisfy exact source-reference checks; manual fallback is separate |
| Nonfallback pipeline completion | >=95% of eligible runs, without excluding provider failures after scheduling |
| Qualified recommendation coverage | >=70% of eligible assessed issues; missing-evidence abstentions remain in the denominator |
| Substantive historical disposition comparison | Macro-F1 >=0.80 where labels genuinely map; report abstentions and each class separately |
| Expert-judged material recommendation error | <=5% observed at qualified coverage, plus 95% Wilson upper bound <=10% with at least 60 qualified independent cases |
| Critical missing-evidence / unsupported-conclusion detection | >=95% recall on independently labelled critical defects, with false-positive rate reported |
| Unsupported factual assertions | <=2% of independently reviewed factual claims; exact quotation alone is not factual support |

Issue metrics can contain correlated observations; use case-group clustered intervals
or bootstrap for issue/paired comparisons. Wilson bounds above apply to independent
case-level material-error events, not thousands of related sentences. Report case
and issue denominators together. Empty/small strata remain unknown, not perfect.
Do not optimize thresholds on locked test labels. Tuning after a failed run requires
a new version and another genuinely untouched test set before a new holdout claim.

The initial pilot has only uncalibrated low/medium confidence, no numeric correctness
probability. Any future high-confidence capability needs a separately approved,
independently tested calibration protocol; passing the table does not unlock it.

## Must debate earn its cost?

Compare paired case results at matched qualified coverage. Establish the strongest
single-agent and voting-only baseline before selecting a winner. Proposed mechanism
acceptance requires either:

1. At least five percentage points improvement in independently judged materially
   correct recommendations, with a case-clustered 95% interval excluding zero; or
2. At least 20% lower median human review effort, with an interval supporting a real
   reduction and the 95% upper bound on added material-error rate no more than +2 pp.

Use blinded randomized review order and counterbalanced cases so a reviewer does not
learn the outcome from the first arm. Reviewer expertise, rubric, sample size and
uncertainty must be disclosed. If evidence is underpowered or no benefit appears,
the debate value gate remains open/failed; do not select a convenient metric later.

## Full user-facing E2E

Run a rights-cleared actual case through real HTTP intake, extraction, model roles,
critic, ballots, consensus, human correction/review and downloadable export. Verify
exact spans, preserved dissent and changed-document invalidation through the browser,
not solely direct Store calls. Include upheld/non-upheld/mixed issues, evidence gaps,
malicious text and two-client isolation. Repeat on the actual Windows service host.

Separate mock-provider tests, actual provider tests, source replay, native authorized
case intake and physical Windows/Cloudflare tests in reports. Capture versions,
hashes, commands, actual denominators, failures, receipts, unknown usage and skipped
gates. No skipped integration test or prepared script counts as a completed test.

## Commercial acceptance and final cadence

Three paid design-partner pilots are a hypothesis-validation goal, not an available
customer list. No sales outreach is authorized by this documentation request.
Customer success requires the agreed review-effort benefit without increased material
defects or unfair outcomes, plus acceptable data handling and measured operating cost.

After implementation, publish the actual implementation/deviation map, measured
validation report, study guide and single blog. Both learning docs must include
failed gates and observed limits. Full release acceptance requires all applicable
gates, not just completion of the coding checklist.
