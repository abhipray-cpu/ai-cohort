# PropertyBrief web

React/TypeScript property investigation workspace with persistent conversations, candidate confirmation, eight-source coverage, evidence drawer, activity, review/edit and Markdown export. A printable report layout is included.

```bash
npm --prefix apps/propertybrief-web ci
npm --prefix apps/propertybrief-web test
npm --prefix apps/propertybrief-web run build
make propertybrief-up
```

The API serves the built assets and authenticates the same-origin browser session at `http://127.0.0.1:8002/`. The development launcher can reuse existing TenderLens credentials. Source and generation progress is polled from durable server state; reload does not restart an investigation.

[UI specification](../../docs/propertybrief/reviewer-ui.md), [API/worker](../propertybrief-api/README.md), and [validation status](../../docs/propertybrief/implementation-status.md). A build and presentation tests do not establish browser interaction or visual acceptance.
