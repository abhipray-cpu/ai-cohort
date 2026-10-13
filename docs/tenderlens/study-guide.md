# TenderLens study guide: connect the concepts to the product

This is a learning map for the implemented Day 1 product, not a production certification. Read [product](product.md), [architecture](architecture.md), and [current validation](validation-2026-10-13.md) alongside the code. A local Codex executable is the adapter; inference still requires configured OpenAI authentication and network access. The planned Windows service and Cloudflare Tunnel are not yet deployed or accepted.

## The one-sentence mental model

TenderLens turns a PDF pack into a *reviewable, evidence-backed draft*, not an autonomous bid decision. The model proposes claims. Application-owned contracts, source checks, durable processing, and a human reviewer decide what can become an approved export.

```text
PDF bytes → page text/OCR → bounded chunks → Codex JSON → Pydantic/evidence checks
          → SQLite checkpoints → complete or partial brief → human review → export
```

## Learn it in this order

1. **Product and source of truth.** Read [product.md](product.md), then inspect [`DraftBrief` and `Claim`](../../packages/contracts/src/contracts/tenderlens.py). Ask: what is a claim, what is a citation, and who owns the final decision? A source quote is evidence of what the document says, not proof that the document itself is correct.
2. **Documents and provenance.** Read [`Store.add_document`](../../apps/tenderlens-api/src/tenderlens_api/store.py) and the frozen [source manifest](../../data/tenderlens/manifests/public-evaluation-sources.json). PDF SHA-256 pins bytes; page number plus exact quote lets a reviewer find a claim. Text extraction and OCR are different paths. OCR makes image text searchable, but a clean OCR regression does not prove quality on poor scans. Try `pytest -q tests/test_public_evaluation_pdfs.py tests/test_ocr_status.py`.
3. **Structured output, in two layers.** Read [`LocalCodexProvider`](../../packages/agent-core/src/agent_core/codex_local.py), then [`ExtractionOrchestrator`](../../packages/agent-core/src/agent_core/orchestrator.py). Pydantic creates a JSON Schema for the provider. The adapter makes that schema strict for Codex; this constrains generation. The application then parses JSON and validates the response with Pydantic again. The second check matters because a provider guarantee is not a trust boundary. Try `pytest -q tests/test_provider.py tests/test_contracts.py`.
4. **Tool response validation.** The application looks up a page through a typed `PageLookupRequest`/`PageLookupResult`. It validates the returned document ID, page, and shape *before* putting that text into the prompt. The PDF's text is untrusted data: a sentence inside a tender cannot authorize an arbitrary tool call. Inspect `test_invalid_tool_result_is_rejected_before_model_call` in [`test_agent.py`](../../tests/test_agent.py).
5. **Repair versus operational retry.** Malformed JSON, schema errors, and citation mismatches produce validation events and a bounded repair prompt. A provider timeout or failed CLI process is operational; repeating the same repair prompt is not a fix. Multi-page timeouts trigger a smaller chunk. A terminal failure leaves a partial brief when earlier chunks succeeded. Read [`worker.py`](../../apps/tenderlens-api/src/tenderlens_api/worker.py) and [`test_long_pack_recovery.py`](../../tests/test_long_pack_recovery.py). OpenAI's [iterative repair-loop example](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex) is useful background for the review–repair–validate pattern; TenderLens's exact policy is in its own code.
6. **Durability and state.** SQLite stores `runs`, `run_chunks`, `claims`, and `events`. A successful chunk is committed before the next model call. `pending` leaves are resumed after a retry; `split` parents are excluded from progress; a draft appears only after all leaves complete. A `partial` preview is read-only and cannot be exported. Trace `Store.ensure_chunks`, `save_chunk`, `split_chunk`, `requeue_run`, and `finish_run` in [`store.py`](../../apps/tenderlens-api/src/tenderlens_api/store.py). This is a single-host, single-worker design, not a distributed queue.
7. **API and human gate.** Read [`api.py`](../../apps/tenderlens-api/src/tenderlens_api/api.py) and [`App.tsx`](../../apps/tenderlens-web/src/App.tsx). HTTP Basic protects local API routes; the planned Cloudflare Access gate is separate and not implemented here. The reviewer can accept, edit, or leave claims unresolved on a complete draft. Exports require review. Inspect the authenticated retry and partial export-lock tests.
8. **Evaluation.** Read [data and evaluation](data-and-evaluation.md), the [12 October baseline](public-evaluation-2026-10-12.md), and the [13 October follow-up](validation-2026-10-13.md). A green unit suite proves specific invariants. A live Codex run proves that a particular executable, account, source set, and moment worked. Neither is a quality score. Gold labels need independent human annotation, adjudication, and a held-out split by opportunity.

