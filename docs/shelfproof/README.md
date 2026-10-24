# ShelfProof — Day 10 self-reflecting product-content agent

21 October 2026. **Engineering and bounded actual-model validation passed: 785
repository tests and 6/6 USDA products review-ready. Broader production acceptance
is not claimed.** The design documents below are
the target specification; [implementation status](implementation-status.md) is the
authority for implemented-versus-pending evidence. Actual-data/model validation
follows implementation, not the other way around. No production deployment claimed.
ShelfProof is a provisional name; trademark/domain availability is not established.

Industry: packaged food and beverage. Initial buyer: grocery-commerce agencies
maintaining multiple brands' product listings. The proposed product turns approved
facts and existing drafts into reviewable, source-linked listing patches. It does
not certify food safety, generate regulatory labels or publish to retailers.

## Every requested concept has a planned observable behaviour

| Day 10 concept | Required behaviour | Design |
| --- | --- | --- |
| Execute | Produce version 0 from a frozen fact pack and channel brief, or evaluate an imported draft | [Reflection protocol](reflection-protocol.md) |
| Evaluate with LLM as judge | A separate judge context returns rubric scores, evidence-bound findings and uncertainty | [Judge and rubric](judge-and-rubric.md) |
| Critique reasoning | Produce a short correction plan tied to findings and proposed edits, not hidden chain-of-thought | [Protocol](reflection-protocol.md), [contracts](contracts-and-evidence.md) |
| Regenerate with constraints | At most two revisions; immutable facts, explicit allowed edits, regression checks and best-version retention | [Protocol](reflection-protocol.md) |
| Log improvement metrics | Per-version factual errors, coverage, judge scores, fixes, regressions, calls, time and nullable observed usage | [Data/evaluation](data-and-evaluation.md), [acceptance](validation-and-acceptance.md) |

All five behaviours are implemented, engineering tested and observed in the
bounded actual-Codex run. Four of six products completed critique/regeneration;
the others exited early at review-ready. See the measured validation log for
exact cohorts, findings, retries and retained historical unknown usage.
Actual-inference evidence comes from that separately authorized development
campaign; authored tests and judge scores are not independent quality results.

## Read the pack in order

1. [Product and scope](product-and-scope.md): buyer, paid workflow and exclusions.
2. [Research and sources](research-and-sources.md): primary sources, competitors and assumptions.
3. [Architecture](architecture.md): C4 levels 1–4, lifecycle, data and deployment boundaries.
4. [Reflection protocol](reflection-protocol.md): execution, evaluation, critique, revision and stop logic.
5. [Judge and rubric](judge-and-rubric.md): scores, evidence, uncertainty and anti-gaming controls.
6. [Contracts and evidence](contracts-and-evidence.md): proposed Pydantic/API/export interfaces.
7. [Data and evaluation](data-and-evaluation.md): real USDA records, labels, splits and comparison arms.
8. [Validation and acceptance](validation-and-acceptance.md): TDD, real processes, browser and real-data gates.
9. [Reviewer UI](reviewer-ui.md): premium batch desk and safe comparison/review workflow.
10. [Permissions and security](permissions-and-security.md): tenant boundaries, data egress and export safety.
11. [Audit and recovery](audit-and-recovery.md): durable checkpoints, unknown receipts and restore.
12. [Operations](operations.md): planned Windows service, installed-Codex adapter and protected tunnel.
13. [Implementation plan](implementation-plan.md): dependency-ordered red/green phases.
14. [Decisions and risks](decisions-and-risks.md): accepted defaults, open risks and change procedure.
15. [Implementation status](implementation-status.md): present evidence and later learning cadence.
16. [Implementation map and TDD evidence](implementation-notes.md): actual code, safety regressions and explicit implementation decisions.
17. [Actual-data validation log](real-data-validation.md): measured acquisition, mapping discrepancies and later run results.
18. [Study guide](study-guide.md): concept-to-code walkthrough, actual-case traces, safe exercises and review questions.

Planned stack: Python/FastAPI/Pydantic, React/TypeScript, an isolated SQLite store,
durable serialized worker and installed-Codex provider port. Target host is the old
Windows laptop; Cloudflare exposes only the protected application, never Codex.
Local hosting does not mean offline inference. Provider egress needs authorization.

The bounded USDA scan yielded 1,000 distinct-GTIN candidate packs; six development
products were used in the actual-model run. These are not independent quality labels.
The first channel profile is a versioned English/US Google Merchant text patch,
not a full live feed or promise of retailer acceptance. Review-only exports remain
distinct from current human-approved patches.

The study guide and one blog were written after implementation and the measured
bounded live checkpoint, at the user's request, with all acceptance limits preserved.
