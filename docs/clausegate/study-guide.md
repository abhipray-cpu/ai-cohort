# Study guide: human-in-the-loop agents through ClauseGate

Day 6 of the product challenge. Read this alongside the [complete real-data evaluation](development-validation-2026-10-17.md) and [architecture](architecture.md).

ClauseGate is an implemented NDA exception-review pilot. Its engineering checks pass, but semantic and full-product acceptance remain blocked. We evaluated all 61 official development NDAs: 790/1,037 labels matched, and 162/637 model-marked supported findings were wrong. Learning why those facts can coexist is central to understanding this product.

## 1. Start with the business decision

The proposed buyer is a team with an approved contract playbook and exceptions waiting for review. ClauseGate's intended outcome is less reviewer effort and waiting without more missed exceptions. That commercial outcome has not been validated with customers.

The model proposes what a passage says. Policy decides whether that interpretation needs review or a permitted exception. Authorization decides who may respond. Currentness checks decide whether the response can still be used.

These are different questions:

- Is the interpretation correct?
- Does the organization's policy permit that situation?
- Did the right person approve the exact permitted deviation?
- Is that approval still applicable to today's document and context?

A valid JSON object answers none of the last three by itself. An exception approval does not make a model interpretation true.

## 2. Locate the five requested concepts

| Concept | Implemented responsibility | Code and evidence |
| --- | --- | --- |
| Uncertainty detection | Separate semantic labels from unsupported/incomplete execution; detect gaps, missing facts and mandatory policy blockers | [worker](../../apps/clausegate-api/src/clausegate_api/worker.py): aggregate; [Store](../../apps/clausegate-api/src/clausegate_api/store.py): _evaluate |
| Pause | Persist checkpoint, request and audit; release the worker instead of retaining a sleeping model process | Store._request, _evaluate, complete_analysis; [worker tests](../../tests/test_clausegate_worker.py) |
| Request human input | Ask a scoped question with source evidence, permitted responses, role, assignment, rationale and expiry | Store.decide/assign; [API](../../apps/clausegate-api/src/clausegate_api/api.py); [React workbench](../../apps/clausegate-web/src/main.tsx) |
| Resume with validated context | Recheck dependencies, live authority, decision validity, epoch and lease before using an approval | Store._binding, _live_decisions, _schedule_resume, _check_job, complete_resume |
| Full audit trail | Connect source, findings, requests, responses, continuation and packet; check integrity and disclose its trust boundary | Store._event/_verify/anchor; [authority](../../apps/clausegate-api/src/clausegate_api/authority.py), [backup](../../apps/clausegate-api/src/clausegate_api/backup.py) |

Schemas live in [contracts.clausegate](../../packages/contracts/src/contracts/clausegate.py). Shared model access is through the installed Codex adapter, not a direct product model API. The CLI may use remote inference: host-local storage does not mean local model weights or zero document egress.

## 3. Follow one case end to end

For an exception-approval path:

~~~text
Import source + activate playbook + supply business context
  → queued case / running analysis job
  → waiting_human with a durable bound request
  → independently scoped exception response
  → resume_queued
  → worker revalidates context
  → review_ready internal packet
  → independent exact-packet review
  → finalized, exportable packet
~~~

This is an illustrative path, not every transition. Clarification changes context and requires re-review; interpretation confirmation/correction reevaluates findings and can reach review readiness directly. An exception's final valid response queues deterministic worker continuation. A hard block cannot be waived by ordinary exception approval.

The case and job have separate states. A running job is not evidence of a completed analysis. Review-ready is not finalized. A finalized internal packet is not an e-signature or permission to send it to a counterparty.

## 4. Understand uncertainty without inventing confidence

The semantic labels are Entailment, Contradiction and NotMentioned. They are distinct from execution assessments supported, uncertain, unavailable and incomplete.

NotMentioned is a proposed answer about absence, not a synonym for “the model failed.” Incomplete processing cannot establish document-wide absence. The scorer counts unusable partial results as missing, not correct guessed NotMentioned answers. An uncertain but completed interpretation is still scored as a prediction.

Uncertainty also comes from deterministic facts:

- Source extraction has image/OCR gaps or an unprocessed chunk.
- Required company side or disclosure purpose is unknown.
- Chunk interpretations disagree.
- Policy requires review even for a well-supported interpretation.
- A non-waivable rule blocks clearance.

A person may supply missing business context, resolve an interpretation or accept an allowed exception. They cannot approve away an unreadable source or unrelated hard block.

