# CatalogBridge workbench

React/TypeScript matching desk: source import, budget authorization, evidence/candidate review, stale-context guard, reviewed CSV/coverage export and explicit cost/usage states. API/static UI share an origin in the production build.

From repository root: `npm --prefix apps/catalogbridge-web ci`, `npm --prefix apps/catalogbridge-web test`, `npm --prefix apps/catalogbridge-web run build`. Development Vite proxy targets loopback 8006. [Runbook](../../docs/catalogbridge/implementation-and-operations.md) describes explicit credentials and current limitations. Build/state tests pass; no connected browser was available for visual acceptance.
