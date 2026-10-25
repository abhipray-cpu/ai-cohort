# AI Cohort — 12 Projects in 12 Days

This repository contains a collection of production-minded AI products. Each product is independently runnable, while shared packages provide consistent contracts, local Codex execution, validation, observability, and deployment conventions.

## Product catalog

| Day | Product | Status |
| --- | --- | --- |
| 1 | TenderLens — tender eligibility and requirement extraction | active implementation; not production ready |
| 2 | ResolveDesk — PostgreSQL RAG chat with citation grounding | implemented pilot; validation and deployment gates remain open |
| 3 | PropertyBrief — property investigation and diligence planning | implemented pilot; actual-data validation and release gates documented |
| 4 | PatchDesk — client security-maintenance orchestration | implemented pilot; rigorous validation finds release-blocking coverage/AI gaps |
| 5 | RelayDesk — persistent technical escalation memory | Corrective-tested pilot; 89 real threads/6,680 non-bot messages, 283 tests; full release acceptance incomplete |
| 6 | ClauseGate — human-in-the-loop NDA exception approval | Implemented pilot; 61/61 development analyses, 346 tests, workflow/recovery checks pass; semantic/release gates remain blocked |
| 7 | CatalogBridge — cost-aware supplier catalog matching | Local draft router implemented; 476 tests; live comparison quota-stopped; savings/confidence and full acceptance remain blocked |
| 8 | BuildRelay — event-triggered CI failure response | Corrective-tested pilot: 533 tests; lease crash fixed; development anchor retention 90.20%; full acceptance open; study guide available |
| 9 | CaseCouncil — adversarial insurance-complaint decision review | Implemented engineering pilot; all five debate concepts; real-data permission and browser/Windows acceptance remain open |
| 10 | ShelfProof — self-reflecting food-listing review and repair | 785 tests passed; bounded live USDA/Codex run 6/6 review-ready with all five concepts; broader production acceptance pending |
| 11 | ReleaseFence — production-agent observability and release assurance | Bounded tracing/control and six browser E2E checks pass; larger 200-product live cohort failed (provider failures/Phoenix dead letters); Windows and statistical acceptance open |
| 12 | RepairClaim — consumer repair-coverage discovery and evidence casework | Scoped implementation with TDD; 187 local tests, actual process checks and 4 frontend tests. Public complaint metadata: 400 workflows / 4 distinct inputs; real repair documents: 7 packs / 52 pages, expanded correction/follow-up/privacy controls and six packet flows passed. General invoice extraction, browser, host and consumer acceptance remain open |

## Repository layout

[Windows Codex handoff: container deployment](guide.md): the current target for
all twelve products, private host Codex bridge and `orch1.sentiolus.in` gateway.

[Run the portfolio on the Windows laptop](docs/windows-laptop-deployment.md): setup,
installed Codex, protected Cloudflare access, backups and deployment qualification.

```text
apps/                 Independently deployable product applications
packages/             Shared, versioned platform code
data/                 Versioned datasets and evaluation artifacts (no secrets)
infra/                Windows and Cloudflare operational configuration
scripts/              Cross-product developer and CI utilities
tests/                Cross-product integration and contract tests
```

## Runtime model

Each product runs on the Windows laptop as a service. Its AI layer invokes the locally installed Codex CLI through `agent-core`, so product code does not call a model API directly. Codex CLI still requires configured OpenAI authentication and network access for model inference. Cloudflare Tunnel may expose an application endpoint, but never the Codex runtime directly.

TenderLens planning documents: [index](docs/tenderlens/README.md).
ResolveDesk planning documents: [index](docs/resolvedesk/README.md).
PropertyBrief planning documents: [index](docs/propertybrief/README.md).
PatchDesk planning documents: [index](docs/patchdesk/README.md).
RelayDesk: [docs](docs/relaydesk/README.md), [runbook](docs/relaydesk/implementation-and-operations.md), [corrective validation](docs/relaydesk/corrective-validation-2026-10-17.md), [study guide](docs/relaydesk/study-guide.md). Start/stop: `make relaydesk-up` / `make relaydesk-down` (port 8004).
All product delivery packs: [documentation catalog](docs/README.md).

RepairClaim Day 12: [delivery pack](docs/repairclaim/README.md), [requirements](docs/repairclaim/functional-requirements.md), [traceability](docs/repairclaim/requirements-traceability.md), [C4 architecture](docs/repairclaim/architecture.md), [TDD checkpoints](docs/repairclaim/tdd-checkpoints.md), [status](docs/repairclaim/implementation-status.md). Use `make repairclaim-test repairclaim-lint` for local checks; product-specific up/down/status targets and explicit provisioning are documented in [operations](docs/repairclaim/operations.md). Real-data E2E is a later phase, not a startup side effect.

