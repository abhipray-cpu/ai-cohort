# PropertyBrief API and worker

Authenticated NYC property investigation service, durable ReAct worker, source adapters, evidence validation, review and exports. Full product documentation: [delivery pack](../../docs/propertybrief/README.md).

Install the Python workspace from the repository root with `python -m pip install -e '.[dev]'`. The frontend must be built before starting the same-origin web host. `make propertybrief-up`, `make propertybrief-status`, and `make propertybrief-down` manage only this product. Default URL: `http://127.0.0.1:8002/`.

The development launcher loads `.env` and can reuse TenderLens credentials when explicit PropertyBrief credentials are omitted. Services require explicit `PROPERTYBRIEF_USERNAME` and `PROPERTYBRIEF_PASSWORD`. Do not use the placeholder password. AI invokes the installed, authenticated Codex CLI; source APIs and model inference need network access.

Direct foreground commands, with configuration loaded in the environment:

```bash
.venv/bin/python -m uvicorn propertybrief_api.api:app_from_env --factory --host 127.0.0.1 --port 8002
.venv/bin/python -m propertybrief_api.worker
```

Use `.venv/Scripts/python.exe` on Windows. Development process supervision is distinct from [Windows startup packaging](../../infra/windows/install-propertybrief.ps1), which still requires target-host acceptance.

Core modules: [sources](src/propertybrief_api/sources.py), [evidence](src/propertybrief_api/evidence.py), [store](src/propertybrief_api/store.py), [worker](src/propertybrief_api/worker.py), [API](src/propertybrief_api/api.py), and [backup](src/propertybrief_api/backup.py). Snapshots, reports and exports are stored in the separate `var/propertybrief/propertybrief.sqlite3` database, not a citywide mirror.

```bash
make propertybrief-test
.venv/bin/python -m propertybrief_api.backup backup var/propertybrief var/backups/propertybrief-new
.venv/bin/python -m propertybrief_api.backup restore var/backups/propertybrief-new var/propertybrief-restored
```

Backup/restore refuse existing destinations. A restore verifies SQLite integrity and hashes, preserves reviewed evidence, and expires stale worker ownership. Do not replace the live directory during a test.
