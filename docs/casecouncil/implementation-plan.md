# Dependency-ordered TDD implementation plan

**Engineering implementation executed under the subsequent user authorization.**
This is the original dependency-ordered requirements baseline, not a claim that
every phase's acceptance gate passed. See the [actual module map/runbook](implementation-and-operations.md)
and [verification record](implementation-validation-2026-10-19.md).
Browser, authorized real data, expert comparison and target-host gates remain open.

## Working discipline

For each behaviour: write a focused test, run it and retain its meaningful failure;
implement the smallest coherent change; run the test; refactor under regression.
Record red/green commands and evidence. Do not claim every CSS change had a prior
failing test or that fixture tests establish real-model quality.

Use dependency-injected provider, clock, storage and parsing boundaries. Deterministic
stand-ins test orchestration; actual provider/process/real-data runs remain separate.
Preserve dirty user work and unrelated products. Run relevant shared-package and
whole-monorepo regression after additive integration. No rewrite of previous products.

## Phases and exit criteria

| Phase | Failing tests first | Deliverable / exit condition |
| --- | --- | --- |
| 0. Feasibility and contracts | Rights/egress refusal, unsupported scope, strict ingress bounds | Resolve/record G0 for real acquisition; agree user scope and freeze schema/protocol defaults |
| 1. Deterministic consensus core | Fixed roster, invalid ballots, all vote/abstention patterns, conflicting remedies, stale registry, missing roles | Pure candidate/ballot/consensus functions with exhaustive/permutation tests; no model call needed |
| 2. Scoped durable store | Cross-client IDs, concurrent claim, revisions, idempotent grant, cancellation, expiry, stale-worker/error-handler rejection | Independent data root/schema, leased checkpoints and atomic audit; no API authority from client fields |
| 3. Source intake/evidence | Corrupt/scanned/encrypted/oversized PDF, duplicate quote, Unicode offsets, redaction/page-map gaps, unsafe names | Immutable source/extracted/redacted revisions, exact spans and honest coverage |
| 4. Runtime and accounting | Serialized preflight, environment restriction, forbidden tool event, timeout/unknown usage, grant exhaustion/restart | Restricted installed-Codex adapter wrapper, safe receipts, cumulative allowances and fail-closed circuit |
| 5. Proposer/critic protocol | Isolated first contexts, spoofed roles, malformed proposals/critique, bounded repair and unavailable participant | Three initial roles and non-voting critic with validated attempt-bound checkpoints |
| 6. Revision, registry, ballots | No repeated revision cycle, frozen candidates, blind votes, duplicate commitment, ignored dissent | At most one revision; exact registry/ballot bindings; deterministic aggregation integrated |
| 7. Synthesis and degradation | Invented facts, changed winner/conditions, lost dissent, late-stage timeout | Source-validated explanation or deterministic partial pack, never false consensus |
| 8. Auth/API and human review | CSRF, session/grant revocation, maker/checker, stale review/export, ambiguous repeat mutations | Scoped actual HTTP flows, attributed correction/override and exact-revision exports |
| 9. Workbench | State-derived domain tests, vote labels, no fake metrics, permissions, safe source highlighting | Premium responsive React desk; production build plus actual browser scenarios |
| 10. Recovery/operations | Real child crashes at each checkpoint, disk/lease faults, backup/restore quarantine, call-ledger integrity | Worker supervision, verified backup/restore, additive Make/launcher/Windows/Cloudflare plans implemented and tested |
| 11. Authorized real data | Manifest integrity, duplicate/split/leak checks, outcome canaries, gold isolation | Rights-cleared actual inventory and expert annotation; honest exclusions and locked inputs |
| 12. Actual model comparison | Bounded smoke, frozen baselines, all failure denominators and usage | Development/calibration/locked campaigns under explicit allowance; no quota failure counted as a pass |
| 13. Product acceptance | Browser-to-export actual cases, client isolation, target Windows/tunnel recovery, blind expert utility comparison | Measured gate report with failures and open items; only then study guide and single blog |

G0 blocks real corpus capture/evaluation; useful contracts/fixture engineering can
proceed after explicit implementation authorization, but should not conceal a source
feasibility failure. If rights/partner access cannot be secured, ask for a source or
product decision before presenting the full commercial build as validation-ready.

## Original planned file boundaries

Future app: `apps/casecouncil-api/`, `apps/casecouncil-web/`; contracts under the
shared contracts package with product-specific models; isolated `var/casecouncil`
runtime storage. Proposed tests named `test_casecouncil_contracts`, `consensus`,
`evidence`, `store`, `protocol`, `runtime`, `security`, `api`, `recovery`,
`http_process`, `evaluation` and browser flow coverage. These are planned names,
not existing files or collected test counts.

Acquisition/evaluation/acceptance utilities are explicit operator actions. They
must create new run directories, preserve failed baselines and report code/input/
policy/prompt hashes. No corpus downloaded during a normal unit test or first boot.
Never use evaluator labels in provider fixtures that are presented as real inference.

## Release-gate discipline

Implementation completion requires actual modules, passing code tests and an
explicit implemented-versus-designed mapping. Real-data-ready additionally requires
source authority, corpus/labels and a bounded campaign setup. MVP/pilot acceptance
requires the applicable [acceptance gates](validation-and-acceptance.md), including
expert judgement and target-host checks—not merely a working chat/debate screen.

Any deviation in scope, participant count, candidate equivalence, confidence logic,
input/egress limits or baseline policy must update the docs and tests before the
new behaviour is described as complete. Preserve observed defects and failed
campaigns rather than editing history into an uninterrupted success story.
