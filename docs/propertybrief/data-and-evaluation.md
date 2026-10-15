# Actual data and evaluation plan

Status: functional validation implemented over a frozen 12-building, 3,346-record official-source corpus. Actual Codex and live HTTP runs are recorded in [15 October validation](validation-2026-10-15.md). Independent labels, the 60-case quality evaluation and commercial baselines below remain planned; no production-quality pass is claimed.

## Data acquisition before feature work

1. Capture the ten [source registry](research-and-sources.md#source-registry) definitions and metadata. Verify keys, filters, required fields, pagination order and official status dictionaries. Avoid unknown implicit source defaults.
2. Select a small feasibility cohort of 12 actual buildings spanning multiple boroughs and record patterns. Include a multi-building lot, unusual address, open/closed records, enforcement participation, conflicts, and a sparse-data case when available. Record sampling queries; absence of a desired case is a gap, not permission to invent one.
3. Fetch property-scoped records through bounded ordered queries. Save raw responses, request/filter fingerprint, dataset metadata, retrieval interval, pagination trace, row counts, completeness flags, and SHA-256 hashes. Keep the original fields and dates.
4. Verify expected joins independently. Cross-check selected record IDs/statuses in official agency portals where practical, recording access time and disagreements rather than overwriting the captured snapshot.
5. Publish an immutable corpus manifest only after all files and hashes are verified. A partial acquisition remains explicitly partial. Do not call a sequence of live pages an atomic snapshot; capture update metadata before/after and record possible drift.

Live changes after freezing do not invalidate an internally consistent snapshot evaluation. Refresh evaluation is a separate task comparing revisions. Current-status datasets do not reconstruct historical status merely because they contain old issue dates. As-of historical claims require actual archived snapshots, which are not yet acquired.

Logical data layout (raw captures/evaluation stores exist under ignored `var/`; gold labels/splits below are still planned):

```text
data/propertybrief/
  manifests/       source registry, corpus manifests, splits and attribution
  gold/            independently reviewed finding/coverage/identity labels
  adversarial/     mutation specifications and fixture provenance
var/propertybrief-corpus/
  raw/             ignored original API payloads and metadata
  normalized/      derived records with original values retained
var/propertybrief-evaluation/
  <session>/       isolated database, reports, traces and scored metrics
```

Initially keep building-specific raw records and labels ignored until reuse/publication requirements are reviewed. Never commit tenant/owner contact collections unnecessarily. Compact manifests can reference public dataset IDs and hashes; review building-specific examples before publication.

## Proposed evaluation cohort and gold labels

After feasibility, target 60 actual-building cases: 20 development, 10 calibration, and 30 held-out. Stratify across boroughs and material record patterns. Group by building and parcel; where relevant also group related properties with shared records, so nearly identical evidence does not leak across splits. Publish case counts, sampling method, coverage gaps, and source sizes. This is a curated challenge set, not a representative sample of all NYC buildings.

Two independent reviewers build expected findings from the frozen records, resolve disagreements, and record adjudication. If only one reviewer is available, label that limitation and keep the production-quality gate open. The implementation/model output cannot define its own gold answers.

Gold fields: identity candidates and confirmed scope; required source coverage; source row keys and statuses; material findings with supporting fields; conflicting records; expected qualifications; acceptable follow-up purposes; prohibited assertions. Multiple reasonable task plans are allowed. Reviewers judge whether proposed checks address the evidence gaps, not whether wording matches a template.

Known initial seeds: closed HPD violation `10081311`, building `375411`; DOB test row `24174`; vacate order `260021` with inconsistent dates. Acquire and hash their original payloads before using them as durable fixtures. These seeds alone do not supply enough positive/negative cases for evaluation.

## Baselines and metrics

Compare manual official-record research, a deterministic source checklist/report, one-shot generation using the same evidence, and the adaptive agent. Hold evidence access, task scope, and call/time budgets explicit. Measure benefit from planning and critique separately through development-set ablations; never tune prompts on held-out outcomes.

| Metric | Definition | Proposed release target |
| --- | --- | --- |
| Property identity correctness | Correct selected building/parcel scope per adjudicated case | 100%; ambiguous inputs must clarify |
| Material finding recall | Gold material findings recovered / all gold material findings | At least 95% overall; publish per-category counts |
| Finding precision | Supported material findings / all material findings presented | At least 98%; no wrong-property factual assertion |
| Provenance integrity | References resolving to exact supplied row/fields | 100% |
| Coverage honesty | Unavailable/truncated/unknown checks shown accurately | 100% deterministic tests and held-out reports |
| Status interpretation | Correct current/historical/unknown interpretation | At least 98%; no critical false reassurance |
| Follow-up usefulness | Reviewer-approved actionable tasks / tasks assessed | At least 90%, rubric and denominators published |
| Critique performance | Unsupported claims detected and supported claims incorrectly challenged | Publish precision/recall; select threshold on calibration only |
| Graceful degradation | Completed observations survive injected failures and export gaps | 100% required failure scenarios |
| Budget compliance | No run exceeds hard counters or starts work past its deadline | 100% deterministic tests; measure actual wall-clock overrun |
| Analyst effort | Paired active review/research time to accepted report | Target at least 30% median reduction on ten paired tasks |

Targets are provisional and unmeasured. Report raw numerators/denominators and uncertainty, especially with only 30 held-out cases. One critical wrong-building conclusion or a false “no issues” conclusion blocks release regardless of averages. Missing labels do not count as passes. Source fact accuracy and physical building condition are different outcomes; public records can validate only the former directly.

Report queued time, end-to-end latency, model/tool/HTTP attempts, failure rates, memory, CPU, and disk growth. No SLA exists yet. If the agent fails to improve over simpler baselines, narrow or revise the product claim rather than hiding the result.

## End-to-end acceptance matrix

| Scenario | Data / setup | Expected observable behavior |
| --- | --- | --- |
| Ordinary real building | Complete acquired records | Correct identity, required coverage, cited findings and reviewed export |
| Historical closed violation | Actual closed-record case | Historical wording, no unqualified current-condition claim |
| Complaint plus problems | Actual complaint/problem rows | Distinct counts and source statuses; no complaint-to-violation promotion |
| Repeated water records | Actual qualifying case selected during acquisition | Appropriate adaptive follow-up; action trace explains evidence relationship |
| Program discharged | Actual program rows | Historical/current participation distinguished |
| DOB placeholder | Actual test-record sample | Invalid/conflicting source flag; no active-property finding |
| Contradictory order dates | Actual vacate sample | Conflict visible; no inferred current legal status |
| Ambiguous address | Actual candidate addresses | Candidate selection required before building findings |
| Multi-building parcel | Actual lot/buildings | Parcel-level rows distinguished from selected-building rows |
| Empty source | Complete exact-property query | Scoped zero-result observation, no blanket clearance |
| Pagination/cap | Actual records and bounded test transport | Counts/keys correct; caps and drift remain visible |
| Source 429/outage | Fault injected around real frozen payloads | Bounded retries, unavailable source, useful partial result |
| Later model timeout | Failure after several saved real-source observations | Earlier preview survives; stage failure and terminal reason logged |
| Critique unavailable | Real evidence with provider failure | Critique not assessed; qualified reviewable pack retained |
| Repeated/malformed decisions | Scripted provider faults | Bounded correction then partial; no budget reset |
| Worker restart/cancel | Saved checkpoints on a real case | No regenerated saved evidence, lease fencing, explicit stop/resume history |
| Source injection text | Clearly labelled mutation of a real payload | Text cannot alter tools, identity, budgets or instructions |
| Review edit/export/reload | Browser using real case | Revision checks, revalidation, durable gaps and evidence links |
| Live source refresh | Two live acquisitions of same property | New revision, source timing and meaningful change summary |
| Windows/tunnel | Target laptop and protected hostname | Service identity, auth, restart, backup/restore and measured resources |

Mutated/fault-injected payloads validate robustness; they are never counted as naturally occurring data-quality cases or live model success. Identify deterministic fixtures, frozen actual-data runs, live-source runs, and human judgments separately in every report.

## Reproduction and evidence package

Each evaluation session pins commit, platform, registry/adapter versions, source hashes and acquisition interval, split/label versions, contract/prompt versions, budget policy, provider identity when available, and reviewer rubric. Save reports, safe action/critique traces, source failures and score computation. Preserve unsuccessful sessions.

Implemented reproduction commands are in [the data README](../../data/propertybrief/README.md) and [operations](operations.md). Acquisition and evaluation refuse existing destinations. `resume_propertybrief_validation.py` explicitly grants one additional bounded attempt without resetting cumulative counters. The frozen corpus is a development cohort, not held-out gold.
