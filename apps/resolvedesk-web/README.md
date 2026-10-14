# ResolveDesk RAG chat UI

React/TypeScript/Vite chat-first interface: persistent conversation sidebar, multi-turn composer, per-answer source quotes, uncertainty labels, worker progress, and safe retry. Default `/` or `#chat`; `#chat/{id}` reopens a thread. `#knowledge` and `#workspace` provide the secondary knowledge library and case review/export tools. It calls the authenticated same-origin API. Development Vite requests proxy to loopback port 8001.

```bash
npm --prefix apps/resolvedesk-web ci
npm --prefix apps/resolvedesk-web run build
npm --prefix apps/resolvedesk-web test
```

The API serves the production build. `make resolvedesk-up` builds it and starts the API/worker. Responsive layouts, modal keyboard focus, source text escaping, and explicit uncertainty/review controls are implemented. Actual browser visual/interaction acceptance remains a separate gate.

The test command uses Node's built-in test runner and TypeScript stripping (Node 22.12+ or 24 recommended). It verifies the four concept descriptions, low-confidence labels and truthful retrieval/search provenance strings. These are presentation unit tests, not a replacement for browser acceptance.
