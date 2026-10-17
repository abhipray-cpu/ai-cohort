# Product: investigation continuity for technical escalations

Status: proposal, 16 October 2026. Product name, positioning, price and buyer benefit are hypotheses. Market/source access observations do not establish willingness to pay.

## Buyer, trigger and paid outcome

Initial buyer: support lead or engineering manager at a small B2B software vendor or specialist technical-support agency with approximately 5–25 engineers. Trigger: an escalation changes hands, resumes after days, or reopens after a purported fix.

Job: establish the current reported environment, attempts and outcomes, corrected assumptions, unresolved contradictions, owners and explicit commitments without rereading several disconnected conversations or repeating failed troubleshooting.

Proposed paid outcome: a source-backed, reviewable handover plus an ongoing conversation that stays consistent as the investigation evolves. Value is reduced preparation/repeated-question effort, not another vulnerability scanner, generic chatbot, CRM or meeting recorder.

Positioning: **The next engineer starts where the investigation stopped—not where the ticket started.** Unlike ResolveDesk's documentation-based RAG, RelayDesk manages the changing state of a specific investigation. Unlike PatchDesk, it does not orchestrate security feeds or assess dependency upgrades.

## First workflow

1. Authorized owner creates an account and case; account identity is explicit, not guessed from usernames/email similarity.
2. Import a bounded conversation export or approved public GitHub issue/comments. Preview scope, source dates, edits, privacy and capture gaps.
3. System proposes source-linked episodic memories and structured investigation state. Engineer reviews consequential corrections/commitments; inferred suggestions are not verified facts.
4. Incoming engineer opens **Take over this case** and asks what is current, what failed, what changed and what remains unanswered.
5. Answer combines a short-term conversational buffer with relevant long-term memory and exact source evidence. It labels ambiguity, stale/index-pending state and missing coverage.
6. New turns and approved corrections create revision events. Other authorized sessions invalidate/reload stale context; drafts referring to revoked/erased evidence cannot be served as current.
7. Reviewer approves the exact handover revision for local Markdown/JSON/print export. The product does not send it to customers automatically.

## Memory categories that matter

| Category | Required distinction |
| --- | --- |
| Environment | User-reported versus independently verified; exact version/OS where supplied |
| Attempt | Proposed versus performed; action and attributable outcome stored separately |
| Workaround | Proposed / reported successful / failed / superseded / applicability unknown |
| Hypothesis | Explanation under investigation, not established root cause |
| Decision | Who explicitly decided, relevant case scope and effective interval |
| Commitment | Who explicitly promised what; dates/owners cannot be invented from vague discussion |
| Open question | Missing evidence, conflicting report or pending confirmation |

An engineer confirming that a message was faithfully captured does not certify the technical truth of the message. Historical facts remain inspectable but cannot masquerade as the latest state. Case closure is not proof of resolution; bot closure or duplicate labels are particularly weak evidence.

## First-release scope

Case list, scoped conversation, paired raw-source/memory views, Take-over handover, attempt/outcome timeline, versioned summaries, vector-backed recall with relevance explanation, correction/rejection, recall suppression/erasure workflow, multi-session freshness indicators and reviewed exports.

Start with English text, timestamps and plain logs represented as inert text. JSON conversation import and read-only GitHub issue ingestion are the only connectors. Case memory is default; account-wide memory requires explicit promotion with review and permissions. No automatic cross-case/customer linking.

Out of scope: customer-facing autonomous support, production commands, incident remediation, downloading attachments, executing logs/scripts, Slack/email/CRM write connectors, audio transcription, full ticketing, formal SLA enforcement, sentiment profiling and automated legal/commercial promises. Do not infer action authority from a remembered command.

## Commercial differentiation to test

The narrow hypothesis is that a correctable attempt/outcome ledger, environment applicability and current-versus-superseded memory make technical handovers more useful than ordinary ticket summaries. Do not claim competitors lack memory or cannot support this workflow: [research](research-and-sources.md) documents existing memory/account intelligence products.

Start by testing one recurring handover workflow, not a platform replacement. Proposed offer: **$99/team/month paid pilot**, with defined active-case/import/model budgets and explicit hosting/inference responsibilities. This is an experiment, not a researched market price or unlimited inference promise. Self-hosted service operations and availability need a supportable delivery model before selling.

Future customer discovery, only under separate authorization: five support leads, ten historical handovers per consenting team, measure time to an accepted handover and duplicate-question rate. Compare with their existing helpdesk and summaries. Target 30% less median preparation time without more material omissions. If existing tools already solve the need adequately or teams refuse the required data access, change/reject the positioning.

No outreach, paid integrations, third-party messages or sales commitments are authorized by this documentation work.
