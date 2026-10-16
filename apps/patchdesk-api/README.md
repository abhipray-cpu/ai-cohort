# PatchDesk API and worker

Day 4 multi-tool maintenance desk. [Delivery pack](../../docs/patchdesk/README.md), [runbook](../../docs/patchdesk/operations.md), [actual validation](../../docs/patchdesk/implementation-validation-2026-10-15.md).

From the monorepo root: install `.[dev]`, run `npm --prefix apps/patchdesk-web ci`, then `make patchdesk-up`. API/static UI: loopback 8003; separate worker/store; first-store per-user admin bootstrap. No direct LLM API, project installation or automatic external writes. See runbook for credentials, scoped egress, tests and Windows target.
