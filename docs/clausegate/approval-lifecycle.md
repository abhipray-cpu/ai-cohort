# Durable pause, human input and validated resume

Status: core lifecycle implemented and engineering-tested. This remains the invariant specification; [actual scope](implementation-and-operations.md) and [validation](implementation-validation-2026-10-17.md) distinguish delivered behavior from broader legal/product/browser/Windows acceptance.

## Three distinct human interactions

| Interaction | Human supplies | What it does not authorize |
| --- | --- | --- |
| Clarification | Missing business fact or corrected interpretation, with provenance | Automatic acceptance of every downstream term |
| Exception decision | Explicit acceptance/rejection of one policy deviation for bounded scope | Editing the underlying playbook or overriding hard blocks |
| Final packet review | Internal sign-off on the exact artifact and disclosed scope | E-sign, counterparty send or certification of legal safety |

Confirming an interpretation is not accepting its risk. Requesting a change is not approving the current document. Free-text “looks good” cannot substitute for a typed decision when an explicit exception is required. `NotMentioned` can be a supported semantic label; required missing context is a separate blocker.

## Workflow checkpoint

An analysis run pins case/document bytes and text hashes, extraction coverage, playbook ID/revision/hash, company side/purpose and other context revision, findings revision, uncertainty/policy version, actor-grant version and restore epoch. Stage output and model/prompt/schema versions are recorded. An analysis is not allowed to silently swap to a newer playbook mid-run.

When blockers exist, one transaction commits checkpoint, `waiting_human`, distinct requests, outbox/in-app notice and audit. Only then release the lease. A crash before commit leaves no half-created waiting state; a retry after commit finds existing request IDs. Polling/waking must not repeatedly create requests or incur model calls.

Persist requests per deterministic `(checkpoint, rule, finding, required_role, question_kind)` key. Multiple blockers can wait in parallel; one valid response does not clear the others. Dependent finalization is always blocked; independent analysis may continue only within the original declared coverage and grant.

## Request contents and ownership

Every request carries a precise machine-owned purpose, plain-language question, exact source passages and broader context links, policy excerpt/revision, uncertainty reasons, proposed interpretation, permitted response schema, request revision, current assignee/role constraints, created/due/expiry times and binding hash. Model question wording is optional explanatory text, not the authority that decides the response type.

Inbox visibility is scoped to current workspace/case grants. No reviewer available means unassigned/blocked with a visible owner task—not selection of any logged-in user. Initial notifications are in-app only. Reassignment/delegation requires authorized action, records scope/expiry, increments request/authority revision and stales incompatible outstanding decision forms. A requester cannot approve their own exception under the default separation-of-duties policy.

## Human response validation

Decisions are immutable records, not updates to the source or AI finding. Require authenticated actor, current capability, expected request revision, binding hash, idempotency key, explicit response type and nonempty rationale. Role grants and delegation must be valid now; role names submitted by the browser are ignored. Supplied business facts require their own type/range checks and provenance.

Responses: `clarify`, `confirm_interpretation`, `correct_interpretation`, `approve_exception`, `reject`, `request_revision`. Their allowed fields and actor capability depend on request kind. Store the proposed-versus-human value and reason. A correction creates a new finding/context revision and reevaluation; it is not a hidden rewrite of the earlier model response. Any changed binding reopens affected requests. In v1, conservatively invalidate all case decisions for a material document/playbook/context change; fine-grained reuse is future work and requires dependency proof.

For multi-reviewer rules, all specified independent roles must respond to the same checkpoint; a role grant cannot count as two independent people where policy requires distinct actors. A rejection blocks that checkpoint. Conflicting approved positions go back for authorized resolution; last-writer-wins is forbidden. “Approve all” is not a first-release endpoint. Hard-block rules remain non-waivable through the decision API.

## Scheduling and resume fences

After each decision, atomically recompute whether all active blockers are satisfied. If yes, create a single continuation intent keyed by checkpoint plus valid decision-set hash. A normal final-review requirement remains even after all exceptions clear. No need for the person to hold a browser session open.

Before claiming continuation, before any new model egress, and before committing a packet, verify:

1. Workflow is not cancelled/rejected/erased, and worker lease/deadline/usage reservation is valid.
2. Workspace/case, document bytes/text, extraction version/coverage and source digests still match.
3. Active playbook and business context revisions match the checkpoint. New business facts have been reevaluated.
4. Every required decision targets this request and binding, is the latest unsuperseded valid decision, and has not expired or been withdrawn.
5. Approvers still hold the required scope/role or valid explicit delegation, with separation of duties satisfied.
6. Findings and policy evaluation are current, blockers actually cleared, and restore epoch matches.
7. Model egress permission is current if another call is needed. Source interpretation or human consent does not grant egress by itself.

If any check fails, record a typed failure, invalidate dependent readiness and reopen/reassign requests or mark stale as appropriate. Never silently continue with yesterday's approval. Validation success followed by a dependency change is caught again by the final transactional fence.

## Waiting time, expiry and budgets

Human waiting does not consume a worker lease or model wall-clock allowance. Each active execution grant has its own immutable active-stage deadline and reserved call budget; cumulative workflow grants/calls remain capped. Resume does not reset past usage or create unlimited retries. Human requests have separate due/expiry times; due means overdue, expiry invalidates a decision/request as configured. Neither automatically approves anything.

Proposed defaults: two model attempts per stage including one repair, four calls per active grant, two explicit grants per document/playbook/context tuple; 600-second active deadline; ≤120 seconds per model call and remaining grant allowance. A revised source creates a new checkpoint, not a way to relabel old counters. Owner-authorized new grants are audited; UI exposes accumulated spend and remaining allowance.

## Races and recovery acceptance

| Event | Required behavior |
| --- | --- |
| Two decisions with the same expected request revision | One succeeds; the other gets conflict, unless it is the identical idempotent replay |
| Same idempotency key, different response | Reject conflict; never overwrite the original decision |
| Source changes after approval but before resume | Old decisions unusable; no current packet from old source |
| Reviewer grant revoked while worker builds packet | Final fence rejects publication and marks dependent readiness stale |
| Playbook changes while a person has the form open | Reject stale submission or require explicit resubmission after comparison |
| Worker killed immediately after request commit | Restart sees waiting state; no duplicate requests or provider calls |
| Worker killed after decision commit | Outbox replay schedules at most one effective continuation |
| Duplicate queue deliveries or stale worker | Idempotent writes plus lease token prevent duplicate committed effects |
| Restore older DB | Rotate epoch, expire sessions/leases and revalidate all restored approvals against current external authority |
| Provider unavailable after valid human response | Keep decision and evidence; publish no unsupported final approval; explicit partial/retry state |

See [audit/recovery](audit-and-recovery.md) for old snapshots, withdrawal and erasure; see [evaluation](data-and-evaluation.md) for required real-data and multi-person testing.
