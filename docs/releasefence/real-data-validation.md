# Real-source and live integration acceptance — 22 October 2026

**Historical 18-call checkpoint.** The subsequent user-approved
[MLflow/Phoenix OSS checkpoint](oss-validation-2026-10-22.md) supersedes current
counts/status: 24/24 cumulative calls spent and bounded dual-backend checks pass.
The results below remain unchanged historical evidence, including failed runs.

**Not complete MVP acceptance.** Real-source, installed-Codex and actual local
Phoenix campaigns have now run. LangSmith, browser and the Windows/Cloudflare
deployment have not passed. Do not replace those gates with these results.

## Evidence and denominators

Artifacts below are under `var/validation/`, excluded from Git. Keep failed runs.

| Campaign | Actual result | Evidence |
| --- | --- | --- |
| Source integrity | 1,000 distinct GTINs; literal identity/ingredients and published package quantities verified against each retained raw USDA record; archive, dictionary, manifest and record hashes checked | Source receipt in `releasefence-source-acceptance-20261022-r5/report.json` |
| Full source pipeline | 1,000 sessions, 12,000 unique lifecycle/tool events, three isolated organizations; 334/333/333 products; all 1,000 source checks completed; zero incidents after an explicit complete-corpus detector scan | Same report, archived executable sources and local spools |
| Source metric/privacy checks | Expected task/event/model-call counts match; SDK-local terminal durations independently recomputed with inclusive quantiles and compared to the HTTP dashboard; no raw input field names in lifecycle storage; durable worker completes a new cycle after restart | Same report; API/worker logs |
| Controlled mechanical matrix | **150 passed**, 30 named scenario families × five independently initialized database/router episodes, 25.40s; 150 distinct USDA records bind the cases | `releasefence-fault-matrix-final-20261022.xml`; `tests/acceptance_releasefence_faults.py` |
| First live campaign | Six actual Codex responses passed source-fidelity checks; three fault/alert/rollback drills; **Phoenix export failed** | `releasefence-live-acceptance-20261022/report.json` |
| Corrected live campaign | Six distinct products, six actual Codex invocations, all six literal source-fidelity checks passed; real candidate and subsequent stable HTTP dispatch in each of three organizations | `releasefence-live-acceptance-20261022-r2/report.json`, preserved intermediate pass |
| Final signed-evidence live campaign | Same six products, six new invocations; all source/backend/control checks passed; six exported server-command signatures and six original runtime receipt signatures independently verified; new worker-cycle proof after restart | `releasefence-live-acceptance-20261022-r3/report.json`; archived executable sources; 103.59s |
| Actual Phoenix | 20.23.0, isolated Python installation and loopback server; **12 spans** independently queried, four per organization, both release arms; trace/span/release/status/parent identities and privacy allowlist checked | Corrected live report includes queried backend rows, proofs and source-code hashes |
| Actual backend outage | **1 passed**, 46.66s; stop a separate owned Phoenix process, observe durable retry/degraded state, restart against the same data, recover exact spans without duplicate lifecycle metrics | `releasefence-phoenix-outage-20261022.xml`; `tests/acceptance_releasefence_phoenix.py` |
| Real alert/rollback | Three HMAC-verified deliveries; three signed, probed, verified rollbacks; new sessions actually served the stable HTTP bundle | Corrected live report and receiver receipts |
| Repository regression | **839 passed, 5 skipped**, 6 upstream warnings, 92.09s; other-product skips remain unpassed | `releasefence-monorepo-acceptance-final-20261022.xml` |
| Web client | Two domain tests and TypeScript/Vite production build pass | Execution checkpoint; not a browser test |

Repeated source campaigns do not multiply the independent product denominator;
the source sample remains 1,000 products. The source replay has **zero model calls**.
Its ten tool checks per product inspect
distinct source fields; accepted/terminal events bring the total to twelve per
product. These are legitimate deterministic source-validation operations, not
12,000 LLM calls or invented customer traffic. Local task/session IDs intentionally
overlap between organizations; tenant/runtime namespacing must keep them separate.

