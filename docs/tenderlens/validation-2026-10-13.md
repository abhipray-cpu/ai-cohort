# Recovery validation — 13 October 2026

This is an engineering validation record, not a quality benchmark or release sign-off. It follows the [12 October public-PDF baseline](public-evaluation-2026-10-12.md). Source bytes remain gitignored; URLs, hashes, and page counts are frozen in the [public-source manifest](../../data/tenderlens/manifests/public-evaluation-sources.json). The machine-local JSON reports and persistent evaluation DBs are under gitignored `var/tenderlens-evaluation/`.

## What changed and what the tests prove

The worker now plans at most four pages and 12,000 extracted characters per initial chunk. Each validated chunk is committed in SQLite. A typed provider timeout writes a `provider_timeout` event and splits a multi-page pending leaf. A terminal failure after completed leaves materializes a read-only `partial` brief with progress and an error. Review and export reject that partial state. The authenticated retry endpoint requeues the same run and processes only pending leaves. Strict provider-schema normalization was also added because a real Codex call rejected optional fields/defaults in the raw Pydantic JSON Schema.

On this host, the current automated suite has **37 passing tests**, Ruff passes, and the React/TypeScript production build passes. Fault tests cover JSON parse repair, invalid page-lookup response, missing citation evidence, typed timeout events, splitting, partial review/export locks, same-run retry, stale-worker recovery, and a two-invocation persistent benchmark session. The session test uses a deterministic fake provider; it proves checkpoint/resume behavior without claiming model quality. A live structured-output smoke with the installed Codex CLI returned one schema-valid draft in 12.7 seconds on 13 October. The updated local API and worker started successfully; `/health/ready` returned 200 and an unauthenticated opportunity request returned 401. `make down` stopped both managed processes and `make up` restarted them cleanly, leaving the local UI/API available at `http://127.0.0.1:8000/`.

## Real-PDF follow-up

| Input / attempt | Observation | What it establishes |
| --- | --- | --- |
| Serbia, 29 pages, early recovery build | An initial live attempt preserved 31 claims in a `partial` brief after a later call failed on a provider-schema rejection. | Earlier validated chunks survived; strict schema normalization was necessary. Not a full-pack pass. |
| Serbia, 29 pages, strict-schema build | Two chunks succeeded in 57.0 and 66.5 seconds; a third call hit a Codex usage limit. The run preserved 30 claims in `partial`, with a provider failure event; 131.1 seconds total. | Partial materialization and event persistence worked on real PDF content. Quota stopped full completion; the old ephemeral harness could not resume that particular DB. |
| Serbia, persistent session `serbia-recovery-2026-10-13`, first invocation | Codex returned a model-capacity/503 error after 10.9 seconds, before a chunk was saved. Run state was `failed`, progress 0/14, one provider event. | The harness retained the same run for retry. No extraction-quality conclusion. |
| Serbia, same persistent session, retry | Completed `draft`: 14/14 chunks, 14 Codex calls, 1,552.4 seconds (25.9 minutes), 291 claims. The final report has one provider event retained from the earlier capacity-failed invocation. | The checkpointed worker can complete this full 29-page PDF on this host after a retry. This is one latency/functional observation, not a quality or SLA pass. |

The capacity error surfaced only as a generic provider failure in that first invocation. The adapter/orchestrator now recognizes capacity and usage-limit stderr patterns and records short, actionable summaries without copying raw tender text into events. This classifier has deterministic tests; its live behavior is not yet separately accepted.

The completed Serbia draft is **not review-ready on quality grounds**. All 291 claims have at least one citation and 285 are marked `verified`, but there are **88 open questions**, many asking for fields absent from an individual chunk even though other chunks contain them. The submission-deadline conflict is correctly kept unresolved with quotes from pages 7–8 (18 February versus 9 March 2026). However, `deadline` also includes clarification and general contract-period claims, creating significant reviewer noise. The current exact-quote check establishes grounding, not correct categorization or recall. A human gold set and pack-level reconciliation are required before treating this as a product-quality pass.

## Remaining acceptance work

- Complete the full Nepal pack live and measure resource use; Serbia completed once but took 25.9 minutes and produced noisy output. Do not infer quality from draft status or claim counts.
- Adjudicate a human-labeled corpus for recall, precision, critical misses, and citation correctness; the six PDFs are exploratory data, not gold labels.
- Test actual browser interactions, especially source navigation, conflict visibility, partial-state controls, and narrow-screen usability. No in-app browser connection was available for the earlier visual test.
- Reconcile across chunks. Exact duplicates are removed, but a question from one chunk may be answered in another and still remain in `open_questions`.
- The live Serbia retry made this concrete: early chunks each asked for a submission deadline because their local pages lacked one, while another chunk had cited conflicting deadline dates. Simply concatenating open questions can mislead a reviewer. Treat the merged question list as unaccepted until a pack-level reconciliation test passes.
- Run Windows service-account, Codex authentication, restart/restore, protected Cloudflare Access, and backup tests on the target laptop.

## Reproduce

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
npm --prefix apps/tenderlens-web run build
.venv/bin/python scripts/fetch_public_evaluation.py
.venv/bin/python scripts/smoke_codex.py --brief
.venv/bin/python scripts/benchmark_public_evaluation.py --case serbia --session serbia-recovery-2026-10-13
```

The final two commands need a working, authenticated Codex CLI and network access. A persistent session keeps its document set and SQLite checkpoints between commands. Repeating its command resumes a failed/partial run; it does not create a new benchmark sample. Model capacity or usage limits may interrupt it. Store run IDs and report JSON before deleting any session data.
