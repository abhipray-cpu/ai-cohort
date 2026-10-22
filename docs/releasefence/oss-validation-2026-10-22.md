# Self-hosted MLflow/Phoenix — measured acceptance checkpoint

**Historical bounded checkpoint.** See the subsequent
[browser/larger-cohort follow-up](followup-acceptance-2026-10-22.md): six browser
cases pass, but the new 200-product live campaign failed. The original results and
24-call denominator below are unchanged; a separate new grant spent 239/240 calls.

22 October 2026. **Bounded end-to-end checks pass; full MVP acceptance remains open.**
The user authorized the recommended upstream MLflow alternative to an unavailable
LangSmith account. See [ADR 0002](adr-0002-self-hosted-mlflow.md). This qualifies
named checks for `mlflow-phoenix-v1`, not LangSmith or Arize AX. Historical failed
reports and the [earlier 18-call checkpoint](real-data-validation.md) are retained.

## Actual services and workload

The lab ran upstream **MLflow 3.17.2 with basic authentication and scoped experiment
permissions**, **Phoenix 20.23.0**, real isolated PostgreSQL, API/worker processes,
customer-side HTTP agent bundles, a connector and HMAC notification receiver.
Backends run in separate workspace virtual environments. No commercial account,
private fork, vendor impersonation or external tracing service was used.

Data comes from the actual public USDA FoodData Central branded-food release of
30 April 2026. Frozen 1,000-record source SHA-256:
`86690b369cac989d01a77fabd95a9438cbe1a2edb61cf6df4281e7cbf4ce8bcc`.
Source provenance is retained in every campaign report. These are not customer
traffic, semantic expert labels or evidence of food/regulatory decision accuracy.

| Campaign | Measured result | Evidence under `var/validation/` |
| --- | --- | --- |
| Source volume, no inference | 1,000 products, 1,000 sessions, 12,000 unique events, three organizations; metric/count oracles and full detector scan pass | `releasefence-oss-source-20261022/report.json` |
| Full process path, no inference | Six source-derived deterministic responses; actual dual export/read-back, alerts, signed canary/rollback and worker restart pass | `releasefence-oss-integration-20261022-r2/report.json` |
| Live installed Codex | Six products, six fresh calls, three organizations; source fidelity, metrics, alerts, signed/probed rollback and both backend reads pass | `releasefence-oss-live-20261022/report.json` |
| Real backend security/recovery | 1 process acceptance test passes: unauthorized and foreign-experiment read/write denied; each backend independently stopped/restarted with healthy peer/read-back preserved | `releasefence-dual-backend-security-20261022.xml` |
| Controlled source-bound faults | 150 cases pass; controlled timing/fault fixtures, not 150 natural live model incidents | `releasefence-oss-fault-matrix-20261022.xml` |
| Monorepo regression | 844 pass, five pre-existing other-product skips, zero failures/errors | `releasefence-oss-monorepo-20261022.xml` |
| UI | Three domain tests and TypeScript/Vite production build pass; no browser available | Commands below; not interactive UI acceptance |

The source-volume campaign is lifecycle/detector validation, **not** a 12,000-span
dual-backend load test. The deterministic process campaign is **not** inference.
The live campaign contains three explicitly authored iteration-cap failure drills,
not spontaneous customer failures. Stable bundles served fresh sessions afterward.

## Independent evidence audit

`var/validation/releasefence-oss-acceptance-summary-20261022.json` records hashes
of the six campaign artifacts and independent checks of the saved live evidence:

- All **24 executable source snapshots** still match current file hashes.
- Six traces / **12 unique spans** were queried from each actual backend: 24
  backend rows, not 24 unique spans. Original IDs, parentage, release identity,
  names and status agree after decoding MLflow protobuf-JSON IDs. Privacy
  allowlists and absent payload/events were checked by the campaign.
- All six command envelopes and six runtime-proof envelopes verify independently
  against exported public keys; command identity, revision and evidence hashes agree.
- Three notifications arrived 0.675–0.733 seconds after incident creation. Verified
  rollback was observed 0.393–0.633 seconds after the corresponding candidate task
  ended. These are tiny lab samples, not percentiles, command-only latency or SLAs.
- Metric oracles and both-release trace gates pass for the actual measured span
  windows; all eight per-organization exports were verified. This does **not**
  establish statistical canary promotion on a sufficiently powered live cohort.
- API/worker/backend owned processes stopped; worker restart required a newly
  completed cycle, not a leftover readiness file.

Usage was reported, but provider/model billing identity was not independently
verified. Six calls retain **unknown USD cost**, and cost-per-success remains null.
A zero known-cost subtotal is not a free-inference claim.

## Reproduction and authority

Install optional backends in separate environments using the pinned manifests in
`infra/releasefence-observability/`; see the [runbook](implementation-notes.md).
Run non-inference checks from the repository root:

```sh
RELEASEFENCE_MLFLOW_PYTHON="$PWD/var/validation/releasefence-mlflow-venv/bin/python" \
RELEASEFENCE_PHOENIX_PYTHON="$PWD/var/validation/releasefence-phoenix-venv/bin/python" \
  .venv/bin/python -m pytest -q tests/acceptance_releasefence_dual_backend.py
RELEASEFENCE_ACCEPTANCE_CORPUS="$PWD/var/validation/shelfproof-usda-grouped-20261021" \
  .venv/bin/python -m pytest -q tests/acceptance_releasefence_faults.py
.venv/bin/python -m pytest -q
npm --prefix apps/releasefence-web test
npm --prefix apps/releasefence-web run build
.venv/bin/python scripts/validate_releasefence.py --help
.venv/bin/python scripts/validate_releasefence.py \
  --mode integration --backend-lab \
  --corpus var/validation/shelfproof-usda-grouped-20261021 \
  --output var/validation/releasefence-oss-integration-next
```

The explicit dual-backend test requires the two interpreter paths above; inspect
its version/path prerequisites before opting in. Source/integration campaigns use
`--backend-lab` and a **new** output directory. Their integration mode makes zero
model calls. The lab provisions and stops only its own isolated loopback services;
it is not the production/Windows service installer.

The original approval is now **24/24 calls spent** across four campaigns (including
the failed first campaign). This checkpoint spent the final six. The durable global
ledger is `var/validation/releasefence-live-approval-20261022.sqlite3`.
**Do not rerun live mode, reset the ledger or change output directories to bypass
the cap. Any additional inference needs a new explicit bounded approval.**

## Remaining acceptance gates

Browser discovery returned no available browser (`[]`), so interactive navigation,
accessibility and browser tenant-session isolation remain unpassed. The target
Windows laptop, protected Cloudflare access, resource/soak testing, representative
actual-traffic statistical promotion, independent security/semantic review and
customer pilot remain open. Larger workload/fault-family targets are not replaced
by the controlled 150-case matrix. Phoenix remains a customer-owned ELv2 component,
not an unrestricted managed-service resale dependency.

The retained machine report deliberately says `scoped_checks_passed: true` and
`mvp_accepted: false`. Its generic `full_oss_profile_acceptance` pending marker is
not a claim that dual export failed; it covers the unclosed product gates above.
