# Implementation validation — 18 October 2026

Historical implementation-phase record. The later [rigorous real-data validation](real-data-validation-2026-10-18.md)
found selection-quality failures and an expired-lease worker crash. Latest full
baseline regression was 522 passed / one failed. The
[19 October corrective run](fixes-and-validation-2026-10-19.md) passed 533 tests;
the earlier results below remain historical, not the current validation status.

Status: **implementation-tested pilot; full product acceptance not complete**.
This is an evidence record, not a production-ready/MVP-accepted declaration.

## Executed checks

The integrated local report at
`var/validation/buildrelay-implementation-2026-10-18/report.json` records:

- 38 BuildRelay Python test cases passed, **zero skipped** in this integrated run.
- Four frontend domain tests passed; TypeScript/Vite production build passed.
- Actual official NATS server **v2.15.1**, macOS arm64, checksum-verified, bound to
  loopback with test authentication. Its test publishes 50 duplicate queue envelopes
  plus a signed HTTP/ASGI webhook to one canonical inbox event, confirms no pending
  consumer ACKs, records poison input, and runs one incident workflow using an AI
  test double. This is a controlled transport/workflow test, not live GitHub traffic.
- Actual separate Uvicorn API and worker processes passed loopback TCP readiness,
  built HTML serving/CSP, unauthenticated rejection, session login, and empty-state
  authenticated API read. No external repository or model call occurs in that test.
- Actual installed-Codex smoke: **one controlled fixture call**, exit 0,
  14,329 ms, `tools_audited: true`; schema/citation validation passed. Receipt:
  `var/validation/buildrelay-codex-smoke-2026-10-18/report.json`.
- Actual public corpus acquisition and integrity audit: 797 logs / 797 annotations,
  80 repositories, 29 languages; zero missing references/empty chunks. This is not
  semantic AI validation. See [data and evaluation](data-and-evaluation.md).

Post-review report: `var/validation/buildrelay-post-review-2026-10-18/report.json`
records **39 Python cases passed, zero skipped**, four frontend tests/build passed,
and both actual broker/TCP gates passed. It preserves the earlier 38-case result.
A new regression first exposed the recovery-close retry bug: the internal recovered
projection could incorrectly skip a retry of the external issue update. The fixed
guard now retries the close. Existing security/audit tests were also extended to
reject malformed non-ASCII signature bytes without a 500 and record the actual
owner identity on client/repository configuration, not merely the owner role.

Earlier full-monorepo regression: 506 passed / one skipped in 44.23 seconds, before
the final additional BuildRelay handoff/revocation/corpus/lease tests. The broker
skip in that earlier run was subsequently executed separately and in the integrated
38-case run.

Implementation-phase **post-review full-monorepo regression: 515 passed, zero skipped, in 47.26
seconds**, including all 39 BuildRelay cases and both actual local integrations.
Machine-readable result:
`var/validation/buildrelay-post-review-regression-2026-10-18.xml`.
This was rerun after the recovery guard, signature and audit-actor corrections;
the count is not inferred by adding separate suite results.

Python checks emit existing Starlette/httpx and PyMuPDF/SWIG deprecation warnings.
They are not failures and were not hidden. New backend/scripts/tests lint passed.

## Explicit gaps

- Real-failure diagnosis quality on held-out data has **not** been evaluated.
- Live GitHub evidence permissions and real issue-create/update/recovery have not
  been tested with an authorized owned repository. HTTP tests use controlled sources.
- Browser setup was attempted using the available Browser skill/runtime; it returned
  no available browser, and discovery returned an empty list. No rendered interaction,
  screenshot, accessibility or responsive-layout acceptance is claimed.
- Old Windows laptop installation/reboot, Cloudflare path exceptions and downtime
  recovery are not tested on their actual target systems.
- Capacity/load, disk-retention guarantees, stronger audit integrity and independent
  security review remain open. Small controlled duplicate tests are not a live-load
  qualification.

The acceptance collector intentionally emits `release_accepted: false` and exits 1
despite passing local gates. Its remaining-gate list cannot be cleared by merely
supplying a command-line success flag. Do not call that exit a test failure or an
accepted release.

## Reproduce implementation checks

```sh
make buildrelay-test
# Set the actual binary path for the host; the temporary macOS path is not portable.
BUILDRELAY_NATS_BINARY=/path/to/nats-server BUILDRELAY_PROCESS_TEST=1 \
  .venv/bin/python -m pytest tests/test_buildrelay*.py -q

# Evidence collector; expected nonzero until full release acceptance is implemented/proven.
BUILDRELAY_NATS_BINARY=/path/to/nats-server BUILDRELAY_PROCESS_TEST=1 \
  .venv/bin/python scripts/accept_buildrelay.py \
  --output var/validation/buildrelay-implementation-new \
  --corpus var/validation/buildrelay-capture-2026-10-18 \
  --runtime-smoke var/validation/buildrelay-codex-smoke-2026-10-18/report.json
```

Optional fresh fixture runtime smoke, explicitly consuming authenticated service usage:

```sh
.venv/bin/python scripts/smoke_buildrelay_codex.py --live --output var/validation/buildrelay-codex-new
```

No raw logs, test passwords, broker tokens or `.env` values belong in committed docs.
