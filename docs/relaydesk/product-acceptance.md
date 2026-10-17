# Full product acceptance — rejected / incomplete

Latest assessment: **17 October 2026, corrective build v3**. Six gates passed, one failed, five blocked; `full_acceptance_completed=false`. Engineering defects were fixed under the user's explicit approval, but unavailable or incomplete release evidence is not converted into a pass.

## Reproduce the assessment

```sh
make relaydesk-acceptance ACCEPTANCE_OUTPUT=var/validation/relaydesk-acceptance-UNIQUE
# Explicit audit selection, if required:
make relaydesk-acceptance ACCEPTANCE_OUTPUT=var/validation/relaydesk-acceptance-ANOTHER-UNIQUE ACCEPTANCE_AUDIT=var/validation/relaydesk-corrective-audit-v3.json
```

Output must be new. The default audit is corrective-v3. The runner validates product/model hashes, frozen input manifests/batches, run/auxiliary report hashes and the pre-run code-freeze manifest; executes Python tests with `--runxfail`; builds/tests the frontend; then assesses all mandatory gates. Nonzero exit is intentional until every gate passes. Historical files must not be overwritten.

Latest report: `var/validation/relaydesk-full-acceptance-v3/report.json`, UTC start `2026-10-17T10:03:33.938996+00:00`, finish `2026-10-17T10:04:11.025388+00:00`. It reuses the freshly frozen live-run evidence rather than counting assessment as eleven additional provider calls.

## Gate matrix

| Gate | v3 result | Evidence / remaining requirement |
| --- | --- | --- |
| G01 product/model currentness | Passed | Pre-run product hashes unchanged; model namespace and referenced report hashes match |
| G02 frozen-input integrity | Passed | Captured source, batch and manifest hashes verified |
| G03 full real cohort | Failed | 89 threads, 22 repos, 6,680 non-bot messages, one >100-message thread; need 200 screened substantive threads and ten long histories |
| G04 unmasked tests | Passed | 283 Python tests, zero failures/skips |
| G05 frontend build/state | Passed | Three state tests and TypeScript/Vite build; not browser acceptance |
| G06 independent quality/held-out | Blocked | Need actual two-human-reviewer 300-question adjudicated set, 150/60/90 repository split, critical-fact/support/abstention measurements |
| G07 live grounding/continuity | Blocked | Eleven live AI-stage completions/78 exact source-resolving quotations; independent natural-answer relevance/quality review still absent |
| G08 privacy/integrity/currentness | Passed | Corrective frozen replays reject wrong ledger, source corruption and stale publication; not a penetration-test certificate |
| G09 bounded capacity/context | Passed | 1k/5k/10k replica probes below provisional 500 ms; summaries under 6,000 chars; not actual-Windows acceptance |
| G10 browser UI | Blocked | Connection unavailable; no keyboard/responsive/accessibility/two-browser acceptance |
| G11 Windows/edge/operations | Blocked | Actual old Windows identity/reboot/Codex, protected Cloudflare, disk/ACL/process cleanup and five-product resource drills unavailable here |
| G12 usefulness | Blocked | Need separately consenting customer paired tasks, reviewer-accepted facts and effort evidence; no external outreach performed |

[Corrective report](corrective-validation-2026-10-17.md) distinguishes engineering provenance from semantic correctness. Quotations can still be irrelevant, incomplete or wrong in their source context. Human review and the larger blind evaluation remain essential.

## Data quality and acquisition

The expanded public capture used 42 bounded core GETs after quota reset; no credentials were discovered or gated agreements accepted. Deduplicated aggregate: 6,857 source records, 6,680 non-bot/177 bot, 6,578 distinct non-bot body hashes, 102 repeated bodies, 84 complete/five partial threads. There are 87 threads with at least 20 non-bot records and one bot-only negative control. Discovery includes feature/branding material; these are not 89 independently screened substantive customer incidents.

Original/expanded corpus overlap is deduplicated, not summed. Reacquired complete variants replace earlier partial variants in aggregate counts; all variants and manifests are retained. Capacity replicas contribute zero new real histories. The 5,000-message threshold alone does not pass G03.

No browser was available after selection and read-only recovery discovery (`[]`). This host is macOS. Another model run cannot provide independent human review or actual Windows evidence. The gated BigCode alternative was not accessed and no terms/contact-information consent was accepted.

## Historical comparison

Original aggressive v1 found eight triaged issues and seven strict regression failures. Acceptance-v2 recorded 269 Python passes/seven failures, three passed gates/five failed/four blocked. Those reports remain intact.

Corrective-v3 fixes the reproduced engineering boundaries, removes expected-failure markers, improves live-stage completion and meets bounded local latency/context observations. It does not relabel regression examples as a blind held-out benchmark. Intermediate corrective-v2 also had two live-stage failures; the later 11/11 sample is not an availability guarantee.

## Next required work

Expand and screen the cohort under source quotas; obtain the independent human-reviewed split; evaluate natural-answer quality and critical omissions; connect a browser for actual UI acceptance; run target Windows/protected-edge/operational drills; and conduct an authorized consenting-customer usefulness study. Then rerun the same gate runner against current verified evidence.

**The product is not fully accepted. Full acceptance testing has not completed.**
