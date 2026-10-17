# Premium approval workbench and browser acceptance

Status: React workbench implemented; frontend state/build and live HTTP tests pass. Screenshots/keyboard/accessibility/responsive/two-browser acceptance remain unrun because no browser was connected. [Actual UI/deviations](implementation-and-operations.md), [validation](implementation-validation-2026-10-17.md). Use the existing monorepo visual language where helpful, but keep the NDA decision workflow distinct from a generic chat transcript.

## Primary layout

Desktop: a compact left rail for case/inbox views; central original-document reader; right decision panel with finding, policy and precise question; a lower collapsible chronological audit drawer. The review target remains visible while the person decides. On narrower screens, use clearly labelled Document/Decision/History tabs without hiding blocker counts or the active revision.

This is a proposed layout, not a screenshot:

```text
+----------------+---------------------------------+---------------------------+
| My approvals   | NDA name / revision / coverage  | Decision request          |
| Waiting cases  |                                 | Why human input is needed |
| Due / overdue  | Original text                   | Source and policy links   |
| Review-ready   | Highlighted support + exception | Required role / expiry    |
| Playbooks      | Neighboring paragraphs          | Typed response + rationale|
+----------------+---------------------------------+---------------------------+
| Revision changed / blocked count / scoped audit timeline / current packet  |
+---------------------------------------------------------------------------+
```

## Required views

| View | Required behavior |
| --- | --- |
| Case/inbox | Scoped assignment, urgency/age, request kind, document revision, pending blocker count; no unauthorized case metadata |
| Intake | Company side/purpose, source type, approved playbook, egress choice, supported-input limits and parse coverage |
| Review reader | Source-linked passages, broader surrounding context, page/text fallback and explicit evidence gaps |
| Decision panel | Interpretation versus policy deviation, why escalation occurred, permitted response types, scope/rationale and current authority |
| Context update | Typed missing facts or corrected interpretation; comparison showing what becomes invalid |
| Progress | Distinct analyzing, waiting, overdue, expired, stale, provider-unavailable, rejected and ready-for-final-review states |
| Playbook admin | Draft/active revision, supported checks, authority/quorum, hard blocks; no silent activation |
| Final review/export | Exact packet/source/policy/context versions, approvals and limits; blocked until current required reviews complete |
| Audit | Request/decision/resume lineage, changes/reasons, verification assurance and anchor gap; not a raw prompt viewer |
| Erasure | Affected-artifact preview, typed confirmation, downloaded/backup limitations and receipt |

## Decision interaction

Do not preselect approval. Present permitted options with neutral labels: clarify, correct interpretation, approve the stated exception, reject or request revision. The server owns allowed choices and final authority. An exception action must show the exact policy deviation and scope it accepts; a clarification cannot silently become approval.

Require rationale and necessary structured fields, mark errors next to controls, retain an unsent form locally only within safe session policy, and warn clearly when it becomes stale. No hidden bulk approval. Requester and reviewer cannot impersonate each other through a role dropdown; testing requires separate identities/sessions. Who can act and why is visible without exposing unrelated memberships.

Waiting is not an endless spinner. Show “Waiting for legal reviewer — 2 of 3 required decisions outstanding,” latest checkpoint and next owner action. Overdue does not mean denied or approved; expiry has distinct semantics. Resume controls say “Revalidate and continue,” never “Force approve.”

## Version changes and sync

Proposed two-second scoped polling/events with revision and restore epoch. On document/playbook/context/authority change: show a persistent changed-context banner, mark old decisions/packets stale, disable submission/export, preserve unsent comment visibly for deliberate review without resubmitting it automatically, and load a comparison. Reconnect/restore forces authoritative refetch; cached status is not permission.

Source text and model/human content render escaped with clear labels. Evidence buttons take the user to original context, not an AI-generated paraphrase. Do not call AI rationale “verified” or use a green confidence badge as legal clearance. Uncertainty, complete supported absence, unassessed coverage and provider failure must look different beyond color alone.

## Browser acceptance

At minimum test 1440×900 desktop, 1024×768 compact desktop and 390×844 mobile. Keyboard-only navigation, focus order/visible focus, reader/decision headings, accessible names, error association, screen-reader status announcements, contrast and zoom/reflow are mandatory. Use neutral premium typography/spacing, consistent status labels and deliberate empty/error/loading states; no unsupported “100% safe” visuals.

Required journey: requester imports a real NDA, submits with a fixture playbook, reviewer opens an assigned source-backed request in a separate authenticated browser session, requester supplies missing context, reviewer receives a stale-form conflict and reevaluates, then completes a valid exception decision. Resume revalidates, final reviewer signs off the exact packet, and a new document revision invalidates the old export. Repeat after API/worker restart and expiry/revocation.

Build/type/state tests and HTTP clients do not certify this journey. Record browser/viewport/tool version, actors/scenario IDs and actual screenshots without secrets. If no browser is connected, mark the gate blocked; do not replace visual acceptance with guessed screenshots or a passing API test.

We can run requester/reviewer roles together on public data without pretending to be qualified legal reviewers. Dataset label checks and qualified legal-quality review remain separate evidence.
