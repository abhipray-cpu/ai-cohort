# Implementation verification — 19 October 2026

Subsequent alternative-source work is recorded in the [Irish FSPO report](fspo-source-and-validation-2026-10-19.md):
132 actual PDFs acquired, 122 usable excerpts passed local checks, 91 product tests
and 624 final monorepo tests passed. Real-case model inference remains unexecuted
pending explicit payload/destination approval. Earlier no-corpus statements below
describe the prior source-gate attempt and are retained as history.

## Subsequent real-data validation request: source preflight

Following the user's request to commence rigorous real-world end-to-end testing,
the workspace source inventory and permission gate were checked again. Available
CaseCouncil artifacts are engineering smoke stores and test reports; no eligible
actual-case manifest or source-clearance record was found. Other products' corpora
are not an authorized substitute for motor-insurance complaint files.

The [official FOS legal page](https://www.financial-ombudsman.org.uk/legal-policy)
was rechecked on 19 October 2026. Its copyright section still distinguishes
personal-use extracts from reproduction/storage in public or private retrieval
systems, which requires prior permission unless specifically permitted. No
applicable permission or reviewed alternative basis is recorded here. This is
a source-preflight finding, not a determination of every possible legal exception.

**Result: G0 blocked; real-case inference and real-data E2E acceptance not started.**
No decision PDFs were downloaded, transformed, indexed or sent to the model in
this attempt. No new model quota was consumed and earlier engineering results
were not relabelled as real-data validation. Continuing requires authorized case
files with approved egress, applicable source clearance, or the user's approval
to research a different rights-cleared source and update the validation scope.

## Earlier implementation verification scope

Scope: the user authorized full implementation following TDD, **then** real-world
validation. This record covers coding and engineering verification. No actual FOS
corpus or customer files were acquired, no permission was assumed and no real-data
acceptance claim is made. See the [runbook/module map](implementation-and-operations.md).

## Executed evidence

| Check | Observed result | Artifact or command |
| --- | --- | --- |
| Product Python suite, including explicit real-HTTP process flag | **86 passed, 0 skipped** | `var/validation/casecouncil-engineering-2026-10-19-final-combined/tests.xml` |
| Frontend domain tests | **5 passed** | Same directory, `frontend_tests.log` |
| TypeScript + Vite production build | Passed | Same directory, `frontend_build.log` |
| Scoped Ruff | Passed | `.venv/bin/ruff check apps/casecouncil-api packages/contracts/src/contracts/casecouncil.py tests/test_casecouncil*.py tests/support_casecouncil_process.py scripts/*casecouncil*.py` |
| Entire monorepo regression with actual NATS and HTTP-process flags | **619 passed, 0 skipped** | `var/validation/casecouncil-full-regression-2026-10-19-final.xml` |
| Final actual installed-Codex smoke | `draft_ready`, **8 calls**, 8 known receipts, all tools audited, no unavailable stages | `var/validation/casecouncil-engineering-smoke-2026-10-19-final/report.json` |
| Browser discovery | No browser available (`[]`) | Interactive UI/accessibility gate remains unexecuted |
| Windows/tunnel installation | Not performed | Packaging/configuration only |
| Actual case corpus / independent semantic acceptance | Not performed | G0 source authority remains blocked |

The collector's report explicitly records `engineering_checks_passed: true`,
`real_data_validated: false`, `full_product_accepted: false`. Its engineering-only
exit zero is **not** release acceptance. Actual HTTP tests use controlled provider
responses to verify process boundaries, not the real Codex model. The actual model
smoke is separately identified and uses original fictional material only.

Final actual-model receipt totals: **86,552 input tokens; 2,391 output tokens**.
Input is the provider's reported input (cached tokens are a subset, not added).
These are not dollar costs or a price promise. Packet hash:
`4bf441443fa2fb3c251fc118f733d01ea8c0bf91bdb4e2595ed889c8ed64ef2a`.
All runtime artifacts under `var/` are local/ignored, not a committed dataset.
Earlier smoke `...-v1` and process `...-v1.xml` were retained, not overwritten.

## TDD and defects found

Focused failing tests preceded the contracts, deterministic consensus, evidence,
store, protocol, runtime, API and evaluator implementations. Tests were rerun after
the implementation and during refactoring. This is not a claim that every styling
line had a prior failing test or that engineering fixtures prove domain accuracy.

Concrete red-to-green hardening cases included:

- Candidate missing evidence could be dropped by otherwise-valid ballots: winning
  candidate gaps now survive aggregation and block an unqualified recommendation.
- A repeated owner policy mutation could fail on its old revision: idempotent
  request replay now precedes the mutation inside the same authorized transaction.
- Pending unreceipted usage could permit another call: a global reservation guard
  blocks further invocation until usage is settled/reconciled.
- Four expired claims could lose the usable partial work: available checkpoints
  now form a clearly manual-required packet with no invented consensus.
- Corrupt exhausted checkpoints could cause endless recovery failures: a regression
  now requires terminal failure plus workspace hold, without publishing corrupt text.
- The parser's POSIX address-space limit failed on macOS: a real generated-PDF
  subprocess test caught this. Linux retains the limit; macOS/Windows keep bounded
  process/time/input/text limits and explicitly require further hard-memory isolation.
- Unbounded child stdout could exhaust memory: actual child overflow/cancellation
  tests now cover streaming limits and owned-process cleanup.
- A terminal job without a packet could display “Review in progress”: a failing
  frontend state-label test now requires explicit failed/stale/cancelled labels.
  The combined collector reran all product tests and built the UI after this fix.
- Changed authority/rights, snapshot or frozen registry corruption, cancelled runs,
  late provider failure after replacement, journal drift and restored old stores
  cannot silently publish or reset known/unknown liabilities in the tested cases.

Six real child-crash checkpoints cover proposal, critic, registry, ballot,
consensus and synthesis. Another crash test dies after reservation, retaining the
unknown liability without blind replay. The eighth process test starts an actual
loopback API and separate controlled worker, authenticates, schedules and polls a
run, checks unapproved export, built assets and response security headers.

Evidence tests include exact Unicode offsets, selected-span membership, altered
quotes/hashes, best-effort redaction, partial large text, unsupported inputs and
actual text/encrypted/blank PDF child parsing. Baseline tests exercise real
controller paths (`single`: 2, `vote_only`: 7, `single_refine`: 11 normal calls) and
prove that an evaluator gold canary is absent from every captured prompt.

## Reproduction and interpretation

Product suite/build were collected with:

```sh
CASECOUNCIL_PROCESS_TEST=1 .venv/bin/python scripts/accept_casecouncil.py \
  --engineering-only \
  --runtime-smoke var/validation/casecouncil-engineering-smoke-2026-10-19-final/report.json \
  --output var/validation/casecouncil-engineering-2026-10-19-final-combined
```

Choose a new directory for another run. Full regression used
`BUILDRELAY_PROCESS_TEST=1`, `CASECOUNCIL_PROCESS_TEST=1` and an existing local NATS
2.15.1 test binary through `BUILDRELAY_NATS_BINARY`; it neither installed nor changed
the production broker. The final suite emitted six upstream deprecation warnings
(Starlette/httpx and PyMuPDF/SWIG); tests did not fail. No dependency-wide migration
or unrelated product rewrite was made to suppress them.

## Explicit limits and next phase

Not verified: semantic correctness, prospective completeness, calibration,
independent reviewer agreement, debate's incremental benefit, commercial demand,
browser-to-export interaction/accessibility, Windows process-tree isolation,
reboot/sleep/network/disk/load behaviour, protected Cloudflare ingress or production
security. No screenshots or actual-host results are implied by an asset build.

The UI and evaluator are implemented, but current metadata uses a versioned
`protocol: v1` binding rather than proving a reproducible upstream model-build
identity. Capture the actual deployed model/profile and code revision before
freezing any real-data benchmark. Redaction is best effort, not de-identification
certification; operators must inspect the full approved preview.

The next phase requires source authority, approved egress and independent domain
reviewers. Audit the actual inventory first, establish exclusions/splits and lock
the gold isolation, then run explicitly bounded development and held-out baseline
campaigns. Do not substitute authored fixtures for that work. Study guide and blog
follow that validation, grounded in actual outcomes and remaining failures.
