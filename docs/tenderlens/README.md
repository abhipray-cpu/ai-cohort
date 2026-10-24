# TenderLens delivery pack

Status: active implementation, 13 October 2026. The diagrams include the target Windows deployment. A backend, local Codex adapter, reviewer UI, checkpointed long-pack worker, and real-document tests exist; full-pack live acceptance, the 40-pack human-labeled benchmark, Windows service packaging, and browser usability gates remain open.

TenderLens turns a tender or RFP document set into an evidence backed bid brief. A reviewer sees the extracted obligations beside the exact source page, resolves uncertain claims, and approves an export. AI output is always validated and auditable.

Read in order:

1. [Product and scope](product.md) — users, workflows, requirements, and acceptance criteria.
2. [Architecture](architecture.md) — all four C4 levels plus runtime and data flows.
3. [Implementation plan](implementation-plan.md) — build order, interfaces, release gates, and operations.
4. [Data and evaluation](data-and-evaluation.md) — real source corpus, gold labels, metrics, and end-to-end tests.
5. [Reviewer UI](reviewer-ui.md) — premium interface specification and usability validation.
6. [Implementation status](implementation-status.md) — current evidence and open release gates.
7. [Public-PDF evaluation](public-evaluation-2026-10-12.md) — six real PDFs and the initial long-pack failures.
8. [Validation follow-up](validation-2026-10-13.md) — checkpoint/retry tests and subsequent live attempts.
9. [Study guide](study-guide.md) — learn the concepts through product code and exercises.

## Decisions to verify in the first implementation spike

- Whether the chosen Windows Codex CLI version accepts the strict schema transformed from Pydantic with `codex exec --output-schema`. The macOS smoke passed; Windows remains unverified. Pin and record the tested CLI version.
- How a dedicated Windows service account authenticates Codex without an interactive session; prove this on the actual host before release.
- Tender document redistribution rights per source. The manifest may link to a document when committing the PDF is not permitted.
- OCR quality and throughput on the old laptop; record CPU, RAM, page count, and elapsed time before choosing defaults.

## References

- [OpenAI Cookbook: Codex CLI with JSON Schema output](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex)
- [C4 model: four diagram levels](https://c4model.com/diagrams)
- [India Government eProcurement tender portal](https://www.etenders.gov.in/eprocure/app?page=Home)
- [World Bank procurement notices](https://projects.worldbank.org/en/projects-operations/procurement)
