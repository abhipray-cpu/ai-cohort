# A support agent should remember the investigation—not invent its conclusion

*Blog draft, updated 17 October 2026. RelayDesk is an implemented pilot, not a production launch. Nothing here has been published externally.*

The most frustrating moment in a technical escalation is often the handover. A new engineer joins, reads a long thread and proposes the same workaround that failed yesterday. The team has a record, but not useful continuity.

For Day 5 of our AI product challenge, we built RelayDesk: a source-linked conversation workspace for technical-support investigations. Its commercial hypothesis is simple: help the next engineer resume faster, without turning a participant's theory into a verified fix. Public engineering threads let us test the system against messy real histories. They do not prove customers will pay.

## Six kinds of work hidden inside “memory”

A chatbot history is not a complete memory architecture.

RelayDesk keeps a short-term buffer of recent turns in the current session. It separately stores long-term source-linked memories and genuine semantic vectors. Recall selects relevant authorized evidence. Structured compression fits selected context into a bounded prompt. Relevance scoring explains the selection. Revision-aware synchronization keeps corrections and deletion authoritative across sessions.

A new session resets the immediate buffer, not the case. A restart should not make the investigation disappear. A later correction should not leave yesterday's answer looking current.

Those distinctions make memory a product capability rather than a longer prompt.

## Small-host architecture, explicit boundaries

The target service host is an older Windows laptop behind a protected Cloudflare tunnel. Source records, jobs, memory revisions and vectors live in SQLite. A pinned MiniLM ONNX encoder produces actual 384-dimensional vectors on CPU; there is no remote embedding API or separate vector-database server.

Generation goes through an adapter to the installed Codex CLI. That is not a promise of offline inference. Model-context egress is a separate permission, denied by default.

Authorization happens before similarity ranking. We do not search every customer's plaintext and filter the top ten afterwards. Retrieved items carry exact source spans, hashes, attribution and state. Similarity helps locate a report; it cannot establish that the report is true.

Windows deployment, protected-edge behavior and all-five-product capacity still require acceptance on the actual target host. Working on macOS is not that proof.

## The first honest test result was a list of defects

Our broader initial campaign covered 49 public threads across 22 repositories and 3,576 non-bot messages. It found important failures: an unrelated deletion ledger could be accepted during restore; a corrupted source body could retain its old hash; the current question could cite itself; and compression metadata could overflow the complete model-context limit.

Only five of ten live jobs completed the AI stage. We retained the failures and did not call the product ready.

The corrective work started with reproductions. Tests now fence late vector publication after source edits, recompute source integrity, bind stores to the independent erasure ledger, exclude the active question as its own evidence, and budget serialized context—including omission metadata and nested prior assistant artifacts.

Batched authorized vector access also replaced per-candidate database work. The point was not merely speed: permission boundaries and numeric validation had to survive the optimization.

## Valid JSON can still tell the wrong story

The most instructive failure was a schema-valid claim of universal recovery with an allowed citation.

The JSON was valid. The citation ID existed. The source did not say what the answer claimed.

We narrowed the factual publication boundary. Each claim must now be an exact contiguous quotation from one supplied source. The server maps it back to the original offsets and publishes attribution and state. A model-written narrative summary is not promoted into factual authority; the server supplies a neutral quotation count or abstention.

This is a tradeoff. The handover is less fluent than a freely synthesized narrative. It is also easier to inspect. Exact quotation establishes provenance, not truth or relevance, so human review and independent quality evaluation remain necessary.

## Compression has to admit what it omitted

Our initial “bounded summary” included every omitted memory ID. At ten thousand memories, that metadata alone pushed the serialized summary far beyond the full prompt allowance.

The corrected representation keeps a bounded sample, full omission count, hash and authorized ledger reference. Selected text and metadata share the budget. Original history stays available outside the prompt.

This is not lossless compression. A smaller prompt can omit an important failed attempt. Coverage and partial status must remain visible, and independent evaluation must measure which critical facts were missed.

## The product is the boundaries

The final frozen build passed 283 unmasked Python tests, plus frontend state tests and a production build. The deduplicated corpus expanded to 89 threads/22 repositories and 6,680 non-bot messages. Eleven live jobs completed the AI stage, publishing 78 original source-resolving quotations; all remained partial drafts. Fresh authenticated HTTP and worker-recovery checks passed. The [corrective validation report](corrective-validation-2026-10-17.md) separates those results from intermediate runs and explains the remaining acceptance failures.

Browser acceptance remains unavailable without a browser connection. The full screened corpus, two-human-reviewed question set, Windows deployment and consenting-customer usefulness study remain release gates. Additional retrieved data is not independent ground truth; replica capacity fixtures are not new customer histories.

The lesson is not that an agent becomes reliable when it remembers more. It becomes more inspectable when it can explain what it retrieved, why it was eligible, what changed, what was omitted and what it cannot conclude.

RelayDesk's next proof is independent quality and real deployment acceptance—not a larger claim about the same tests.

[Study guide](study-guide.md) · [Architecture](architecture.md) · [Acceptance gates](product-acceptance.md)