ReleaseFence Day 11: [product docs](docs/releasefence/README.md), [implementation/runbook](docs/releasefence/implementation-notes.md), [C4 architecture](docs/releasefence/architecture.md), [TDD evidence](docs/releasefence/tdd-checkpoints.md), [latest OSS validation](docs/releasefence/oss-validation-2026-10-22.md), [status](docs/releasefence/implementation-status.md). Use `make releasefence-up/down/status/test`; explicit PostgreSQL/runtime credentials and separate keys are required. Bounded source/Codex/MLflow/Phoenix checks are not complete browser/Windows/statistical acceptance. The approved 24 live calls are fully spent.

ShelfProof Day 10: [product docs](docs/shelfproof/README.md), [implementation map](docs/shelfproof/implementation-notes.md), [status/evidence](docs/shelfproof/implementation-status.md), [C4 architecture](docs/shelfproof/architecture.md). Use `make shelfproof-up`, `make shelfproof-down`, `make shelfproof-status` and `make shelfproof-test`; explicit ShelfProof credentials are required. Real-data/quality/host acceptance are separate from implementation.

CaseCouncil Day 9: [delivery pack](docs/casecouncil/README.md), [implemented runbook](docs/casecouncil/implementation-and-operations.md), [C4 architecture](docs/casecouncil/architecture.md), [verification](docs/casecouncil/implementation-validation-2026-10-19.md), [data/permission gate](docs/casecouncil/data-and-evaluation.md). Use `make casecouncil-up/down/status/test`; actual source clearance, browser and Windows/tunnel acceptance remain open.

BuildRelay Day 8: [delivery pack](docs/buildrelay/README.md), [runbook](docs/buildrelay/implementation-and-operations.md), [corrective validation](docs/buildrelay/fixes-and-validation-2026-10-19.md), [study guide](docs/buildrelay/study-guide.md). Start/stop: `make buildrelay-up` / `make buildrelay-down` (8007; explicit credentials). Real-record HTTP/NATS/Codex replay reran; the lease crash is fixed and development failure-anchor retention reached 90.20% with a larger bounded context. Latest full regression: 533 passed, no skips. Model-quality results and open independent review, browser, live issue-write and Windows/Cloudflare gates are explicit in the report.

CatalogBridge Day 7: [delivery pack](docs/catalogbridge/README.md), [actual runbook](docs/catalogbridge/implementation-and-operations.md), [implementation evidence](docs/catalogbridge/implementation-validation-2026-10-17.md), [real-data evaluation](docs/catalogbridge/data-and-evaluation.md). Start/stop: `make catalogbridge-up` / `make catalogbridge-down` (port 8006; explicit credentials). Advisory token mode only; full acceptance remains blocked.

Latest: [CatalogBridge local-routing validation](docs/catalogbridge/local-routing-validation-2026-10-18.md): opt-in local review-draft scorer, 476 Python tests and eight web tests/build. The live comparison stopped on quota after 123 calls, with three new unknown liabilities and no eligible savings result. [Study guide](docs/catalogbridge/study-guide.md) documents implementation and measured limits. Historical [receipt/cache evidence](docs/catalogbridge/receipts-and-repeat-work-2026-10-18.md) and [240-call hardening phase](docs/catalogbridge/runtime-hardening-2026-10-18.md) remain separate.

18 October: [fresh real-data validation](docs/catalogbridge/fresh-real-data-validation-2026-10-18.md), 60 new pairs/400 query IDs, 98% retrieval, 416 tests. Original unknown-liability failures remain recorded; the successful bounded replay does not clear release gates.

ClauseGate Day 6: [docs](docs/clausegate/README.md), [runbook](docs/clausegate/implementation-and-operations.md), [complete development evaluation](docs/clausegate/development-validation-2026-10-17.md), [study guide](docs/clausegate/study-guide.md). Start/stop: `make clausegate-up` / `make clausegate-down` (port 8005). Independent final review is mandatory; not production/legal-quality accepted.

## Product conventions

- Product code belongs under `apps/<product-name>/`.
- Reusable code belongs under `packages/`; products must not import from one another.
- All model and tool inputs/outputs have Pydantic contracts in `packages/contracts`.
- A product must log validation failures, retries, and final outcomes through `packages/observability`.
- Product-specific data belongs below `data/<product-name>/` using the raw/extracted/gold/adversarial/manifests convention.

## Tooling

Python tooling is configured in `pyproject.toml`. TenderLens is under active implementation; its current release gates and limitations are recorded in [the delivery pack](docs/tenderlens/README.md).

## Run TenderLens locally

