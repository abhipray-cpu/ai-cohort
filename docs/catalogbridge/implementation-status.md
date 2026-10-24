# Implementation status

**Latest, 18 October:** [local-routing implementation and stopped validation](local-routing-validation-2026-10-18.md). A local JSON-tree scorer can make opt-in, source-validated review drafts without inference; default LLM routing and automatic-acceptance restrictions remain unchanged. API/UI expose profile availability and bind its hash. 476 Python tests, eight frontend tests/build pass. Offline 600-pair challenge: 101 local drafts, one disagreement. The 123-dispatch live campaign stopped on quota, leaving three new unknown liabilities and no eligible savings comparison. A separate cross-source research candidate failed qualification and produced no profile. [Study guide](study-guide.md) is complete as learning material, not release certification.

**Latest amendment, 18 October:** [receipts and repeat work](receipts-and-repeat-work-2026-10-18.md). Timeout accounting and ambiguous-turn guards are fixed; sanitized receipts persist with settlement. Opt-in 24-hour exact-context draft reuse is implemented in worker/store and UI, never promoting acceptance. 455 Python tests, eight web tests/build; 400-query HTTP/stress replay and three live calls/20,355 tokens/zero unknown usage. Two eligible repeats reuse drafts after restart with zero new inference; an uncertain third is not cached. Fresh-row routing savings and the unchanged release blockers below remain open.

**Current implementation and validation, 18 October:** [runtime hardening report](runtime-hardening-2026-10-18.md). Cross-batch workspace hold, campaign-wide stop, safe provider evidence, visible UI hold, owner retry authorization that cannot erase liabilities, explicit compact profile and unverified-calibration rejection are implemented. 432 Python tests, eight web tests/build, wheel asset check. A clean 60-pair run gives 56/60 router benchmark agreements; all 240 new paid dispatches across phases have known usage. The original 61 unknown liabilities remain unchanged. The original routing-token target, qualified empirical confidence/effective identity and full external acceptance still block release. No thresholds were lowered.

## Historical handoff summaries

The dated paragraphs below preserve earlier measurements. Statements about fixes still pending in those historical runs do not override the current report above.

**Latest validation, 18 October:** [fresh real-world results](fresh-real-data-validation-2026-10-18.md). Sixty new pairs and 400 new query IDs; fresh HTTP retrieval 98%, ten paid HTTP queries and workflow/stress/recovery pass. The original paired comparison is ineligible for savings because 61 attempts lack usage/audit confirmation. A separately preserved 12-case replay has complete usage, 12/12 router benchmark agreement and 7.02% token reduction, still below 20%. Original liabilities remain held. Regression: 416 Python tests, seven web tests/build. Product runtime is unchanged from the repairs below. Release remains blocked; error diagnostics/campaign failure-stop handling now also need implementation work.

Latest implementation: [repairs and targeted validation](fixes-and-targeted-validation-2026-10-17.md). Policy/prompt/retrieval v2 correct normalization, single-candidate assessment, uncertainty escalation, unnecessary paid escalation on decisive drafts, preflight accounting and partial-draft retention. The original [failed real-data evidence](real-data-validation-2026-10-17.md) is preserved separately. Fresh regression: 413 Python tests, seven web tests/build and Ruff. Full release remains blocked; draft completion is not validated confidence acceptance.

As of 17 October 2026: **implemented supervised pilot; full design/release acceptance incomplete**. Start with [actual runbook/deviations](implementation-and-operations.md). The table below is current status; older implementation and diagnostic reports retain their original measurements.

Current real-data workflow evidence: 1,000 queries against 2,841 master records, 789/800 positive retrieval hits (98.625%), 400 automated review fixtures, 40 stale revisions, 600 concurrent reads during 100 writes, five scope denials and quarantined recovery. Three fresh HTTP model calls settle 32,108 tokens with no unknown usage. These are not 1,000 AI answers or actual independent human reviews. Both requested model names return answers; effective identity and qualified calibration remain absent. Strict-token mode is refused. No real credentials or `.env` changed.

Commands now available: `make catalogbridge-up/down/status/test/validate/acceptance` (explicit product credentials). Acceptance intentionally exits nonzero. Study/blog remain scheduled after real-data validation. Full design gaps are recorded in the runbook; this is not a claim every proposed interface exists.

| Area | Current evidence |
| --- | --- |
| Product/research/architecture | Specifications written; C4 levels 1–4 and deployment/state/sequence included |
| Public data | Acquired official WDC archives, hashes and schema/split audit; commercial rights not cleared |
| CatalogBridge API/worker/web | Implemented supervised workflow; HTTP and frontend checks pass |
| Shared model adapter | Typed actual usage and audited tools; effective identity absent |
| Two-model routing/calibration | Requested-model routing implemented/tested; no qualified real calibration |
| Strict token enforcement | Unsupported, fail-closed; advisory reserves may overrun |
| Cost/savings analytics | Reconciled measured tokens and reference rates; no demonstrated billed/business savings |
| Auth/security/backup/restore | Role/scope/revision checks, independent liabilities and quarantined recovery tested |
| Unit/HTTP/browser/real-data tests | Engineering and named real-data checks pass; browser acceptance unperformed |
| Windows/Cloudflare/customer acceptance | Not performed |
| Study guide / single blog | Intentionally scheduled after implementation and validation |

Use documented Make targets; a historical design milestone is not current status. No passing workflow test substitutes for the full live campaign, independently qualified confidence, Windows/edge or buyer acceptance. Earlier product business logic and data remain unchanged.

## Implementation entry checklist

- Check linked document completeness and scope/threshold consistency.
- Establish failing tests before each behavior; preserve red/green evidence.
- Verify additive adapter capabilities without breaking earlier products.
- Implement supported behavior even where external acceptance remains blocked; label unsupported hard-budget mode honestly.
- Track implemented, fixture-tested, real-provider-tested and production-accepted separately.
- Complete actual-data validation before writing results-based study/blog content; preserve failures and precise blockers.
