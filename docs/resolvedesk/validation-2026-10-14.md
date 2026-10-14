# Real-data validation — 14 October 2026

This is functional validation on macOS using actual PostgreSQL documentation, installed Codex and official-site search. It is not a production certificate, a reproduced database incident, or an independent answer-quality benchmark. Earlier observations remain in [13 October validation](validation-2026-10-13.md).

## Final outcome

The final complete matrix passed **11/11 scenarios and 12/12 turns**, with **16/16 source-page retrieval checks**. Its 23 generated claims contained 31 citation references; all passed structural passage/quote/version checks. Report: `var/resolvedesk-acceptance/20261014T061630821832/report.json`. There were no expectation failures in that run. This closes the scoped actual-document functional validation, not the open production gates below.

| Scenario                                    | Result                                                         |   Time per turn | Claims |
| ------------------------------------------- | -------------------------------------------------------------- | --------------: | -----: |
| Backup compatibility + version-16 follow-up | Supported draft on both turns; first answer preserved          | 37.94 / 37.05 s |  3 / 4 |
| Custom archive restore                      | Supported, version-17 manual citations                         |         31.93 s |      3 |
| Connection SSL host verification            | Supported, version-17 manual citations                         |         33.49 s |      3 |
| `pg_upgrade --check`                        | Supported, version-17 manual citations                         |         29.23 s |      2 |
| General question, no environment form       | Supported cited answer                                         |         33.73 s |      4 |
| Private recovery promise                    | Clarification, insufficient evidence, no invented promise      |          9.57 s |      0 |
| Ambiguous first message                     | Clarification, insufficient evidence                           |          8.15 s |      0 |
| Historical unsupported versions             | Escalation, insufficient evidence                              |          7.66 s |      0 |
| Empty-index live search                     | Fetched official evidence cited; index remains empty           |         38.92 s |      2 |
| Weak-local-evidence live search             | Missing detail page fetched and cited after initial assessment |         48.68 s |      2 |
| Injected search outage                      | Escalation with explicit insufficient-evidence reason          |          6.61 s |      0 |

These timings exclude a production queue/load experiment. The suite runs at most two isolated cases concurrently; it does not change the product's serial-worker design.

## Data and test boundaries

- Knowledge: 16 SHA-256-frozen official HTML pages, eight topics each for PostgreSQL 16 and 17. All source hashes are checked before evaluation. See [sources.json](../../data/resolvedesk/manifests/sources.json).
- Questions: 11 adapted/provisional scenarios, including a two-turn thread, in [chat-acceptance.json](../../data/resolvedesk/manifests/chat-acceptance.json). These are not 11 customer incidents or human-adjudicated gold cases.
- Generation: actual installed Codex adapter for every live case; no fake model responses in the live matrix.
- Search: actual remote official PostgreSQL site search and fetched HTML for recovery cases. The outage case deliberately injects a search exception and is labelled as fault injection.
- Isolation: each scenario gets a new SQLite store. Indexed scenarios use the frozen corpus; empty-index scenarios begin at revision zero. The active application's knowledge and conversations are not reset.
- Deterministic checks: 89 monorepo Python tests, including 52 ResolveDesk tests; five frontend presentation tests. Production UI build and Ruff pass.

## Four-concept acceptance criteria

| Concept                       | Required observable evidence                                                                                                                                                                                             |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Retrieve context              | Correct versioned pages reach bounded context; each chat turn resolves context and retrieves anew. Sixteen expected-page retrieval checks cover all frozen sources.                                                      |
| Generate answers with sources | Every material claim has a supplied passage ID and matching quote; stored identity, index/search scope and citation-version applicability validate. Required rules/pages are checked for selected scenarios.             |
| Flag low confidence           | Ambiguous questions request clarification; private contractual promises and out-of-scope versions do not become supported answers. Search failure retains insufficient evidence with a visible reason.                   |
| Fallback to search            | Empty local context and weak nonempty local context trigger real official-source search, page fetching, ranking, answer generation and assessment. A discovered missing page must actually be cited, not merely fetched. |

The chat welcome disclosure names all four concepts. Per-answer provenance distinguishes retained indexed passages from search and shows unused, fetched, empty, unavailable and failed fallback states. Presentation tests prevent failed/empty search or incomplete answers from being labelled as successful/support-complete. These tests do not establish browser usability.

## Defects found and corrected

### Multi-utility retrieval

A question naming both `pg_dump` and `pg_restore` retrieved only the first utility's manual. The original answer was supported by the dump manual, but the context omitted useful restore-specific evidence. A failing real-corpus test reproduced this. Retrieval now gives all named utility pages equal preference before BM25 ranking. Both manuals reach context and the live restore case passes.

### Search query specificity and early stopping

The weak-evidence case asks whether authentication failure on a matching `pg_hba.conf` record causes the server to try later records. The authentication overview is locally indexed, but the detailed matching-rule page is deliberately absent.

