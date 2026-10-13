# Real data and end-to-end evaluation

This document is the evaluation plan, not a claim that a labeled dataset has been completed. Six public PDFs have now been checksum-frozen and tested as an exploratory corpus; see [the 12 October public-PDF evaluation](public-evaluation-2026-10-12.md) and [the 13 October recovery follow-up](validation-2026-10-13.md). Human gold labels and held-out metrics remain absent. Results must be measured and published with corpus and runtime versions.

## Sources and acquisition

Start with original public sources, not third party tender aggregators:

| Source | Why | Acquisition note |
| --- | --- | --- |
| [India Government eProcurement](https://www.etenders.gov.in/eprocure/app?page=Home) | Real tenders, varied departments, free schedule download, corrigenda | Save tender reference, notice URL, PDF URLs, capture date, and amendment links. Check each document's reuse terms before committing bytes. |
| [World Bank procurement notices](https://projects.worldbank.org/en/projects-operations/procurement) | International notices and differing formats | Include only notices with accessible source documents; distinguish a short notice from a full RFP. |
| [UNICEF procurement documents](https://www.unicef.org/nepal/documents/lrps-2026-9205846-institutional-service-digital-health-ecosystem-and-architecture) | Multi annex RFP packs and explicit submission rules | Preserve the RFP and annexes as one opportunity pack; review reuse terms per file. |
| Customer supplied pilot documents | Product fit on realistic workflow | Keep outside the public repository, use explicit consent, and evaluate in a private split. |

Verified seed candidates for the first acquisition pass:

- [UNICEF Serbia LRPS-2026-9202334](https://www.unicef.org/serbia/media/29961/file): 29 page RFP with a submission deadline, required documents, and detailed conditions.
- [UNICEF Montenegro LRPS-2026-9202732](https://www.unicef.org/montenegro/en/media/26051/file): compact RFP with technical and financial scoring, proposal packaging, and required references.
- [UNICEF Nepal LRPS-2026-9205846](https://www.unicef.org/nepal/documents/lrps-2026-9205846-institutional-service-digital-health-ecosystem-and-architecture): multi file RFP with terms of reference, evaluation criteria, price schedule, and vendor forms.

These are source candidates, not yet labeled benchmark cases. Acquisition must confirm stable download, checksum, document completeness, and redistribution rights.

The first frozen benchmark target is 40 public opportunity packs: 20 native text PDFs, 10 scanned or mixed text PDFs, and 10 packs with corrigenda or multiple files. Stratify by goods/services/works and document length. This target is contingent on accessible documents and rights review; record gaps instead of silently replacing cases. A separate 10 pack private pilot set is desirable if a partner participates.

Store documents at `data/tenderlens/raw` only when redistribution is permitted. Otherwise store a manifest and reproducible retrieval instructions. `extracted` holds parser output and page quality; `gold` holds human adjudicated labels; `adversarial` holds corruption/edge fixtures; `manifests` holds source, checksum, rights, split, and version. Never label model generated answers as gold.

## Gold annotation protocol

1. Freeze the source pack and all corrigenda, with SHA 256 for each file.
2. Two annotators independently label deadline, buyer, scope, eligibility, mandatory documents, technical conditions, evaluation criteria, financial terms, and disqualifiers. Each label gets source document, page, exact quote, and `stated/ambiguous/not_stated` status.
3. Adjudicate disagreements with a named reviewer and rationale. Preserve both original annotations for audit.
4. Mark document level limitations: OCR unreadable, malformed PDF, missing annex, inconsistent amendments, language, and reference ambiguity.
5. Freeze train/development/test by opportunity, not by page or document, so amended files stay in one split. Do not tune prompts or thresholds on the test split.

Suggested split of 40 packs: 20 development, 10 validation, 10 held out test. The held out set is intentionally small, so report counts and confidence intervals rather than implying population level certainty. Expand it before broad commercial claims.

## Metrics and pilot gates

| Metric | Definition | Pilot gate |
| --- | --- | --- |
| Schema valid rate | Successful outputs passing Pydantic / completed runs | 100% of outputs presented as structured drafts |
| Deadline exact match | Correct source date, time, timezone status and amendment precedence | At least 9/10 held out packs; zero silent timezone inventions |
| Mandatory requirement recall | Matched mandatory requirements / gold mandatory requirements | At least 90% overall; report raw counts |
| Mandatory requirement precision | Supported extracted mandatory requirements / extracted mandatory requirements | At least 95% |
| Citation correctness | Sampled claims with matching quote on cited page / sampled claims | At least 95%; no unverifiable claim labeled verified |
| Critical miss rate | Wrong deadline, missed disqualifier, or fabricated mandatory condition per pack | Zero on held out test for supported document types |
| Review completion | Reviewer can inspect and approve/reject all material claims | 100% in browser test tasks |
| Repair rate | Attempts requiring validation repair / completed runs | Report by error type; no target until measured |
| Latency | Upload to reviewable draft by page count and OCR class | Report p50/p95 and hardware profile; establish SLA after host run |

These are release gates, not expected results. If a gate fails, limit supported tender types or require manual review for the affected fields. Report per category and parser quality; a pooled score can hide scanned PDF failures.

## Test pyramid

- Contract tests: exact Pydantic and JSON Schema round trip, unknown fields, enum mistakes, numeric/date edge cases, tool argument/result validation.
- Parser tests: real source PDFs with checksums, page count, quote offsets, OCR quality, tables, scanned pages, and text order.
- Agent fault tests: deterministic fake provider emits malformed JSON, missing fields, inconsistent claims, missing page, wrong quote, timeout, auth failure, and empty output. Check retry budgets and logs.
- Recovery tests: a later chunk times out; prior validated chunks survive, the timeout appears in run events, export is blocked for partial output, and the same run resumes without regenerating completed chunks. Persistent public-evaluation sessions exercise the same path across separate harness invocations.
- Real model benchmark: run the frozen pack through the pinned Codex CLI, collect every raw attempt securely, score against gold, and save run metadata.
- API integration: upload, queue, rerun, review mutation, idempotency, export, unauthorized access, restart/recovery.
- Browser end-to-end: actual PDF rendered beside a claim; citation click lands on exact page; reviewer correction survives rerun and reload; approved export includes corrected value; failure state explains next action.
- Host acceptance: Windows service cold start, laptop restart, tunnel Access sign in, session expiry, backup/restore, low disk, and network outage.

## Required end-to-end scenarios

| ID | Input | Expected observation |
| --- | --- | --- |
| E2E-01 | Public native text tender | Upload through UI, extract, review cited deadline and mandatory items, approve and export |
| E2E-02 | Scanned tender | OCR state visible; low confidence claim flagged; page citation still navigable |
| E2E-03 | Original plus corrigendum | Revised deadline wins only with explicit evidence; original and superseding claim visible |
| E2E-04 | PDF with missing financial value | `not_stated` shown; no invented budget |
| E2E-05 | Bad JSON then valid JSON fake provider | One logged validation failure, one repair, valid final draft |
| E2E-06 | Invalid page lookup tool result | Tool result rejected; no false verified citation |
| E2E-07 | Repeated invalid response | Retry budget exhausted; actionable UI state and run ID |
| E2E-08 | Service/network interruption | Job resumes or safely fails; reviewed claims and audit trail intact |
| E2E-09 | Unauthorized browser request | No PDF, brief, or audit data leaked |
| E2E-10 | Reviewer edits claim then reruns | Human edit retained with provenance; no silent overwrite |

## Reproducible scorecard

Every benchmark run writes a JSON manifest with corpus version, document hashes, split, parser/OCR versions, prompt version, Pydantic schema version, Codex CLI version, model identifier, host CPU/RAM, run time, retry counts, and scoring script commit. Publish aggregate results plus per pack error categories; keep raw tender text out of public telemetry.
