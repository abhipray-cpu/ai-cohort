# AI Cohort — 12 Projects in 14 Days

This repository contains a collection of production-minded AI products. Each product is independently runnable, while shared packages provide consistent contracts, local Codex execution, validation, observability, and deployment conventions.

## Product catalog

| Day | Product | Status |
| --- | --- | --- |
| 1 | TenderLens — tender eligibility and requirement extraction | active implementation; not production ready |
| 2 | ResolveDesk — PostgreSQL RAG chat with citation grounding | implemented pilot; validation and deployment gates remain open |

## Repository layout

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
All product delivery packs: [documentation catalog](docs/README.md).

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
