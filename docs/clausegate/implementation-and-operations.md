# Implemented ClauseGate: code map, limits and runbook

Status, 17 October 2026: **implemented pilot; read-boundary defect corrected, full release not accepted**. The rejected campaign is retained; [fixes and fresh validation](fixes-and-validation-2026-10-17.md) describe the coherent-read fence, backup/source/erasure corrections, full-context planning, exact quotes and version-bound retries. Regression/build passes do not establish semantic quality or target-host acceptance. Do not use it as autonomous legal approval.

## Delivered code

| Boundary | Actual implementation |
| --- | --- |
| Strict Pydantic schemas | `packages/contracts/src/contracts/clausegate.py`: rules, interpretations, typed human input, revisions, grants and exact review |
| Intake | `clausegate_api.intake`: bounded safe archive handling, original-Unicode source spans, PDF/text extraction, mixed-image coverage gaps, evaluator-only normalization |
| Scope/auth | `Store`: per-user credentials/session hashes, scoped workspace roles and case lists, live expiry checks; `api`: same-origin/CSRF/body/CSP controls |
| Uncertainty/policy | `worker.aggregate`, `Store._evaluate`: incomplete/disagreeing/uncertain results, missing business context, required review/exception and non-waivable block |
| Durable pause | `Store._evaluate/_request`: checkpoint/request/event committed together; worker returns, no model process sleeps for a reviewer |
| Human input | `Store.decide/assign/withdraw`: typed role/assignment/revision/expiry-bound responses, distinct reviewers, explicit rationale and idempotency |
| Resume | `_live_decisions/_schedule_resume/_check_job/complete_resume`: live dependencies/authority, durable queue, leases and publication fences |
| Audit | `_event/_verify/anchor`: per-case sequence/hash chain, state-head binding, safe transactional events, independent retained heads |
| Read consistency | `Store.coherent_read`: short serialized read/write fence, also used for anchor publication and backup validation/copy; no inference inside the fence |
| Narrow citations | `Finding.evidence_quotes`, `intake.resolve_evidence`: unique exact substrings inside cited original spans, server-derived Unicode offsets; legacy ID-only citations remain valid |
| Recovery | `authority.py`, `backup.py`: identity-bound erasure ledger, dependency erasure, new-directory quarantined restore and fresh operator provisioning |
| UI | `apps/clausegate-web/src/main.tsx`: cases/intake/playbook, original text reader, targeted decisions, manual fallback, people/grants, audit and reviewed exports |
| Evaluation | `capture_clausegate_corpus.py`, `validate_clausegate.py`, `score_clausegate.py`, HTTP/recovery runners and `accept_clausegate.py` |

Backend modules live under `apps/clausegate-api/src/clausegate_api/`. The deterministic domain is concentrated in `Store`, rather than separate proposed `policy/approvals/audit` classes. Worker orchestration is `run_once`, not the indicative `AnalysisController` class. No earlier product store/controller is imported. Shared `agent_core.codex_local.LocalCodexProvider` is reused through an isolated, tool-audited boundary.

## Installation and service commands

```sh
.venv/bin/python -m pip install --no-build-isolation -e '.[dev]'
npm --prefix apps/clausegate-web ci
make clausegate-up
make clausegate-status
make clausegate-test
make clausegate-down
```

UI: `http://127.0.0.1:8005/`. The managed API and worker were started for implementation validation. Only ClauseGate was stopped/restarted; earlier products were not restarted. Development launcher can reuse existing TenderLens bootstrap credentials if explicit `CLAUSEGATE_USERNAME/PASSWORD` are absent. It does not overwrite any existing password. No credential values are recorded here. The production service runner requires explicit ClauseGate settings.

Windows direct launcher parity: `.venv/Scripts/python.exe scripts/dev_stack.py --product clausegate up` after building the web app. `infra/windows/install-clausegate.ps1` installs separate limited-account startup tasks and refuses replacement; actual Windows acceptance is unrun. Cloudflare example adds only a placeholder application route; no DNS/tunnel/Access account was changed.