Prerequisites: Python 3.12, Node.js, npm, and an authenticated Codex CLI. Copy `.env.example` to a local `.env` and set a strong `TENDERLENS_PASSWORD`; never commit the real value. The app reads environment variables from the shell or service manager, not `.env` automatically.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
npm --prefix apps/tenderlens-web ci
npm --prefix apps/tenderlens-web run build
```

Start the API and worker in separate terminals from the repository root, with the environment variables loaded:

```bash
.venv/bin/uvicorn tenderlens_api.api:app_from_env --factory --host 127.0.0.1 --port 8000
.venv/bin/python -m tenderlens_api.worker
```

For a local development run, create `.env` from `.env.example`, replace the placeholder password,
then use `make up`, `make status`, and `make down`. `make up` builds the web UI and starts both
processes in the background; logs and PID state live in the gitignored `var/tenderlens-dev/`.
It binds only to `127.0.0.1`. Python dependencies and `npm ci` must be installed first.
Shell environment variables override values in `.env`.

On Windows, where Make is not installed by default, run the same launcher directly:
`./.venv/Scripts/python.exe scripts/dev_stack.py up` (or `status`/`down`). Build the web UI
with `npm --prefix apps/tenderlens-web run build` before `up`. This launcher is for local
development and smoke testing, not Windows service installation or Cloudflare deployment.

Open `http://127.0.0.1:8000/` and sign in with the configured HTTP Basic credentials. On Windows, use `py -3.12 -m venv .venv` and `./.venv/Scripts/python.exe -m pip install -e ".[dev]"` for setup. Start the two processes with `./.venv/Scripts/python.exe -m uvicorn tenderlens_api.api:app_from_env --factory --host 127.0.0.1 --port 8000` and `./.venv/Scripts/python.exe -m tenderlens_api.worker`. The local Codex executable must be available to the worker service account.

Quality checks:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
npm --prefix apps/tenderlens-web run build
```

Run `.venv/bin/python scripts/fetch_seed.py` to download and checksum-verify the public RFP fixture. The real-document test then runs as part of pytest. The PDF is gitignored because redistribution rights have not been established.

## Run ResolveDesk

Install the Python workspace again after pulling the new application, then install its web dependencies:

```bash
.venv/bin/python -m pip install -e '.[dev]'
npm --prefix apps/resolvedesk-web ci
.venv/bin/python scripts/fetch_resolvedesk_sources.py
make resolvedesk-up
```

Open `http://127.0.0.1:8001/`. The development launcher loads `.env` and can reuse TenderLens credentials when explicit ResolveDesk credentials are absent. `make resolvedesk-status` and `make resolvedesk-down` manage only this product. Default data is `var/resolvedesk`; TenderLens data/processes remain independent.

ResolveDesk retrieves from frozen PostgreSQL 16/17 documentation, generates through the installed Codex CLI, and searches the official PostgreSQL site when saved evidence is insufficient. Default search needs no API key. Optional Brave search uses `RESOLVEDESK_SEARCH_PROVIDER=brave` and `BRAVE_SEARCH_API_KEY`. Human review is required before a resolved reply can be exported.

Checks and an opt-in live evaluation:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
npm --prefix apps/resolvedesk-web run build
.venv/bin/python scripts/smoke_resolvedesk_http.py
.venv/bin/python scripts/fetch_resolvedesk_sources.py --data-dir var/resolvedesk-evaluation
.venv/bin/python scripts/benchmark_resolvedesk.py --live
```

The final command consumes authenticated Codex service usage. Smoke expectations are provisional, not an independent accuracy benchmark. See [ResolveDesk status](docs/resolvedesk/implementation-status.md) for measured results and remaining gates.

## Run PropertyBrief

```bash
.venv/bin/python -m pip install -e '.[dev]'
npm --prefix apps/propertybrief-web ci
make propertybrief-up
```

Open `http://127.0.0.1:8002/`. Development startup loads `.env` and reuses TenderLens credentials if explicit PropertyBrief credentials are absent. `make propertybrief-status` and `make propertybrief-down` manage only PropertyBrief. Windows startup services require explicit product credentials; see [operations](docs/propertybrief/operations.md).

PropertyBrief investigates confirmed NYC building identities using eight official HPD/DOB record sources. Its conversational, application-controlled ReAct worker produces cited findings and seller/inspector/attorney follow-ups, with bounded actions, self-critique and durable partial results. A reviewed pack is exportable as Markdown or JSON. It is not title research, a safety assessment or investment clearance.

```bash
make propertybrief-test
.venv/bin/python scripts/fetch_propertybrief_sources.py var/propertybrief-corpus/new-capture --count 12
.venv/bin/python scripts/validate_propertybrief.py --corpus var/propertybrief-corpus/new-capture --all
# Opt-in actual model run; consumes authenticated Codex usage:
.venv/bin/python scripts/validate_propertybrief.py --corpus var/propertybrief-corpus/new-capture --live --case 375411
```

See the [PropertyBrief delivery pack](docs/propertybrief/README.md) for measured validation, limitations and learning material. Raw source captures and local evaluation databases remain gitignored.
