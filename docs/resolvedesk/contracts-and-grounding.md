# Contracts, citation grounding, and uncertainty

Contract version: `1.0`. Implemented Pydantic models forbid unknown fields, bound collections/text, and use explicit enums. Provider JSON Schema is derived from these contracts and returned JSON is independently validated. The records below include persisted dictionaries and typed model boundaries; see [contracts code](../../packages/contracts/src/contracts/resolvedesk.py).

## Input and source records

Chat-first additions: `ChatCreate`, `ChatMessage` and `ChatResolution` govern persistent conversations and contextual follow-ups. See [chat contracts and bounds](chat.md). History never substitutes for retrieved evidence. General documentation questions need no mandatory server/client values; diagnosis-specific ambiguity should be clarified.

| Record | Required meaning |
| --- | --- |
| `CaseInput` | Case ID, question/error, product, optional server/client versions and OS, revision, actor |
| `SourceSnapshot` | Source ID, canonical URL or internal reference, title, product/version, authority, visibility, fetched timestamp, content hash, parser version, immutable content location |
| `Passage` | Passage ID, snapshot ID, heading/anchor, exact extracted text, character offsets into normalized snapshot text, version scope |
| `RetrievalRequest` | Case/run ID, bounded query, environment filters, pinned index revision, permitted source visibility, top-k |
| `RetrievalResult` | Echoed request scope, ranked passages, retrieval method, rank/score metadata, index revision |
| `SearchRequest` | Sanitized public query, approved domains, product/version, result limit |
| `SearchResult` | Provider identity, query ID, result URLs/titles/snippets, retrieved time; snippets are discovery data |

Separate server version from client utility version. Unknown versions remain unknown. A snapshot's publication date and fetch date are distinct. Do not infer version applicability from URL text alone when source content disagrees.

The table is the complete target record vocabulary. Current snapshots persist URL, title, version, visibility, content hash, origin, creation time, normalized text and section metadata. Explicit publication dates, per-snapshot parser-version telemetry, and a separately typed retrieval-request/result envelope remain refinements; retrieved passages themselves are typed and checked against pinned stored records.

## Generated and reviewed output

| Record | Fields / behavior |
| --- | --- |
| `AnswerClaim` | Claim ID, text, category, version/environment applicability, citation list, uncertainty reasons |
| `Citation` | Passage ID, exact quote, optional validated character span; source identity resolves from the server's passage map |
| `AnswerDraft` | Schema version, claim list, ordered reply segments referencing claim IDs, clarification questions, proposed next checks, evidence assessment |
| `EvidenceAssessment` | `supported/partial/conflicting/insufficient`, reason codes, unresolved claim IDs, conflicting source IDs, assessor version |
| `AnswerRevision` | Run and case revision IDs, validated draft, source/index snapshots, generation metadata, status, parent revision |
| `ReviewAction` | Revision ID, accept/edit/escalate decision, actor, timestamp, reason, and replacement evidence where applicable |
| `ApprovedReply` | Immutable approved revision, final customer text, authorized citations, reviewer and provenance metadata |

The application renders material reply text from validated claim references. It rejects unknown claim IDs and technical assertions hidden in uncited free-text reply segments. Clarification and greeting text may be uncited if they contain no material technical claims. Private source URLs are never returned merely because a model emits them.

## Validation layers

1. **Tool arguments/results:** validate shape, bounds, request identity, source permissions, environment filters, and index revision before the result reaches generation.
2. **JSON and output contract:** reject malformed JSON, invalid enums, unknown fields, missing references, and oversized collections.
3. **Provenance:** every citation resolves to a passage supplied to this run; normalized exact quote/span belongs to that passage and snapshot. Citation source links are resolved by the server, not accepted from generated citation fields. A plain-text URL in generated prose is not independently validated and is not citation authority; use the source controls to inspect provenance.
4. **Applicability:** reject an answer that asserts a different product/version as applicable without an explicit supported comparison. Missing environment details become a reason for qualification or clarification.
5. **Support assessment:** evaluate whether the cited passage supports the claim, including caveats and negation. Deterministic identity/quote tests cannot establish entailment. Any model-based support verifier is advisory and must be scored against human labels.
6. **Approval:** a human reviews the final revision, citations, qualifiers, and unresolved issues. Editing material text invalidates earlier approval and requires rechecking the edited claims.

The term `supported` describes current evidence assessment; it is never an unconditional statement of truth. Conflicting and insufficient answers cannot be exported as a resolved customer reply. They can be exported as clearly labelled clarification/escalation packets. A partial draft requires explicit review of its visible limitations before approval.

## Confidence and fallback policy

| Observation | Evidence state / next action |
| --- | --- |
| Correct scope, sources support all material claims, no unresolved contradiction | Candidate `supported`; human review required |
| Some claims supported; missing facts limit the answer | `partial`; qualify answer and search or clarify |
| Plausibly relevant sources disagree for the same version/context | `conflicting`; show both and escalate if unresolved |
| No supporting passage, wrong version, or only search snippets available | `insufficient`; search within budget, then clarify/escalate |
| Server/client/OS information changes the diagnosis but is absent | Ask for the specific detail; searching alone cannot recover private environment facts |

Do not equate a BM25/cosine score, an LLM's self-rated confidence, or the number of citations with a probability of correctness. Numeric confidence requires a calibration experiment on held-out labels. Evidence states must be tested for false reassurance and excessive abstention.

## Search rules and starting budgets

- Default adapter: the remote PostgreSQL site search with its version-scoped `u=/docs/17/` form parameter (16 as appropriate). It needs no API key. An optional Brave adapter is selected explicitly and requires its own credential. Fetched evidence remains restricted to approved versioned PostgreSQL documentation.
- Sanitize queries to product names, public error tokens, versions, and documented feature terms. Do not send customer identifiers, credentials, private hostnames, connection strings, or complete ticket text. Show a redacted query in history.
- Treat search results as leads. Fetch the selected official page, validate destination/redirects, preserve an immutable snapshot, and retrieve actual passages before using it as evidence.
- Starting run limits: one search round, at most two search queries and five fetched pages; at most eight context passages and 16,000 source-text characters per generation call.
- Generation limit: six calls per chat turn, including contextual resolution, repair, post-search regeneration and advisory support assessment; legacy ticket runs retain four calls. At most one repair per generated response. Each call is capped at 180 seconds and the remaining ten-minute run budget. These are bounds, not latency promises.
- Request timeouts, maximum page bytes, and retry limits belong to fetch/search adapters. A run-level budget must include provider time and stop further work when exhausted.
- Successful searches do not automatically promote external content into the team's approved long-term knowledge base. Reviewer promotion creates a new source/index revision.

## Persistence and events

Use separate product tables for cases, environment revisions, source snapshots, passages/index revisions, runs/checkpoints, answer revisions, reviews, exports, and events. Persist the request scope and evidence map before generation. Checkpoint validated retrieval and fetched evidence before the next external call. Writes that change review/approval require optimistic revision checks.

Persist failed and successful stage outcomes with run ID, stage, attempt, duration, outcome, safe reason code, source/index/prompt/schema versions, CLI/model identifier when exposed, and search adapter version. Never invent unavailable model metadata. Do not put raw tickets, private passages, secrets, or provider stderr into routine logs. Detailed evidence remains in authorized product storage.

Fault fixtures must cover wrong-version retrieval, a valid quote that does not support a claim, fabricated passage IDs, malformed search results, private-source citation leakage, quota/capacity errors, and search/provider timeouts.
