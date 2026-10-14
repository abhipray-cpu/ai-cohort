# Conversational RAG — implementation correction

The initial delivery implemented single-ticket RAG, not the requested RAG chat. This correction makes persistent multi-turn chat the primary interface. Production acceptance remains open.

## User journey

Open `http://127.0.0.1:8001/`, ask “Can pg_dump 16 back up a PostgreSQL 17 server?”, inspect the citation buttons, then ask “Does that also apply to 16?” The follow-up resolves its subject from the conversation and retrieves version-16 evidence anew. Refresh or choose the conversation from the sidebar to reopen it. General questions such as “What is pg_dump?” require no server/client form. Explicit environment facts can be stated in subsequent messages.

No commands are executed by the agent. These are advisory answers, not automatic remediation. `supported` is an evidence assessment, not human approval or guaranteed correctness.

## Runtime sequence

```mermaid
sequenceDiagram
  participant U as Chat UI
  participant A as API / store
  participant W as Durable worker
  participant C as Installed Codex adapter
  participant R as FTS5 / approved search
  U->>A: Send message + expected turn count + idempotency key
  A->>A: Atomically persist message, turn and queued run; pin index revision
  W->>A: Load current message + bounded same-thread history
  W->>C: ChatResolution (standalone question, documentation scope, environment)
  W->>A: Checkpoint contextual resolution
  W->>R: Fresh version-filtered retrieval for this turn
  R-->>W: Immutable passages
  W->>W: Validate passage identity / scope
  W->>C: Generate cited AnswerDraft; history is context only
  W->>C: Independently assess citation support (advisory)
  opt Missing or weak evidence and remaining budget
    W->>R: Sanitized official-source search, fetch and rank
    W->>C: Regenerate and reassess against fetched evidence
  end
  W->>A: Persist answer + evidence + uncertainty + stage events
  U->>A: Poll transcript / reopen later
  A-->>U: Every turn with its own answer, evidence and status
```

## Contracts and storage

- `ChatCreate`: optional title and known server/client/OS context. Unknowns stay nullable.
- `ChatMessage`: nonblank 1–8,000-character content and optimistic `expected_turn_count`.
- `ChatResolution`: standalone retrieval question, documentation versions (16/17), nullable actual environment, clarification flag and questions. Comparing documentation must not silently change the actual server version.
- `chats` stores conversation metadata. `chat_turns` links ordered user messages to durable runs. Existing runs, answer revisions and evidence snapshots are reused, not overwritten as a rolling answer.
- `POST /v1/chats`, `GET /v1/chats`, `GET /v1/chats/{id}`, `POST /v1/chats/{id}/messages`. Sending requires `Idempotency-Key`; conflicting keys, stale counts and concurrent pending turns return conflicts. Existing auth and same-origin protections apply.
- Failed latest turns use `POST /v1/runs/{id}/retry`. Retrying older turns after a later message is rejected to preserve the later conversation's context.

## Context, grounding and bounds

Only the last six prior turns from the same thread are considered. Each prior user/assistant message is capped at 1,200 characters, with 8,000 characters total history. Current messages retain their separate input bound. Previous environment resolution is carried forward. This is bounded recent context, not unlimited memory; long conversations can lose older non-environment details.

History is untrusted context, never a citable source. The contextualizer has no tools. Each answer uses freshly retrieved, application-validated passages and its own exact citation quotes. Contextual resolution itself remains model-dependent and needs wider quality evaluation. General documentation queries do not inherit the ticket workflow's mandatory environment gate.

Chat permits at most six model calls (contextualization, answer, assessment, bounded repairs/fallback) within the existing 600-second overall deadline and 180-second per-call ceiling. Legacy ticket runs retain four calls. Resolution, evidence, search and partial candidates have checkpoints. A timeout retains the user message, failure event and any incomplete candidate with visible warning.

## Acceptance evidence

All four concepts are explicitly described in the chat welcome screen's “How this RAG chat works” disclosure. Completed turns show indexed-context retention and search fallback status. Failed/empty/unavailable search must not render as successful recovery. Uncertain and incomplete answers use a low-confidence label, never an invented probability. Five frontend presentation tests cover these labels; they are not browser interaction tests.

Wider actual-source and live-model validation: `make resolvedesk-test` and opt-in `make resolvedesk-validate-live`. See [data/evaluation protocol](data-and-evaluation.md).

`tests/test_resolvedesk_chat.py` covers persistence/reopen, follow-up scope, distinct historical evidence, general questions without required environment, idempotency, pending-turn conflicts, failure/retry and authenticated HTTP contracts. Existing grounding/search/review regressions remain required.

Run opt-in real-model HTTP acceptance:

```sh
.venv/bin/python scripts/smoke_resolvedesk_chat.py
```

It creates a real two-turn conversation in the running product, checks idempotency, waits for worker completion, verifies exact citation membership and version-16 follow-up sources, and ensures the first answer remains unchanged. Reports are ignored under `var/resolvedesk-evaluation/reports/`. Functional smoke is not an independent accuracy benchmark. Browser interaction checks, human-adjudicated quality and Windows deployment remain separate gates.
