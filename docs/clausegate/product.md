# Product: the NDA exception-approval desk

Status: implemented pilot, 17 October 2026; commercial positioning remains a proposed hypothesis. ClauseGate is a working name, not a cleared trademark. Workflow validation and willingness to pay are unproven.

## Buyer and job

Initial buyer hypothesis: a small in-house legal/operations team or fractional counsel supporting businesses that repeatedly receive third-party English-language NDAs but do not want a full contract-lifecycle platform.

Job: “Help me resolve the terms outside our approved positions, know who owns each decision, and ensure the internal packet reflects the exact agreement those people reviewed.”

Requesters are business staff; authorized reviewers own clause interpretations and exceptions. A designated final reviewer owns the internal approval packet. Product roles are access grants, not proof of professional legal qualifications.

## Proposed paid outcome

Reduce active review minutes and unowned approval waiting, while preserving or improving critical-exception detection. The purchase hypothesis is a team/workspace subscription or managed self-hosted installation with configured playbooks and reviewer roles. Price, sales cycle, adoption and support cost require customer discovery; no invented market size or validated revenue claim.

The product sold is a decision workflow, not merely clause extraction, a summary, an LLM chat or an “Approve” button. It should answer: what exactly needs a decision, why, by whom, against which source/policy, what changed, and what is still blocked?

## First-release workflow

1. Owner configures an explicitly approved playbook, hypotheses/checks, missing-data rules and reviewer authority. Draft rules cannot silently become active.
2. Requester creates a case, identifies company side/purpose and uploads a third-party NDA. Incomplete business context remains unknown rather than inferred.
3. System extracts a revisioned canonical text, records coverage and proposes source-grounded findings. Document instructions are untrusted data.
4. Deterministic policy and uncertainty evaluation identify blockers, mandatory exceptions and clarification needs. No policy match is not equivalent to approval.
5. System atomically persists waiting state and targeted requests. It stops consuming model calls while a person is deciding.
6. Reviewer opens exact passages in context and confirms/corrects an interpretation, supplies a fact, requests changes, approves a permitted exception or rejects. Decisions need rationale and applicable bounds.
7. Resume revalidates all dependencies and reviewer authority. New interpretation facts trigger reevaluation; an exception approval does not override unrelated rules.
8. Final reviewer signs off an exact internal packet revision. Export labels approval scope and unresolved/partial coverage. No signature or counterparty transmission is performed.

Example scenario is illustrative, not a legal recommendation: a retention exception is found, but its applicability is ambiguous. The requester clarifies intended data use; an authorized reviewer assesses the clause and either requests revision or accepts a bounded exception. A revised NDA invalidates affected decisions. The AI cannot turn “retain a backup copy” into a statement that retention is universally acceptable.

## Initial scope

English-language third-party NDAs; source-linked checks grounded in an administrator's playbook; PDF/text intake; internal evidence review; scoped approval queue; durable pause/resume; explicit delegation; revision-aware packet export; audit verification and safe recovery.

Native text PDFs and text imports are the first supported intake targets. Scanned/encrypted/malformed documents must be visibly rejected or marked incomplete pending an explicitly supported OCR capability. Do not silently treat partial extraction as the whole agreement. JSON dataset text validation is separate from PDF layout/OCR validation.

All cases require final human packet review in the first release. Clear findings can progress to packet preparation without per-finding review only under explicit policy; the agent never grants legal approval. Hard-block rules cannot be waived by an ordinary reviewer. A later authorized playbook revision creates new analysis, not retroactive permission.

## Non-goals

- Autonomous signing, e-sign integrations, legal opinions, enforceability certification or jurisdiction advice.
- General contract drafting/redlining, Word tracked changes, email/Slack ingestion or sending.
- Arbitrary internet document fetch, CRM/CLM replacement, unsupervised agent tools or payment actions.
- Inferring organization policy, signatory authority, commercial context or reviewer qualification from a contract.
- Learning a shared policy automatically from one person's exception decision.

## Positioning and competition

Juro and Ironclad already address playbooks and approval workflows; features alone are not defensible differentiation. Proposed wedge: narrow NDA setup, transparent source/decision binding, modest self-hosted footprint and easy internal handoff without full CLM migration. Whether buyers value those attributes must be tested. Self-hosting is not a claim of offline LLM inference or zero data egress.

## Commercial experiment

With explicit consent, recruit three target teams for discovery and at least two for a measured pilot. Use their approved playbook and separately authorized/redacted NDA cases; a qualified reviewer establishes critical exceptions independently. Compare paired manual versus assisted tasks in counterbalanced order. Record active review time, elapsed wait separately, missed critical issues, corrections, approval reversals, setup effort and willingness to pay. Do not contact anyone or upload customer contracts during the docs stage.

Provisional usefulness target: median active review-time reduction ≥25% over at least 20 paired tasks across at least two teams, with no increase in adjudicated critical misses. These are decision targets, not observed results or statistical guarantees. Failure to improve workflow is a product failure even if the model matches a dataset.
