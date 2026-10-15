# Contracts, identity, and evidence

Implemented contracts are in [propertybrief.py](../../packages/contracts/src/contracts/propertybrief.py); prompt version is `propertybrief-1.1`. Product Pydantic models forbid unknown fields, bound collections/text, and use explicit enums. JSON Schema supplied to Codex is derived from these models and specialized with captured source/row/field allowlists; returned JSON is independently parsed and validated. Source APIs evolve independently: adapters preserve raw fields and validate required identity/status fields with drift reporting rather than applying strict product models to every upstream column.

The vocabulary below describes domain responsibilities, not a promise of one Pydantic class per row. Current models are `PropertyInput`, `AgentDecision`, `EvidenceRef`, `Finding`, `PlanTask`, `ReportDraft`, `Critique`, `Message`, `IdentitySelection`, `Review`, `ExportRequest`, `SourceRecord` and `ToolResponse`. `ToolResponse.outcome` is `success`, `no_records`, `partial` or `unavailable`; invalid/mismatched records are flags or validation failures, not extra outcome enums. Evidence references contain `source`, `record_id`, `field`, `value`; the run's immutable source manifest resolves the snapshot. Raw/normalized evidence lives in SQLite, not raw-file references.

## Record vocabulary

| Record | Required meaning |
| --- | --- |
| `PropertyInput` | Case, raw address, borough, optional BIN/BBL, question, actor, input revision |
| `PropertyCandidate` | Source-derived identifiers, address, match method, conflicts, candidate ID |
| `PropertyIdentity` | Confirmed HPD building ID, BIN/BBL when available, jurisdiction, scope and selection revision |
| `SourceDefinition` | Dataset ID, catalog/API URL, adapter/schema version, required coverage role, key and status mappings |
| `SourceSnapshot` | Source, query/filter fingerprint, property scope, retrieval interval, metadata version/hash, content hash, completeness and raw-file reference |
| `SourceRecord` | Dataset ID, canonical source row key, snapshot ID, original/normalized fields, building/parcel scope, quality flags |
| `ToolRequest` | Run/step/attempt IDs, allowed tool enum, typed arguments, confirmed identity revision |
| `ToolResult` | Echoed scope, outcome, snapshots, rows/counts, pagination, coverage, error/quality codes |
| `AgentDecision` | Next action or finish/clarify, decision summary, expected evidence, reflection and hypothesis changes |
| `Finding` | Claim text/category, evidence references, source status/dates, uncertainty, interpretation flags |
| `EvidenceRef` | Snapshot ID, row key, field paths, exact values or bounded quote; link resolved server-side |
| `PlanTask` | Purpose, recipient role, priority reason, evidence/finding IDs, prerequisites and verification criteria |
| `Critique` | Unsupported finding IDs, contradictions, missing checks, proposed correction, outcome |
| `ReportRevision` | Identity/input revision, findings, plan, coverage, limitations, stop reason, critique state and evidence hash |
| `ReviewAction` | Exact report revision, actor, accept/edit/request-follow-up decision, changes and reason |
| `Export` | Immutable reviewed report revision, source manifest/hash, reviewer, format, partial/completeness labels |

Separate completeness: `complete_for_query`, `truncated`, `drift_detected`, `unknown`. Success does not itself establish current physical condition. `no_records` requires a successful complete scoped query; source outage cannot map to it. `identity_conflict` is a quality flag that forces affected completeness unknown.

## Property identity and joins

HPD building ID, BIN, and BBL identify different entities. Store them as strings; preserve leading zeros, original values, and the normalized form. A BIN identifies a building; a BBL identifies a tax lot that may contain multiple buildings. Record the scope of every row. Never silently apply all parcel rows to the selected building.

For a valid NYC borough/block/lot triple, derive BBL as one borough digit, five block digits, and four lot digits. Validate borough 1–5, numeric range and non-placeholder values before deriving it. A sample confirmed building `375411` has borough `3`, block `3031`, lot `15`, giving `3030310015`. Compare any supplied BBL rather than overwriting it. Registry mappings must handle `buildingid` versus `building_id` explicitly.

Resolve exact official identifiers first. Address matching supplies candidates, with borough and house-number semantics preserved, including Queens hyphens, ranges, rear/front units, and aliases. Ambiguous or conflicting identity requires user selection; no arbitrary highest-score match. User selection cannot suppress source identity contradictions. Do not treat inactive or zero-valued sample rows as valid matches.

Current resolver supports exact official address forms (including FRONT/REAR) and optional BIN/BBL, not a comprehensive alias/geocoding service. All candidates require explicit confirmation. Over 20 candidates requires a more precise identifier. DOB violation queries prefer confirmed BIN even when historical parcel fields differ; only missing-BIN rows fall back to current parcel scope. DOB query lot padding is five digits, distinct from BBL's four-digit lot component. Historical parcel differences stay flagged. See [actual query regression](validation-2026-10-15.md).

