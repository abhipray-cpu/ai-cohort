# ReleaseFence implementation and evidence status

21–22 October 2026. **Implemented engineering build; not production-accepted.** The user
subsequently authorized implementation using TDD. Backend/API, worker, operator UI,
customer SDK, outbound connector, loaded-bundle HTTP gateway, tracing adapters,
control/recovery and explicit operations tooling are now present. Subsequent
[OSS real-source/live validation](oss-validation-2026-10-22.md) ran on 22 October; it is
partial acceptance, not a complete MVP or production-acceptance declaration.

## Latest follow-up — browser passed, larger live cohort failed

See [measured follow-up](followup-acceptance-2026-10-22.md). Six real browser cases
pass, including independent approval, tenant isolation, mobile navigation and
all-seven-view automated accessibility scans; four domain tests/build pass.
This closes that bounded browser scope, not full accessibility/security certification.

The newly approved 200-product/240-call campaign attempted all 200 products,
spent **239 calls** and returned **165 successful source-bound outputs**. It failed
after six Phoenix exports reached read-back dead letters. No closed-window decision
or rollback was reached in that campaign. A separate zero-inference replay verified
all 439 retained spans in both fresh backends. The original failed result remains.
Unexplained wall-clock discontinuities prevent latency/soak qualification. The
target Windows/Cloudflare host is unavailable. Do not call this a fully accepted MVP.

The original 24-call ledger is unchanged; the new ledger is independent. Final
regression: **850 passed, five unrelated skips**, 99.12s. The current zero-inference
actual-source/dual-backend process campaign passes, including 12 independently
verified signatures. Full evidence lives in the follow-up, not the older counts below.

| Area | Present evidence |
| --- | --- |
| Buyer/product | Proposed B2B SaaS agent release-assurance wedge, not validated demand |
| Market research | Primary source register; incumbents already provide tracing/alerts and some rollout capabilities |
| Concepts | All five have code/tests; actual source/Codex/MLflow/Phoenix workflow exercised under the user-approved alternate profile; full host/statistical qualification open |
| Architecture | C4 levels 1–4 updated to actual module/transport boundaries |
| TDD | Observed red/green slices recorded in [checkpoints](tdd-checkpoints.md); not a claim every line/test was test-first |
| Code/API/UI/connector | Present; [module map, supported scope and runbook](implementation-notes.md) |
| Database/worker | Actual isolated PostgreSQL installations with non-bypass runtime roles, RLS and immutable evidence; real worker/process checks |
| Trace backends | Actual authenticated MLflow 3.17.2 and Phoenix 20.23.0 dual read-back/privacy and independent stop/restart checks pass; MLflow unauthenticated/foreign-experiment read/write denied. Legacy LangSmith unqualified |
| Dashboards/alerts | Measured engineering metric oracles; real isolated HMAC receiver, failed-first delivery/retry and stable dedup ID |
| Canary/rollback | Actual Codex-backed candidate/stable HTTP bundles served in three organizations; three signed, probed rollbacks verified; partial/offline/incompatible controlled cases pass; ordinary live statistical promotion unpassed |
| Data | 1,000 actual USDA GTINs, 1,000 sessions, 12,000 events across three organizations; 150 controlled source-bound matrix cases pass; no expert semantic gold labels |
| Live model | Original grant 24/24 spent. New 200-product grant 239/240 spent; larger campaign failed, 165/200 successful outputs. No model/auth settings changed |
| Browser/Windows/Cloudflare | Six isolated headless Chrome E2E cases and automated seven-view accessibility checks pass after fixes. Independent/manual review remains open; Windows/tunnel host unavailable |
| Security/commercial | Review and paid pilot not secured; no certification, customer or SLA claim |
| Study/blog | [Study guide](study-guide.md) and [blog](blog.md) complete at the measured checkpoint; neither claims full product acceptance |

## Earlier measured engineering checks (preserved)

Latest user-authorized OSS acceptance checkpoint:

- **844 passed, 5 skipped**, six upstream warnings, 99.53s; 64 ordinary ReleaseFence
  tests, none skipped. Separate controlled fault matrix: **150 passed**, 30.01s.
- Real dual-backend auth/scope and independent outage/restart test: **1 passed**,
  19.16s. Separate no-inference full-process campaign also passes.
- Source rerun: **1,000 products / 1,000 sessions / 12,000 unique events**, no inference.
- Final OSS live run: **six fresh calls**, three organizations, 12 unique spans
  queried from each backend, three HMAC notifications and verified runtime rollbacks.
  Independent saved-evidence audit verifies 12 signatures and all 24 executable
  source hashes. **24/24 cumulative approval spent; no further live authority.**
- UI: **three domain tests** and TypeScript/Vite build pass. Browser discovery
  returned no available browser; interactive/accessibility acceptance stays open.
- Artifacts, scope limits and exact independent audit:
  [OSS checkpoint](oss-validation-2026-10-22.md). USD cost remains unknown.

### Preserved earlier 18-call acceptance checkpoint

The following is historical and superseded by the OSS checkpoint above:

- Full monorepo: **839 passed, 5 skipped**, 6 upstream warnings, **92.09s**;
  `var/validation/releasefence-monorepo-acceptance-final-20261022.xml`.
  Includes 59 ordinary ReleaseFence checks, no ReleaseFence skips. The separately
  selected real-source matrix adds **150 passing** controlled cases, 25.40s;
  `releasefence-fault-matrix-final-20261022.xml`.
