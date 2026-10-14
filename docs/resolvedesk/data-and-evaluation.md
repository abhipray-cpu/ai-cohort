# Real data and end-to-end evaluation

This is the wider collection and evaluation plan. Sixteen official documentation pages have been acquired and checksum-frozen. The expanded adapted functional matrix passed 11 scenarios / 12 turns, including live search on empty and weak local evidence. No independent human gold set or 60-case quality benchmark exists. See [current validation](validation-2026-10-14.md).

## Separate knowledge, questions, and labels

The knowledge corpus contains approved versioned manual sections and runbooks. Evaluation questions come from real public support cases and reproduced errors. Expected answers are independently reviewed labels grounded in official sources and, where useful, actual reproduction. Do not index benchmark questions, accepted community answers, model outputs, or gold labels into the knowledge collection being evaluated.

The implemented acquisition cache is `data/resolvedesk/raw` (ignored HTML), with provenance in `manifests`. Normalized application source snapshots/passages are in SQLite. Future independent labels belong in `gold` and fault datasets in `adversarial`. Keep private pilot cases out of the public repository.

## Actual-data acquisition

1. Acquire selected PostgreSQL 16/17 HTML sections for `pg_dump`, `pg_restore`, `pg_dumpall`, `pg_upgrade`, connection parameters, authentication, and backup/upgrade behavior. Seed URLs and actual public-question candidates are in [research and sources](research-and-sources.md).
2. Record canonical URL, version, section anchor, capture time, SHA-256, parser version, reuse/license status, and required notices. Validate HTTP result, content type, expected headings, and declared product version before marking a source ready.
3. Select public questions by distinct issue family. Preserve original versions, symptoms, missing details, and source attribution. Do not pretend historical questions are current customer cases. Adapted examples get a new ID and explicit parent.
4. Reproduce selected errors in isolated PostgreSQL instances with generated non-sensitive data. Capture exact commands/tool versions, observed output, expected effect, and cleanup instructions. This lab can run on a suitable development host; the product's Windows service does not need a production database or Docker installed merely to answer questions.
5. Use original public messages as links/metadata until reuse rights are resolved. Community answers are investigative leads, not gold. Review each case against version-correct official documentation.

## Initial 60-case target

Classify every case along two axes: origin (`public/reproduced/adapted`) and expected outcome. Seek at least 20 distinct public issue families, supplement with reproducible lab cases, and label deliberate variants separately. Do not fill a shortfall silently with generated questions.

| Expected outcome | Target | Purpose |
| --- | ---: | --- |
| Answerable from saved knowledge | 20 | Retrieval and directly supported answers |
| Requires multiple passages | 10 | Coverage and combining conditions |
| Version-sensitive | 10 | Client/server distinctions and wrong-version traps |
| Requires official-source search | 10 | Relevant page intentionally absent from local index |
| Ambiguous or unanswerable | 10 | Clarification, abstention, and escalation |

Families can involve backup/restore, connection/authentication, or upgrade behavior. Avoid claiming reliability beyond these supported categories. Private customer tickets are a later pilot source, requiring consent and appropriate access; none are currently available.

## Gold protocol and splits

Two reviewers independently record expected behavior, required material claims, accepted citation passages, applicable versions, necessary clarification, and forbidden assertions. A reviewer adjudicates disagreements and records rationale. If only one reviewer is available, call the labels provisional and keep the stronger quality sign-off open. Model-generated answers may assist review but never become independent gold automatically.

Suggested initial split: 40 development cases and 20 held-out test cases, stratified by expected outcome. Keep the same issue family, historical/adapted variants, and paraphrases together to prevent leakage. Freeze prompts, source/index revisions, thresholds, and search budget before the held-out run. Test cases can share public documentation with development cases; their question families and labels must not leak.

For search cases, keep the required page absent from the local evaluation index and record its authoritative URL in restricted labels. The agent discovers it through live search. Replayed search fixtures measure reproducibility; live runs measure actual integration. Report both separately because search results change.

## Proposed pilot gates

These are targets subject to an initial feasibility baseline; none has been met.

| Metric | Definition | Proposed gate |
| --- | --- | --- |
| Retrieval Recall@5 | Required passages found in top five / labelled required passages on local-answerable cases | At least 90%; publish raw counts and multi-passage breakdown |
| Version leakage | Claims wrongly applied across product/client/server versions | Zero critical errors on held-out cases |
| Structural citation validity | Cited passage exists in supplied snapshot and quote matches | 100% of material claims presented with accepted citations |
| Citation support | Human-reviewed claims actually supported by cited passage | At least 95%; zero unsupported critical instructions |
| Answer correctness/completeness | Held-out answerable cases satisfying adjudicated expectations | At least 90%; show omitted and incorrect claims separately |
| Appropriate abstention | Ambiguous/unanswerable cases asking for clarification or escalating | All held-out critical cases; publish exact denominator |
| Over-abstention | Answerable cases unnecessarily withheld | Report separately; proposed maximum 20% |
| Search recovery | Fallback cases with needed fetched evidence and a correctly qualified answer | At least 80%; small denominators reported explicitly |
| Reviewer usability | Evidence inspection, correction, approval, and escalation tasks completed | At least 4/5 participants per task; no hidden conflict approved |
| Reviewer effort | Median time to correct approved reply versus manual task baseline | Proposed 25% reduction; require observed pilot sessions |
| Latency/resource use | p50/p95 by local-answer/search case, RAM/CPU and index size | Measure before promising an SLA; initial usability target p95 under 180 seconds on target host |

