# Product specification

This specification defines the pilot scope. The core workflow is implemented; [implementation status](implementation-status.md) distinguishes demonstrated behavior from remaining acceptance gates.

## Customer and outcome

Buyer hypothesis: a database consultancy, managed service provider, or small SaaS company supporting PostgreSQL installations. User: a support engineer who repeatedly consults manuals and previous investigations to answer customer questions. Reviewer: the senior engineer responsible for approving uncertain or consequential advice.

The primary product outcome is a useful, evidence-backed answer in a continuing support conversation. Chat does not require creating a ticket or approving an export. Optional customer-facing replies still require review. Measure time to a useful grounded answer, follow-up resolution, correction rate, and escalation quality.

Competitors already offer knowledge-grounded support tooling; the proposed entry point is version-specific troubleshooting with inspectable evidence gaps. Validate this focus through five support-team interviews and a pilot before making market or revenue claims. See [research](research-and-sources.md).

## First supported domain

PostgreSQL 16 and 17: backup/restore, connection/authentication, and major/minor upgrade questions. Version selection includes server, relevant client utility, and OS; these can differ. Use versioned source URLs, not a mutable `/current/` manual as the authority for a pinned-version case.

A public historical ticket retains its original versions. A rewritten 16/17 variant is an adapted test, not an original customer ticket. Versions outside the initial scope are flagged; finding an official page through search does not automatically expand the supported product range.

## Core journey

1. Open chat and ask a question/error. Select server context or describe the environment naturally when relevant. General manual questions need no environment wizard. Conversation history persists across refreshes.
2. Retrieve passages from the approved, indexed source collection using environment filters. Preserve source URL, section anchor, version, and content snapshot.
3. Produce a reply draft and an internal investigation note. Material technical claims link to supporting passages. Ask focused clarification questions when the environment is underspecified.
4. Show `supported`, `partial`, `conflicting`, or `insufficient` evidence with reasons. Avoid numerical confidence until it has been calibrated against an independent benchmark.
5. If coverage is insufficient, search approved official sources with a sanitized public query, fetch relevant pages, and validate the new evidence. Show which sources came from search.
6. If sufficient support remains unavailable, prepare an escalation packet containing the question, environment, attempted sources, and specific missing information.
7. Ask a follow-up in the same thread. Resolve its meaning using recent messages, retrieve again, and attach that turn's own citations. Earlier answers retain their evidence. Human approval/export is an optional secondary workflow for customer-facing replies.

## Example acceptance case

Input: a PostgreSQL 17 server with a PostgreSQL 16 `pg_dump` client and a version mismatch error. The reply explains the documented compatibility constraint and cites the versioned manual. If the utility version is missing, request it and keep any diagnosis conditional. The expected rule comes from the [official pg_dump manual](https://www.postgresql.org/docs/17/app-pgdump.html), not an accepted community answer alone.

## Release scope

| First pilot | Later |
| --- | --- |
| Persistent multi-turn RAG chat, with secondary case review | Multi-tenant SaaS and billing |
| Approved PostgreSQL HTML documentation snapshots | Arbitrary web crawling and large PDF/OCR collections |
| Manually imported Markdown/text runbooks with explicit visibility | Automatic Slack, Zendesk, and email connectors |
| Typed retrieval, cited drafts, evidence labels | Autonomous remediation or command execution |
| Bounded official-source search fallback | Broad internet research across unreviewed publishers |
| Human approval, copy/Markdown/JSON export | Automatic sending of customer replies |
| Evidence and knowledge-gap history | Automatically promoting generated answers into trusted knowledge |

## Product rules

- Citation existence and exact quote membership establish provenance. They do not prove that the quote supports the claim or that the answer is complete.
- `supported` is a conservative evidence assessment, distinct from human approval. Store its reasons and verifier version.
- Missing client/server versions cannot be guessed. Where multiple versions matter, scope each claim accordingly.
- An answer based only on public sources cannot establish a customer's internal configuration, backup success, contractual SLA, or security posture.
- Conflicting sources must remain visible; a recent page is not automatically authoritative for an older product version.
- Private runbook evidence remains internal. Customer exports must not expose private URLs or excerpts without explicit reviewer authorization.
- Reviewer edits create revisions; subsequent generation never silently overwrites them.

## Acceptance

A support engineer can open a real case, inspect evidence, correct a reply, and approve an export. Unanswerable and version-ambiguous cases produce useful clarification/escalation. Search fallback must work with a real configured backend and clearly show an outage when unavailable. Quality, usability, latency, and Windows acceptance must pass the [evaluation gates](data-and-evaluation.md).
