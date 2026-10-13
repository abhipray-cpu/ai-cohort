# A schema-valid answer is not a trustworthy answer: building TenderLens

*A field report from Day 1 of a 12-AI-products-in-14-days challenge. TenderLens is an active implementation, not a production release.*

We chose a real job for the first product: a bid manager opens a tender pack and needs to know the deadline, mandatory documents, evaluation rules, disqualifiers, and unresolved questions. A missed page can cost an opportunity. A confidently invented requirement can waste days of work. The product therefore cannot stop at “the model returned JSON.” It must produce a draft a person can verify against the original PDF.

TenderLens runs on a single host with a React reviewer interface, a FastAPI backend, SQLite persistence, PDF extraction/OCR, and a worker that invokes the locally installed Codex CLI. “Locally installed” describes the executable and adapter, not offline inference: Codex still needs authentication and network access to its model service. The eventual target is an older Windows laptop exposed through a protected Cloudflare Tunnel; that deployment is still a release gate, not a completed feature.

## The contract is the start of the trust boundary

Our Pydantic models describe a draft brief, typed claims, source citations, and page-lookup requests/results. From the output model we derive JSON Schema and pass a strict form to `codex exec --output-schema`. The CLI writes its final message to a file. The worker parses that file and validates it again with Pydantic. OpenAI documents the [non-interactive CLI pattern](https://learn.chatgpt.com/docs/non-interactive-mode); we keep the application-side validation because the output contract belongs to the product, not the provider.

That distinction matters. A syntactically valid object can still cite a nonexistent page. A correctly shaped citation can quote words that are not on that page. A real quote can be misinterpreted. TenderLens checks page and quote membership in code, then leaves semantic judgment and approval to a reviewer. These are different gates: shape, grounding, meaning, and approval.

The page lookup is typed too. Before source text goes into the model prompt, the application verifies that the returned document and page match the request. Tender PDFs are treated as untrusted input. A line inside a tender saying “ignore previous instructions” is not allowed to become an instruction to the worker.

## Repairs need a budget; outages need a different path

If JSON parsing, Pydantic validation, or citation checking fails, the orchestrator records a validation event and makes a focused repair attempt. It stops after two repairs. That is a bounded version of the [review–repair–validate loop described in OpenAI's Codex Cookbook](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex). It avoids both silent acceptance and endless retries.

A subprocess timeout, model-capacity error, or usage-limit error is not a malformed answer. The worker now records provider failures separately. When a multi-page chunk times out, it splits that chunk and tries smaller leaves. When a terminal failure occurs after earlier leaves have succeeded, it keeps their validated outputs as a read-only partial brief. The user can retry the *same run* later; completed leaves are not regenerated. Partial briefs cannot be approved or exported.

This recovery design came from testing, not from a diagram. In our initial public-PDF evaluation, a 29-page Serbian RFP and a 67-page Nepal pack each completed an early chunk but timed out on a later eight-page call. Both runs lost a usable draft, and the timeout was missing from validation history. Four-page/character-bounded planning, SQLite chunk checkpoints, timeout events, adaptive splitting, and partial/retry states now address those failure modes in deterministic tests.

## The public documents exposed the limits

We froze checksums for six public UNICEF PDFs totaling 98 pages. The short Montenegro RFP produced a cited live draft; focused Nepal annex runs also produced drafts and surfaced a procurement-ID mismatch between two annexes. Those are useful observations, not precision or recall scores. No human-adjudicated gold set exists yet.

The follow-up live test also reminded us that reliability has an external dependency. A Codex smoke call succeeded, while the first 29-page Serbia recovery attempt stopped at the provider with a model-capacity error before saving a chunk. A prior run had preserved 30 claims as a partial brief after a separate usage-limit interruption. The persistent Serbia session then resumed and completed all 14 chunks in about 26 minutes. That proves one full-pack functional completion on this host, not a useful latency target or a quality pass. The exact result belongs in the [validation record](validation-2026-10-13.md).

The harder quality problem remains: a citation match is not the same as complete requirement extraction. The completed Serbia draft had 291 cited claims and 88 open questions. Some questions asked for a deadline absent from one chunk despite conflicting deadline dates being cited in another. The current merge deduplicates identical cited claims, but it does not reconcile those cross-chunk questions. Nor does it decide which deadline a corrigendum supersedes without explicit evidence and review. Those are product problems, not JSON problems.

## What “production-minded” means here

The immediate value is a transparent workflow: immutable source hashes, page-level evidence, typed contracts, bounded model calls, durable work, visible failures, human review, and an export gate. The next evidence must come from an adjudicated benchmark, browser usability testing, and a restart/security drill on the Windows host. We will report accuracy and latency by document class rather than extrapolate from one attractive demo.

The lesson from Day 1 is simple: structured output makes an AI feature easier to integrate, but a product earns trust only when it can explain *where an answer came from, what failed, what survived, and what a human still needs to decide*.
