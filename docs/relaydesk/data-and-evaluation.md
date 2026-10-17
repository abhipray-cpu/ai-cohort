# Actual data, independent labels and rigorous evaluation

Status: release-evaluation plan. [Corrective validation, 17 October](corrective-validation-2026-10-17.md) covers a deduplicated 89 real threads/22 repositories/6,680 non-bot messages, 84 complete/five partial captures, eleven live AI-stage completions and 78 exact source-resolving quotations. Across overlapping original/long/expanded runs: 1,258 query executions and 2,921 invariant assertions, not independent unique examples. Engineering checks pass; full cohort, substantive screening, independent labels, calibration, browser and Windows gates remain open. Targets below are unchanged. Capacity replicas add no unique real data; quotation provenance is not answer accuracy. [Original failures](aggressive-validation-2026-10-16.md) are preserved.

## 1. Cohort volume and representation

Target **200 substantive public investigation threads from at least 20 repositories**, and **at least 5,000 unique human-authored messages** after deduplication/bot separation. Prefer roughly ten threads per repository; no repository should dominate the held-out cohort. A message count, a thread count, source revisions and distinct supported facts are different denominators.

Proposed discovery repositories, subject to access/terms/quality screening: microsoft/vscode, microsoft/TypeScript, elastic/elasticsearch, nodejs/node, nodejs/undici, node-red/node-red, postmanlabs/newman, fastify/fastify, expressjs/express, axios/axios, nock/nock, websockets/ws, webpack/webpack, vitejs/vite, rollup/rollup, eslint/eslint, babel/babel, jestjs/jest, jupyterlab/jupyterlab and pandas-dev/pandas. This is a source shortlist, not an acquired or guaranteed eligible corpus. Non-npm ecosystems are fine: conversation continuity is not a package-parser task.

Stratify before tuning: short controls, >30-message investigations, multi-day/month histories, environment/version changes, failed attempts, proposed versus confirmed workaround, explicit corrections, multiple reporters, reopened/duplicate/bot-closed threads, unresolved cases and long logs. Include at least ten >100-message threads if available; never inflate volume by counting repeated quoted text, bots or the same thread twice. Report missing strata rather than inventing favourable data.

Freeze discovery rules/exclusions and a source manifest with repository/issue IDs, full source pagination, retrieval times, raw and canonical hashes, edit times, terms review and coverage. Partial acquisition remains partial. If fewer eligible real messages/threads exist under the rules, expand the predeclared shortlist or document the shortfall; do not lower the bar silently.

## 2. Acquisition and sessionization

Use bounded read-only GitHub APIs, explicit page traversal/Link handling and rate-limit checkpoints. Exclude pull requests from issue lists unless separately admitted as a labelled source stratum. Capture all selected comments within declared limits, not only the first page. Optional timeline events require separate access/schema checks; do not claim reopen history from current `state` alone.

Preserve exact source text/revisions and IDs. Separate bots, human comments, issue bodies, quotes and attachments. Messages suspected to be AI-authored cannot be guaranteed human merely because author type is a user; record provenance limitations. Never execute or fetch links from body text.

Proposed analytic session boundary: an explicit source-session marker where available, otherwise a predeclared inactivity gap (initially 24 hours). These are derived replay sessions—not evidence that real browser logins or engineer shifts occurred. Report sensitivity to 12/24/48-hour grouping. Cross-browser sync is tested independently with actual separate sessions.

Current GitHub bodies can be edited. A future-edited body is not valid past evidence. If original revisions cannot be obtained, conservatively make the captured body eligible no earlier than its known update time, or exclude it from earlier cutoffs and record a gap. Issue `updated_at` can reflect activity other than body editing; this policy is conservative, not a claimed reconstruction of original wording. Capture-time versus event-time distinctions remain in every replay.

## 3. Independent labels and partitions

Target **300 independently reviewed chronological questions**: approximately 150 development / 60 calibration / 90 held-out. Partition by repository before prompt/ranking tuning: ten repositories development, four calibration, six held-out. Keep a linked issue family together across partitions where possible; quantify remaining component/phrase/family overlap. A repository split is not proof of unseen-topic generalization.

Two reviewers label independently, adjudicate disagreements and retain rationales/exact sources. Questions must have known cutoff, required evidence-message IDs/spans, answerable/ambiguous/unanswerable state, supported atomic facts, current/superseded status, applicability and prohibited inferences. Include an independently labelled fact/attempt/outcome ledger for each evaluated thread, not only selected easy questions.

Minimum question strata: 60 multi-session recall, 60 temporal/update, 50 attempted-versus-proposed/outcome, 40 conflicting environment/reporter, 40 explicit commitment/open action, 50 abstention/insufficient-evidence. Assign a primary category for denominators and retain overlapping tags. Negative/critical cases cannot be silently removed after a failure.

No model-generated question/answer or self-score is independent gold. A single annotator remains single-reviewer evidence, even if a model agrees. Real public technical data does not establish private customer value or permission to contact its contributors. Customer pilots require separate consent/authority.

## 4. Frozen chronological replay

Replay a thread incrementally into source revisions, episodes, memory and summaries. At each question cutoff expose only eligible messages/state. Do not ingest later answers into the vector index, summary, source metadata, cached context or query expansion. Explicitly test future-info leakage.

Measure retrieval before generation, generation after retrieval, and sync/compression separately. Context budgets, encoder/model versions, source scope and cutoff are pinned for all baselines. Keep excluded/unsupported/edited/partial cases in the denominator/report with a reason rather than selecting only successful conversations.

Report all actual-model attempts, validation failures, repairs, timeouts, provider unavailability, valid narrative outcomes and fallback outcomes separately. A durable partial response or HTTP 200 is not successful AI completion. A recovery retry is a new observation, not a replacement for the failed run.