## How the requested concepts relate

The monorepo is an ownership map: `apps/tenderlens-api` and `apps/tenderlens-web` are the product, `packages/contracts` is the shared language, `packages/agent-core` owns the Codex adapter/orchestration boundary, and `packages/observability` owns failure-event shape. `data/tenderlens` holds manifests and future labels; `scripts` supplies repeatable developer/evaluation commands. Future challenge products can reuse packages without importing TenderLens internals.

The [C4 diagrams](architecture.md) are four zoom levels of this same system. Level 1 asks who uses TenderLens and which external services it depends on. Level 2 maps deployable pieces on the Windows host and the external model service. Level 3 explains the worker's parser, chunk planner, validator, and store. Level 4 maps those responsibilities to concrete classes. Follow one claim from PDF upload through each level; if a box has no implementation yet (Windows service or Cloudflare Access), treat it as a planned boundary.

| Concept | TenderLens implementation | What it protects against | What it does not prove |
| --- | --- | --- | --- |
| Pydantic contract | `DraftBrief`, `Claim`, `SourceCitation`, page lookup models | Missing/wrongly typed fields and invalid enum values | Semantic truth or complete recall |
| Provider JSON Schema | `codex exec --output-schema` with normalized strict schema | Nonconforming generation when provider enforces it | That the returned quote exists in a source PDF |
| Parse/schema retry | Bounded orchestrator loop, at most two repairs | Transient malformed output | Outage, quota exhaustion, or an overlong chunk |
| Tool-result validation | Page result checked against request | Wrong page or malformed lookup result entering the prompt | OCR fidelity |
| Evidence validation | Quoted text must occur on cited page | Fabricated page/quote pairs marked as verified | A quote interpreted correctly or a missed obligation |
| Validation failure log | `events` plus run ID, stage, attempt, summary | Invisible failures and untraceable repair attempts | Complete end-to-end telemetry; successful attempts are not yet all logged |
| Checkpoint/partial/retry | `run_chunks` and same-run retry | Losing every prior chunk when a later call fails | Long-pack success under every quota or capacity condition |
| Human approval | Review state separated from generated value | Treating model output as final | Reviewer accuracy |

The important separation is *shape → grounding → meaning → approval*. JSON Schema and Pydantic check shape. Citation matching checks grounding. A human and a labeled benchmark assess meaning and completeness. Approval is a workflow decision after those checks.

## A 45-minute hands-on lab

From the repository root on macOS/Linux (use `.venv/Scripts/python.exe` on Windows):

```bash
.venv/bin/python -m pytest -q tests/test_agent.py tests/test_long_pack_recovery.py
.venv/bin/python -m ruff check .
npm --prefix apps/tenderlens-web run build
```

Then inspect the test names and predict the state after a timeout on page 3: one saved chunk, a `partial` brief, a `provider_timeout` event, and locked export. Run the test and compare your prediction. Next, change *only a test fixture* to make a citation quote absent from the page: explain why a schema-valid output still fails evidence validation. Finally, open a stored run in the UI (if the local stack is up) and compare its `status`, `progress`, `events`, and review controls.

Optional live experiment, only when Codex is authenticated and available:

```bash
.venv/bin/python scripts/smoke_codex.py --brief
.venv/bin/python scripts/benchmark_public_evaluation.py --case serbia --session serbia-study
```

Fetch the public PDFs first with `scripts/fetch_public_evaluation.py`; source URLs and hashes are frozen in the manifest. The `--session` database is kept under gitignored `var/tenderlens-evaluation/sessions/`, so running the same command after a partial/failed result reuses its completed chunks. A live call may incur service usage and fail due to account quota or model capacity. Read the report rather than treating a nonzero exit as a product-quality score.

## Questions to answer before calling this production-ready

- Can a representative 20–60-page pack finish on the actual Windows laptop within a measured p95 target, with a reboot and Codex re-authentication drill?
- Do two humans agree on the mandatory obligations and deadline labels, and how does the product score against their adjudicated set?
- Can the reviewer see source conflicts and open questions prominently, and does citation navigation work in a real browser?
- Are Windows service identity, file ACLs, backup/restore, Cloudflare Access, and unauthorized-access tests demonstrated rather than diagrammed?
- Does cross-chunk reconciliation avoid duplicate claims and false open questions? The current merge deduplicates identical cited claims but does not resolve semantic conflicts across chunks.

For Codex CLI terminology and the documented `--output-schema`/`--output-last-message` invocation, see the official [non-interactive mode guide](https://learn.chatgpt.com/docs/non-interactive-mode). The repository code and tests, rather than that guide, are the source of truth for TenderLens behavior.
