# Design decisions, open risks and change control

22 October 2026. These are proposed implementation defaults, not installed systems
or proven results. The user approved moving from the full requirements into design
and documentation, then authorized implementation. Foundation implementation is
in progress; actual-provider and private-data processing need their own authority.

## Decisions

| ID | Decision and reason |
| --- | --- |
| D1 | Initial English/US Honda reviewed-programme inventory; a testable scope, not all-make/global coverage |
| D2 | All twelve functional requirements in release one, including retrospective checks and version explanations |
| D3 | Case-preparation/evidence product, not diagnosis, legal representation or guaranteed reimbursement |
| D4 | Manual user submission after approved download; no outgoing-message connector or settlement authority |
| D5 | Condition-level unknowns/conflicts and separate external confirmation; no “refund probability” |
| D6 | Facts, source captures, assessments and packets are versioned; approval binds exact content and authority |
| D7 | Dedicated SQLite/one expensive worker for a bounded single-host pilot; measure before higher concurrency |
| D8 | Public source registry separate from household records; app auth independent of protected tunnel |
| D9 | Installed Codex adapter is a candidate generation integration; optional decision services require separate evaluation/egress approval |
| D10 | No experimental visual-model dependency for core correctness; real parser/OCR output is verified/correctable |
| D11 | Daily consented source checks and in-app notifications; source-review holds and freshness are visible |
| D12 | Proposed 180-day inactivity retention, 90-day monitoring consent, 24-hour live purge and 30-day backup expiry require privacy/host validation |
| D13 | No billing initially; willingness-to-pay is a research hypothesis, not reason to add payment processing |
| D14 | Preserve separate engineering/public-data/actual-consumer/Windows/business gates and later study/blog cadence |

## Highest risks

| Risk | Consequence and required response |
| --- | --- |
| Consumer expects automatic entitlement/refund | Condition-level explanation, comprehension test and specialist review; block misleading copy |
| Programme inventory too small, stale or legally inaccessible | Verify acquisition/rights first; report scope/volume failure without fabricated expansion |
| Actual vehicle coverage depends on nonpublic manufacturer records | Require external confirmation; VIN/model match alone never clears applicability |
| Source guidance old/expired or lookup inaccessible | Revalidate current official channels; label archive/stale; manual route, no portal bypass |
| Need real invoices/responses, not just public documents | Obtain voluntary separate pilot consent; acceptance remains open without actual cases |
| OCR/model introduces facts or omits exclusions | Correctable facts, independent evidence checks and hard critical-error release gate |
| New source revision misread as improved coverage | Human registry review, change types, stale invalidation and before/after provenance |
| Sensitive household information leaks to helpers/providers | Per-case grants, minimal egress, private blobs/redaction and adversarial scope tests |
| Repeated retries consume unknown paid usage | Persisted budgets and unknown-liability hold, no silent campaign reset |
| Laptop cannot isolate parsers or meet retention/load targets | Preflight and real host drills; block launch or request architecture change |
| Manual submission feels incomplete | Test actual consumer usefulness; do not disguise manual send as integrated delivery |
| One-time case economics do not support operation | Interview/price/effort tests; no invented recovery revenue or mandatory subscription |
| Name/brand conflict or implied endorsement | Clear provisional name and no-affiliation notices; check name before publishing |

## Open before implementation

Actual supported programme list and currency; legitimate public acquisition volume;
specialist/reviewer availability; pilot recruitment/consent; OCR/sandbox dependency
and license choice; Windows capacity/identity/backup key recovery; auth enrollment/
recovery UX; provider budgets and data-handling approval. An adapter interface may
be implemented with fakes for TDD while these are open, but fakes cannot close the
corresponding release gates.

Any scope/provider/delivery/retention/authority change must update requirements,
contracts, security, matrix and tests before implementation. Freeze a new evaluation
version and keep earlier failures. Unavailable data or a hard benchmark is not a
reason to silently lower the bar or describe a plan as completed capability.