Actual settings: `CLAUSEGATE_DATA_DIR` (default `var/clausegate`), `CLAUSEGATE_ERASURE_LEDGER_DIR` (default adjacent `<data-name>-authority`), bootstrap username/password, host/port, `CLAUSEGATE_CODEX_COMMAND` (fallback `CODEX_COMMAND`), and `CLAUSEGATE_SECURE_COOKIES`. Use secure cookies behind protected HTTPS; loopback HTTP development uses `0`. Audit anchors share the configured independent authority store; the proposed separate `CLAUSEGATE_AUDIT_ANCHOR_DIR` is not implemented.

## Manual joint validation

1. Sign in as the requester/owner and create a workspace/case. In Intake, upload a licensed/public or explicitly authorized NDA, or paste its original text. Check source coverage.
2. Supply company side/purpose or deliberately leave them unknown to exercise clarification. Load/edit the clearly labelled example playbook. Save a draft or explicitly activate it; it is not legal advice or a universal policy.
3. In People, provision a separate reviewer identity if you are the bootstrap administrator. Grant only this case's reviewer/approver/final-reviewer capabilities. Grant changes conservatively stale existing workspace case approvals, so configure people before analysis.
4. Owner explicitly allows model-context egress if appropriate. Start bounded analysis. Installed Codex may use remote inference. With egress denied/provider unavailable, manual review remains available and AI success is not claimed.
5. Open a separate browser session as reviewer. Inspect original source spans, qualifications and the exact request. Use clarification, explicit correction or a scoped exception response—not a free-text blanket approval.
6. Owner responds to missing context as needed. Clarification invalidates the old interpretation's readiness and requires re-review; it does not accept an exception. Corrections reevaluate policy and may create a separate approval request.
7. Last required valid decision queues one continuation. The worker rechecks current source/policy/context, roles, assignments, expiry and epoch, then prepares an internal packet. Final independent review is still required before JSON/Markdown download.
8. Upload changed wording under the same filename, revoke a grant or withdraw a decision. Old forms/exports must stop working. Observe audit events and the visible stale-context conflict.

The retained HTTP validation case demonstrates a real-source workflow with synthetic decisions; its temporary test reviewer is not your human account. Create your own separate identity through People. Browser visual/keyboard/accessibility validation was not executable here because no browser connection was available.

## Real-data tooling

```sh
# New destination only. Publisher archive retained; unsafe member names are quarantined.
.venv/bin/python scripts/capture_clausegate_corpus.py --output var/validation/clausegate-corpus-UNIQUE

# Mechanical corpus/PDF and explicitly labelled workflow fixtures; optional development smoke.
.venv/bin/python scripts/validate_clausegate.py --corpus var/validation/clausegate-corpus-v2 --output var/validation/clausegate-run-UNIQUE --workflow-cases 60 --live-jobs 3
.venv/bin/python scripts/score_clausegate.py --corpus var/validation/clausegate-corpus-v2 --evidence var/validation/clausegate-run-UNIQUE --output var/validation/clausegate-run-UNIQUE/scores.json

# Fresh full regression/build plus all-gate assessment; nonzero while gates remain blocked.
make clausegate-acceptance CLAUSEGATE_OUTPUT=var/validation/clausegate-run-UNIQUE
```

Default live sample is the shortest requested development records, not a random or blind quality sample. For broader validation use `--workflow-cases 300 --live-jobs 30 --sample length-spread --pdf-limit 1000`; see [full reproduction](rigorous-validation-2026-10-17.md). `--live-split test --allow-heldout --live-jobs 123` explicitly opens the official test run; do not do so until thresholds/splits are frozen. The full held-out run has not been performed. The scorer now reports character and explicitly defined Unicode-regex token overlap; neither is the official ContractNLI scorer or proof of legal sufficiency. No calibrated risk probability is available. Supply retained read-race evidence to the acceptance runner; missing evidence blocks that gate and failed evidence rejects release.