The full development evaluation found 162 incorrect labels in 637 model-marked supported proposals: 25.43% error in that subset. This is not calibrated confidence. Printing a probability or repeating the model cannot establish it. Calibration needs representative independent evidence and risk/coverage measurements; qualified challenge review remains outstanding.

## 5. Grounding: exact quotation is necessary, not sufficient

Finding carries the check ID, label, assessment, evidence IDs and rationale. Optional EvidenceQuote values narrow a citation to a unique verbatim substring within an authorized original span.

The server, not the model, resolves the substring into original Unicode character offsets. It rejects invented, ambiguous, duplicate or uncited quotes. ID-only legacy/manual findings still resolve to whole original spans. Exact matching establishes provenance; a real quote can still be irrelevant, misinterpreted or omit an exception.

Keep three identities distinct:

1. Original bytes hash: the uploaded file.
2. Canonical extracted-text hash: the version interpreted.
3. Evidence range: the exact source slice being cited.

The full evaluation's evidence-token F1 is 0.5370. This is the documented custom Unicode token-overlap metric, not the official ContractNLI scorer or proof of complete legal support. All exact quotes resolving does not imply every required qualifier was recovered.

Full-document planning keeps related clauses together when prompt plus schema fit the bounded request. Oversized inputs split; incomplete coverage stays explicit. The 48,000-character allowance is not an exact token count or unlimited context guarantee. The live development cohort does not validate every possible 500,000-character supported input.

## 6. Durable pause and bounded execution

A durable pause is a committed database transition. The source-bound checkpoint, human request and audit must survive the process that produced them.

After analysis, the worker returns. Waiting for a person consumes no inference calls or active worker lease. Human waiting time and the inference job's active deadline are different clocks.

Execution remains bounded: one active worker per store, reserved calls, expiring leases, a deadline, one structured repair per chunk and two explicit analysis grants for unchanged analysis input. A later failure preserves available chunk checkpoints and a degraded draft; it does not fabricate completion.

ANALYSIS_VERSION participates in the analysis input binding. Changing the pipeline must not reuse an old cursor whose chunk boundaries or schema mean something different.

Read the [actual worker recovery drill](../../scripts/validate_clausegate_recovery.py). It terminates an isolated worker while paused, records a response while the worker is down and verifies one effective continuation after restart. At-least-once execution plus idempotent, lease-fenced commits is not universal exactly-once execution.

## 7. Validate the human response

Authentication identifies the actor; authorization determines their current capability and case scope. A role named reviewer in a test is not proof of professional legal qualification.

Responses are typed:

| Input | Meaning |
| --- | --- |
| Clarify | Supply required company facts; invalidate the old interpretation context |
| Confirm/correct interpretation | Review the source-linked meaning; correction must explicitly identify the changed label |
| Approve exception | Accept only a permitted deviation under the active policy |
| Reject/request revision | Stop or request a changed source; do not quietly clear a blocker |
| Final review | Acknowledge limitations and review the exact packet hash |

The server checks request revision, binding, permitted kind, rationale, assignment, scope and expiry. It rejects self-approval, blank rationale and stale forms. Required roles can require distinct actors; workspace administration does not itself supply exception/final-review authority.

Idempotency is precise: same actor/key and same response can return the original decision. Reusing the key with a different payload conflicts.

## 8. Resume against the context that was actually approved

The binding pins source identity/digests/coverage, playbook, business context, findings and restore epoch. Request revisions and live permissions/assignments/expiry are additional checks; not every authorization fact is merely a field in one hash.

Revalidate when scheduling, executing and publishing/exporting. Otherwise an approval can be valid at submission but invalid by the time its consequence is used.

Try these on a disposable case:

- Upload changed wording under the same filename.
- Revoke the reviewer's case grant.
- Withdraw an earlier exception response.
- Submit a previously opened form after the revision changes.

The old approval/form/export must not remain usable. A disabled button is not the security boundary: the API and worker must reject it too.

The frontend also guards against older polling responses replacing newer context and against showing an asynchronously fetched old document beside a new request. See [frontend state tests](../../apps/clausegate-web/tests).

## 9. Audit correctness includes consistent reads

Events form a per-case sequence/hash chain. The head also binds current case state. That detects a row changed to finalized without its legitimate transition.

Real testing found a subtler problem: legitimate concurrent updates caused readers to compare old audit events with new case state, falsely reporting corruption. The final audit was valid.

The correction is Store.coherent_read(), a short BEGIN IMMEDIATE fence also respected by ordinary anchor publication. Backup verifies/copies under that fence using a separate source connection; copying from the connection holding a write transaction can wait on itself. Source-byte authorization and retrieval are atomic too.

