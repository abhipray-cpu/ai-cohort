# Dependency-ordered test-driven implementation plan

Implementation is now authorized and underway using TDD. The sequence below remains
the target plan; [implementation status](implementation-status.md) records current
evidence and gaps. Actual-data/model validation begins after implementation.

## TDD discipline

For each behavioural slice, write a focused test, run it and retain a meaningful
failure, implement the smallest coherent solution, rerun and refactor under green
regression. Record red/green commands, failures, artifacts and code changes. Do not
claim every style change was TDD or that fake providers establish model quality.

Inject provider, clock, storage, parsers and external-source adapters. Keep pure
validation/selection independent of network/CLI. Use real process tests as well as
unit tests. Extend shared contracts/provider interfaces additively and test prior
consumers; no application-to-application imports or copying another product's store.

## Phases and exit evidence

| Phase | Red tests first | Deliverable / exit criterion |
| --- | --- | --- |
| 0. Scope/source freeze | Unsupported product/claim classes, missing facts, absent source/egress authority | Versioned protocol defaults, source registry and exact limits; no phantom data counts |
| 1. Strict contracts | Unknown fields, bad IDs, nonfinite decimals, span/reference bounds, stale hashes | Finite Pydantic wire/generation models and compatibility tests |
| 2. Intake/facts | CSV ambiguity/encoding, duplicate headers, GTIN zeros, null/zero, unit/basis conflict, ingredient order | Bounded CSV/JSON import, explicit mapping/freeze, immutable raw/typed facts |
| 3. Deterministic checks | Invented references, wrong numeric basis, prohibited claims, omitted required facts, Unicode offsets | Versioned fact/reference/profile checks and honest uncertain-coverage flags |
| 4. Rubric/selector | Invalid ratings/findings, missing dimensions, score gaming, ties, new critical defects, worse candidate | Pure score calculation, hard-gate precedence and incumbent/stop decisions |
| 5. Durable authority | Scope denial, conflicting idempotency, stale leases including failure writes, revisions/cancel | Independent Store, snapshots/checkpoints, audit, membership/session lifecycle |
| 6. Provider/accounting | Timeout/tool event/missing receipt, stream cap, reserve-before-call, restart/global hold, grant exhaustion | Restricted installed-Codex adapter, sanitized diagnostics and independent usage journal |
| 7. Execute/evaluate | Isolated judge context, whole-text checks, schema repair limit, version 0 provenance | Real controller stages with validated attempt-bound checkpoints |
| 8. Reflect/regenerate | Missing finding coverage, invented facts, source requests instead of fabricated fixes, third revision | All five concepts integrated; at most two revisions and 16 cumulative calls |
| 9. Degradation/recovery | Crash between each stage, unknown/unsafe incident, fsync/commit mismatch, exhausted resume, rollback restore | Useful partial artifacts, bounded explicit recovery and quarantined new-root restore |
| 10. API/review/export | Auth/CSRF, two-client denial, maker checker, stale review, inline edit reevaluation, spreadsheet injection | Real HTTP intake-to-reviewed-patch flow with unresolved manifest and no publish path |
| 11. Premium workbench | Domain-state tests, original/candidate/incumbent labels, source highlights, no fake score/probability | Responsive React desk; production build and actual browser/accessibility scenarios |
| 12. Monorepo/operations | Additive launchers, no credential/data reuse, process cleanup, backup health, limits | Tested Make/launcher/package integration, Windows/tunnel packaging; packaging not deployment acceptance |
| 13. Actual-data inventory | Archive/field/join integrity, grouping/leak tests, gold canaries, measured exclusions | Frozen actual source corpus and split/label manifest, no synthetic count inflation |
| 14. Actual provider evaluation | Approved six-product smoke, all stage observability, bounded baseline arms and receipts | Measured development/calibration/locked reports; failure and pending denominators preserved |
| 15. Product acceptance | Browser actual record, independent labels/utility comparison, actual Windows/tunnel/recovery | Explicit pass/open/fail gate report and implemented-versus-designed runbook |
| 16. Learning cadence | Evidence/source/link checks | Study guide and single blog after measured checkpoint; no advance success narrative |

Acquisition can occur after source/implementation authorization while deterministic
engineering proceeds; model egress requires its own exact payload/destination and
finite grant. Do not block all useful unit work on unavailable customer pilots,
and do not hide missing independent acceptance behind fixture volume.

## Planned repository integration

New application roots `apps/shelfproof-api/` and `apps/shelfproof-web/`; namespaced
contracts; `var/shelfproof` runtime root; explicit acquisition/evaluation/acceptance/
backup/recovery utilities. Test families: contracts, facts/intake, rubric/selection,
store, protocol, runtime/accounting, security/API, export, recovery, actual child/HTTP
processes, corpus/evaluation and frontend domain/browser scenarios. Implementation
now exists; see implementation-notes.md and implementation-status.md for the actual
module map, measured checks and still-unpassed browser/provider/deployment gates.

Add only ShelfProof entries to project metadata, Make, launchers, `.env.example`,
Windows packaging and protected tunnel example after code exists. Check port 8009
and all configured paths. Do not modify real `.env`, old service registrations,
existing data, prior product sources or unrelated dirty work without authority.

## Evidence to retain during implementation

- Actual module/interface map with design deviations and migration notes.
- Red/green examples and final JUnit/build/lint/browser artifacts, with skipped
  process tests clearly marked incomplete and all regression failures explained.
- Source/label/split counts and hashes, code/prompt/profile/rubric versions, grants,
  per-attempt receipts, holds, incidents and model identity evidence where available.
- Every original/rejected/final version, selection reason, gate/coverage outcomes,
  independent reviewer results, paired baseline comparisons and cost uncertainty.
- Target-host installation/restart/outage/restore and real two-client browser evidence.

Do not change rubric, nonregression, allowed claims, sources, channel, iteration cap,
budget semantics or review authority without updating design/tests and freezing a
new evaluated version. If business benefit is absent or evidence is too small,
record that result rather than retune the holdout into a pass.