`make clausegate-validate` defaults to a new `var/validation/clausegate-validation` destination; use `CLAUSEGATE_OUTPUT` and `CLAUSEGATE_CORPUS` to select explicit new paths. Outputs must not exist. Preserve old failed/intermediate reports rather than replacing them.

## Bounds and deliberate differences

Native PDF/text only; no OCR, Word redlining, e-sign, CRM or outbound messaging. PDF pages with images are conservatively partial, even if an image is a logo; empty text pages also signal gaps. This does not prove visual completeness of every text-only page. Provide separately reviewed complete text as a new source revision when appropriate; do not waive coverage as an ordinary exception. The UI renders original extracted text with spans and offers original-byte download, not a verified original-layout PDF renderer.

20 MiB uploads, 150 pages, 500,000 extracted characters; at most 25 playbook checks, 30 evidence IDs/finding, 1,000 historical requests and 1,000 decisions/case. Archive bound: 256 MiB compressed/512 MiB expanded/10,000 entries. Oversized/missing data is explicit, never silently certified complete.

One worker, active queue 20, renewable lease 150 seconds, original active deadline 600 seconds, call ≤120 seconds/remaining deadline, four calls/grant including one repair per chunk, two explicit analysis grants per unchanged bound input. Explicit retry reuses saved chunks and counts prior grants. Later chunk failure returns partial state and preserves checkpoints. This is character-budgeted (≤48,000 serialized prompt/schema characters), not exact token accounting. Very long documents can remain incomplete within these limits.

Playbooks are revisioned per case, not a reusable workspace-wide library. Assignment delegates only to an actor who already has the required scoped capability; it does not create that capability. In-app pending requests are the notification mechanism; email/Slack are absent. Separate coverage/change endpoints were not added: case snapshots, scoped audit pagination and two-second revision/epoch-aware polling provide those views. Old out-of-order snapshots cannot replace newer UI state.

No autonomous final clearance: every packet needs an independent final reviewer. Model “supported” is an uncalibrated proposal, not truth or authority. The smoke sample has errors even among such proposals; see the validation report. Reviewer decisions do not train a shared policy automatically.

## Backup, restore and audit assurance

```sh
.venv/bin/python -m clausegate_api.backup backup var/backups/clausegate-UNIQUE --data-dir var/clausegate --ledger-dir var/clausegate-authority
# Stop services; NEW nonexistent destination only; current independent authority required.
.venv/bin/python -m clausegate_api.backup restore var/backups/clausegate-UNIQUE --data-dir var/clausegate-recovered --ledger-dir var/clausegate-authority
# Inspect quarantined recovery, then provision a NEW operator identity interactively.
.venv/bin/python -m clausegate_api.backup provision operator --data-dir var/clausegate-recovered --ledger-dir var/clausegate-authority --username NEW_OPERATOR
```

Backups include source/raw bytes in SQLite and verify source/audit/file integrity; no separate upload blob tree is omitted. Restore rejects the unrelated authority before copying, reapplies later erasures, rotates epoch, cancels jobs, removes sessions/memberships and makes restored approvals unusable. New operator/reviewer grants and fresh reviews are required. Original snapshot usernames/password hashes alone do not reauthorize the recovered store. Never roll back the independent authority store.

Audit events contain safe identifiers/digests, not source text or human rationale bodies. Erasure deletes content-bearing source/case history/decisions/jobs and leaves non-content receipts and hashes. Hashes can still be sensitive; backup/media retention is an operator policy, not certified wiping. Already downloaded packets cannot be recalled. A local chain plus local state hash cannot defeat a privileged administrator who rewrites all trusted material; independent retained heads improve rollback detection, but a stale same-identity authority clone remains an operational hazard. Protect its latest version outside ordinary rollback snapshots.

## Remaining release work

Full held-out/near-duplicate screening, qualified semantic/challenge review, measured uncertainty calibration, ≥30 distinct live-document workflow runs, actual two-person/browser/accessibility acceptance, target Windows/protected edge/all-six-product resource drills and consenting-customer usefulness remain open. The actual runtime and measured tests exist; production readiness does not follow from that fact.
