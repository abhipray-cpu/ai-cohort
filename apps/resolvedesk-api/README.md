# ResolveDesk API and worker

Python/FastAPI application with an independent SQLite store. Install from the repository root with `.venv/bin/python -m pip install -e '.[dev]'`. See the [delivery pack](../../docs/resolvedesk/README.md) and [implementation evidence](../../docs/resolvedesk/implementation-status.md).

Primary flow: persistent multi-turn RAG chat. Authenticated `/v1/chats` and `/v1/chats/{id}/messages` atomically queue turns, resolve follow-ups with bounded history, retrieve fresh passages and retain each answer's evidence. See [chat API and design](../../docs/resolvedesk/chat.md). Review/export remains optional and separate from chatting.

```bash
make resolvedesk-up
make resolvedesk-status
make resolvedesk-down
```

The launcher loads `.env`, uses loopback port 8001, and keeps process/log state in ignored `var/resolvedesk-dev`. Explicit ResolveDesk credentials win; if absent, this development launcher can reuse the local TenderLens team credentials. The service entrypoint requires explicit ResolveDesk credentials instead.

Manual processes, with environment already loaded:

```bash
.venv/bin/python -m uvicorn resolvedesk_api.api:app_from_env --factory --host 127.0.0.1 --port 8001
.venv/bin/python -m resolvedesk_api.worker
```

Default data: `var/resolvedesk`. Official PostgreSQL site search is enabled by default and restricted to supported documentation versions. `RESOLVEDESK_SEARCH_PROVIDER=brave` selects the optional keyed adapter; `disabled` makes fallback explicitly unavailable. Generation uses the installed Codex CLI through the shared provider boundary.

Source ingestion/refresh, version-filtered FTS5 retrieval, bounded generation, citation validation, advisory support assessment, clarification/escalation, immutable reviewed revisions, and Markdown/JSON exports are implemented. Normalized source snapshots and export records live in SQLite; raw acquisition HTML is kept separately in ignored `data/resolvedesk/raw`.

Source refresh is bounded and synchronous in this pilot, with atomic publication per source; failed refresh of a source retains its old index entry. Investigations run in the durable worker queue. Collection-level atomic refresh and background ingestion jobs are later extensions.
