# RelayDesk corrective validation — 17 October 2026

Disposition: **corrective engineering validation passed; full product acceptance remains rejected/incomplete**. The final gate assessment has six passed gates, one failed gate and five blocked gates. This is not a production launch or independent answer-quality certification.

## Build and evidence discipline

After the user authorized fixing the earlier findings, failing regressions drove the corrective work. The final campaign froze product API/UI/contract hashes at `2026-10-17T09:56:27.489550+00:00` and verified them unchanged at aggregation and acceptance. Model namespace matched. UTC times in artifacts differ from local Asia/Kolkata dates/times; this report is dated locally 17 October.

Original failed `relaydesk-aggressive-*-v1` and acceptance-v1/v2 artifacts remain intact. Corrective-v2 is an intermediate build/result, not final evidence. Final paths use corrective-v3, expanded-v3 and acceptance-v3. Script/report and product/model hashes bind results to actual files. Captures and generated validation stores are ignored local artifacts, not committed distributable source datasets.

Final audit: `var/validation/relaydesk-corrective-audit-v3.json`. Final acceptance: `var/validation/relaydesk-full-acceptance-v3/report.json`, finished `2026-10-17T10:04:11.025388+00:00`.

## Actual real data, without inflated counts

The public GitHub quota reset; a bounded acquisition used 42 core requests, explicit allowance 54, plus separately limited discovery calls. It reused hash-verified captures and added public issue histories. No token was discovered, gated terms accepted, or source command executed.

Deduplicated across original, long and expanded captures:

| Measure | Observed |
| --- | ---: |
| Distinct repository/issue threads | 89 |
| Repositories | 22 |
| Source messages | 6,857 |
| Attributed non-bot messages | 6,680 |
| Bot messages | 177 |
| Distinct non-bot body hashes | 6,578 |
| Repeated non-bot bodies | 102 |
| Complete / partial thread captures | 84 / 5 |
| Threads with at least 20 non-bot messages | 87 |
| Bot-only negative-control threads | 1 |
| Threads over 100 non-bot messages | 1 |

For repeated repository/issue captures, the audit selects a complete capture over a partial one, then the more populated capture, then the later supplied corpus. Source identities are counted once. Old partial variants remain retained; counts are not summed across overlapping runs. Complete means connector-declared capture coverage, not independently screened technical quality. Discovery includes feature/branding threads and negative controls; do not call all 89 substantive customer incidents.

The 5,000-message and 20-repository numerical targets are met; the 200-screened-thread and ten-long-history targets are not. Human screening and independent questions remain missing.

## Automated tests and real-data invariants

Final unmasked acceptance run: **283 Python tests passed, zero failed/skipped**, 34.83 seconds. Three frontend state tests and TypeScript/Vite production build passed. Repository-wide Ruff checks passed. Seven original defect regressions are ordinary passing tests; no `xfail` masks them. Seven additional corrective tests cover narrative isolation, original CRLF spans, bounded prior-turn projection, legacy enrollment, missing tombstones, ledger replacement and corrupt-source publication.

| Frozen real-data replay | Threads | Invariant assertions | Retrieval queries | Failed assertions |
| --- | ---: | ---: | ---: | ---: |
| Original corpus replay | 48 | 1,012 | 431 | 0 |
| Complete long TypeScript history | 1 | 31 | 10 | 0 |
| Expanded capture replay | 88 | 1,878 | 817 | 0 |

These total 2,921 assertion executions and 1,258 query executions, **not independent unique examples**: the expanded corpus overlaps the original. Each run uses a new isolated store. Checks include import replay, source spans, authorization, temporal/state behavior, index/deletion races, corruption rejection and wrong-ledger recovery. The deliberate corruption is restored before the independent backup drill; otherwise one injected fixture would contaminate another check.

Extractive source-derived probes, hit@10 numerators:

| Run | Probes | Hybrid | Lexical | Vector-only |
| --- | ---: | ---: | ---: | ---: |
| Original | 239 | 238 | 239 | 206 |
| Long | 6 | 6 | 6 | 5 |
| Expanded | 465 | 463 | 464 | 408 |

Copied/extractive probes favor lexical matching. These are engineering diagnostics, not an independently labelled natural-question accuracy benchmark or proof hybrid outperforms lexical. Recall p50/p95 in expanded replay was 18.64/24.05 ms on macOS.

## Live Codex and conversation behavior

The final run used the installed isolated Codex adapter, not the fake provider, for eleven jobs:

- Six original natural-thread handovers: axios #318/#2130, VS Code #981/#16488, TypeScript #449/#14600.
- One complete 137-non-bot-message TypeScript #26242 handover.
- Elasticsearch initial question, same-session follow-up, fresh-session follow-up, and one separately labelled poisoned-source job.