## Source status and temporal interpretation

| Source pattern | Required interpretation |
| --- | --- |
| HPD `violationstatus=Open` | Recorded open status, qualified by retrieval time and detailed current status |
| HPD `violationstatus=Close` | Historical closed record; no assertion of present physical correction |
| Complaint status `CLOSE` | Source complaint status; preserve problem status and disposition separately |
| Program status says discharged | Historical participation with recorded discharge; not current active enrollment |
| DOB category active but disposition says deleted/test | Conflict/invalid-record flag; no unqualified active violation finding |
| Vacate rescind date earlier than effective date | Temporal conflict; preserve both raw fields and require clarification |
| Unknown status code or missing field | Unknown interpretation; preserve raw data and mark affected coverage partial |

Source dates occur in several formats, including ISO timestamps, `YYYYMMDD`, and `MM/DD/YYYY`. Use source-specific parsers and retain raw values. Treat dates without offsets as source-local/date-only values, not automatically UTC instants. Use UTC for application retrieval/events. Applicable NYC local time uses `America/New_York`, including daylight-saving transitions.

DOB ECB hearing, certification, payment, and overall status are separate dimensions. Do not infer that a paid balance closes a violation, or that an open balance is a legally enforceable debt. Description text may quote historical law and is not a current-rule authority. Any legal-rule explanation requires a pinned current official rule source and separate applicability review.

## Citation and claim validation

1. Validate tool arguments against the registry, confirmed property revision, allowed fields, and remaining budgets.
2. Validate upstream result shape, identity, row keys, pagination/completeness, and field mappings; retain invalid rows with quality flags outside verified findings.
3. Resolve every generated evidence reference to a snapshot available to this run and exact row/field values. Reject invented IDs, swapped snapshots, and mismatched properties.
4. Validate claimed counts against deterministic deduplication with source-specific keys. A complaint can have multiple problems; count complaints and problems separately. Do not count the same notice twice through repeated pages.
5. Validate status/time language, source type, and completeness. Block blanket “clear”, “safe”, “no issues”, and similar conclusions unsupported by the checked records.
6. Ask the critic to assess entailment and proposed follow-ups. Exact-value matching proves provenance, not the correctness of all prose interpretations.
7. Save a validated report revision. Review edits require revalidation of material claims; approval applies to an exact revision, never a mutable case.

Findings distinguish `recorded_fact`, `interpretation` and `conflict`; follow-ups are separate `PlanTask` objects. Priorities include a reason, with source severity retained separately. Exact citation values preserve whitespace: ordinary text stripping would corrupt evidence equality. A captured `buildings` identity row has its own snapshot and is citable. No fabricated repair amounts, penalties, legal deadlines or numeric confidence probabilities are supported.

## Review, conversation, and export

Conversation messages and report revisions share a case and selected identity. Follow-ups always retain that identity; changing property requires a new case. There is no automatic new-address detector/linker. Default follow-ups reuse pinned evidence with acquisition time. Refresh creates new snapshots and history; automatic semantic diffs are deferred.

Exports contain source coverage, retrieval dates, unresolved flags, critique state, and reviewer decisions. A reviewer can export a qualified partial pack but cannot remove its machine-determined coverage gaps. Analyst edits may add explicitly attributed notes; they do not mutate official source records. Unknown/cancelled/failed stages remain visible.

Review notes use optimistic revision checks. Material draft edits are revalidated and create a new report ID with `parent_report_id`; old content is preserved, the new critique becomes `not_assessed_after_edit`, and the edited pack remains partial. An unreviewed report cannot export; partial exports require explicit limit acknowledgment. Exports pin an immutable JSON report snapshot. Current validators prove provenance and reject selected unsafe phrasings, not general natural-language entailment; human review remains necessary.

Initial formats: Markdown and JSON, plus a printable HTML view. PDF generation is a later feature requiring its own rendering tests. Model-supplied URLs never become trusted evidence links; the server resolves catalog and record links from approved source definitions. When no reliable row permalink exists, cite the catalog, query scope, row key, and captured snapshot fields.

## Audit events

Persist safe events for queued/claimed jobs, identity resolution/selection, action dispatch/result, validation failures, model attempts, reflection changes, critique, limits, cancellation, checkpoint recovery, review, export, and refresh. Include run/step/attempt IDs, stage, outcome, reason code, duration, remaining/cumulative budget, source/schema/prompt versions, and evidence hash.

Provider timeout/capacity/parse failures produce both a stage event and a run outcome. The top-level run error is not a replacement for validation history. Store only bounded safe error summaries in logs. Raw provider stderr, source apartment details, acquisition strategy, and case conversations belong only in authorized storage if needed, not routine telemetry.

Source data and generated HTML are untrusted input. Escape display/export text, validate destination hosts/redirects, and prevent source prose from altering tools, budgets, or instructions. Permission checks apply to cases, snapshots, report revisions, and exports consistently.
