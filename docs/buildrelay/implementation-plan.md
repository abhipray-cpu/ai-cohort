# TDD implementation record and remaining acceptance

This pack records the implementation sequence; no Day 8 documentation pack existed
before the user authorized implementation. It must not be presented as a previously
approved detailed plan.

Tests were introduced and observed failing before corresponding behavior:

| Stage | Red evidence | Implemented behavior / tests |
| --- | --- | --- |
| Durable kernel | Missing contracts/module | Inbox, cross-transport dedupe, repository binding, leases, retries, replay (`test_buildrelay_core.py`) |
| Response workflow | Missing workflow module; later SQL projection failure | Grounded triage, repair audit, checkpoints, lost-create reconciliation, manual fallback (`test_buildrelay_workflow.py`) |
| Transports | Missing GitHub adapter | Typed envelopes, ack-after-persist, poison input audit, API limits, redirect/archive guards (`test_buildrelay_transports.py`) |
| Auth/API | Missing API module | HMAC, CSRF, identity/client grants, scoped reads/replay, real readiness (`test_buildrelay_api.py`) |
| Recovery/operations | Missing repair/backup; absent launcher product | Bounded repair, crash exhaustion, restricted runtime, snapshots and additive launch wiring (`test_buildrelay_recovery.py`, `test_buildrelay_operations.py`) |
| Frontend logic | Missing domain module | Replay permission, empty/actual counts, recovery labels, safe links (web `domain.test.mjs`) |
| Handoff | Missing acknowledge endpoint returned 405 | Ownership acknowledgment, safe draft export (`test_buildrelay_handoffs.py`) |
| Corpus | Missing corpus module | Hash/reference checks; no implicit AI pass (`test_buildrelay_corpus.py`) |
| Revocation | Missing grants endpoint returned 405 | Immediate grant replacement, session revocation, last-owner guard (`test_buildrelay_security.py`) |
| Long work | Missing renew method | Renewable lease without resurrecting an expired worker (`test_buildrelay_core.py`) |

Actual broker and TCP process integration tests complement these. Not every CSS
change has a preceding failing test; frontend logic tests and compilation are not
browser interaction tests. No claim of complete test coverage is made.

## Next acceptance order

Update: [actual validation](real-data-validation-2026-10-18.md) now includes 797-log
selection checks, 80 real-log AI analyses, 36 fresh GitHub records, actual HTTP/NATS/
Codex replay and child-process crashes. Its evidence-selection and expired-lease
blockers led to the [corrective run](fixes-and-validation-2026-10-19.md): typed lease
loss, diagnostic-window selection, 90.20% corpus anchor retention and 533 passing
tests. Final model-quality results and remaining independent/target-system gates
are recorded there; they must not be inferred from the green regression suite.

1. Held-out real failure interpretation: independent failure-chunk relevance and
   diagnosis/next-step review, including ambiguous/incomplete logs and languages.
2. Controlled, owned GitHub test repository: source permissions, actual attempt logs,
   opt-in issue lifecycle and crash/redelivery ambiguity. Do not write to dataset
   repositories or create public issues without separate authorization.
3. Connected-browser flows: login, setup, grants/revocation, incident evidence,
   acknowledgment/export, replay/rearm, keyboard navigation and mobile layout.
4. Old Windows laptop: Task Scheduler identity, installed Codex, authenticated broker,
   reboot, process cleanup, power/network outages, backup/restore and disk limits.
5. Cloudflare authentication/path exceptions, full outage recovery, load/retention,
   secret-redaction review and measurable recovery objectives.

These gates remain unpassed. The acceptance command deliberately reports
`release_accepted: false` and exits nonzero; green unit tests cannot clear them.
