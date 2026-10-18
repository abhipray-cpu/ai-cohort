# CatalogBridge API and worker

Independent supplier-catalog matching pilot on loopback 8006. Read the [runbook](../../docs/catalogbridge/implementation-and-operations.md), [engineering evidence](../../docs/catalogbridge/implementation-validation-2026-10-17.md) and [release gates](../../docs/catalogbridge/product-acceptance.md).

From repository root, after installing the Python workspace/frontend and configuring explicit `CATALOGBRIDGE_USERNAME/PASSWORD`: `make catalogbridge-up`, `make catalogbridge-status`, `make catalogbridge-down`, `make catalogbridge-test`.

Direct processes are `python -m uvicorn catalogbridge_api.api:app_from_env --factory --host 127.0.0.1 --port 8006` and `python -m catalogbridge_api.worker`; these require environment variables already loaded. Model access uses the installed Codex adapter and explicit batch egress; inference may be remote. Advisory token limits only; strict mode is refused. No qualified automatic-acceptance calibration or real-data quality/savings result exists yet.