The matrix mixes failure episodes and healthy negative controls: bounded polling,
human waits and healthy canaries must not be called faults. Some rules/analysis
are pure deterministic checks; some exercise actual PostgreSQL/SQLite/network
failure. Connector probes in this matrix are controlled fixtures. Clocks are
simulated. Neither these tests nor their 1,000-per-arm synthetic statistical
samples prove population calibration, live statistical promotion, every possible
crash checkpoint, or 150 spontaneous model/customer failures. Real wall-clock
HTTP/model/backend evidence is reported separately above.

## Source provenance and rights

Source: U.S. Department of Agriculture, Agricultural Research Service,
[FoodData Central](https://fdc.nal.usda.gov/api-guide/), April 30, 2026 branded
download. USDA states that the data are public-domain/CC0. This campaign reuses
the existing frozen acquisition **read-only**; it does not reuse ShelfProof's
database, approvals, authentication or model-call budget.

- Archive: 204,270,542 bytes, SHA-256
  `57b0f122e61cf2840f03c11e9520275d0d2018dc036e16273fcd3cd370db2256`.
- Official external field dictionary PDF SHA-256:
  `e21d658d4d3fa583aceaa78e23efd4e64dbf9010fd0210a87b94edbcfb56928a`.
- Grouped records SHA-256:
  `86690b369cac989d01a77fabd95a9438cbe1a2edb61cf6df4281e7cbf4ce8bcc`.
- Manifest SHA-256:
  `de93c819f26507339cdc402f414d306e83e41bbc41ab8565f4a14a9cbf59ad9b`.
- Source directory: `var/validation/shelfproof-usda-grouped-20261021`;
  original archive/dictionary: `shelfproof-usda-20261021-resolved`.

These are snapshot facts, not current-package certification. The retained sample
comes from a 50,031-record prefix and conservative eligibility mapping; it is not
the entire USDA release or a representative customer workload. There are no
expert semantic gold labels. Copy-task expectations come independently from
literal published fields, not an LLM judge.

## Bounded live authority and measurements

The user explicitly approved six public USDA products and **24 cumulative local
Codex calls including harness retries** on 22 October. Approval reference:
`user-2026-10-22-releasefence-6-products-24-calls`. All three campaigns used the same
six products: the distinct-product denominator remains six.

**18/24 invocations spent in total**: six in the failed-backend campaign, six in
the corrected campaign, six in the final signed-evidence campaign. No automatic
retries were made. The SQLite ledger at
`var/validation/releasefence-live-approval-20261022.sqlite3` reserves before spawn;
failed/unknown attempts remain spent. Changing the output directory does not
change this fixed ledger. Live mode is bound to the approved corpus hash and its
first six records. Never delete/replace the ledger to obtain another budget.

The shared installed-Codex port runs schema-directed, ephemeral, read-only and
tool-restricted; no model identity/configuration or authentication was changed.
CLI version was 0.160.0. These are audited CLI-turn invocations; invisible provider
transport retries or billing are not independently reconciled. Raw reasoning,
prompts, answers and stderr are not sent to tracing vendors. The adapter checks
each response against the seven literal source fields before declaring source
fidelity. The model identity remains explicitly unverified in release manifests.

Candidate cap exhaustion is an **authored staging fault**, applied after an actual
model response. It is not falsely described as a naturally looping Codex model.
The gateway normalizes this contradictory success to failure; the worker raises
the incident and requests the independently preauthorized rollback. Fresh gateway
requests then execute the stable bundle. No production tool effects occur.

Final signed-evidence run measurements, n=3 each:

- Receiver arrival minus incident creation: 0.0205–0.0313 seconds.
- Verified rollback observation minus candidate adapter completion:
  0.8165–1.1272 seconds. This is the stated observation interval, not an exact
  command execution timer or a customer SLA.
- Twelve actual queried spans: six agent roots and six LLM children; candidate
  roots carry ERROR for the injected hard failure. No arbitrary attributes/events
  or raw payloads survived the backend read-back privacy assertions.
- Token receipts were available. Per-call USD receipts were **not** available;
  each of the six calls remains cost-unknown, and cost-per-success is null. A zero
  known-cost subtotal must not be marketed as free inference or billing accuracy.
- Final six-call receipt totals: 53,016 input tokens, including 7,040 cached input
  tokens, and 750 output tokens. Cached input is a subset, not an extra charge.
- Exported evidence retains all six signed commands and all six signed runtime
  command receipts; both signatures are independently verified using public keys.
  The exact 23-file executable source snapshot has zero hash mismatches against
  the final exercised product/harness at handoff.

## Defects found and fixed using red/green checks

1. Phoenix export did not target the configured project. Read-back queried the
   project but ingestion selected the backend default. A failing header assertion
   preceded the `x-project-name` fix.
2. Real Phoenix returned HTTP 415 to JSON OTLP. Its trace endpoint requires
   `application/x-protobuf`. A failing content-type/decoded-ID regression preceded
   protobuf encoding with correctly converted trace/span byte IDs. Actual backend
   root/child read-back then passed. See the
   [upstream ingestion contract](https://github.com/Arize-ai/phoenix/blob/main/src/phoenix/server/api/routers/v1/traces.py).
3. Early harness status could say scoped checks passed while vendor status was
   degraded. The original report is preserved, **not accepted**. A negative
   acceptance-summary regression now prevents model success hiding failed Phoenix
   qualification. The corrected report derives scoped status from named checks.
4. Source inventory guards now reject changed hashes, duplicate GTINs, literal
   brand relabeling and substituted package quantities, while preserving published
   `fl oz` units. The finite grant survives restart and rejects cap/approval changes.
5. Runtime signatures were checked on ingress, but only decoded receipt bodies
   were retained. A new audit regression failed on missing `proof_envelope`.
   Original signed command/heartbeat/window envelopes are now retained and their
   hashes audited. The final live campaign verifies exported signatures itself;
   earlier decoded-only records are not retroactively re-signed or qualified.

Initial source startup failed because the harness omitted explicit API bootstrap
credentials. The first two mechanical matrix reports also retain test-setup errors
(wrong rollout revision / rollout expiry instead of approval expiry). Correcting
these harness setups did not relax product authority checks. Failed reports remain
separate from the final passing artifacts.

## Reproduce without implicitly authorizing paid work

```sh
.venv/bin/python scripts/validate_releasefence.py \
  --corpus var/validation/shelfproof-usda-grouped-20261021 \
  --output var/validation/releasefence-source-NEW --mode source

RELEASEFENCE_ACCEPTANCE_CORPUS=var/validation/shelfproof-usda-grouped-20261021 \
  .venv/bin/python -m pytest tests/acceptance_releasefence_faults.py -q

RELEASEFENCE_PHOENIX_PYTHON="$PWD/var/validation/releasefence-phoenix-venv/bin/python" \
  .venv/bin/python -m pytest tests/acceptance_releasefence_phoenix.py -q
```

Use a new output path; existing campaign directories are refused. The source
runner requires isolated PostgreSQL via the existing `pgserver` dev dependency
(macOS/Linux), starts only owned loopback services, archives its sources and stops
its processes. On Windows this particular campaign runner is not yet qualified.
The regular product can target an explicitly dedicated external PostgreSQL DSN.

Live mode is **not** part of `make up`, normal pytest, worker startup or the source
command. It additionally requires `--mode live`, the exact `--approval` reference,
an explicitly owned `--phoenix-url`, the remaining global grant and existing Codex
authentication. Do not spend the remaining grant or create vendor accounts just
to turn this report green.

## Still required before declaring the scoped MVP accepted

- Actual authorized **LangSmith** project export/query and cross-backend failure
  isolation. No test project/key is available. Self-hosting is a licensed Enterprise
  option, not a substitute free server; see
  [LangSmith's deployment requirements](https://docs.langchain.com/langsmith/self-hosted).
  Phoenix success does not qualify LangSmith or Arize AX.
- Real healthy canary statistical promotion at the frozen sample/power/coverage
  gates. Six live tasks with unknown USD costs cannot qualify that transition.
- Browser interaction/accessibility and full operator flows. Browser skill setup,
  troubleshooting and discovery returned no browser / an empty list; builds and
  HTTP clients do not replace this proof.
- Target Windows service identity/ACLs, protected Cloudflare browser/machine paths,
  laptop resources/soak and declared recovery/security acceptance. macOS results
  must not be labelled Windows deployment acceptance.
- Independent security/semantic review where required by the chosen pilot scope;
  controlled tests are not certification. Paid-pilot willingness-to-pay remains
  a separate commercial gate, not something unit tests can establish.

The source/fault/live campaigns are distinct artifacts, not a single end-to-end
pass for every platform and vendor. No 100%/launch-ready/SLA assertion is made.
