# TDD checkpoints — observed, not reconstructed success claims

22 October 2026. Commands below ran in the repository's existing virtualenv.
All programme/case test data was authored. Red results remain part of the record;
green does not establish real-source or consumer acceptance.

| Slice | Observed red | Change | Observed green |
| --- | --- | --- | --- |
| Core contracts/rules | `pytest -q tests/test_repairclaim_core.py`: collection failed, missing `contracts.repairclaim` | Added bounded shared contracts and pure rules, registered new app package/test path | 48 passed |
| Core adversarial regressions | Same command: 5 failed / 49 passed (revision conflict, direct bulletin bypass, contradictory extraction, misleading next question, external confirmation) | Fail closed on conflicting revisions/noncoverage; preserve contradiction; avoid irrelevant questions; separate external confirmation | 54 passed |
| SQLite/auth/cases | `pytest -q tests/test_repairclaim_store.py`: collection failed, missing `repairclaim_api.errors` | Added safe errors and actual SQLite/session/scope/revision/grant store | Combined core/store: 72 passed |
| HTTP boundary | `pytest -q tests/test_repairclaim_api.py`: collection failed, missing API module | Added bounded HTTP/auth/CSRF/case/fact/grant API | 15 passed |
| Security hardening | Store/API command: 3 failed / 36 passed (foreign DB accepted, blank password accepted, absurd Content-Length crashes integer parsing) | Application-ID guard before journal changes, serialized schema setup, reject whitespace-only enrollment and overlong length headers | Combined core/store/API: 93 passed |

The concurrent-initialization, duplicate/nonfinite JSON and untrusted-host checks
passed when first introduced; do not describe those individual checks as observed
red/green cycles. Initial import failures prove missing modules, not deep business
defects; the later behavioural reds provide that evidence.

## Historical foundation-only commands (superseded below)

```bash
make repairclaim-test
make repairclaim-lint
```

At this earlier checkpoint the Make targets did not build a frontend, install services,
download source documents, send messages or invoke a model. Formatting is scoped
to the newly added RepairClaim source/test files. Full repository regression is
recorded in [status](implementation-status.md) when its actual result is available.

Final repository regression: 943 passed, five skipped, six upstream warnings in
98.35 seconds. Earlier retries retained 27 ReleaseFence setup errors due first to
sandbox process enumeration, then Unix-socket path length. The final test process
used approved permissions and `TemporaryDirectory(prefix='rcpg-', dir='/private/tmp')`
for pgserver's `runtime_path`, `lock_path` and matching `InterProcessLock`, followed
by unmodified `pytest.main(['-q', '--tb=short',
'--junitxml=var/repairclaim-regression-short-runtime-junit.xml'])`.
No PostgreSQL tests or assertions were skipped/replaced to obtain that pass.

Those foundation tests exercised actual temporary SQLite files, hashing/session logic,
threaded compare-and-set contention and FastAPI through TestClient. They do not
exercise a real HTTP socket, browser, parser sandbox, PDF redaction, live provider,
manufacturer lookup, Windows service or private consumer case. All those gates
remained explicitly open at that checkpoint. Current process/render evidence is below.

## Full implementation cycles

All data in this phase is authored. No actual-data acceptance campaign was started.
These are observed failing tests, not retrospective claims that every new test was red.

