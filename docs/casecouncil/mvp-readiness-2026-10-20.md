# MVP readiness — 20 October 2026

Follow-up: the user approved [irrecoverable incident closure](incident-closure-2026-10-20.md).
That policy is now implemented and the same-store real-model continuation has begun.
The [final continuation record](real-data-continuation-2026-10-20.md) now records all
six artifact sets and the one receipt that remains explicitly unverified.
The proposal/hold status below is the decision record **before** that approval,
not the current live state. External browser/domain/target-host gates remain open.

Status: **working engineering proof of concept, not an accepted customer MVP**.
The user's request to make it an MVP is the objective, not evidence it is achieved.
No release thresholds were lowered, new model campaign started, or existing safety
hold cleared during this follow-up.

## Completed follow-up

TDD introduced a mechanical campaign summary that distinguishes terminal packets,
full protocols, partial/failed results, pending IDs and unknown-usage calls. Empty
campaigns, duplicate/unselected results, missing roles/critic/ballots/synthesis,
unavailable stages and unknown/unaudited calls cannot pass. A full protocol can
still be low confidence or no consensus; that is not domain-quality acceptance.

`scripts/replay_casecouncil_http.py` now exits nonzero for an incomplete campaign.
Its historical `completed` compatibility field is explicitly labelled as terminal
packets, not passes. New progress output uses `terminal_packets`.
`scripts/verify_casecouncil_replay.py` recomputes completion from stored packets and
receipts, handles missing critics, and offers a new-only `--output` path to preserve
original campaign reports. It also exits nonzero for incomplete protocol coverage.
Neither command claims full product or independent semantic acceptance.

The original store was opened read-only for the recheck. No migration, receipt
rewrite, reconciliation, hold clearance, dispatch or new model inference occurred.
Artifact: `var/validation/casecouncil-mvp-recheck-2026-10-20-v1.json`.
Observed: six selected, three terminal packets, two full protocols, one partial,
three pending, 21 calls, one unknown receipt and 30 exact citations rechecked.
The expected exit status was 1, **not** a successful campaign exit.

The initial engineering acceptance attempt failed because the sandbox denied a
loopback socket (109 passed / 1 environment failure). Its artifact is preserved at
`var/validation/casecouncil-mvp-engineering-2026-10-20-v1/`.
The authorized loopback rerun passed frontend tests, production build and all 123
then-collected product Python tests, without skips, at
`var/validation/casecouncil-mvp-engineering-2026-10-20-v2/`.
Two further verifier regression cases were subsequently added; use the final
regression result below for the current code freeze.

Final regression: **658 passed, zero failed or skipped**, including **125
CaseCouncil Python tests**, with actual loopback/NATS fixture tests enabled.
Artifact: `var/validation/casecouncil-mvp-regression-2026-10-20-v1.xml`.
The focused campaign/verifier checks passed 17 tests. Frontend logic tests passed
5 tests and the production build passed. Scoped Ruff and `git diff --check` passed.
Six upstream dependency deprecation warnings remain; these are not validation of
real model reliability, Windows deployment or domain quality.

Browser connection was retried using the Browser skill. Setup reported no browser;
documented troubleshooting and discovery returned an empty list. No visual,
accessibility or interactive browser acceptance is claimed.

## Decision required: irrecoverable receipt incidents

The existing [recovery design](recovery-fix-2026-10-20.md) correctly refuses to
fabricate a receipt, guess zero usage or silently forgive a potentially unsafe call.
However, it requires independently verified supplemental usage and tool-audit
evidence. Such evidence is unavailable for the old failure. The original campaign
therefore remains held even though diagnostic recording has now been improved.

A usable service needs an explicit policy for **irrecoverable** incidents. The
following is a proposed decision for the owner, **not implemented or approved**:

- Retain the unknown receipt and full conservative reservation permanently.
- Require separate authenticated owner/operator incident approval, reason and
  evidence references, with explicit acknowledgement that usage/tool safety is
  unknown; never relabel it observed, known or safe.
- Establish that dispatch is stopped and the failed runtime is no longer live;
  quarantine suspect state. Explicit unsafe-tool or integrity incidents require
  separate investigation, not this path.
- Define a bounded risk allowance and cumulative accounting that cannot be reset
  by a new workspace, campaign, restore or repeated incident closure.
- Authorize any continuation separately under current source rights and original
  remaining call/stage/time ceilings. Preserve prior packets/checkpoints and
  report the incident and incomplete campaign in every acceptance denominator.

This would change the current fail-closed policy and risk assumptions. It requires
the user's explicit policy choice before design/implementation, threat review and
red/green failure tests. It is not a request to create a new workspace to evade the
hold, and a healthy subsequent model call would not resolve the old incident.

## Acceptance still requiring external evidence

1. Actual-model campaign completion and independently reviewed usefulness, including
   comparison against baselines. Source summaries lack full policy/case files;
   do not force qualified recommendations from missing evidence.
2. A connected browser for login, intake, debate, source navigation, maker/checker
   review, export, stale-context and responsive/accessibility acceptance.
3. The actual old Windows laptop and protected tunnel for account isolation,
   service restart, outage/recovery, resource limits and access-control checks.
4. Authorized prospective UK evidence and qualified domain review before making
   customer-facing UK decision-quality claims. Paid-pilot/commercial evidence
   remains distinct from engineering and deployment acceptance.

No study/blog success story or customer-ready claim follows from the fixes above.
