# Implementation and evidence status

24 October 2026. The scoped API/worker/web application is implemented. **Real-data
E2E has started after passing the implementation gate; bounded public-source
integration passed, but full consumer acceptance remains open.**
Bounded live-model advisory calls are measured below; no broad model-quality,
actual coverage, consumer savings, Windows or production acceptance is claimed.
[Actual module map](implementation-notes.md).

## Measured local results

| Check | Observed result |
| --- | --- |
| make repairclaim-test repairclaim-lint | Latest expanded repair-document run: production web build passed; 187 Python tests passed / 3 opt-in process tests skipped in the normal invocation; 4 frontend domain tests passed; scoped Ruff passed |
| Actual production-process checks | All 3 passed separately, and were enabled again in the full regression: restricted parse/redact/re-OCR/preview; native file-content/network denial; actual API + worker + authored source + attachment rendering + approval + download |
| Owned launcher | Actual up/status/down passed on a temporary synthetic account and free loopback port; only its two verified processes were stopped and the owned PID state was removed |
| Full repository regression | Latest expanded-acceptance rerun: **1,040 passed / 5 skipped / 0 failures / 0 errors**, 6 upstream warnings, 114.78 seconds; RepairClaim process checks enabled |
| Actual PostgreSQL regression setup | Approved process permissions and a short owned temporary pgserver runtime; no PostgreSQL assertions mocked or removed |
| PDF visual QA | Generated enquiry and redacted attachment rendered through Poppler and visually inspected: readable title/body/footer, unapproved marker and opaque redaction. Separate tests cover pagination and underlying text removal |
| Browser UI QA | **Not performed**: Browser initialization succeeded, selection reported no available browser; documented troubleshooting followed by discovery returned an empty list. No desktop/mobile interaction, accessibility or UI screenshot pass is claimed |
| Real public corpus / independent labels | 12 official PDFs downloaded; 11 parsed / 68 pages, one active-content quarantine; six exploratory programme configurations, not independently reviewed |
| Actual socket API/worker replay | 48 authored boundary cases and six actual packet flows passed against frozen official sources, before and after a packet-heading fix; genuine source-revision/consent/deletion checks passed. Not actual consumer invoices or independent accuracy |
| Actual RepairClaim Codex calls | Zero; simulated providers test control/fault semantics only |
| Actual Jev acceptance attempts | Two native requests, zero validated decisions; second recorded HTTP 403 with free-tier/model/credit markers. Reported account spend unchanged; $0.02 conservative reservations retained. Optional API/worker adapter added, no browser Jev integration or acceptance pass. [Campaign](jev-live-validation-2026-10-24.md) |
| Separately authorized free-proxy smoke | jevmodel.org: one explicit-version paid-plan rejection, one successful alias probe, then 11 validated live decisions across eight authored cases plus dependent checks. Packet and monitoring controls passed; three advisory disagreements safely routed. Total 40,794 input tokens, 59,206 remaining, no purchase; no USD receipt or full quality pass. [Checkpoint](jevmodel-validation-2026-10-24.md) |
| Actual public consumer-record metadata | Four official cohorts / 4,745 returned records; 400 distinct minimized records passed actual HTTP/worker flows, four packet flows, eight validated live decisions on four representatives. Four unique metadata signatures, not 400 independent domain cases. No invoice/narrative/outcome acceptance. This run used 25,834 tokens; latest remaining 33,372. [Report](public-complaint-validation-2026-10-24.md) |
| Private consumer cases / outcomes | None; no authoritative applicability, approval or refund observed |
| Actual public repair-document packs | Seven packs / 52 pages acquired; final actual API/worker run passed six packet flows and one unsupported-Kia refusal. One unconfirmed DTC proposal after a red/green parser fix; six packs still produce no proposals. General invoice extraction and consumer acceptance remain unpassed. [Report](public-repair-document-validation-2026-10-24.md) |
| Expanded real-document workflow | Seven expected outcomes passed again; actual proposal confirmation, manual invoice-total correction, seven reminder/export checks, six monitoring-revocation flows, historical agency-correspondence review and follow-up render passed. Invoice-as-refund rejection, stale approved-download denial and owned account-erasure checks passed. UI now warns that parsing does not imply invoice understanding; browser remains unavailable |
| Windows/container/tunnel qualification | Not deployed or tested; target laptop unavailable |
| Learning docs | [Study guide](study-guide.md) available with measured results and explicit acceptance limits; blog draft removed at user request |