| Slice | Observed red / issue | Implemented correction and observed green |
| --- | --- | --- |
| Documents and sources | Missing modules; image_profile TypeError in installed PyMuPDF | Restricted parser, PDF/image validation, redaction/rendering, official fetch bounds; 16 combined document/source tests passed |
| Rule extensions | Five behavioural failures in age windows, VIN/scope and missing-fact targeting | Explicit calendar-month clamp, identity conflicts and correct in-service question; 9 extension tests passed |
| Durable workflow | Missing upload/investigation/packet/consent methods | Five local workflow tests passed through scoped storage and injected fixture parser |
| Continuity/privacy | Missing response/outcome/reminder/export/invitation methods | Persisted attributed casework and privacy controls; later expanded regressions pass |
| Encryption | Raw SQLite dump contained private extraction/fact text | Per-case encrypted payloads and blobs; dump regression passed |
| Lease/source/recovery hardening | Four failed tests: concurrent lease, old anchors blessed, restored deleted account, identical source recovery | Global lease admission, revision-aware source checks, account tombstones, outage recovery; all four passed |
| Account erasure crash | Family helper retained access when account ledger existed before case ledger entries | Account-ledger replay erases all owned cases/grants/keys; regression passed |
| HTTP workflows | Two tests failed because parser injection/API routes were absent | Added typed authenticated routes and queued render operations; complete local HTTP packet/privacy flow passed |
| Frontend rules | Node tests failed importing absent domain module | Freshness/approval, next-action and precision-preserving input rules; 3 tests passed |
| Reminder worker | Missing tick method, then NOT NULL audit actor failure | Durable due-state transition, owner-associated system audit, retention maintenance; idempotence/expiry regression passed |
| Documented deadline | Valid anchored deadline rejected | Current reviewed source, literal deadline phrase/date and timezone-date validation; wrong-date rejection passed |
| Response follow-up | Missing frozen comparison and response references | Reason-to-condition snapshot and literal response-linked factual follow-up; tests passed |
| Financial evidence | Invoice estimate accepted as documented received money | Type/currency/positive-language checks and explicit ambiguous-evidence rejection; both negative/positive regressions passed |
| Parser tool validation | Invalid mileage unit accepted as ready | Pydantic Fact validation, literal value grounding and validation-history event; regression passed |
| Erasure during parse | Worker cleanup raised not_found after case deletion | Erasure wins, late result discarded without recreating state; regression passed |
| Final download control | POST download test failed with 405 against the earlier GET-only endpoint | Final packet download moved to CSRF-protected POST; HTTP roundtrip passed; private data export remains a scoped GET |
| Multi-attachment rendering | Four individually bounded stages exceeded the initial lease and left the packet a draft | Renew lease/heartbeat between stages, recheck owner/source validity and preserve the original overall deadline; simulated 220-second render regression passed |
| Container egress | Parser command inherited ambient remote Docker context rather than selecting a local endpoint | Force local Unix socket/Windows named pipe and disable Podman remote mode; command-policy regression passed without contacting an engine |

The actual native sandbox failure and runtime-path diagnosis were integration
debugging, not presented as an invented unit-test red/green cycle. Production
process tests use actual restricted parsing, not FixtureParser. Browser setup was
attempted but no browser is connected; no interaction tests were fabricated.

Current reproduction: make repairclaim-test repairclaim-lint builds the web app,
runs 185 local Python tests and 3 frontend tests, and checks scoped lint. Three
process tests are opt-in and passed separately. Full repository regression with
those enabled: **1,010 passed / 5 existing optional skips**, six upstream warnings,
113.90 seconds in the final rerun. See [status](implementation-status.md) for boundaries.

## Actual-source validation follow-up

After the implementation gate, acquisition-harness tests failed importing the
absent harness, then passed after implementation. During actual-source PDF QA,
packet headings incorrectly described rejected programmes as potential references.
Three parameterized regressions visibly failed before the correction; headings
now preserve missing-evidence, potentially-applicable and outside-condition states.
All three passed and a second 48-case actual socket/worker campaign passed.
See the [checkpoint](real-data-validation-2026-10-22.md). These remain authored
case facts against real PDFs, not independently labelled consumer cases.
Final follow-up full regression with actual RepairClaim process checks enabled:
**1,015 passed / five existing optional skips**, six upstream warnings, 113.20 seconds.

## Native Jev advisory follow-up — 24 October

The first Jev test collection failed because `repairclaim_api.jev` did not exist.
After implementing the optional native boundary and distinct egress approval,
twelve simulated-HTTP boundary tests pass. Final scoped suite: 174 passed / three
optional process skips, three frontend tests, build/lint passed. Lint initially
caught import order and an unused test variable; both corrected.