**11/11 completed the AI stage**, each using two calls, each retaining `partial` product status. All published `answer_state=quoted_evidence`, not empty-claim abstentions. Across them, 78 factual quotations resolve to original source/hash/revision/character spans with zero mismatches. Seven corpus jobs had zero turn-source recall hits. Earlier user reports can legitimately appear in continuity recall; the active question must not support itself.

The controlled instruction marker was absent from the published answer and proposed questions. Provider tool audits remained required. This is one adversarial mutation, not proof against every injection.

A separately labelled fake-provider fabrication of universal recovery was rejected after its bounded repair allowance. It is an injected boundary check, not a natural hallucination-rate observation. Earlier live v1 had 5/10 AI-stage completions; final v3 adds a same-session check and changes prompts/publication policy. Intermediate v2 still had two failed jobs; final 11/11 is not an uptime guarantee or an independent experiment.

The factual boundary is now deliberately extractive: one supplied memory and an exact original quotation per claim, explicit attribution, server-neutral summary. Free model narrative is not published as verified fact. This prevents unsupported paraphrase from passing merely because a citation ID exists. It does **not** prove relevance, completeness, truth, environment applicability or semantic quality. Independent quality review remains blocked.

## Capacity and bounded context

Labelled replicas of real payloads; no additional unique real histories. Same pinned model, macOS ARM64, two probes per size—not cold-start distributions or Windows SLO acceptance.

| Memories | Vector chunks | Recall probes, ms | Serialized compression, characters |
| --- | ---: | --- | ---: |
| 1,000 | 1,230 | 43.35 / 38.77 | 5,884 |
| 5,000 | 6,391 | 149.68 / 136.77 | 5,888 |
| 10,000 | 12,845 | 217.84 / 216.22 | 5,926 |

All six probes were below the provisional 500-ms target; all summaries fit their 6,000-character budget with full omission counts. Previous 10k recall was 5.7–7.2 seconds and serialized compression 366,025 characters. Batched authorized access and bounded omission metadata account for the corrective design; this is not an isolated causal or hardware-normalized benchmark. SQLite integrity checks passed; database size is not process RSS. No live 10k complete answer-quality test is claimed.

## Service, recovery and migration

The managed RelayDesk store was explicitly enrolled with a quarantined pre-binding snapshot; prior sessions expired and drafts were staled. No password reset or user-data deletion was performed. Only RelayDesk was stopped/restarted. API and worker report running at `http://127.0.0.1:8004/`.

- 19 authenticated HTTP journey checks passed, including two sessions, CSRF/origin, fresh-session recall, revision conflict, reviewed export and stale-export rejection.
- 20 HTTP stress/negative checks passed; 160 reads, concurrency eight, p50 32.66 ms/p95 47.77 ms including fresh-client setup.
- Five isolated recovery checks passed: real process killed after two indexed chunks, restart completed 404 chunks, original deadline/usage preserved, no duplicate committed turns. Lease expiry was explicitly injected, not falsely described as a natural wall-clock wait.
- Schema-2 backup restore rejects the unrelated ledger; correct current-ledger restoration reapplies erasures. A stale clone of the same bound ledger still needs operational freshness protection.

Browser testing followed the browser skill; connection selection failed and read-only discovery returned `[]`. Visual/two-browser/keyboard/responsive/accessibility checks remain unrun. The host is macOS, not Windows. [Runbook and migration caveats](implementation-and-operations.md).

## Retained final evidence

Under `var/validation/`:

- `relaydesk-corrective-freeze-v3.json`, `relaydesk-corrective-audit-v3.json`.
- `relaydesk-corrective-evaluation-v3/report.json`, `relaydesk-corrective-long-evaluation-v3/report.json`.
- `relaydesk-expanded-corpus-v3/` with raw manifests/batches; `relaydesk-expanded-evaluation-v3/report.json`.
- `relaydesk-corrective-continuity-v3/report.json`, `relaydesk-corrective-published-quotes-v3.json`.
- `relaydesk-corrective-scale-v3/report.json`, `relaydesk-corrective-recovery-v3/report.json`.
- `relaydesk-corrective-http-journey-v3.json`, `relaydesk-corrective-http-v3.json`.
- `relaydesk-full-acceptance-v3/`: gate JSON, unmasked JUnit, Python/frontend logs.

## What still prevents full acceptance

The gate runner intentionally exits nonzero: G03 fails full cohort coverage; G06/G07 lack independent answer-quality sign-off; G10 lacks browser access; G11 lacks actual Windows/protected-edge/operational acceptance; G12 lacks consenting-customer usefulness evidence. It does not turn public source availability or a passing suite into paid-product proof.

[Study guide](study-guide.md) correlates the concepts with code/tests. [Product blog](blog.md) and [corrective engineering blog](blog-corrective-validation.md) are drafts grounded in these results.
