# Voting, consensus and confidence

Target deterministic policy `casecouncil-consensus-v1`. A model never declares the
group's outcome. Voting is a structured recommendation mechanism, not a vote on
what the source documents say or on a person's legal rights.

## Issues and candidate identity

The handler confirms a revisioned issue registry at intake: e.g. coverage, premium
deduction, delay, communication and proposed service remedy. All proposers address
the same declared issues. Agents may suggest additional issues; material unassessed
suggestions are visible coverage blockers pending human confirmation/new snapshot,
not silently ignored or inserted into only one participant's ballot.

A candidate binds issue ID, substantive disposition, proposed action/remedy,
material conditions, supporting/contradicting evidence and originating proposal
revision. The server assigns IDs and freezes the registry after critique/revision.
Use exact canonical structured equality to merge duplicates with lineage. “Reject
the complaint” and “reject coverage but compensate poor service” are not one candidate.
Different compensation amounts/conditions are not collapsed into superficial agreement.

Issue dispositions: `uphold`, `partial_uphold`, `do_not_uphold`, `undetermined`.
These differ from workflow routing and from the source database's historical labels.
Every proposal includes an evidence-request/escalation option when a decision is
unsupported; “not enough evidence” is a valid outcome, not a failed forced choice.

## Ballot contract

Each of the three configured proposer roles has exactly one final ballot per issue,
bound to snapshot, registry, policy, critique and proposal revisions. A ballot is
either a known candidate ID or `abstain` with a reason and named missing evidence.
Role identity comes from the scheduled attempt, not a model-supplied identity.
No current vote totals or other ballots are disclosed before all ballots are committed.

Unknown candidate, duplicate role, stale registry, forged identity or invalid
evidence rejects that ballot with one bounded repair. A provider failure is
`unavailable`, not a valid abstention. The first committed ballot is immutable;
only an explicitly authorized new ballot-stage revision can replace a stage, and
aggregation cannot mix stage revisions.

## Aggregation algorithm

For each issue, in this order:

1. Validate the exact three-role roster and all bindings. Require all three ballot
   stages to finish with valid vote/abstention objects. A missing/unavailable role
   yields `insufficient_participation`, regardless of the other two votes.
2. Apply integrity, evidence, source-currentness and mandatory-policy blockers.
   Detect unresolved material critique, inaccessible decisive evidence, unassessed
   new issues and an incomplete revision cycle. Agreement cannot clear these.
3. Count candidate votes against the **fixed denominator of three**. Do not convert
   a 1-vote/2-abstention result into 100% agreement among the votes cast.
4. A candidate with at least two votes has `majority_agreement`; three gives
   `unanimous_agreement`. Preserve abstention, dissent and each candidate's conditions.
5. A 1–1–1 result, one vote plus two abstentions, or three abstentions is
   `no_consensus`. A two-vote majority with an unresolved decisive-evidence blocker
   is `agreement_blocked`, not a qualified recommendation.
6. Route unblocked supported agreement to `ready_for_human_review`. Route a resolvable
   missing fact to `request_evidence`; unavailable roles, serious conflicts, unsupported
   scope or unresolved disputes to `escalate`. No-consensus packs remain useful drafts.

Two matching votes and one valid abstention can form majority agreement, but an
abstention about decisive missing evidence still blocks qualification. Mechanical
policy may flag a missing item; the critic may propose a substantive blocker. Exact
citations establish traceability, not correctness of that proposed interpretation.
Unresolved material criticism requires human attention; “two models disagreed with
the critic” is not sufficient clearance.

Critique resolution states are `open`, `deterministically_resolved`,
`needs_domain_review`, `human_resolved`. A corrected nonexistent span/registry
reference can be verified mechanically. A proposer saying “accepted” does not by
itself resolve a substantive fairness/interpretation objection. Substantive critical
findings remain for an authorized reviewer; their resolution records evidence,
reason and exact packet revision. That human resolution does not rewrite the
historical automated blocker or convert disagreement into automated unanimity.

| Ballots / circumstance | Agreement result | User-facing consequence |
| --- | --- | --- |
| A / A / B, complete permitted evidence, no blocker | Majority, 2/3 | Review draft A plus B's dissent |
| A / A / abstain over a decisive missing policy | Agreement blocked | Request policy; no qualified conclusion |
| A / A / unavailable | Insufficient participation | Degraded/manual packet; no reduced quorum |
| A / B / C | No consensus | Escalation with alternatives; no artificial tie-breaker |
| A / A / A, stale input | Invalid currentness | Block publication and reauthorize current snapshot |

## Confidence representation

Persist separate fields, not one opaque blended score:

- `agreement`: voted count / fixed role count, vote distribution and abstentions.
- `evidence_coverage`: assessed/required issues and documents, partial/missing items.
- `critique_status`: unresolved findings and severity, accepted/contested responses.
- `execution_coverage`: stage validity, unavailable roles, revision completeness.
- `confidence_band`: `low` or `medium` for the initial uncalibrated pilot, with reason codes.
- `calibration_status`: initially `unqualified`; any later profile has independently
  verified dataset/split/model/prompt/policy bindings and revocation criteria.

`High` and a numerical probability are unavailable in the initial pilot. Unblocked,
fully assessed majority agreement can be medium. Any material omission, unresolved
conflict or degraded stage is low. All results require human review, including
unanimity. Do not average self-reported confidence or label 2/3 agreement as a
66.7% chance of correctness. Human approval also does not calibrate model confidence.

## Synthesis and human decisions

The synthesizer receives the frozen computed result, permitted source spans,
proposals and dissent. It may explain, organize next actions and draft wording;
it cannot change candidate IDs, disposition, remedy conditions, votes, blockers,
confidence band or review status. The server injects those authoritative fields.
Every factual synthesis claim must resolve to source citations or be explicitly
labelled a hypothesis/proposal, not a new fact attributed to another agent.

Invalid or missing synthesis produces a deterministic degraded pack from earlier
valid checkpoints. Never select the most confident proposer as a hidden fallback
winner. A human can correct/override the recommendation with evidence and reasons;
that is a separate attributed human decision, not retrospective automated consensus.
Changed sources or policies require a new snapshot and invalidate current-review
eligibility. Earlier decisions remain historical and cannot silently transfer.

Acceptance tests and counterexamples belong in [validation](validation-and-acceptance.md),
not only in prompt examples. Independent expert review is required to learn whether
qualified recommendations are actually useful and safe.