Citation-support and uncertainty scoring require humans; a second model's approval is not independent proof. Never summarize all metrics as one accuracy percentage. With 20 held-out cases, report counts and uncertainty rather than imply broad population reliability. Expand the set before commercial quality claims.

## End-to-end scenarios

| ID | Input | Expected result |
| --- | --- | --- |
| E2E-01 | Actual backup mismatch with known client/server versions | Retrieve correct versioned rule; cited qualified reply |
| E2E-02 | Same symptom with unknown utility version | Ask for missing version; no unconditional diagnosis |
| E2E-03 | Restore format error | Separate dump/restore utility versions from server version; evidence or clarification |
| E2E-04 | Locally omitted official manual section | Live search, fetched snapshot, new evidence used and labelled |
| E2E-05 | Empty search / provider outage | Preserve available evidence; clear retry/escalation state |
| E2E-06 | Correct quote but unsupported interpretation | Support assessment flags it; cannot silently pass as a resolved answer |
| E2E-07 | Conflicting runbook and versioned official guidance | Show scope/conflict; no arbitrary winner |
| E2E-08 | Private runbook with customer identifiers | No private query leakage or unauthorized export citation |
| E2E-09 | Reviewed reply followed by regenerate/reload | Preserve approved revision; create separate draft |
| E2E-10 | Restart after fetched-evidence checkpoint | Resume bounded remaining work; no lost review or duplicate approval |
| E2E-11 | Forged passage ID or malformed retrieval result | Reject and log stage before exposing a cited answer |
| E2E-12 | Source refresh between retrieval and review | Original citations still resolve to pinned snapshot |
| E2E-13 | Desktop/narrow browser with long error text | Readable reply and evidence; keyboard-accessible controls |
| E2E-14 | Remote user without authorization | No case, internal source, or export access |

## Evidence artifacts

### Expanded conversational acceptance

The reproducible adapted scenarios are now in [chat-acceptance.json](../../data/resolvedesk/manifests/chat-acceptance.json). They cover backup and a version-specific follow-up, custom restore, SSL host verification, upgrade checking, a general question without environment, private-policy abstention, ambiguity, unsupported historical versions, empty-index live search, weak-local-evidence live search, and an explicitly injected search outage. These are provisional functional expectations, not independent human gold or customer incidents.

```sh
make resolvedesk-test
make resolvedesk-validate-live
```

The second command invokes actual installed Codex and remote PostgreSQL search, with at most two independent evaluation cases concurrently. Every case has its own fresh SQLite store; active product data is not reset. Sixteen source checksums are verified before execution. Each source page has an expected-page-in-bounded-context check; this is coverage, not labelled passage Recall@5. Live fallback starts with either an empty index or the relevant detail page deliberately absent. Search snippets cannot pass as evidence, and fetched pages must not be auto-published into the index.

The runner validates claim/quote/version provenance, required manual pages/rules, visible uncertainty, thread persistence, historical-answer preservation, and duplicate-message idempotency. Reports retain resolutions, answers, events, snapshot hashes and failures under ignored `var/resolvedesk-acceptance/<timestamp>/`. Nonzero exit means an expectation failed. Reruns create new directories; do not discard earlier failures. See [validation evidence](validation-2026-10-13.md) for measured outcomes and limits.

Every evaluation should save corpus/case manifest hashes, source/index/prompt/schema/parser versions, split and label revision, CLI/model metadata when available, search adapter and query/fetch outcomes, run IDs, budgets, timings, hardware/OS, human scores, and failure categories. Preserve failed runs. Store sensitive raw output separately with access control. Frozen reports are immutable; a rerun creates a new report and links its parent.

Reproduction commands now exist:

```bash
.venv/bin/python scripts/fetch_resolvedesk_sources.py --data-dir var/resolvedesk-evaluation
.venv/bin/python scripts/benchmark_resolvedesk.py
.venv/bin/python scripts/benchmark_resolvedesk.py --live
.venv/bin/python scripts/benchmark_resolvedesk.py --case missing-client-version --live
```

The default benchmark is retrieval-only. `--live` invokes Codex and remote search when needed; service usage/authentication apply. Reports are uniquely named under ignored `var/resolvedesk-evaluation/reports`. The four starter cases are provisional smoke inputs, not a substitute for the 60-case adjudicated benchmark. Choose a fresh isolated data directory to exercise real fallback with an empty local index.