## 5. Baselines and ablations

Compare recent-buffer only; lexical/BM25 over full authorized past history; vector-only recall; structured summaries without vectors; and the full hybrid memory system. Also compare raw ticket reading/helpdesk summaries in consenting usefulness pilots. Keep equivalent source/time access and explain differing compute budgets.

Ablate compression, temporal/status ranking and cross-session cache invalidation independently. Include a feasible full-history oracle on smaller cases to separate retrieval omissions from generation errors. Full-history exceeding context is an explicit non-applicable/partial baseline, not silently truncated “oracle.”

Prove actual semantic recall: paraphrases whose evidence is outside the buffer, retrieval results tied to persisted vector rows after restart, and comparison against lexical-only. A mocked vector fixture can test shape/bounds but cannot validate this concept.

## 6. Metrics and proposed release gates

| Measure | Denominator / proposed requirement |
| --- | --- |
| Source acquisition coverage | Complete selected eligible messages / all discoverable selected eligible messages; 100% or explicit partial case, with rate/page caps counted |
| Evidence recall@10 | Required evidence items represented in top 10 / all gold-required evidence items; target >=95%, critical corrections/commitments 100% |
| Memory factual precision/recall | Supported accepted atomic memories / accepted; required ledger facts retained / required; target >=98% / >=95%, all critical items preserved |
| Currentness/applicability | Gold-scored state/version/reporter decisions; zero critical superseded-as-current or wrong-account assertions |
| Answer support | Human-supported material claims / presented material claims; >=98%, with exact references 100% resolvable |
| Abstention | False answer rate on insufficient-evidence cases; zero critical invented outcomes/commitments, publish all counts |
| Compression preservation | Critical active constraints, failed attempts, commitments/open questions retained or explicitly linked/omitted; 100% critical preservation |
| Compression efficiency | Serialized context reduction versus equivalent uncompressed past evidence, with semantic preservation reported alongside; initial target >=50%, not a standalone success |
| Cross-session consistency | Corrections/deletions/revocations/restarts reflected at requested revision; 100% controlled scenarios, no stale publication labelled current |
| Sync latency | Commit-to-visible-update p50/p95 on actual host; proposed p95 <=2 seconds in active local sessions, measured separately from model latency |
| Resource/latency | CPU/RSS/disk and vector recall p50/p95 at 1k/5k/10k eligible vectors; no old-laptop readiness without actual measurements |
| Handover usefulness | Reviewer-accepted required facts/actions and effort versus incumbent; target >=30% median preparation reduction over paired consenting tasks |

Thresholds are proposals, not observations. Publish raw numerators/denominators, uncertainty and per-stratum results. Cluster repeated questions by case/repository when estimating uncertainty. Rank scores, judge scores, citation counts and successful HTTP responses are not interchangeable accuracy measures.

The PatchDesk lesson applies directly: successful reads and valid citations can coexist with missing required evidence. Report source→extraction→indexed→eligible→retrieved→compressed→answered coverage separately. A fixed top-k/context cap must not hide unrepresented critical items.

## 7. End-to-end and fault matrix

| Scenario | Expected evidence |
| --- | --- |
| Restart after buffer overflow | Real persisted vector recall of an older fact, original sources resolve |
| Different engineer/browser resumes | Same authorized latest investigation state, with explicit attribution |
| Failed workaround followed by correction | No repeated “successful” advice; earlier state available only as history |
| Source edit after question cutoff | Excluded/conservative eligibility, no future leakage |
| Similar issue under another account | No candidate, prompt, event, cached answer or export leak |
| Compression excludes a critical open item | Gate fails, omission visible, no exhaustive handover claim |
| Encoder unavailable / model hash changed | Explicit semantic degradation/rebuild; no mixed-vector scoring |
| Late model timeout after indexing | Durable memories/sources survive; validation/stage event and partial handover |
| Simultaneous correction in two sessions | Expected-revision conflict; no silent overwrite |
| Erasure while vector/reply job runs | Fence/invalidation prevents resurrection or answer publication |
| API/worker killed and restarted | Counters/leases/events preserved, no duplicate committed turns/memories |
| Stale event cursor / restored backup | Scoped reset/new epoch and erasure reconciliation before serving |
| Actual UI journey | Import→chat→overflow→recall→correct in second browser→review/export→forget, tested at three viewports |
| Windows and protected tunnel | Service identity/model auth, CPU embedding, reboot/resources/access accepted on target host |

Injected outages/races/mutations are labelled robustness tests over real payloads, not natural incidents. No unsolicited upstream issue/reply is created to validate a workflow.

## 8. Artifacts and reproducibility

Proposed, not existing:

```text
data/relaydesk/manifests/       versioned selection, terms, split and safe metadata
data/relaydesk/gold/            reviewed questions, ledgers, adjudication and source refs
data/relaydesk/adversarial/     labelled mutations and fault descriptions
var/relaydesk-corpus/<freeze>/  raw source revisions, page manifest, hashes and failures
var/relaydesk-evaluation/<run>/ isolated store, traces, context manifests and metrics
```

Freeze source/model/tokenizer/code hashes, policy/summary/ranking/schema versions, split/label revisions, actor grants, budgets, host/provider versions and exact failures. Acquisition/evaluation tools must refuse overwriting freezes or resetting cumulative work silently. Keep raw private/public-comment payloads out of git until reuse/privacy review.

Supplemental LongMemEval is separately labelled constructed-history benchmark; it does not replace real-thread volume, semantic support labels, actual browser sync or a paid pilot. Study/blog follow implementation and measured validation, not this plan.
