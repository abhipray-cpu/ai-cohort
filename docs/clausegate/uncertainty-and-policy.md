# Uncertainty detection and approval policy

Status: deterministic uncertainty/policy routing and conservative chunk aggregation implemented; confidence is uncalibrated. The small natural-model diagnostic has wrong labels even among supported proposals. [Measured results](implementation-validation-2026-10-17.md) do not pass independent quality gates; the broader taxonomy/calibration below remains a target where not mapped in [the runbook](implementation-and-operations.md).

## Separate the questions

1. **Interpretation:** does this contract support, contradict or not mention a defined proposition?
2. **Evidence quality:** did we cover enough of the document and identify the supporting/exception passages?
3. **Organizational policy:** does that interpretation comply with this organization's configured position?
4. **Authority:** even if the system is certain, must a named role approve this exception?

These are distinct. A well-supported exception may require mandatory review. Missing evidence may mean partial ingestion, not absence of a clause. An annotation label is not legal advice. A policy rule does not become universally correct because it is in a fixture.

## Signal taxonomy

| Reason code | Trigger / handling |
| --- | --- |
| `document_incomplete` | Missing pages/chunks, scanned content without supported OCR, unreadable sections; prohibit complete clearance |
| `unsupported_interpretation` | No resolving original source spans or invalid source hash/version; reject finding or escalate |
| `exception_or_conflict` | General clause and exception/distributed qualifiers cannot be reconciled reliably; include all relevant spans |
| `missing_business_context` | Company side, disclosure purpose or required policy fact unknown; ask requester rather than infer |
| `policy_unmapped` | Unsupported/out-of-scope contract type, unknown rule or no applicable approved playbook; manual review |
| `model_disagreement` | Optional bounded independent passes disagree; heuristic flag, not calibrated probability |
| `provider_or_schema_failure` | Timeout, unaudited output, parse/schema/evidence failure after bounded repair; explicit degraded state |
| `mandatory_exception` | Deterministic rule requires a specified approver regardless of model confidence |
| `hard_block` | Active non-waivable rule prohibits clearance; ordinary approval cannot override it |
| `stale_context` | Input, findings, authority or playbook changed; analysis/decision no longer current |

Unknown values use explicit unknown enums, not empty strings or invented defaults. The detector produces multiple reasons per finding and workflow-level coverage flags; a single averaged score cannot hide one critical missing section.

## First-release policy evaluator

Versioned administrator-approved rules map a defined check/proposition and expected interpretation to an action: `record`, `clarify`, `require_review`, `require_exception` or `block`. Rules declare required business fields, role(s), distinct-actor/quorum requirements, permitted response kinds, materiality, hard-block status and any expiry. No executable Python, arbitrary expressions or source-selected tool names in a playbook; use a small typed predicate language or explicitly supported checks.

For development, use clearly labelled example playbooks approved by a test administrator. Do not market their positions as legal best practice. Real deployment requires the customer's qualified owner to configure/adopt the policy. No default “all terms acceptable” fallback.

Example fixture: hypothesis H is contradicted; rule R requires legal review for that label. The semantic oracle is a dataset annotation, while routing is determined by the fixture. H may concern a return/deletion obligation, but the company-specific acceptability of that provision is not supplied by ContractNLI. Store both oracle identities separately.

The server—not model wording—computes blocker status. Unknown/incomplete results cannot be classified compliant. A person can clarify an unknown or accept an allowed exception, but cannot bypass unrelated unassessed checks or hard blocks. Final internal packet review is mandatory in v1.

## Grounding boundary

Model output is a structured proposal with three-way interpretation, original-span references, explanatory reasoning and uncertainty signals. Validate exact document revision, offsets/quotes and coverage independently. Interpretation may need multiple noncontiguous spans, especially an exception elsewhere in the agreement. Never truncate to the first supporting quote and imply the complete evidence set was recovered.

Do not ask the model to certify its own confidence. Exact source matching establishes provenance, not semantic entailment. The model's rationale remains AI-generated; authorized correction and dataset/qualified-human evaluation establish separate evidence. Self-consistency can expose disagreement but cannot prove truth. Review UI shows original context alongside the rationale.

## Calibration and measurements

Start conservative: deterministic gaps/blockers always route to people; high-impact interpretations require review until measured risk permits a narrower rule. A heuristic uncertainty band is labelled `uncalibrated`. No percentage is shown as probability without held-out calibration.

Using development data, choose thresholds/features; use a separate calibration subset for selective prediction, then freeze policy before test evaluation. Measure retained coverage versus conditional error (risk–coverage), class-wise precision/recall/F1, per-hypothesis errors, unsupported findings, evidence-span precision/recall and false-clearance rate. Escalating every item is a valid safety fallback but fails the usefulness/automation-coverage objective; never report zero accepted errors without its abstention denominator.

Gold `NotMentioned` is not an abstention. Report predicted `NotMentioned`, model abstention, unsupported/incomplete, provider failure and pending-human separately. Existing test labels must not appear in model prompts, examples, requests or worker files accessible to the provider.

## Degradation

When generation fails, retain original text, completed stage checkpoints and safe explanations. Permit a manual source review with typed human findings, clearly attributed and coverage-bound. Do not invent model classifications or autoapprove from keyword fallback. An unavailable reviewer leaves the queue blocked; overdue timers and usage exhaustion never clear an exception.

Document and policy changes revoke derived readiness. Restored/deleted sources cannot regain status merely because a stored model score was high. These failure modes are first-class tests, not only warnings in the UI.
