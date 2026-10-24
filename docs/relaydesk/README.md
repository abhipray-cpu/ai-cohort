# RelayDesk delivery pack

Full product acceptance: [current rejected/blocked gate matrix and command](product-acceptance.md). A passing frontend build or masked expected failures cannot produce acceptance.

**Current release verdict: rejected/incomplete, corrective engineering checks passed.** See [17 October corrective validation](corrective-validation-2026-10-17.md): 89 distinct threads/22 repositories/6,680 non-bot messages; 283 unmasked Python tests, eleven live AI-stage completions and 78 exact source-resolving quotations. Earlier [aggressive failures](aggressive-validation-2026-10-16.md) are preserved; [findings](validation-findings.md) now record mitigations and residual limits. Six gates pass, one fails, five remain blocked—not production acceptance.

Day 5: memory-enabled conversation agent. Status on **17 October 2026: implemented and corrective-engineering-tested pilot**, not production-certified. Backend, React UI, real CPU semantic vectors, installed Codex adapter, service commands and identity-bound backup/restore are delivered. RelayDesk is a working name, not a cleared trademark.

Start with [implemented architecture/operations and deviations](implementation-and-operations.md), [current validation](corrective-validation-2026-10-17.md), [study guide](study-guide.md). Earlier specifications remain release targets where they exceed the pilot; they are not proof that those gates passed.

Product: an investigation-continuity workspace for B2B technical support teams. The incoming engineer resumes from what is known, attempted, corrected and outstanding—not from a fresh summary that forgets the previous shift. It sits alongside the helpdesk; it does not replace ticketing or autonomously reply to customers.

| Requested concept | Implemented observable behavior | Specification |
| --- | --- | --- |
| Short-term buffer | Bounded recent turns for the current conversation, rebuilt from durable messages after restart | [Memory and recall](memory-and-recall.md) |
| Long-term vector memory | Persistent genuine semantic embeddings of source-linked episodes and memories, scoped before retrieval | [Memory and recall](memory-and-recall.md), [architecture](architecture.md) |
| Recall | Recover previous attempts, outcomes, constraints and corrections across sessions with exact sources | [Contracts](contracts-and-evidence.md), [evaluation](data-and-evaluation.md) |
| Context compression | Budgeted source-preserving structured selection, with versioned dependencies and visible omissions | [Compression](compression-and-sync.md) |
| Relevance scoring | Explainable, initially uncalibrated hybrid semantic/lexical/recency/status ranking; scores are not truth probabilities | [Memory and recall](memory-and-recall.md) |
| Cross-session sync | Ordered revision events, optimistic edits, index watermarks and invalidation across authorized browser sessions | [Sync](compression-and-sync.md), [security](permissions-and-security.md) |

Read in order:

1. [Product](product.md): buyer, workflow, commercial hypothesis and first-release boundaries.
2. [Research and sources](research-and-sources.md): market evidence, competition, primary technical/data references and limitations.
3. [Architecture](architecture.md): C4 levels 1–4, sequence/state/deployment and decisions.
4. [Memory and recall](memory-and-recall.md): buffer, durable semantic vectors, recall policy and ranking.
5. [Compression and sync](compression-and-sync.md): compression invariants, source revisions, multi-session consistency and forgetting.
6. [Contracts and evidence](contracts-and-evidence.md): typed boundaries, exact source spans, memory/answer/review semantics.
7. [Permissions and security](permissions-and-security.md): account/case boundaries, egress, prompt injection, deletion and restore risks.
8. [Data and evaluation](data-and-evaluation.md): real-data volume/quality, chronological replay, independent labels, baselines and release gates.
9. [Reviewer UI](reviewer-ui.md): premium conversational handover workspace and browser acceptance.
10. [Implementation plan](implementation-plan.md): test-first phases, proposed interfaces and API surface.
11. [Operations](operations.md): Windows/Cloudflare target, resource ceilings, configuration and recovery drills.
12. [Implementation status](implementation-status.md): delivered documentation versus unverified engineering/product gates.
13. [Source feasibility — 16 October](validation-2026-10-16.md): observed source checks, failures and what they do not validate.
14. [Study guide](study-guide.md): the six memory-agent concepts correlated with implemented code, tests, exercises and validation limits.

Run `make relaydesk-up`, `make relaydesk-down`, `make relaydesk-status` and `make relaydesk-test`; first installation/model provisioning is documented in [the current runbook](implementation-and-operations.md). Public issues validate engineering paths, not customer willingness to pay or independent answer quality. Browser/Windows and the larger evaluation cohort remain open.