Actual API/worker campaigns attempted two live decisions. Neither returned a
validated result; the diagnostic run recorded HTTP 403 with free-tier/model/credit
markers. Both retained the rules checkpoint and halted without automatic retries.
This is actual failure-path evidence, not a successful Jev E2E or accuracy test.
See [live report](jev-live-validation-2026-10-24.md) for cost reservations and blocker.
Final full regression: **1,027 passed / five existing optional skips**, six upstream
warnings, 114.41 seconds; actual RepairClaim process tests enabled.

## Free-proxy follow-up — 24 October

The initial proxy test collection failed on the absent `repairclaim_api.jevmodel`
module. Six new boundary tests passed after the explicit approved-host integration,
including destination-bound approval, durable quota, missing-balance/version holds
and receipts which do not invent a dollar cost. Scoped tests: 180 passed / three
optional process skips, three frontend tests, build/lint passed.

An actual versioned request was rejected as paid-only, while the documented default
alias succeeded and reported Jev 1.14. The bounded API/worker replay passed eight
engineering cases and three monitoring/privacy checks over eleven native decisions.
Three advisory disagreements were retained and routed to manual review. This is not
eight correct Jev answers or full consumer acceptance. See the
[free-proxy checkpoint](jevmodel-validation-2026-10-24.md).
Full follow-up regression: **1,033 passed / five existing optional skips**, six
upstream warnings, 114.49 seconds, RepairClaim process tests enabled.

## Actual public-record metadata — 24 October

Initial acquisition test collection failed on the absent script. The first actual
four-query run safely rejected every record due to `productMake`/`productModel`
schema differences. A focused test reproduced that incompatibility as a failing
assertion; corrected field handling passed before the second acquisition froze
400 real public records. Tests also reject duplicates, inferred repair facts and
quota inflation on reopen. Scoped tests: 185 passed / three optional process skips,
three frontend tests, build/lint passed.

Actual HTTP/worker replay: 400 metadata workflows, four packet controls and eight
validated live Jev calls passed. Metadata has only four distinct input signatures;
no private invoice or narrative accuracy claim. Full regression with process checks:
**1,038 passed / five existing optional skips**, six warnings, 115.37 seconds.
See [measured report](public-complaint-validation-2026-10-24.md).

## Real repair-document packs — 24 October

New harness test first failed because the document scenario function did not exist;
it now verifies actual make preservation, no inferred payment and an unsupported
Kia verdict of `None`, not an asserted negative coverage decision. A separate parser
test failed on the dealer's `dtc code` label, then again on OCR table separators;
the bounded pattern fix passed both and preserves exact page-quote grounding.
The final actual API/worker replay of seven original public packs passed six
packet flows and one unsupported-make refusal. The first campaign's incorrect Kia
packet expectation and stale proposal counters are retained, not rewritten.
Scoped tests: 187 passed / three optional process skips; three frontend tests,
production build and Ruff passed. This does not pass general invoice understanding:
six of seven packs still yield no automatic fact proposals.
See [document evidence](public-repair-document-validation-2026-10-24.md).

Final full regression with actual PostgreSQL and RepairClaim process checks enabled:
**1,040 passed / five existing optional skips**, six upstream warnings, 115.79 seconds.

## Expanded document-review acceptance — 24 October

Frontend test first failed on the missing review-notice export. The notice now
appears in the actual document-review screen for empty, partial/unconfirmed and
unreadable extraction; four frontend tests, production build and scoped lint pass.
This is an honest manual-review fallback, not a claim that general extraction is fixed.

Expanded real-document run `repair-document-e2e-20261024-e`: seven case outcomes and
one account-erasure/isolation check passed. Original-byte flows additionally verify
manual invoice-total attribution without inferred payment, actual DTC confirmation,
reminders, private exports, historical correspondence/follow-up, monitoring revoke,
invoice-as-refund rejection and stale approved-download denial. No recipient was
contacted and no new provider call was made. Browser discovery again returned no
available browser after supported recovery; UI acceptance remains unpassed.

Final expanded-acceptance full regression: **1,040 passed / five existing optional
skips**, six upstream warnings, 114.78 seconds; native RepairClaim process checks
and real PostgreSQL enabled. JUnit:
`var/repairclaim-expanded-acceptance-regression-20261024.xml`.