The five full-suite skips are existing optional checks: two require NATS and three
require other products' process-test opt-ins. RepairClaim's three process checks
were enabled and passed in that full run. PyMuPDF and Starlette/httpx deprecation
warnings remain visible. Local ignored JUnit:
var/repairclaim-expanded-acceptance-regression-20261024.xml. Earlier passing runs:
var/repairclaim-repair-documents-regression-20261024.xml,
var/repairclaim-public-complaints-regression-20261024.xml,
var/repairclaim-jevmodel-regression-20261024.xml,
var/repairclaim-jev-regression-20261024.xml,
var/repairclaim-public-validation-regression-junit.xml,
var/repairclaim-handoff-final-junit.xml,
var/repairclaim-implementation-regression-junit.xml,
var/repairclaim-implementation-final-junit.xml and
var/repairclaim-implementation-lease-final-junit.xml. Scoped process run:
var/repairclaim-process-final-junit.xml.

## Failed checks and corrective work retained

- Earlier foundation regression retries hit ReleaseFence process-enumeration
  restrictions and PostgreSQL Unix socket length. The earlier final foundation run
  was 943 passed / 5 skipped in 98.35 seconds; its ignored XML artifacts remain.
- Behaviour-first tests exposed overlapping leases, stale programme anchors being
  blessed by a different activation, source recovery staying unavailable, private
  SQLite plaintext, account resurrection on restore, account-erasure crash ordering,
  estimates presented as documented payment, malformed parser facts and late
  parsing after erasure. Corrective regressions pass; see [TDD](tdd-checkpoints.md).
- Native parser initially aborted on synthetic fixtures. Runtime directory access
  was corrected: metadata-only traversal and the root directory itself are
  permitted; private file content remains denied. Extraction and denial policy were
  tested separately with actual child processes.
- Lint caught a missing explicit subprocess check argument in a test; corrected.
- Offline npm installation failed because cache metadata was absent. Approved
  dependency installation then succeeded and reported zero vulnerabilities at that
  time. That is not a dependency/license/security certification.
- HTTP test scaffolding initially used the wrong host and expected 403 where the
  store deliberately conceals unauthorized resources with 404. Those were test
  corrections, not product fixes.

## Reproduce local verification

```bash
make repairclaim-test repairclaim-lint
# Native macOS sandbox or the configured isolated parser container is required.
REPAIRCLAIM_PROCESS_TESTS=1 .venv/bin/python -m pytest tests/test_repairclaim_process.py -q
```

No command above acquires actual-world data, invokes a real model or sends a claim.
The full-regression launcher set pgserver.PostgresServer runtime_path, lock_path
and InterProcessLock to TemporaryDirectory(prefix='rcpg-', dir='/private/tmp'),
then ran unmodified pytest with RepairClaim process opt-in and JUnit output.

## Acceptance still open

All twelve FRs have implementation surfaces; the requirement matrix distinguishes
those from acceptance. G1 has local engineering evidence, not a blanket gate pass.
Real-source accuracy/rights/labels, actual private records with consent, available
browser interaction, configured-provider quality and Windows/tunnel performance
remain G2–G5 work. An empty inventory is not a complete programme search. A fake
provider is not live inference. A public-source fixture is not a consumer outcome.

See the [public-source checkpoint](real-data-validation-2026-10-22.md) for actual
manifests, failures, reproduction and remaining volume/label/pilot gates, and
[Jev free-access research](jev-free-access-research.md) for advertised versus
verified access. This latest repair-document campaign made no provider calls;
earlier live calls are recorded above. Do not carry campaign permissions or
success claims from previous products into RepairClaim.
