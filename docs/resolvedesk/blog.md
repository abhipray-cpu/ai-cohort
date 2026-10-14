# Day 2: Building a RAG Chat That Has to Show Its Evidence

_Part of my 14-day, 12-AI-product challenge. Written from the implementation and validation results recorded on 14 October 2026._

A PostgreSQL support question can look deceptively simple:

“Can my pg_dump 16 client back up a PostgreSQL 17 server?”

A language model can produce a fluent answer immediately. But a support engineer needs more than fluency. Which version of the documentation supports the answer? Does the advice distinguish the client from the server? Can the engineer inspect the relevant paragraph? And what happens when the next message is simply, “Does that rule also apply to 16?”

Those questions shaped ResolveDesk: a conversational RAG product for PostgreSQL support, built as Day 2 of this challenge.

The objective was four concrete behaviors: retrieve context, generate answers with sources, flag low confidence, and fall back to search. The interesting work was making those behaviors observable and testing when they failed.

## A chat product, not just a RAG function

The initial implementation made an important product mistake. It offered a ticket investigation workbench when the intended primary experience was RAG chat.

The underlying pipeline already retrieved passages and generated cited replies, but that did not make it the conversational product I wanted. A user should be able to ask a question, inspect the evidence, and continue the conversation without creating a support case or navigating an approval workflow.

The correction made chat the default screen. Conversations persist. Follow-ups retain bounded recent context. Each new message triggers fresh retrieval and gets its own answer and evidence. Knowledge management and customer-reply review remain useful secondary tools.

That distinction matters: implementing a technique is not the same as delivering the intended workflow.

## Conversation history and evidence have different jobs

For a follow-up such as “Does that rule also apply to 16?”, the system first needs to understand what “that rule” means.

ResolveDesk uses a schema-validated contextual resolution step to produce a standalone retrieval question and documentation-version scope. It carries known environment details forward without treating a documentation comparison as a change to the actual server.

But conversation history is not evidence. A previous assistant answer can be wrong. Its presence in a thread must not promote it into trusted knowledge.

The conversation supplies meaning; retrieved documentation supplies authority. Every turn must earn its citations again. Earlier answers keep their own evidence snapshots, so asking another question does not rewrite their provenance.

## RAG does not have to start with a vector database

The target deployment is an older Windows laptop acting as a service host. I started with SQLite FTS5 and BM25 retrieval instead of adding an embedding service and vector database immediately.

PostgreSQL support questions often contain precise terms: `pg_dump`, `pg_restore`, `sslmode`, or `pg_upgrade`. Lexical retrieval is a useful baseline for that domain, and the smaller runtime fits the deployment constraint.

This is still retrieval-augmented generation. The defining feature is that generation receives retrieved external evidence, not that the retriever uses vectors.

It is also a baseline, not a claim that lexical search always wins. Semantic or hybrid retrieval would need to justify itself through measured recall improvement and host cost.

The initial corpus contains 16 checksum-frozen official documentation pages: eight selected topics each for PostgreSQL 16 and 17. Sources are normalized into immutable snapshots and passages, with version metadata and section information. Each investigation pins an index revision.

The context budget is bounded. Relevant knowledge somewhere in a source collection is useless if the needed paragraph never reaches generation.

## Citations are a contract, not a finishing touch

Instead of accepting arbitrary prose followed by a list of links, the model returns structured claims. Each material claim has a version and one or more passage citations with exact quotes.

Pydantic supplies the output contract, and the provider receives JSON Schema derived from that contract. The application still validates the returned output independently.

It checks that a citation refers to a passage supplied to that run, that the quote belongs to its text, and that the claim's version agrees with the cited evidence. A claim applying to both supported versions needs evidence for both.

The UI resolves source links from stored passage records. Engineers can inspect the quote and surrounding passage instead of trusting a model-written URL.

However, quote membership only establishes provenance. A real quote can still be interpreted incorrectly, stripped of a caveat, or applied to the wrong situation. ResolveDesk therefore performs a separate advisory support assessment.

That assessment uses the same model provider. It is another useful check, not independent proof. Human-reviewed evaluation remains necessary before making strong answer-quality claims.

## Low confidence should change the behavior

I did not want an uncalibrated “92% confident” badge.

ResolveDesk instead exposes evidence states: supported, partial, conflicting, or insufficient. Missing details can lead to clarification. Unresolved questions can be escalated. Incomplete runs remain visibly incomplete.

This was tested with deliberately difficult inputs. An ambiguous first message needs a question, not a guessed diagnosis. Public PostgreSQL manuals cannot establish a private customer's contractual recovery promise. Historical PostgreSQL versions outside the pilot scope should not receive an answer dressed in version-17 citations.