Initial fallback safely abstained rather than inventing the rule. Investigation found three interacting issues:

1. The fixed public-term vocabulary omitted `pg_hba`, reducing the query to broad authentication terms.
2. The adapter accepted the first nonempty official search results even if they were unrelated release notes.
3. The site's search distinguishes the stem `pg_hba` from the full filename `pg_hba.conf`. Actual query comparisons showed the filename discovers the reference page while the stem could return only release notes.

The adapter now preserves the approved topic, uses its fixed canonical public filename spelling, tries the bounded second topic query when the expected reference page is missing, and ranks discovered reference pages first. No user-supplied hostname or free-form filename is added to the public-query vocabulary. Secret/private-domain exclusion tests remain required.

The focused real-model retest passed in 58.62 seconds: local retrieval returned five passages, initial generation/assessment found insufficient support, live search fetched the missing page, and regeneration plus assessment produced a supported cited draft in five model calls. Report: `var/resolvedesk-acceptance/20261014T061507402320/report.json`.

### Evaluation expectation correction

One early empty-index test incorrectly required only version-17 citations for a client-16/server-17 compatibility question. The version-16 client manual validly states the rule governing that client. The accepted scope was corrected to 16/17 with claim-version validation retained. A regression proves accepted client-version evidence is allowed and genuinely wrong version scope still fails. This was a label correction, not an unsupported answer being relabelled correct.

## Retained evidence and failed attempts

Reports use UTC timestamps; this document's date follows the user's Asia/Kolkata date.

| Report directory below `var/resolvedesk-acceptance/` | Observation                                                                                                          |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `20261013T181437443684`                              | Initial 10-scenario run: 8 passed; restore context coverage and overly narrow citation-version expectation surfaced. |
| `20261013T181918093004`                              | Expanded 11-scenario run: 10 passed; weak-evidence search abstained without the required missing-page citation.      |
| `20261013T182423390953`                              | Focused vocabulary fix alone: did not recover; retained failure.                                                     |
| `20261013T182625895130`                              | Full rerun: 10/11; weak-search recovery still failed.                                                                |
| `20261013T182933278535`                              | Early-stop fix alone: still failed because the filename spelling remained incomplete.                                |
| `20261014T061507402320`                              | Full-filename fix: focused weak-search retest passed.                                                                |
| `20261014T061630821832`                              | Final full matrix: 11/11 scenarios, 12 turns and 16/16 source-page checks passed.                                    |

No failed run is discarded or counted as a pass. Each report retains inputs, contextual resolutions, answer/evidence, stage events, timings, source hashes and expectation failures.

## Running-system and recovery checks

- Actual HTTP two-turn chat passed after the multi-utility fix: 88.5 seconds and 90.5 seconds, with three and two claims respectively. It checked duplicate-send idempotency, citation membership, version-16 follow-up scope and preservation of the first answer. Report: `var/resolvedesk-evaluation/reports/20261013T182256-chat.json`.
- After loading the final search changes, the HTTP assets/worker/clarification-export smoke passed. Two built assets were fetched, the actual worker produced clarification, and labelled escalation export succeeded.
- A concurrent HTTP smoke initially timed out while queued behind a model-backed chat. Sequential rerun passed. The worker is serial; a 30-second smoke wait does not establish a 30-second end-user SLA.
- An online backup and safe restore of the actual application data preserved its then-existing conversation and all 18 source snapshots. Backup: `var/backups/resolvedesk-chat-validation-20261013T1823`; restore: `var/resolvedesk-restored-validation-20261013T1823`. No live directory was replaced.

## Open gates

- Browser visual/interaction acceptance: the Browser skill connection was retried and reports no browser available. Presentation unit tests and asset HTTP checks do not close this gate.
- Actual database-error reproduction: host `psql`/`pg_dump` binaries were unavailable; the existing Docker daemon was stopped. No PostgreSQL server incident or restore was reproduced. “Actual data” here means real documentation and fetched source snapshots, not production database rows.
- Independent human scoring and the proposed 60-case benchmark are not complete. Quote membership establishes provenance, not entailment or completeness; the model support assessment is advisory.
- Windows service identity/reboot/resource testing, Cloudflare Access/Tunnel acceptance, actual pilot users and commercial validation remain open.
- Latency observations come from small functional runs. They are not calibrated p50/p95 or a capacity benchmark.

## Replay

```sh
make resolvedesk-test
make resolvedesk-validate-live
# Focus on the hard missing-page scenario:
.venv/bin/python scripts/validate_resolvedesk_chat.py --live --cases weak-local-search
# Running service checks; execute sequentially on an idle queue:
.venv/bin/python scripts/smoke_resolvedesk_chat.py
.venv/bin/python scripts/smoke_resolvedesk_http.py
```

Live commands invoke Codex and remote search and consume service usage. Raw reports and databases stay ignored; manifests, tests and this evidence summary are versioned.
