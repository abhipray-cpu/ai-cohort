# RelayDesk aggressive validation — 16 October 2026

**Verdict: FAIL / not production ready.** This expanded validation supersedes the initial small engineering smoke test as the current release assessment. Application code was not changed during this testing request. Validation tools, reproducible tests and documentation were added; defects are not silently patched or relabelled passes.

## Distinct real data and quality

| Measure | Observed |
| --- | ---: |
| Distinct public issue threads | 49 |
| Repositories represented | 22 |
| Acquired messages, including bots | 3,744 |
| Non-bot attributed messages | 3,576 |
| Distinct non-bot body hashes | 3,515 |
| Repeated non-bot bodies | 61 |
| Complete / explicitly partial captures | 45 / 4 |
| Threads with ≥20 non-bot messages | 45 |
| Zero non-bot message threads | 1 |
| Threads with >100 non-bot messages | 1 |

The complete long-history supplement is [TypeScript #26242](https://github.com/microsoft/TypeScript/issues/26242), with 137 non-bot messages. The broader corpus reuses eight original captures without counting their replay as new data. It adds read-only public discovery across the 20 planned repositories, plus the prior Flask/FastAPI sources. Full raw payloads, URL/time/hash manifests, batches, partial gaps and selected identities remain local under ignored `var/validation/`.

GitHub exposed a 60-read/hour public API quota; acquisition respected it. The main run allowed 56 core reads; the separate long-thread supplement used three more, reusing trusted metadata. Search had a separate bounded allowance. No token discovery, upstream writes, IP rotation or quota bypass occurred. [GitHub's documented quota](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) explains why the larger target was not silently called complete.

This is **not** 49 independently screened technical incidents. The popularity/comment-count discovery admits feature discussions and an Axios branding thread, useful as negative/out-of-domain controls but not positive technical-investigation evidence. A bot-only thread and four partial captures are retained, not hidden. Non-bot attribution does not prove human authorship; identical bodies are reported separately, not inflated as distinct supported facts.

The original 200-substantive-thread/5,000-message target, ten >100-message histories, independent 300-question/two-reviewer labels, blind held-out splits and calibrated quality gates remain **unmet**. Repository breadth alone does not meet them.

## Retrieval and state diagnostics

441 retrieval queries ran: 431 across the main corpus and ten on the long supplement. They cover four generic handover intents per case and distributed extractive source-location probes, alongside historical-cutoff, authorization, replay, restart and compression checks.

| Extractive source-location probes | Target source in top 10 / 245 |
| --- | ---: |
| Product hybrid recall | 244 |
| Lexical-only baseline | 245 |
| Vector-only reference ranking | 212 |

These probes reuse words from the target source. They therefore favor lexical retrieval and are **not independent natural-language answer accuracy**, semantic entailment, calibrated confidence or proof of superiority over keyword search. Vector-only uses a validation reference ranking over the same authorized vectors, not a separate product mode. The existing controlled paraphrase test still demonstrates the real semantic path, but does not replace a broad paraphrase benchmark.

Small natural scopes: hybrid recall p50/p95 was 66.2/123.8 ms across the main run and 144.9/176.6 ms on the 137-message case. These are macOS observations, not Windows guarantees.

The two corpus runs executed 1,043 engineering check instances: 1,037 passed and six failed, representing the same three defect classes reproduced in both scopes. These counts include repeated invariant checks over cases, not 1,043 independently reviewed answers. Failures were retained and the runners exited nonzero.

Passed paths included import/bot accounting, replay deduplication, persisted vector indexing, scoped exact spans, no later source timestamps in historical hits, explicit compression omissions, outsider rejection, bounded malformed-JSON repair, late-timeout checkpoint preservation, erasure during generation preventing publication, 16-way optimistic edit conflicts, 16-way enqueue deduplication, and restore with the correct current erasure ledger.

## Ten actual installed-Codex jobs

The broad live subset was frozen by largest acquired message count before provider execution. No failed job was retried and substituted as a pass. A separate long case, a two-session continuity journey and a labelled poisoned-source job complete ten actual jobs.

| Job | AI stage result | Terminal artifact |
| --- | --- | --- |
| Axios #318 | Rejected after bounded repair | Partial evidence fallback |
| VS Code #981 | Rejected after bounded repair | Partial evidence fallback |
| VS Code #16488 | Reply timeout | Partial evidence fallback |
| TypeScript #449 | Rejected after bounded repair | Partial evidence fallback |
| TypeScript #14600 | AI-assisted draft produced | Partial draft |
| Axios #2130, branding/out-of-domain | AI-assisted draft produced; correctly identified nontechnical scope | Partial draft; typed citation defect observed |
| TypeScript #26242, 137-message history | AI-assisted draft produced | Partial draft |
| Elasticsearch, first session | AI-assisted draft produced | Partial draft |
| Elasticsearch, fresh second session | Rejected after bounded repair | Partial evidence fallback |
| Labelled poisoned Elasticsearch source | AI-assisted draft produced; attack marker absent from answer | Partial draft |

**5/10 produced AI-assisted drafts; 5/10 did not. None is a certified complete or independently correct handover.** Four failures exhausted repair after `Unsupported verification claim`; one timed out. A controlled test proves the unsafe-phrase rule also rejects legitimate negation, but discarded raw replies from the natural failed jobs were not retained, so their individual rejection causes cannot be retrospectively classified as false positives.

The initial Elasticsearch answer correctly reported 8.4.2 and mapper-size against supplied evidence. The new session used a fresh 147-character buffer and retained semantic evidence but did **not** complete an AI answer. That is not an end-to-end continuity pass. The one injected prompt attack was not followed, and successful generations retained provider audit records; one attack is not general prompt-injection proof.

### Grounding failure in real outputs

The current user question appears among the retrieved evidence in all seven inspected broad/long outputs. In Axios #2130 it was the **only** selected hit. Its seven factual claims all cited that question's memory ID, while mentioning different compression-source IDs inside prose. TypeScript #14600 likewise reused one typed citation across claims drawing on different summary sources.

This is not proof those facts are all false—the summary supplied actual source content—but the typed claim→evidence mapping is not faithful. Clicking/following the typed citation does not reliably reach the supporting record. `ai_succeeded=true` and valid IDs must not be interpreted as successful grounded answers.

A separate **controlled fabricated provider response**, not a natural model hallucination observation, claimed universal recovery/customer confirmation while attaching an allowed memory ID. It was accepted. This demonstrates the known distinction between structural reference validation and semantic support; required quality gating remains incomplete.

## HTTP, capacity and recovery

The running service passed 20 HTTP negative/security checks and 160 reads at concurrency eight: role separation, revocation, CSRF/origin defenses, malformed/non-JSON/extra-field/oversized input, pagination bounds, traversal, foreign-session rejection and logout. Read p50/p95 was 22.9/35.1 ms including fresh-client setup. Load was bounded and local, never directed at public sources.

The scale fixture uses **labelled copies of real payloads merged into an artificial case**. Replicas add zero unique corpus messages and are not natural histories or accuracy evidence.

| Memory objects | Vector chunks | Two recall probes (ms) | Serialized compression (characters) |
| --- | ---: | --- | ---: |
| 1,000 | 1,230 | 780.7 / 610.9 | 41,859 |
| 5,000 | 6,391 | 3,670.5 / 2,825.2 | 186,068 |
| 10,000 | 12,845 | 7,158.0 / 5,673.6 | 366,025 |

All six probes missed the provisional 500-ms goal. They are individual probes, not a statistically estimated scale p95. SQLite integrity remained `ok`; the 10,000-memory database was about 48.7 MB, which is disk size—not RSS. The compressor's full omitted-ID list grows without bound: at 5k/10k, metadata alone exceeds the entire 48,000-character model-context allowance. At 1k, the summary leaves little room for the other required context. This is a functional model-availability issue as well as a latency problem.

An actual isolated worker was killed after committing two vector chunks during a merged 300-message fixture, then restarted. Five recovery checks passed: durable completion, rotated lease, unchanged original deadline/zero-call reservation, 404 final chunks with semantic readiness, and exactly one user/assistant turn. Lease expiry was **explicitly injected** to avoid waiting 150 seconds; this does not measure watchdog timing. The user's running service was not killed for this drill.

## Findings and release disposition

Final checks: **266 Python tests passed, 7 strict expected failures**; those seven are known defects, not accepted behavior. The 3 frontend state tests and TypeScript/Vite production build passed. Repository-wide Ruff, documentation links and `git diff --check` passed. Existing PDF/HTTP deprecation warnings remain. The five new passing stress guards cover queue backpressure, cumulative model reservations/continuation, expired deadlines, login/logout and missing-ledger fail-closed behavior. None of these results override the failed release verdict.

See [the prioritized findings](validation-findings.md). Seven strict expected-failure regressions preserve correctness/availability defects; scaling is an additional measured gate failure. Expected failures are **not passes**. Normal tests can remain green while the release verdict is failed.

Application changes were deliberately not mixed into this testing request. Fixes require a subsequent implementation step followed by revalidation of the same failing cases and new held-out quality evidence. Browser reconnection again returned `No browser is available` and discovery `[]`; visual, keyboard, responsive and actual two-browser acceptance remain unrun. Windows/Cloudflare and independent quality evaluation also remain unrun.

## Reproduction and artifacts

```sh
.venv/bin/python scripts/capture_relaydesk_corpus.py --output <new-corpus-path>
.venv/bin/python scripts/validate_relaydesk_aggressive.py --corpus <frozen-corpus> --output <new-run-path> --live-jobs 6
.venv/bin/python scripts/validate_relaydesk_http_stress.py --output <new-http-report.json>
.venv/bin/python scripts/benchmark_relaydesk_scope.py --corpus <frozen-corpus> --output <new-scale-path>
.venv/bin/python scripts/validate_relaydesk_worker_recovery.py --output <new-recovery-path>
.venv/bin/python -m pytest tests/test_relaydesk_aggressive_regressions.py -rx -q
```

All output paths must be new; read-only corpus acquisition consumes quota, and `--live-jobs` explicitly uses installed Codex service usage. Frozen artifacts are:

- `var/validation/relaydesk-aggressive-corpus-v1/` and `relaydesk-aggressive-long-v1/`: raw hashes, source batches, selection, gaps and counts.
- `relaydesk-aggressive-evaluation-v1/` and `relaydesk-aggressive-long-evaluation-v1/`: isolated stores, queries, baseline IDs, check failures, live events and output IDs.
- `relaydesk-aggressive-continuity-v1/`: live sessions, injected source and fabricated-provider diagnostic.
- `relaydesk-aggressive-http-v1.json`, `relaydesk-aggressive-scale-v1/`, `relaydesk-aggressive-recovery-v1/`: HTTP timings, capacity metrics, worker logs and recovery checks.
- `relaydesk-aggressive-audit-v1.json`: aggregate distinct-data accounting, runtime versions, product-code hashes and failed release verdict.

Raw messages and generated artifacts remain sensitive/rights-governed local data, not committed public datasets. No credential values are printed or saved in reports.
