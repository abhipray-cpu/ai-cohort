# Short-term buffer, long-term vectors and relevance

Status: implemented pilot, with broader acceptance targets below. Genuine vectors, buffer, recall, source-preserving compression, initial relevance scoring and sync exist in code/tests/UI. Ranking is not calibrated; see [exact implementation/limits](implementation-and-operations.md) and [validation](implementation-validation-2026-10-16.md).

## 1. Durable history and the short-term buffer

Append authorized turns to a durable conversation before generation, with stable turn IDs, monotonic sequence and idempotency keys. A session is a viewing/interaction context, not the only location where history exists. Rebuild recent context from stored messages after restart or a fresh browser session.

Select a suffix by budget, not an unbounded number of turns. Never cut a source quote halfway and leave its attribution attached to the wrong text. Keep unresolved current user intent, recent clarifications and explicit case scope. Older turns remain stored but leave the raw buffer; their compression/recall status is visible.

Starting context allocation target: 2,000 tokens recent turns, 1,500 structured summary, 6,000 retrieved evidence, 1,500 current question and 1,000 instructions/schema. Total target 12,000; unused budget may shift under a versioned policy. Count all serialized instructions/schemas/metadata, not just message text. Verify a compatible tokenizer; until then enforce a conservative hard serialized-character ceiling and report token estimates as estimates. Budget settings and actual truncation are recorded in each reply's context manifest.

Very long current questions, memory sets or open-item lists cannot simply be dropped. Reject oversized input or create a bounded continuation/partial state with omitted IDs. Compression is not permission to claim complete coverage.

## 2. Long-term memory objects

Persist source-linked episodes and atomic memory items independently of the short-term buffer. Keep kind, subject, polarity, attribution, environment, event/observed times, valid interval, source revisions, status and authority/verification level. Memory is case-scoped by default.

Assistant suggestions are stored as suggestions. A command mentioned in a conversation is inert text. Attempts and their outcomes are linked objects; “suggested a rollback” is not “rollback succeeded.” Explicitly reviewed account memory can be reused only by authorized cases in the same account, with originating-case evidence permission checked.

Avoid duplicate memory inflation: deterministic source/span/semantic-key fingerprints coalesce proposals without merging different environments or contradictory assertions. Superseded and disputed items remain historical unless suppressed/erased. Current-state answers exclude superseded claims as current but may recall them for “what changed?”

## 3. Genuine semantic embeddings

Proposed initial encoder: pinned CPU artifact derived from `sentence-transformers/all-MiniLM-L6-v2`, assessed for English technical text. Pin model/tokenizer/runtime hashes, dimension, pooling, normalization and numeric precision before implementation acceptance. The proposed 384-dimensional vectors are real learned semantic representations, not keyword counts, randomized vectors or hash embeddings.

Chunk at tokenizer boundaries below the encoder limit, preserve source spans and include useful local attribution. Do not silently truncate long troubleshooting logs. Store chunk coverage and omitted/unsupported content. Boilerplate, bot activity and quoted duplicate messages need distinct handling; filters must not discard a later correction merely because its wording resembles an earlier report.

Compute locally on CPU after explicitly provisioning model files; no private text is sent to an embedding API. Model download is a separate authorized setup operation. Do not download or execute source-supplied model/plugin code. If ONNX is selected, test pooling/normalization and quality parity; do not assume conversion/quantization is free of semantic changes.

Store normalized float32 vectors with memory/source hash, model revision and scope. Reject wrong dimensions, NaN/infinity, all-zero vectors or mismatched revisions. Do not mix models/dimensions in one similarity calculation. Model migration builds a new index namespace then atomically switches validated readiness; old reports keep provenance.

Initial exact cosine search over authorized vectors avoids an additional service. At 384 float32 dimensions, 10,000 raw vectors require about 15.4 MB before text/metadata/cache overhead; this is arithmetic, not measured application RSS. Bound resident matrices/batches; measure retrieval at realistic scope sizes and across all five products on the old laptop. If exact search is inadequate, evaluate a tested ANN backend later without weakening scope filters.

## 4. Recall pipeline

1. Resolve authenticated actor, account/case, roles, requested historical cutoff and minimum revision server-side.
2. Filter authoritative memory/source rows by permission, eligibility, valid/observed times, deletion/suppression and model/index revision **before top-k vector selection**.
3. Encode the question locally. Collect bounded semantic candidates and lexical candidates, plus explicitly required current constraints/open commitments.
4. Fetch original source spans for candidates. Reject inaccessible/deleted/changed sources; never use a stale vector as its own authority.
5. Apply deterministic versioned ranking and diversity. Preserve conflicting assertions and distinguish same-version applicability from broader historical context.
6. Assemble a bounded evidence pack with memory/source IDs, score components, source dates, index watermark and omitted coverage.
7. Generate a structured reply only if model egress is allowed; independently validate references, IDs, currentness and limits. Otherwise present a qualified deterministic evidence handover.

Recall must work after process restart and in a different session, not just while messages remain in RAM. Retrieval caches include authorized scope, policy revision, query, source/memory revisions and embedding version. Recheck grants before reuse and answer publication.

If vectors are unavailable or pending, lexical/source-only mode may continue with a visible **semantic recall unavailable/pending** state. That is degraded functionality and cannot pass the long-term vector concept gate. Do not silently substitute keywords and call it vector recall.

## 5. Relevance scoring

Hard gates: authorization, source availability, deletion, explicit query scope and historical cutoff. These are never soft scoring penalties.

Proposed rank features:

| Feature | Role / caution |
| --- | --- |
| Semantic similarity | Recall paraphrases; weak at exact versions, negation and truth |
| Lexical/exact entity match | Preserve error codes, versions, components and named attempts |
| Applicability | Prefer same reported environment when appropriate; unknown differs from incompatible |
| Attribution and status | Separate reported/confirmed facts, proposals, disputed and superseded state |
| Recency/effective time | Useful for current questions, not a blanket truth override |
| Diversity/duplication | Avoid ten copies of one quoted workaround crowding out a later failure |

Use a documented feature normalization and weighted policy or calibrated reranker selected on development/calibration data. Do not fix arbitrary weights and report them as learned accuracy. Log components and reasons; a cosine/rank score is **not probability of correctness**. Rank timestamps relative to the query cutoff, not wall-clock time during replay.

Return abstention/clarification when minimum evidence criteria fail. A top-k list always existing does not mean there is a relevant answer. Include explicit mandatory unresolved items even if similarity is low; if they exceed budget, retain a coverage denominator and partial state rather than hiding the rest.

## 6. Required observable tests

- A fact outside the recent buffer is recalled using persisted vectors after API/worker restart.
- Paraphrase recall succeeds where lexical-only baseline fails, with measured retrieval evidence.
- Similar wording from another account never enters the candidate set or model prompt.
- Failed/superseded workaround is not recalled as current success; historical questions still see correct chronology.
- Exact version/error-code queries do not rely on semantic similarity alone.
- Irrelevant question abstains; conflict remains explicit even when one assertion scores higher.
- Embedding outage/lag, invalid vector and changed encoder yield explicit degradation, never fabricated recall.
- Long logs/chunks report coverage rather than silently truncating evidence.

Metrics, real-data denominators and baselines are in [evaluation](data-and-evaluation.md).
