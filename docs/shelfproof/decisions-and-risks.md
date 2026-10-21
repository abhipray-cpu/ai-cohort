# Design decisions and open risk register

These are the frozen design decisions and risks. Implemented controls and actual
evidence are mapped in [implementation notes](implementation-notes.md) and
[status](implementation-status.md); design intent alone is not release evidence.

## Decision log

| ID | Decision | Reason / consequence |
| --- | --- | --- |
| D01 | Packaged-food agency content repair, not a generic writer/PIM | A narrow recurring workflow; willingness to pay remains untested |
| D02 | Frozen approved facts; model can change copy only | Reflection cannot fabricate authority or rewrite its evidence |
| D03 | Separate producer, judge and observable correction-plan contexts | All requested concepts are inspectable; shared model bias remains |
| D04 | Hard checks and nonregression dominate rubric score | Score gain cannot erase known factual harm or missing evidence |
| D05 | Maximum two revisions, finite repairs/calls/time | Prevent an improvement loop becoming unlimited spend or repeated risk |
| D06 | One English/US Google text-patch profile | Controlled serializer/rule surface; no feed/approval/publishing promise |
| D07 | No dietary/certification/allergen-free/medical claims in v1 | Avoid presenting generated claims as specialist verification; scope is intentionally limited |
| D08 | USDA public records for research; real customer workflow is separate | Source-snapshot fidelity is testable without inventing partner access |
| D09 | Dedicated store/service and installed-Codex port on Windows | Fit monorepo/host constraints; local hosting is not offline inference |
| D10 | Independent journal, store-wide liabilities and explicit incident policy | Avoid lost receipts causing false zero usage, bypass workspaces or erased rollback history |
| D11 | CSV review artifact differs from typed machine patch | Spreadsheet safety must not silently change machine-authoritative product facts |
| D12 | Independent human approval before approved export | Rubric readiness is not publication/brand authorization |

Protocol v1 fixes five rubric dimensions/weights, hard-gate severities, forbidden
claim classes and resource ceilings in tested policy code. Owners activate versioned
tested profiles/briefs/rubrics; free-text briefs and model outputs cannot weaken
those invariants. A different threshold/rubric requires a new frozen version and
development evidence, not an ad hoc pass for one row.

## Risks and required evidence

| Risk | Control hypothesis | Evidence required |
| --- | --- | --- |
| Incumbents already offer the feature | Low-integration agency workflow and transparent patches | Buyer observation, pilot and matched workflow comparison |
| Judge favors its own fluent output | Hard gates, blinding, independent labels, regression checks | Judge confusion/error analysis and human review |
| Accurate copy of wrong/stale source | Version/date visibility, limitations and current customer approval | Source-quality audit; real current brand evidence for commercial claims |
| Pack versus serving/basis confusion | Typed fields and explicit mapping; no silent conversions | Real-record mapping/join and numeric tests |
| Claim map misses implicit assertions | Whole-text judge plus conservative checks and human review | Independently annotated semantic claims; no claim of exhaustive proof |
| Missing source leads to prettier hallucination | `needs_data`, immutable facts and forbidden claims | Negative/incomplete cohort and actual provider tests |
| Quality rises only on the judge's score | Distinct factual, coverage, preference and cost metrics | Independent paired comparisons against one-shot and resampling |
| Same-family leakage inflates quality | Group revisions/variants before split | Corpus report, duplicate review and untouched test manifest |
| Dataset huge for old laptop | Streaming, disk budget, bounded subset | Actual resource measurements and Windows parser/process enforcement |
| Provider timeout/unknown/unsafe tools | Reservations, hold, sanitized diagnostics, bounded operator recovery | Actual runtime/fault tests, no fabricated receipt |
| Human edits or stale policy inherit approval | Immutable version bindings and reevaluation | Real HTTP/browser changed-source/edit tests |
| Customer data leaves host unexpectedly | Explicit source/egress grant and preview; no background model requests | Serialized-context audit and service-account isolation |

Open: trademark/domain; actual eligible source volume; independent reviewer
availability; customer data and willingness to pay; target laptop capability;
effective provider tool/accounting controls; exact channel source snapshots and
approval semantics; model spend for any expanded evaluation. No stakeholder, legal
review, pilot, label corpus or host capability is assumed secured.

## Change procedure

Owner-approved scope changes record reason, affected contracts/data/rubric/profile,
security/accounting implications, new tests and new evaluation version before use.
Reclassification of a touched test set as development is mandatory. Preserve old
reports and budget/incident liabilities. No “temporary” new workspace, cleared hold,
silent lower threshold or removed failure denominator can manufacture acceptance.
