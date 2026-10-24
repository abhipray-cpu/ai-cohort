# Dependency-ordered TDD implementation plan

**Implementation phases through local lifecycle are implemented.** The API, worker,
web and restricted native parser have local fixture/process evidence. Browser
interaction is still unverified because no browser is connected. Initial actual
public-source integration has passed after handoff; broader corpus/independent-label,
provider, consumer and target-host acceptance phases remain open.
See [TDD evidence](tdd-checkpoints.md) and
[measured status](implementation-status.md); the phase table is not a pass claim.
For each slice: write a meaningful failing test, run and retain the red,
make the smallest coherent implementation, run green, refactor, then expand
integration/browser proof. Do not claim a prose checklist or an unexecuted test is
TDD. Retain actual commands, failures and changed test/code paths.

| Phase | Write red tests for | Planned deliverable / requirement |
| --- | --- | --- |
| 0 scope/capability freeze | Unsupported source/rights/jurisdiction, absent authority, fake source freshness | Reviewed inventory and parser/auth/host feasibility spikes; G0 |
| 1 schemas and pure rules | Unknown vs false, types/units/Decimal, boundaries, condition precedence, unsupported claims | Bounded contracts, provenance, evaluator; FR-02/03/11 |
| 2 identity and store | Two-household IDOR, composite FK scope, stale writes, helpers/CSRF/invites | Dedicated store, sessions, case-scoped roles; FR-09/12 |
| 3 intake and correction | Bad PDFs/images, limits, OCR confidence, wrong vehicle, current vs repair mileage | Restricted real parsers, fact/source revisions, manual input; FR-01 |
| 4 public sources and registry | Redirect/SSRF/429/404, duplicate family/revision, bulletin vs coverage | Allowlisted capture, review/activation, frozen index; FR-02 |
| 5 investigation lifecycle | Material question, unknown/deferred/resume, conflict, counter reset, late failure | Checkpointed bounded casework, source checks and partial drafts; FR-03/04 |
| 6 drafting and verification | Invented diagnosis/payment, invalid citations, omitted exclusion, bad tool output | Typed ports, constrained draft/independent checks, validation history; FR-05 |
| 7 packet and approval | Render/attachment mismatch, superficial redaction, recipient edit, stale/revoked approval | Actual safe PDF render/preview, manifest, owner approval/download; FR-05/09/12 |
| 8 response and outcomes | Refusal vs records request/partial approval, duplicate payment, currency/reversal | Response mapping, factual follow-up, attributed outcome ledger; FR-06/11 |
| 9 timeline and reminders | User-reported send vs delivery, invented deadlines, sleep/clock/expiry | Timeline, next action, reminder provenance; FR-10 |
| 10 monitoring and revisions | Missing consent, new historical programme, cosmetic/material change, duplicate inbox | Scheduler, review/diff/invalidation/rematch/outbox, consent revoke; FR-07/08 |
| 11 privacy and recovery | Delete during call, cached/blob/export leaks, restore resurrection, orphaned files | Household export/erasure, grant revocation, real crash/restore; FR-12/all |
| 12 consumer web flows | Upload/correction/unknown/no lead, source drawer, review approval, response, monitoring | Complete mobile/desktop UI and accessibility; all FRs |
| 13 owned lifecycle | Port conflict, unsafe process stop, absent secrets, startup paid calls | Additive Make/Windows launch/service/runbooks and no side effects |
| 14 public-source validation | Corpus manifest/labels/split/rights, leakage, counts and critical fail gates | Authorized acquisition, frozen offline evaluation; G2 |
| 15 bounded actual inference | Fake/cache pass, unrecorded failure, exceeded calls, useful partial result | Newly authorized smoke then locked campaign, honest attempt report; G2 |
| 16 consumer/host acceptance | Consent/real-case attribution, actual browser, Windows auth/tunnel/restore | G3–G5 artifacts; no substitution with public-only tests |
| 17 learning cadence | Unsupported success claims, wrong code links, omitted failure denominators | Study guide and one blog after measured checkpoint |

Implement vertical UI/API slices early instead of leaving interaction discovery to
phase 12; that phase completes integrated acceptance. All twelve features, including
monitoring, are required before calling the scoped implementation complete.
Actual-data acceptance follows implemented/testing-ready workflow; read-only source
feasibility can happen earlier without being called end-to-end validation.

## Candidate test organization

Proposed `tests/test_repairclaim_contracts.py`, `_coverage.py`, `_scope.py`,
`_ingestion.py`, `_sources.py`, `_casework.py`, `_packets.py`, `_responses.py`,
`_monitoring.py`, `_outcomes.py`, `_privacy.py`, `_recovery.py`, `_api.py` and
`_validation.py`; frontend domain/components and browser acceptance suites.
Names are design suggestions, not existing files or a mandate to split tiny tests.
Use injected clocks, providers and source servers for fault tests; actual processes,
parsers, browser and separately authorized provider runs prove real integrations.

## Integration and change discipline

Do not mutate old applications/services/data, existing `.env`, authentication/model
settings or providers. Extend shared contracts/helpers additively with compatibility
tests. New dependencies need reviewed licenses/security and Windows feasibility.
No setup command claims a live service exists until verified. Product-specific
campaign authorization is separate from implementation authority and prior products.
Maintain the requirement matrix and actual implementation map as code appears.