This conservative approach serializes these reads and trades throughput for consistency. It holds no model/network/PDF parsing or human waiting inside the fence; disk backup does block writers while copying. A successful small Mac loopback run does not prove Windows capacity, fairness or sustained-load behavior.

A local hash chain is not immutable against a privileged administrator who rewrites everything. Independently retained heads help only if their identity, freshness and protection are trustworthy.

## 10. Restore is an authority change

A backup can contain a source later erased, a role later revoked and an approval later withdrawn.

Restore therefore verifies the independent authority, applies current erasures, rotates epoch, expires sessions/leases, cancels work and removes restored memberships. Serving remains quarantined until a fresh operator provisions current authority. Restored approvals do not automatically become current.

The erasure receipt blocks source access before local reconciliation finishes. Authorized users may retain a non-content erased-case receipt afterward.

The [real-source backup drill](../../scripts/validate_clausegate_backup_recovery.py) checks concurrent writes, later erasure, quarantine and fresh authority. Logical erasure is not secure wiping: retained snapshots, public originals and previously downloaded packets need separate retention controls.

## 11. Read the real-data evidence correctly

The verified corpus contains 607 IDs, 606 exact-distinct texts and 10,319 published labels. That is corpus volume, not 10,319 model answers.

The complete development evaluation uses two disjoint same-code cohorts: 30 retained NDAs plus the other 31. All 61 analyses completed, producing 1,037 scored predictions. No duplicate pair is pooled. Classification is recomputed from predictions; evidence micro-F1 is recomputed from summed overlap counts, not averaged batch F1.

Current results:

- 790/1,037 labels match; macro-F1 0.6995.
- Training-only per-hypothesis majority baseline: 706/1,037 matches; macro-F1 0.6325.
- Supported subset: 162/637 wrong; unsafe as calibrated clearance.
- 300 real-text workflow fixtures pass 3,314 assertions, but policies/responses are synthetic.
- All 374 safe original PDFs were checked; 162 are conservatively partial. No OCR or all-page visual-coverage claim.
- 346 Python tests, four frontend tests/build, HTTP, concurrency and recovery checks pass.

Published lexical overlap, correlated hypotheses, earlier development iterations and possible model-training exposure limit independence. The official test split was not sent to inference, but this does not make development results blind. A complete development set is not a qualified held-out or customer acceptance cohort.

## 12. Run safe learning exercises

Commands below are for the measured macOS workspace. See [operations](implementation-and-operations.md) for deployment differences.

~~~sh
make clausegate-up
make clausegate-test
.venv/bin/python -m pytest tests/test_clausegate_boundaries.py -q -k cannot_mix
.venv/bin/python -m pytest tests/test_clausegate_worker.py tests/test_clausegate_evaluation.py -q
make clausegate-status
~~~

Create two distinct identities and a disposable public-source case following the runbook. Do not erase or terminate processes belonging to an active customer agreement. Recovery scripts create isolated fixtures; use new output paths.

Exercises and expected observations:

1. Leave side/purpose unknown: targeted clarification, not invented facts.
2. Require an exception: requester cannot approve it; a scoped different actor can.
3. Create a hard block: ordinary approval cannot waive it.
4. Change source after approval: old form/export is rejected.
5. Supply an invented or repeated ambiguous quote: validation fails; no arbitrary offset substitution.
6. Restart an isolated paused worker: request persists and waiting makes no inference calls.
7. Run the interleaving regression: a valid concurrent write must not look like audit tampering.
8. Inspect complete-development.json: explain why its 1,037 pairs are only 61 documents and why supported does not mean correct.

Do not open official test inference, tune on failures and call the corrected rerun blind. The [validation report](development-validation-2026-10-17.md) provides reproducible commands and artifact locations.

## 13. Check your understanding

- Why isn't Pydantic enough? It validates structure, not truth, source sufficiency or authority.
- Why can't the model approve? Its output has no approval capability; deterministic server policy and scoped human input control transitions.
- Why check roles again after a click? Authority can expire or be revoked while work waits.
- Why isn't review-ready final? A separate exact-packet review is still required.
- Why can exact quotes coexist with wrong answers? Provenance does not establish entailment or recover every exception.
- Why can more completed answers hide a regression? Recovered provider failures can raise totals while accuracy on previously usable pairs falls.
- Why can tests be green while release is blocked? Engineering correctness, semantic quality, real human usability, target deployment and customer value require different evidence.

The remaining gates are qualified/held-out semantic quality, actual two-person browser/accessibility, Windows/protected-edge/resources and customer usefulness. No production, legal-quality or paid-customer success is claimed.