The absence of a confident answer is sometimes the correct product outcome. The important question is whether the system explains its limit and offers a useful next step.

## Real data found bugs that mocked search did not

The most useful validation failures were not dramatic model hallucinations. They were ordinary retrieval and integration details.

First, a question naming both `pg_dump` and `pg_restore` retrieved only the dump manual. The answer was supported by that source, but restore-specific context was being suppressed by a preference for the first recognized utility. A failing real-corpus regression reproduced the issue. The retriever now considers all named utility pages before BM25 ranking.

The harder problem appeared when local authentication documentation lacked the detailed `pg_hba.conf` record-matching rule. That was exactly the situation where search fallback should help.

Initially, the system safely returned insufficient evidence. It did not invent the missing rule, but it also did not recover.

Three details explained the failure. The privacy-safe search vocabulary dropped the topic name. The adapter stopped after receiving any official results, even unrelated release notes. And the PostgreSQL site's search behaved differently for `pg_hba` and the full configuration filename `pg_hba.conf`.

Actual query comparisons revealed the spelling issue. The fix preserved the approved public topic, used its fixed canonical filename, continued to a bounded second query when the reference page was absent, and ranked discovered reference pages first.

No arbitrary user-supplied filename or private hostname was added to the outgoing query. Search still remained constrained to approved official versioned documentation, and results still had to be fetched and validated before they could support an answer.

The final weak-evidence test started with local passages, assessed their insufficiency, fetched the missing official page, and regenerated a cited answer. It completed in 48.68 seconds using five model calls.

“Search returned results” would have missed the problem. The real acceptance condition was that the needed fetched evidence actually supported the answer.

## What passed—and what that means

The final complete real-model matrix passed 11 scenarios across 12 chat turns. It covered backup and follow-up scope, restore, connection security, upgrade checks, general questions, ambiguity, private-policy abstention, unsupported versions, two search-recovery paths, and an injected search outage.

All 16 source-page retrieval checks passed. The final run generated 23 claims with 31 citation references, all passing structural passage, quote, and version checks. The wider repository suite passed 89 Python tests; five frontend presentation tests verified truthful confidence and search labels. The web build and lint checks passed too.

Actual HTTP checks exercised persistent chat, duplicate-send idempotency, citations, the worker, served assets, and the optional clarification/export workflow. A backup/restore drill preserved the application's then-existing conversation and all 18 stored source snapshots.

These results are functional evidence, not an accuracy percentage. The evaluation questions are adapted and their expectations are provisional, not independent human gold. Source-page coverage is not passage Recall@5. The outage test is explicitly fault injection, not an observed public-service outage.

Earlier failures remain recorded. A corrected test expectation also stays explained: the version-16 client manual validly supports that client's compatibility rule, so requiring only version-17 citations was too narrow.

## The engineering around the model still counts

Chat turns are durable jobs. Message submission uses idempotency keys and an expected turn count. Pending-turn guards prevent interleaved work in the same conversation. Checkpoints retain useful progress, and retries cannot rewrite an older turn after a later message has already used its context.

The product invokes an installed Codex CLI through a provider adapter; it does not call a model API directly. But a locally installed CLI does not mean offline inference. Codex still requires authentication and model-service network access. Official-source search is another network dependency.

The intended Windows host runs the application, worker, and SQLite data. Cloudflare should expose only the protected application endpoint, not the Codex runtime or database.

There are still release gates. No browser was connected for visual and interaction acceptance. Windows reboot/service identity and protected Cloudflare deployment remain unvalidated. Actual database-error reproduction and an independently reviewed quality benchmark are still open. The serial worker also means queue latency must be measured separately from model-call latency.

## The lesson I am carrying into Day 3

The valuable part of this build was not getting a model to answer PostgreSQL questions. It was making the system accountable for where its answer came from, what it could not establish, and whether recovery actually worked.

A chat interface is not enough. A citation is not proof. Search results are not evidence until the pages are fetched and used. A passing mocked test is not a live integration test. And a successful functional run is not production readiness.

That is the standard I want the rest of this challenge to follow: build the product experience, test with actual sources, preserve failures, and make the limits as visible as the answers.

---

Implementation and test evidence: [validation record](validation-2026-10-14.md), [architecture](architecture.md), [study guide](study-guide.md), and [replay commands](data-and-evaluation.md). The technical knowledge comes from versioned [PostgreSQL documentation](https://www.postgresql.org/docs/), including the [pg_dump manual](https://www.postgresql.org/docs/16/app-pgdump.html) and [pg_hba.conf reference](https://www.postgresql.org/docs/17/auth-pg-hba-conf.html).