- Actual Phoenix stop/restart/export-recovery check: **1 passed**, 46.66s;
  `releasefence-phoenix-outage-20261022.xml`. It starts its own real backend process,
  not a contract mock, and verifies persistence/read-back/no double counting.
- Latest 1,000-product source campaign: `releasefence-source-acceptance-20261022-r5/report.json`;
  independent HTTP latency/count oracles, complete-corpus detector scan, no incidents,
  worker restart with a newly completed cycle and archived executable sources.
- Final live campaign: `releasefence-live-acceptance-20261022-r3/report.json`;
  six products, six fresh invocations, 12 actual queried Phoenix spans and three
  alerts/verified rollbacks and independently verified exported command/runtime
  signatures. **18/24 cumulative grant spent** across three campaigns, including
  the first failed-backend run. USD cost remains unknown, not zero/free.
- Web domain tests: **2 passed**; TypeScript/Vite production build passes unchanged.
  Ruff, dependency consistency and whitespace checks pass at this checkpoint.

The following numbers describe the preserved earlier implementation-only checkpoint:

- ReleaseFence Python suite: **51 passed**, 1 upstream Starlette/httpx deprecation
  warning, **18.18s**, no ReleaseFence skips. An additional focused real-PostgreSQL
  check confirms unexported in-window traces appear as a promotion hold.
- Latest focused artifact: `var/validation/releasefence-engineering-2026-10-22.xml`.
  Earlier 44/49-test engineering artifacts are retained separately; they are not
  substituted for the latest run.
- React/TypeScript production build: passed. Vite 7.3.7, 1,579 modules; JS bundle
  253.62 kB / 78.57 kB gzip, CSS 8.57 kB / 2.72 kB gzip at this checkpoint.
- Frontend domain tests: **2 passed** (authority/state hints; unknown vs zero and
  partial vs verified), not browser end-to-end evidence.
- Ruff: targeted source/contracts/tests/launchers checked; final rerun recorded in
  the implementation session.
- Previous monorepo checkpoint: **829 passed, 5 skipped**, 89.39s, before the
  launcher and independent hard-failure guard additions.
- **Final frozen-source monorepo regression: 831 passed, 5 skipped**, 6 upstream
  deprecation warnings, **91.56s**. Artifact:
  `var/validation/releasefence-monorepo-final-2026-10-22.xml`. This includes all
  **51 ReleaseFence tests passing** after the final idempotent-retirement fix.
  The five skips belong to pre-existing other-product NATS/opt-in process campaigns,
  not ReleaseFence, and remain unpassed. Earlier reports remain available separately.
- Runtime versions observed: Python 3.12, Node 24.10.0; the isolated test fixture
  ships PostgreSQL 16.2. That fixture version is **not** a production security patch
  recommendation; target deployment must select and qualify a supported patched DB.
- Source provenance: `var/validation/releasefence-source-2026-10-22.json` records
  SHA-256 for 47 scoped source/config/test files and the base Git revision. This is
  an explicitly dirty-worktree snapshot, not a signed/committed production release.
- Documentation link check: **21 Markdown files, zero broken local links**.

The engineering process case uses actual local HTTP servers, API/worker processes,
PostgreSQL and a real notification receiver. Its bundle answers/usage are fixtures,
not real-world task outcomes or paid inference. The restore case executes real
`pg_dump`/`pg_restore` into a newly created quarantined test database. No customer
runtime, vendor account, original `.env`, other product database or live model was
mutated/called **at that earlier implementation-only checkpoint**. The subsequent
newly authorized calls and real local Phoenix installation are recorded separately
above. New dependencies were installed only in workspace environments.
The shipped launcher was separately run from an isolated temporary root, including
duplicate-start refusal and owned-process shutdown; existing user stacks were not
started or stopped.

## Open qualification / hardening boundaries

- Legacy LangSmith endpoint remains **unqualified**. It is not a blocker for the
  user-approved `mlflow-phoenix-v1` profile. Actual MLflow/Phoenix dual read-back,
  access isolation and independent outages pass; sustained backend pressure and AX
  remain unqualified.
- Real-source mechanical volume and bounded installed-Codex smoke now pass their
  declared checks. Expert semantic labels, representative customer traffic and
  ordinary actual-traffic statistical promotion remain unpassed.
- Statistical calibration/power on real cohorts, exhaustive kill/partition points,
  long-running exporter pressure and admission-imbalance qualification: **open**.
- Broader/manual accessibility, independent security review, Windows service
  identity/ACLs, Cloudflare machine-policy paths, laptop resource/availability tests:
  **open**.
- Commercial pilot/payment evidence: **not secured**. No SLA/compliance claim.
- Production hardening such as key rotation, archival/tenant erasure and independently
  witnessed audit/deletion reconciliation is not advertised implemented. See the
  explicit scope limits in implementation-notes.md.

This is real implementation with engineering evidence, not merely the old design
pack. It is also **not** complete live-product acceptance or a launch-ready SaaS.
Study guide/blog now document the measured validation cadence, including failures;
their completion is not product-acceptance evidence.

Next phase: close the explicit browser/target-host and live statistical
qualification gates. Do not replace unavailable proof with mocks or lower
data-volume/quality floors into unit-test totals. The current result must not be
called a 100% accepted MVP.
